"""
ModSecurity WAF Configuration API
"""

import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

app = FastAPI(title="ModSecurity WAF API", version="1.0.0")

APACHE_CONF_PATH = Path("/usr/local/apache2/conf")
MODSEC_CONF_PATH = Path("/etc/modsecurity.d")
APACHECTL = "/usr/local/apache2/bin/apachectl"


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
async def upload_config(file: UploadFile = File(...)):
    """
    Upload and apply configuration from a zip file.

    Expected zip structure:
    - apache/     -> copied to /usr/local/apache2/conf/
    - modsecurity/ -> copied to /etc/modsecurity/
    After the files are deployed the handler restarts Apache so the new configuration takes effect.
    """
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

    return {"status": "ok", "apache_restart": "graceful", "restart_output": result.stdout.strip()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)

