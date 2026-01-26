from config_generator import generate_config
"""
Configuration Sender

Zips the generated config folder and sends it to the ModSecurity WAF container API.
"""

import io
import zipfile
from pathlib import Path

import requests


def zip_config(config_dir: str = "config") -> bytes:
    """
    Create a zip archive of the config directory in memory.

    Args:
        config_dir: Path to the config directory

    Returns:
        bytes: Zip file content
    """
    config_path = Path(config_dir)

    if not config_path.exists():
        raise FileNotFoundError(f"Config directory not found: {config_path}")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in config_path.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(config_path)
                zf.write(file_path, arcname)

    buffer.seek(0)
    return buffer.getvalue()


def send_config(api_url: str = "http://localhost:9000", config_dir: str = "config", config_id: str | None = None) -> dict:
    """
    Zip and send configuration to the WAF container API.

    Args:
        api_url: Base URL of the WAF API
        config_dir: Path to the config directory
        config_id: Optional configuration identifier

    Returns:
        dict: Response from the API
    """
    zip_content = zip_config(config_dir)

    try:
        files = {"file": ("config.zip", zip_content, "application/zip")}
        params = {"config_id": config_id} if config_id else None
        response = requests.post(f"{api_url}/config", files=files, params=params, timeout=30)
    except requests.exceptions.ConnectionError:
        raise Exception(f"Connection failed: Is the API running at {api_url}?")
    except requests.exceptions.Timeout:
        raise Exception(f"Request timed out connecting to {api_url}")

    if response.status_code != 200:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text or f"HTTP {response.status_code}"
        raise Exception(f"Failed: {detail}")

    return response.json()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Send config to WAF container")
    parser.add_argument(
        "--url",
        default="http://localhost:9000",
        help="WAF API URL (default: http://localhost:9000)"
    )
    parser.add_argument(
        "--config",
        default="config",
        help="Config directory path (default: config)"
    )
    parser.add_argument(
        "--config-id",
        default=None,
        help="Optional configuration identifier"
    )

    args = parser.parse_args()
    result = generate_config(
        overwrite=True,
        apps=[],
        crs_version="4.22.0",
        variables={"PORT": 8080, "MODSEC_RULE_ENGINE": "On", "BACKEND": "http://dvwa:80", "MODSEC_AUDIT_LOG_FORMAT":"JSON","MODSEC_AUDIT_LOG_PARTS":"ABCFHKZ"}
    )

    print(f"Sending config from '{args.config}' to {args.url}...")

    try:
        result = send_config(api_url=args.url, config_dir=args.config, config_id=args.config_id)
        print(f"Result: {result['status']}")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
