import io
import os
import asyncio
import gzip
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
WAF_URL = os.getenv("WAF_URL", "http://waf:8000")
ANALYZER_URL = os.getenv("ANALYZER_URL", "http://analyzer:8000")

@router.post("/store_config")
async def store_config(file: UploadFile = File(...), config_nickname: str = Form(...)):
    if not config_nickname:
        return {"error": "Invalid input"}
    try:
    
        # Store the config in PostgreSQL
        cursor = files_conn.cursor()
        cursor.execute("""
            INSERT INTO public.configs (nickname)
            VALUES (%s)
            RETURNING id
        """, (config_nickname, ))
        response = cursor.fetchone()
        if response is None:
            return {"error": "Failed to config entry in db"}
        config_id = response[0]
        files_conn.commit()

        config_path = extract_config(file.file, name=config_nickname)

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
                    INSERT INTO public.files (config_id, path, content)
                    VALUES (%s, %s, %s)
                """, (config_id, relative_path, file_content))
        # Commit the transaction
        files_conn.commit()

        # All files are now in the DB — the extracted directory is no longer needed
        import shutil
        shutil.rmtree(config_path, ignore_errors=True)
       
        await file.seek(0)
        response = await get_dump_function(file)
        dump = response.get("dump")
        response = await store_dump_function(config_id, dump)
        print(f"Dump stored in storage: {response}")
        return {"config_id": config_id}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to store config: {str(e)}")
    

async def get_dump_function(file: UploadFile = File(...)):
    try:
        await file.seek(0)

        response = await asyncio.to_thread(
            requests.post,
            f"{WAF_URL}/get_dump",
            files={"file": (file.filename, file.file, file.content_type)},
            timeout=60
        )
        if response.status_code != 200:
            raise ValueError("Failed to get config dump: " + response.text)

        # Decompress the gzip response and decode to string
        decompressed_data = gzip.decompress(response.content)
        dump = decompressed_data.decode('utf-8')

        print(f"Successfully got dump result")
        return {"dump": dump}
    except Exception as e:
        traceback.print_exc()
        raise ValueError(f"Failed to get config dump: {str(e)}")
    

async def store_dump_function(config_id: int, dump: str):
    try:
        response = await asyncio.to_thread(
            requests.post,
            f"{API_URL}/store_dump", 
            json={"config_id": config_id, "dump": dump},
            timeout=120  # Increased timeout for large payload
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to store config dump" + response.text)
        
        # Run the blocking JSON parsing in a thread pool
        result = await asyncio.to_thread(response.json)
        print(f"Successfully stored dump")
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to store config dump: {str(e)}")

# display config tree, if file, return content
@router.post("/config_tree/{config_id}")
async def config_tree(config_id: int, path: str = Form(...)) -> List[ConfigContent]:
    try:
        cursor = files_conn.cursor()

        # If an exact path is given, check whether it's a known file
        if path:
            cursor.execute(
                "SELECT content FROM files WHERE config_id = %s AND path = %s",
                (config_id, path)
            )
            row = cursor.fetchone()
            if row:
                raw = row[0]
                file_content = raw.decode("utf-8") if isinstance(raw, (bytes, memoryview)) else raw
                return [ConfigContent(filename=path, is_folder=False, file_content=file_content)]

        # Otherwise list immediate children under the given directory prefix
        cursor.execute("SELECT path FROM files WHERE config_id = %s", (config_id,))
        all_paths = [r[0] for r in cursor.fetchall()]

        prefix = path + "/" if path else ""
        children: dict[str, bool] = {}  # name → is_folder
        for p in all_paths:
            if not p.startswith(prefix):
                continue
            remainder = p[len(prefix):]
            parts = remainder.split("/", 1)
            # Only mark as folder if there is a deeper path component
            children[parts[0]] = children.get(parts[0], False) or len(parts) > 1

        if not children:
            raise HTTPException(status_code=404, detail="Path not found")

        return [
            ConfigContent(filename=name, is_folder=is_folder)
            for name, is_folder in sorted(children.items())
        ]
    except HTTPException:
        raise
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
        return {"status": "success"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to update config file: {str(e)}")



@router.post("/get_dump")
async def get_dump(file: UploadFile = File(...)):
    response = requests.post(f"{WAF_URL}/get_dump", files={"file": (file.filename, file.file, file.content_type)})
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to get config dump: " + response.text)

    # Decompress the gzip response and decode to string
    decompressed_data = gzip.decompress(response.content)
    dump = decompressed_data.decode('utf-8')
    return {"dump": dump}


@router.post("/store_dump")
async def store_dump(request: Request):
    data = await request.json()
    config_id = data.get("config_id")
    dump = data.get("dump")

    # Store the config in PostgreSQL
    cursor = files_conn.cursor()
    cursor.execute("""
        INSERT INTO public.dumps (config_id, dump)
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
