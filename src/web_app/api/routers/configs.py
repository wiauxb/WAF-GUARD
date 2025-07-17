import os
import uuid
from pathlib import Path

import requests
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request

from ..db.connections import files_conn, WAF_URL, ANALYZER_URL
from ..utils.file_utils import extract_config

router = APIRouter(prefix="/configs", tags=["Configuration Management"])


@router.get("")
async def get_configs():
    cursor = files_conn.cursor()
    cursor.execute("SELECT * FROM configs")
    configs = cursor.fetchall()
    return {"configs": configs}


@router.get("/selected")
async def get_selected_config():
    """Get the currently selected configuration."""
    cursor = files_conn.cursor()

    # Get the currently selected config
    cursor.execute("SELECT * FROM selected_config ORDER BY id DESC LIMIT 1")
    selected = cursor.fetchone()
    
    if not selected:
        return {"selected_config": None}
    
    return {"selected_config": selected}


@router.post("/select/{config_id}")
async def select_config(config_id: int):
    """Set the selected configuration."""

    # Validate config exists
    cursor = files_conn.cursor()
    cursor.execute("SELECT * FROM configs WHERE id = %s", (config_id,))
    config = cursor.fetchone()
    if not config:
        raise HTTPException(status_code=404, detail="Config does not exist")

    # Check if selected_config table is empty
    cursor.execute("SELECT * FROM selected_config")
    selected = cursor.fetchone()
    if not selected:
        # Insert new row if table is empty
        cursor.execute("INSERT INTO selected_config (config_id) VALUES (%s)", (config_id,))
    else:
        # Update existing row
        cursor.execute("UPDATE selected_config SET config_id = %s", (config_id,))
    files_conn.commit()
    return {"message": "Config selected successfully"}


@router.delete("/{config_id}")
async def delete_config(config_id: int):
    """Delete a configuration."""
    cursor = files_conn.cursor()
    cursor.execute("DELETE FROM configs WHERE id = %s", (config_id,))
    files_conn.commit()
    return {"message": "Config deleted successfully"}


@router.post("/analyze/{config_id}")
async def analyze_config(config_id: int):
    """Start analyzing a configuration and return a task ID for progress tracking."""
    # Validate config exists
    cursor = files_conn.cursor()
    cursor.execute("SELECT * FROM configs WHERE id = %s", (config_id,))
    config = cursor.fetchone()
    if not config:
        raise HTTPException(status_code=404, detail="Config does not exist")
    
    # Create a new task entry
    task_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO analysis_tasks (id, config_id, status, progress) VALUES (%s, %s, %s, %s)",
        (task_id, config_id, "pending", 0)
    )
    files_conn.commit()
    
    # Send the task to the analyzer service asynchronously
    try:
        response = requests.post(f"{ANALYZER_URL}/process_configs/{config_id}")
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Failed to start parsing: {response.text}")
    except requests.RequestException as e:
        cursor.execute(
            "UPDATE analysis_tasks SET status = %s WHERE task_id = %s",
            ("failed", task_id)
        )
        files_conn.commit()
        raise HTTPException(status_code=500, detail=f"Failed to connect to analyzer service: {str(e)}")
    
    # update the parsed status of the config in the db
    cursor.execute(
        "UPDATE configs SET parsed = TRUE WHERE id = %s",
        (config_id,)
    )
    files_conn.commit()

    # Return the task ID that the client can use to query progress
    return {
        "task_id": task_id,
        "status": "pending",
        "progress_endpoint": f"/parsing_progress/{task_id}"
    }


@router.get("/analyze/{config_id}")
async def get_analyzed_config(config_id: int):
    cursor = files_conn.cursor()
    cursor.execute("SELECT parsed FROM configs WHERE id = %s", (config_id,))
    result = cursor.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"parsed": result[0]}
