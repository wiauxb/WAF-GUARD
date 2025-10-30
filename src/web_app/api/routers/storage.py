import json
import os
from pathlib import Path
import traceback
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
import requests
from ..models.models import ConfigContent, FileContent
from ..db.connections import files_conn, WAF_URL
from ..utils.file_utils import extract_config

router = APIRouter(tags=["Configuration Storage and Analysis"])
API_URL = os.getenv("API_URL", "http://fastapi:8000")

@router.post("/store_config")
async def store_config(file: UploadFile = File(...), config_nickname: str = Form(...)):
    if not config_nickname:
        return {"error": "Invalid input"}
    try:
    
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

        config_path = extract_config(file.file, config_id=config_id, name=config_nickname)

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
        #make request with file uploaded to /get_dump endpoint
        response = requests.post(f"{API_URL}/get_dump", files={"file": (file.filename, file.file, file.content_type)})
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to get config dump" + response.text)
        dump = response.json().get("dump")
        response = requests.post(f"{API_URL}/store_dump", json={"config_id": config_id, "dump": dump})
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to store config dump" + response.text)
        return {"config_id": config_id}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to store config: {str(e)}")

# display config tree, if file, return content
@router.post("/config_tree/{config_id}")
async def config_tree(config_id: int, path: str = Form(...)) -> List[ConfigContent]:
    try:
        info_path = f"/tmp/config_{config_id}_info.json"
        with open(info_path, "r") as info_file:
            config_info = json.load(info_file)
        config_path = config_info["path"]
        if not config_path:
            raise HTTPException(status_code=404, detail="Config not found")
        
        #list dir and files in config_path
        full_path = Path(config_path) / path
        if not full_path.exists():
            raise HTTPException(status_code=500, detail="Path doesn't exist")
        file_content = ""
        config_contents = []
        if full_path.is_file():
            with open(full_path, "r") as file:
                file_content = file.read()
            config_contents.append(ConfigContent(filename=path, is_folder=False, file_content=file_content))
        else:
            for item in full_path.iterdir():
                config_contents.append(ConfigContent(filename=item.name, is_folder=item.is_dir()))
        return config_contents
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get config tree: {str(e)}")
    

#save updated file in config files
#add path and file content in Form data
@router.post("/update_config/{config_id}")
async def update_config(config_id: int, fileContent: FileContent):
    try:
        cursor = files_conn.cursor()
        cursor.execute("""
            UPDATE files
            SET content = %s
            WHERE config_id = %s AND path = %s
        """, (fileContent.content.encode(), config_id, fileContent.path))
        files_conn.commit()

        info_path = f"/tmp/config_{config_id}_info.json"
        with open(info_path, "r") as info_file:
            config_info = json.load(info_file)
        config_path = config_info["path"]
        if not config_path:
            raise HTTPException(status_code=404, detail="Config not found")
        full_path = Path(config_path) / fileContent.path
        with open(full_path, "w") as file:
            file.write(fileContent.content)
        return {"status": "success"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to update config file: {str(e)}")



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


@router.get("/analysis_progress/{task_id}")
async def get_analysis_progress(task_id: str):
    """Get the progress of an analysis task."""
    cursor = files_conn.cursor()
    cursor.execute(
        "SELECT status, progress FROM analysis_tasks WHERE task_id = %s",
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
