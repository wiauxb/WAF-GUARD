import sys
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import shutil
import tempfile
import zipfile
import os
import subprocess
import gzip

app = FastAPI()


@app.on_event("startup")
def snapshot_conf_baseline():
    """Take the pristine snapshot before this container can serve its first upload."""
    try:
        _ensure_baseline()
    except Exception as e:                      # never block startup over this
        print(f"WARNING: could not snapshot httpd conf baseline: {e}")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def check_zip_file(filename: str):
    """Check if the file is a zip file."""
    if not filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a zip file")

async def save_uploaded_file(file: UploadFile, temp_dir: str) -> str:
    """Save uploaded file to a temporary directory."""
    temp_zip_path = os.path.join(temp_dir,file.filename)
    with open(temp_zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        # buffer.write(file.file.read())
    return temp_zip_path

async def extract_zip_file(temp_zip_path: str, temp_dir: str) -> str:
    """Extract zip file to a directory."""
    try:
        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        return extract_dir
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract zip file: {str(e)}")

HTTPD_CONF = "/etc/httpd/conf"
# Pristine copy of what the IMAGE ships, taken before the first upload ever lands.
BASELINE = "/opt/httpd-conf-baseline"


def _ensure_baseline():
    """
    Snapshot the image's own conf tree, once, before any upload has touched it.

    Only safe on a pristine container -- if this ran after an upload it would bake that
    upload in as the baseline. Startup is the one moment that is guaranteed pristine, so
    it is called from the lifespan hook rather than lazily from the upload path.
    """
    if os.path.exists(BASELINE):
        return
    shutil.copytree(HTTPD_CONF, BASELINE)
    print(f"Snapshotted pristine httpd conf baseline "
          f"({sum(len(f) for _, _, f in os.walk(BASELINE))} files) -> {BASELINE}")


async def copy_config_files(extract_dir: str):
    """
    Replace the Apache conf directory with this upload's contents.

    RESET FIRST, then copy. This used to be a bare copytree(dirs_exist_ok=True), which
    MERGES: every upload layered on top of whatever the previous one left behind, and
    nothing was ever removed. That is not cosmetic -- httpd.conf carries globs such as
    `IncludeOptional conf/company/apps/*.conf`, so a leftover file from configuration A
    gets swept into configuration B's dump. The parser then reads a `# In file:` path that
    is absent from B's archive and the parse dies. Exactly that happened: a stale
    company/apps/macros.conf produced a phantom `ProxyTimeout 30` in a later config.

    Restoring the image baseline rather than emptying the directory keeps files the image
    provides and no archive supplies (machine/, ssl/, magic, ...).
    """
    try:
        conf_dir = os.path.join(extract_dir, "conf")
        source_dir = conf_dir if os.path.isdir(conf_dir) else extract_dir

        if os.path.isdir(BASELINE):
            shutil.rmtree(HTTPD_CONF, ignore_errors=True)
            shutil.copytree(BASELINE, HTTPD_CONF)
        else:
            # No snapshot (older container that started before this existed). Copying on
            # top is the old behaviour -- wrong, but better than deleting a tree we have
            # no way to restore.
            print("WARNING: no conf baseline snapshot; falling back to a merge copy. "
                  "Restart this container to enable clean replacement.")

        for item in os.listdir(source_dir):
            src_path = os.path.join(source_dir, item)
            dst_path = os.path.join(HTTPD_CONF, item)
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dst_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to copy config files: {str(e)}")

async def run_apache_config_dump():
    """
    Run httpd command and compress output with minimal memory usage.

    Uses subprocess.run() but compresses immediately with fast compression level.
    """
    try:
        print("Starting httpd dump generation...")

        # Run httpd command - it will buffer output, but we compress immediately
        result = subprocess.run(
            ["httpd", "-t", "-DDUMP_CONFIG"],
            capture_output=True,
            text=False,  # Binary mode
            check=False  # Don't raise exception, we'll check manually
        )

        print(f"httpd completed with return code: {result.returncode}")

        # Check for errors
        if result.returncode != 0:
            error_msg = result.stderr.decode('utf-8') if result.stderr else "Unknown error"
            print(f"ERROR: httpd failed: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Apache config test failed: {error_msg}"
            )

        # Compress immediately with fast compression (level 1)
        print(f"Compressing output ({len(result.stdout)} bytes)...")
        compressed_dump = gzip.compress(result.stdout, compresslevel=1)

        print(f"Generated compressed dump: {len(compressed_dump)} bytes")
        print(f"Compression ratio: {(1 - len(compressed_dump)/len(result.stdout))*100:.1f}%")

        return compressed_dump

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate dump: {str(e)}")

@app.post("/get_dump")
async def get_dump(file: UploadFile = File(...)):
    """
    Process uploaded zip file with Apache configuration and return gzip-compressed config dump.
    Returns a downloadable .gz file instead of JSON to improve performance for large dumps.
    Memory optimized: Streams httpd output directly to gzip compression in 1MB chunks.
    """
    print("getting dump")
    await check_zip_file(file.filename)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_zip_path = await save_uploaded_file(file, temp_dir)
        extract_dir = await extract_zip_file(temp_zip_path, temp_dir)
        await copy_config_files(extract_dir)

        # Stream and compress dump (no memory spike!)
        compressed_dump = await run_apache_config_dump()

        return Response(
            content=compressed_dump,
            media_type="application/gzip",
            headers={
                "Content-Disposition": "attachment; filename=apache_config_dump.txt.gz"
            }
        )

@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    return {"status": "ok"}

@app.get("/")
async def root():
    """
    Root endpoint.
    """
    return {"message": "Welcome to the Apache Config Dump API. Use /get_dump to upload a zip file."}
