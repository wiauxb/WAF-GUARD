import hashlib
import time
import uuid
import zipfile
from pathlib import Path


def extract_config(file, name=None):
    """
    Extract an uploaded config archive to a temporary directory.

    Args:
        file: The uploaded file object
        name: Optional name for the config (used to generate a stable temp path)

    Returns:
        Path object to the extracted directory (caller is responsible for cleanup)
    """
    try:
        if name:
            name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
            unique_filename = f"/tmp/config_{int(time.time())}_{name_hash}.zip"
        else:
            unique_filename = f"/tmp/config_{int(time.time())}_{uuid.uuid4().hex[:8]}.zip"

        with open(unique_filename, "wb") as f:
            f.write(file.read())

        extract_path = Path(f"/tmp/{Path(unique_filename).stem}")
        with zipfile.ZipFile(unique_filename, "r") as zip_ref:
            extract_path.mkdir(exist_ok=True)
            zip_ref.extractall(extract_path)

        Path(unique_filename).unlink()

        return Path(extract_path).absolute().resolve()
    except Exception as e:
        raise Exception(f"Failed to process config archive: {str(e)}")
