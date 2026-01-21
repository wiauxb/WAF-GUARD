"""
Client script to trigger the log cleanup endpoint and extract the downloaded zip.
"""

import argparse
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

import requests


def get_config_id(host: str, port: int) -> str | None:
    """Fetch the current config ID from the API."""
    url = f"http://{host}:{port}/config/id"
    response = requests.get(url)
    response.raise_for_status()
    return response.json().get("config_id")


def cleanup_logs(host: str, port: int, log_path: str, extract_to: str | None = None, verbose: bool = False) -> None:
    """
    Call the log cleanup endpoint and extract the returned zip file.

    Args:
        host: API server host.
        port: API server port.
        log_path: Path to the log file or directory to clean up on the server.
        extract_to: Local directory where the zip contents will be extracted.
                    If None, defaults to <config_id>_<date>.
        verbose: If True, display additional information including config ID.
    """
    config_id = get_config_id(host, port)

    if verbose:
        print(f"Config ID: {config_id}")

    if extract_to is None:
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{config_id or 'unknown'}_{date_str}"
        extract_to = folder_name

    url = f"http://{host}:{port}/logs/cleanup"
    params = {"log_path": log_path}

    response = requests.post(url, params=params)
    response.raise_for_status()

    extract_path = Path(extract_to)
    extract_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(BytesIO(response.content), "r") as zf:
        zf.extractall(extract_path)

    print(f"Logs extracted to: {extract_path.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trigger log cleanup endpoint and extract the backup zip."
    )
    parser.add_argument("--host", default="localhost", help="API server host (default: localhost)")
    parser.add_argument("--port", type=int, default=9000, help="API server port (default: 9000)")
    parser.add_argument("--log-path", required=True, help="Path to the log file or directory to clean up")
    parser.add_argument("--extract-to", default=None, help="Local directory to extract the logs to (default: <config_id>_<date>)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Display additional info including config ID")

    args = parser.parse_args()

    try:
        cleanup_logs(args.host, args.port, args.log_path, args.extract_to, args.verbose)
    except requests.HTTPError as e:
        print(f"Error: {e.response.status_code} - {e.response.text}")
        raise SystemExit(1)
    except requests.ConnectionError:
        print(f"Error: Could not connect to {args.host}:{args.port}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
