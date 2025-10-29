import sys
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import tempfile
import zipfile
import os
import subprocess

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def check_zip_file(filename: str):
    """Check if the file is a zip file."""
    if not filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a zip file")

def save_uploaded_file(file: UploadFile, temp_dir: str) -> str:
    """Save uploaded file to a temporary directory."""
    temp_zip_path = os.path.join(temp_dir,file.filename)
    with open(temp_zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        # buffer.write(file.file.read())
    return temp_zip_path

def extract_zip_file(temp_zip_path: str, temp_dir: str) -> str:
    """Extract zip file to a directory."""
    try:
        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        return extract_dir
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract zip file: {str(e)}")

def copy_config_files(extract_dir: str):
    """Copy extracted files to Apache conf directory."""
    try:
        conf_dir = os.path.join(extract_dir, "conf")
        source_dir = conf_dir if os.path.isdir(conf_dir) else extract_dir
        
        for item in os.listdir(source_dir):
            src_path = os.path.join(source_dir, item)
            dst_path = os.path.join("/etc/httpd/conf", item)
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dst_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to copy config files: {str(e)}")

def run_apache_config_dump():
    """Run the httpd command to get the config dump."""
    try:
        result = subprocess.run(
            ["httpd", "-t", "-DDUMP_CONFIG"],
            capture_output=True, 
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Apache config test failed: {e.stderr}")

@app.post("/get_dump")
async def get_dump(file: UploadFile = File(...)):
    """
    Process uploaded zip file with Apache configuration and return config dump.
    """
    check_zip_file(file.filename)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_zip_path = save_uploaded_file(file, temp_dir)
        extract_dir = extract_zip_file(temp_zip_path, temp_dir)
        copy_config_files(extract_dir)
        dump = run_apache_config_dump()
        return {"dump": dump}

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
