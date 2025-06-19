from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
import requests

from ..db.connections import files_conn, WAF_URL
from ..utils.file_utils import extract_config

router = APIRouter(tags=["Configuration Storage and Parsing"])


@router.post("/store_config")
async def store_config(file: UploadFile = File(...), config_nickname: str = Form(...)):
    if not config_nickname:
        return {"error": "Invalid input"}
    
    # Store the config in PostgreSQL
    cursor = files_conn.cursor()
    cursor.execute("""
        INSERT INTO configs (nickname)
        VALUES (%s)
        RETURNING id
    """, (config_nickname, ))
    response = cursor.fetchone()
    if response is None:
        return {"error": "Failed to store config"}
    config_id = response[0]
    files_conn.commit()

    config_path = extract_config(file.file, config_nickname)

    # Process each file in the extracted directory
    for file_path in config_path.glob('**/*'):
        if file_path.is_file():
            # Get the relative path from the config_path
            relative_path = str(file_path.relative_to(config_path))
            
            # Read file content as binary
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Insert file info into the database
            cursor.execute("""
                INSERT INTO files (config_id, path, content)
                VALUES (%s, %s, %s)
            """, (config_id, relative_path, file_content))
    
    # Commit the transaction
    files_conn.commit()
    
    return {"config_id": config_id}


@router.post("/get_dump")
async def get_dump(file: UploadFile = File(...)):
    response = requests.post(f"{WAF_URL}/get_dump", files={"file": (file.filename, file.file, file.content_type)})
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to get config dump" + response.text)
    else:
        return response.json()


@router.post("/store_dump")
async def store_dump(request: Request):
    data = await request.json()
    config_id = data.get("config_id")
    dump = data.get("dump")

    # Store the config in PostgreSQL
    cursor = files_conn.cursor()
    cursor.execute("""
        INSERT INTO dumps (config_id, dump)
        VALUES (%s, %s)
    """, (config_id, dump))
    files_conn.commit()
    return {"status": "success"}


@router.get("/parsing_progress/{task_id}")
async def get_parsing_progress(task_id: str):
    """Get the progress of a parsing task."""
    cursor = files_conn.cursor()
    cursor.execute(
        "SELECT status, progress FROM parsing_tasks WHERE task_id = %s",
        (task_id,)
    )
    result = cursor.fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status, progress = result
    return {
        "task_id": task_id,
        "status": status,
        "progress": progress
    }
