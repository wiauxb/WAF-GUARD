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
            "error_message": None,
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "logs": [],
            "categories": {}
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
        total_logs: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update session status"""
        session_data = self.get_session(session_id)
        
        if not session_data:
            return None
        
        session_data["status"] = status
        if total_logs is not None:
            session_data["total_logs"] = total_logs
        if error_message:
            session_data["error_message"] = error_message
        if status == "completed":
            session_data["completed_at"] = datetime.utcnow().isoformat()
        
        self._save_session(session_id, session_data)
        return session_data
    
    def add_logs(
        self,
        session_id: str,
        logs: List[Dict[str, Any]],
        categories: Dict[str, int],
        dataframe_dict: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Add logs and categories to session.
        
        Args:
            session_id: Session UUID
            logs: List of log entries
            categories: Category counts
            dataframe_dict: Serialized DataFrame for filtering (optional)
        """
        session_data = self.get_session(session_id)
        
        if not session_data:
            return None
        
        session_data["logs"] = logs
        session_data["categories"] = categories
        session_data["total_logs"] = len(logs)
        
        # Store dataframe if provided (for filtering)
        if dataframe_dict:
            session_data["dataframe"] = dataframe_dict
        
        self._save_session(session_id, session_data)
        return session_data
    
    def get_log_by_transaction_id(
        self,
        session_id: str,
        transaction_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific log by transaction ID"""
        session_data = self.get_session(session_id)
        
        if not session_data:
            return None
        
        for log in session_data.get("logs", []):
            if log.get("A", [{}])[0].get("Transaction_id") == transaction_id:
                return log
        
        return None
    
    def get_logs_by_category(
        self,
        session_id: str,
        category: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get logs filtered by category"""
        session_data = self.get_session(session_id)
        
        if not session_data:
            return []
        
        filtered_logs = [
            log for log in session_data.get("logs", [])
            if log.get("predicted_category") == category
        ]
        
        return filtered_logs[offset:offset + limit]
    
    def get_user_sessions(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        sessions = []
        
        for file_path in self.logs_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    if session_data.get("user_id") == user_id:
                        # Don't include full logs in list view
                        session_summary = {k: v for k, v in session_data.items() if k != "logs"}
                        sessions.append(session_summary)
            except Exception as e:
                logger.error(f"Error reading session file {file_path}: {e}")
        
        # Sort by created_at descending
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
        
        # Authorization check
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
    
    def get_session_columns(self, session_id: str) -> List[str]:
        """Get available column names from session logs"""
        session_data = self.get_session(session_id)
        
        if not session_data or not session_data.get("logs"):
            return []
        
        # Get keys from first log entry
        first_log = session_data["logs"][0]
        return list(first_log.keys())
