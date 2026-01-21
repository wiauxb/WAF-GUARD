"""
ModSecurity WAF Configuration API
"""

import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

app = FastAPI(title="ModSecurity WAF API", version="1.0.0")

ALLOWED_LOG_DIRS = [
    Path("/var/log/apache2"),
    Path("/usr/local/apache2/logs"),
    Path("/var/log/modsecurity"),
]

APACHE_CONF_PATH = Path("/usr/local/apache2/conf")
MODSEC_CONF_PATH = Path("/etc/modsecurity.d")
APACHECTL = "/usr/local/apache2/bin/apachectl"

# Global state for the current configuration ID
current_config_id: str | None = None


def _restart_apache() -> subprocess.CompletedProcess[str]:
    """Gracefully restart Apache so new configs load.

    Returns:
        subprocess.CompletedProcess: Completed restart command for logging or inspection.
    """
    return subprocess.run(
        [APACHECTL, "-k", "graceful"],
        check=True,
        capture_output=True,
        text=True
    )


@app.post("/config")
async def upload_config(file: UploadFile = File(...), config_id: str | None = None):
    """
    Upload and apply configuration from a zip file.

    Args:
        file: The zip file containing the configuration.
        config_id: Optional identifier for this configuration, available globally to all API functions.

    Expected zip structure:
    - apache/     -> copied to /usr/local/apache2/conf/
    - modsecurity/ -> copied to /etc/modsecurity/
    After the files are deployed the handler restarts Apache so the new configuration takes effect.
    """
    global current_config_id

    if config_id is not None:
        current_config_id = config_id

    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a .zip archive")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        zip_path = tmp_path / "config.zip"

        # Save uploaded file
        content = await file.read()
        zip_path.write_bytes(content)

        # Extract zip
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_path)

        # Copy apache config
        apache_src = tmp_path / "apache"
        if apache_src.exists():
            for item in apache_src.rglob("*"):
                if item.is_file():
                    dest = APACHE_CONF_PATH / item.relative_to(apache_src)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)

        # Copy modsecurity config
        modsec_src = tmp_path / "modsecurity"
        if modsec_src.exists():
            for item in modsec_src.rglob("*"):
                if item.is_file():
                    dest = MODSEC_CONF_PATH / item.relative_to(modsec_src)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)
    
    try:
        result = _restart_apache()
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() if exc.stderr else exc.stdout.strip()
        raise HTTPException(
            status_code=500,
            detail=f"Apache restart failed: {detail or exc.returncode}"
        )

    return {
        "status": "ok",
        "config_id": current_config_id,
        "apache_restart": "graceful",
        "restart_output": result.stdout.strip()
    }


@app.get("/config/id")
async def get_config_id():
    """Return the current configuration ID."""
    return {"config_id": current_config_id}


def _is_allowed_log_path(log_path: Path) -> bool:
    """Check if the log path is within allowed directories."""
    resolved = log_path.resolve()
    return any(
        resolved == allowed_dir or allowed_dir in resolved.parents
        for allowed_dir in ALLOWED_LOG_DIRS
    )


@app.post("/logs/cleanup")
async def cleanup_logs(log_path: str):
    """
    Clean up log files and return them as a zip archive.

    Args:
        log_path: Path to the log file or directory to clean up.

    Returns:
        A zip file containing the log file(s) before deletion.
    """
    path = Path(log_path)

    if not _is_allowed_log_path(path):
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Path must be within allowed log directories: {[str(d) for d in ALLOWED_LOG_DIRS]}"
        )

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Log path not found: {log_path}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        zip_path = tmp_path / "logs_backup.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if path.is_file():
                zf.write(path, path.name)
            elif path.is_dir():
                for item in path.rglob("*"):
                    if item.is_file():
                        zf.write(item, item.relative_to(path))

        # Copy zip to a persistent location before cleanup
        output_zip = Path(tempfile.gettempdir()) / f"logs_backup_{path.name}.zip"
        shutil.copy2(zip_path, output_zip)

    # Clean up the original log file(s)
    if path.is_file():
        path.unlink()
    elif path.is_dir():
        for item in path.rglob("*"):
            if item.is_file():
                item.unlink()

    # To auto-delete the temp zip after download, use:
    # from starlette.background import BackgroundTask
    # background=BackgroundTask(output_zip.unlink)
    return FileResponse(
        path=output_zip,
        filename="logs_backup.zip",
        media_type="application/zip",
        background=None
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)

