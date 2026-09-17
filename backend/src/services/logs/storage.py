"""
JSON storage handler for log analysis sessions.
Stores session data as JSON files instead of database.
"""
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LogSessionStorage:
    """Manages log analysis session storage as JSON files"""

    def __init__(self, storage_root: str):
        """
        Initialize storage handler.

        Args:
            storage_root: Root directory for storage (e.g., /app/storage)
        """
        self.storage_root = Path(storage_root)
        self.logs_dir = self.storage_root / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Log session storage initialized at {self.logs_dir}")

    def _get_session_file(self, session_id: str) -> Path:
        """Get the file path for a session"""
        return self.logs_dir / f"{session_id}.json"

    def create_session(
        self,
        user_id: int,
        filename: str,
        configuration_id: Optional[int] = None,
        file_size: Optional[int] = None,
        file_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new log analysis session.

        Returns:
            Session data dictionary
        """
        session_id = str(uuid.uuid4())

        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "configuration_id": configuration_id,
            "filename": filename,
            "file_size": file_size,
            "file_hash": file_hash,
            "status": "processing",
            "total_logs": 0,
            "false_positives": 0,
            "true_positives": 0,
            "error_message": None,
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "entries": [],
            "categories": [],
        }

        self._save_session(session_id, session_data)
        logger.info(f"Created session {session_id}")
        return session_data

    def _save_session(self, session_id: str, session_data: Dict[str, Any]):
        """Save session data to file"""
        file_path = self._get_session_file(session_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False, default=str)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by ID.

        Returns:
            Session data or None if not found
        """
        file_path = self._get_session_file(session_id)

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return None

    def update_session_status(
        self,
        session_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update session status"""
        session_data = self.get_session(session_id)

        if not session_data:
            return None

        session_data["status"] = status
        if error_message:
            session_data["error_message"] = error_message
        if status == "completed":
            session_data["completed_at"] = datetime.utcnow().isoformat()

        self._save_session(session_id, session_data)
        return session_data

    def add_entries(
        self,
        session_id: str,
        entries: List[Dict[str, Any]],
        categories: List[Dict[str, Any]],
        false_positives: int,
        true_positives: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Add classified entries and category summary to a session.

        Args:
            session_id: Session UUID
            entries: List of LogEntryResponse.model_dump() dicts
            categories: List of LogCategoryResponse-shaped dicts (true positives only)
            false_positives: Count of false_positive predictions
            true_positives: Count of true_positive predictions
        """
        session_data = self.get_session(session_id)

        if not session_data:
            return None

        session_data["entries"] = entries
        session_data["categories"] = categories
        session_data["total_logs"] = len(entries)
        session_data["false_positives"] = false_positives
        session_data["true_positives"] = true_positives

        self._save_session(session_id, session_data)
        return session_data

    def get_entry_by_transaction_id(
        self,
        session_id: str,
        transaction_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific log entry by transaction ID"""
        session_data = self.get_session(session_id)

        if not session_data:
            return None

        for entry in session_data.get("entries", []):
            if entry.get("features", {}).get("transaction_id") == transaction_id:
                return entry

        return None

    def get_user_sessions(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all sessions for a user (metadata only, no entries)"""
        sessions = []

        for file_path in self.logs_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    if session_data.get("user_id") == user_id:
                        session_summary = {k: v for k, v in session_data.items() if k != "entries"}
                        sessions.append(session_summary)
            except Exception as e:
                logger.error(f"Error reading session file {file_path}: {e}")

        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return sessions[offset:offset + limit]

    def delete_session(self, session_id: str, user_id: int) -> bool:
        """
        Delete a session file.

        Args:
            session_id: Session UUID
            user_id: User ID for authorization check

        Returns:
            True if deleted, False if not found or unauthorized
        """
        session_data = self.get_session(session_id)

        if not session_data:
            return False

        if session_data.get("user_id") != user_id:
            raise ValueError("Unauthorized to delete this session")

        file_path = self._get_session_file(session_id)
        try:
            file_path.unlink()
            logger.info(f"Deleted session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
