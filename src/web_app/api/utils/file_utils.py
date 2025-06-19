import hashlib
import time
import uuid
import zipfile
from pathlib import Path


def extract_config(file, name=None):
    """
    Process the uploaded config archive file.
    This function handles the extraction and parsing of the config files.
    
    Args:
        file: The uploaded file object
        name: Optional name for the config
        
    Returns:
        Path object to the extracted directory
    """
    # Generate unique filename using timestamp and UUID
    if name:
        name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
        unique_filename = f"/tmp/config_{int(time.time())}_{name_hash}.zip"
    else:
        unique_filename = f"/tmp/config_{int(time.time())}_{uuid.uuid4().hex[:8]}.zip"
    
    # Save the uploaded file
    with open(unique_filename, "wb") as f:
        f.write(file.read())
    
    # Extract the zip file
    extract_path = Path(f"/tmp/{Path(unique_filename).stem}")
    with zipfile.ZipFile(unique_filename, "r") as zip_ref:
        extract_path.mkdir(exist_ok=True)
        zip_ref.extractall(extract_path)

    # Delete the zip file after extraction
    Path(unique_filename).unlink()
    
    return Path(extract_path).absolute().resolve()
