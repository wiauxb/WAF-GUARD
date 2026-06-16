import os
import uuid
from pathlib import Path

import threading

import psycopg2
import requests
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request

from ..db.connections import (
    files_conn, WAF_URL, ANALYZER_URL,
    postgres_host, postgresUser, postgresPass, postgres_db_files, ENVIRONMENT,
)
from ..utils.file_utils import extract_config

router = APIRouter(prefix="/configs", tags=["Configuration Management"])


@router.get("")
async def get_configs():
    cursor = files_conn.cursor()
    cursor.execute("SELECT * FROM public.configs")
    configs = cursor.fetchall()
    return {"configs": configs}


@router.get("/selected")
async def get_selected_config():
    """Get the currently selected configuration."""
    cursor = files_conn.cursor()

    # Get the currently selected config (singleton row with id = 1)
    cursor.execute("SELECT config_id FROM selected_config WHERE id = 1")
    selected = cursor.fetchone()

    if not selected:
        return {"selected_config": None}

    return {"selected_config": selected[0]}


@router.post("/select/{config_id}")
async def select_config(config_id: int):
    """Set the selected configuration."""

    # Validate config exists
    cursor = files_conn.cursor()
    cursor.execute("SELECT * FROM configs WHERE id = %s", (config_id,))
    config = cursor.fetchone()
    if not config:
        raise HTTPException(status_code=404, detail="Config does not exist")

    # Atomic upsert into the singleton row (id = 1 is the only permitted row)
    cursor.execute(
        """
        INSERT INTO selected_config (id, config_id) VALUES (1, %s)
        ON CONFLICT (id) DO UPDATE SET config_id = EXCLUDED.config_id
        """,
        (config_id,)
    )
    files_conn.commit()
    return {"message": "Config selected successfully"}


@router.delete("/{config_id}")
async def delete_config(config_id: int):
    """Delete a configuration."""
    cursor = files_conn.cursor()
    cursor.execute("DELETE FROM configs WHERE id = %s", (config_id,))
    files_conn.commit()
    return {"message": "Config deleted successfully"}


def _run_analyzer(config_id: int, task_id: str):
    """Background thread: call the analyzer and mark the config as parsed when done.

    Opens its own psycopg2 connection — the module-level files_conn is not thread-safe.
    """
    kwargs = dict(
        host=postgres_host,
        user=postgresUser,
        password=postgresPass,
        database=postgres_db_files,
    )
    if ENVIRONMENT == "prod":
        kwargs["sslmode"] = "require"

    status = "failed"
    try:
        conn = psycopg2.connect(**kwargs)
        cursor = conn.cursor()
        try:
            response = requests.post(
                f"{ANALYZER_URL}/process_configs/{config_id}",
                timeout=None  # analysis can take several minutes
            )
            if response.status_code == 200:
                cursor.execute("UPDATE configs SET parsed = TRUE WHERE id = %s", (config_id,))
                status = "completed"
            else:
                print(f"[analyzer] non-200 for config {config_id}: "
                      f"HTTP {response.status_code} — {response.text}", flush=True)
        except Exception as e:
            print(f"[analyzer] exception calling analyzer for config {config_id}: {e}", flush=True)
        finally:
            cursor.execute(
                "UPDATE analysis_tasks SET status = %s WHERE id = %s",
                (status, task_id)
            )
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"[analyzer] DB connection error in background thread: {e}", flush=True)


@router.post("/analyze/{config_id}")
async def analyze_config(config_id: int):
    """Start analyzing a configuration and return immediately; analysis runs in the background."""
    cursor = files_conn.cursor()
    cursor.execute("SELECT * FROM configs WHERE id = %s", (config_id,))
    config = cursor.fetchone()
    if not config:
        raise HTTPException(status_code=404, detail="Config does not exist")

    task_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO analysis_tasks (id, config_id, status, progress) VALUES (%s, %s, %s, %s)",
        (task_id, config_id, "pending", 0)
    )
    files_conn.commit()

    # Fire-and-forget: return 200 immediately, analysis continues in background
    threading.Thread(target=_run_analyzer, args=(config_id, task_id), daemon=True).start()

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
