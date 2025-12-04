import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2

from ..main import main

# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

if os.getenv("RUNNING_IN_DOCKER"):
    pstgr_url = "postgres"
else:
    pstgr_url = os.getenv("POSTGRES_HOST")
pstgr_user = os.getenv("POSTGRES_USER")
pstgr_pass = os.getenv("POSTGRES_PASSWORD")
pstgr_db_files = os.getenv("POSTGRES_DB_FILES", "files")
if not pstgr_url or not pstgr_user or not pstgr_pass:
    raise HTTPException(status_code=500, detail="Database credentials are not set in environment variables.")

# connect to the database and get the files with environment-based SSL
if ENVIRONMENT == "prod":
    file_conn = psycopg2.connect(
        host=pstgr_url,
        database=pstgr_db_files,
        user=pstgr_user,
        password=pstgr_pass,
        sslmode='require'
    )
else:
    file_conn = psycopg2.connect(
        host=pstgr_url,
        database=pstgr_db_files,
        user=pstgr_user,
        password=pstgr_pass
    )

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_analyzer(id: int):
    """Run the analyzer on the config."""
    os.environ["CONFIG_ROOT"] = f"/tmp/{id}"
    main(f"/tmp/{id}/dump.txt")

def get_files_from_db(id: int, temp_dir: str):
    """Get the config files from the database."""
    cursor = file_conn.cursor()
    cursor.execute("SELECT path, content FROM files WHERE config_id = %s;", (id,))
    files = cursor.fetchall()
    if files:
        for file in files:
            file_path = file[0]
            file_content = file[1]
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(file_content)
    else:
        raise HTTPException(status_code=500, detail="Failed to get config files from database.")

def get_dump_from_db(id: int, dump_path: str):
    """Get the config dump from the database."""
    cursor = file_conn.cursor()
    cursor.execute("SELECT dump FROM dumps WHERE config_id = %s;", (id,))
    dump = cursor.fetchone()
    if dump:
        with open(dump_path, "w") as f:
            f.write(dump[0])
    else:
        raise HTTPException(status_code=500, detail="Failed to get config dump from database.")

def clean_directory(directory: str):
    """Clean the temporary directory."""
    if os.path.exists(directory):
        shutil.rmtree(directory)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.post("/process_configs/{id}")
async def process_config(id: int):
    """
    Process uploaded zip file with Apache configuration and return config dump.
    """
    print(f"Processing config with ID: {id}")
    print(f"Cleaning temporary directory")
    clean_directory(f"/tmp/{id}")
    print(f"Loading files")
    get_files_from_db(id, f"/tmp/{id}")
    print(f"Getting dump from database")
    get_dump_from_db(id, f"/tmp/{id}/dump.txt")
    print(f"Running analyzer")
    run_analyzer(id)
    return {"status": "success"}