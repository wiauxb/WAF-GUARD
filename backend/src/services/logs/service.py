"""
Log analysis and classification service.
Orchestrates log parsing, ML classification, and JSON file storage.
"""
from fastapi import UploadFile
from typing import List, Dict, Any, Optional
from pathlib import Path
import tempfile
import os
import json
import logging
import httpx
import hashlib
import pandas as pd
from datetime import datetime

from .storage import LogSessionStorage
from .parser import parse_log_file, logs_to_dataframe
from .processor import normalize_dataframe, create_feature_target_sets, pretty_probabilities
from .schemas import (
    LogClassificationResponse,
    LogCategoryResponse,
    FilteredLogsResponse,
    CategoryDetailsResponse,
    LogDetailResponse,
    LogFilter,
    LogAnalysisSessionResponse,
    LogEntryResponse
)
from shared.config import settings

logger = logging.getLogger(__name__)


class LogAnalysisService:
    """Business logic for log analysis and classification"""
    
    def __init__(self, storage_root: str = None, ml_service_url: str = "http://model:8102"):
        self.storage = LogSessionStorage(storage_root or settings.STORAGE_ROOT)
        self.ml_service_url = ml_service_url
    
    async def classify_logs(
        self,
        user_id: int,
        file: UploadFile,
        configuration_id: Optional[int] = None
    ) -> LogClassificationResponse:
        """
        Process and classify log file.
        
        Process:
        1. Validate file
        2. Create session
        3. Parse log file
        4. Normalize and format logs
        5. Send to ML service for classification
        6. Store results in JSON file
        7. Return summary
        
        Args:
            user_id: User performing the analysis
            file: Uploaded log file
            configuration_id: Optional configuration context
            
        Returns:
            LogClassificationResponse with session and category summary
        """
        # Validate file
        max_size = 500 * 1024 * 1024  # 500MB
        if file.size and file.size > max_size:
            raise ValueError("File too large (max 500MB)")
        
        valid_extensions = file.filename.endswith('.san') or file.filename.endswith('.txt')
        audit_log_pattern = 'audit.log' in file.filename
        
        if not (valid_extensions or audit_log_pattern):
            raise ValueError("File must be .san, .txt, or audit.log")
        
        # Read file content
        file_content = await file.read()
        file_hash = hashlib.sha256(file_content).hexdigest() if file_content else None
        
        # Create session
        session_data = self.storage.create_session(
            user_id=user_id,
            filename=file.filename,
            configuration_id=configuration_id,
            file_size=len(file_content) if file_content else None,
            file_hash=file_hash
        )
        session_id = session_data["session_id"]
        
        try:
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name
            
            # Parse logs
            logger.info(f"Parsing log file for session {session_id}")
            parsed_logs = parse_log_file(Path(tmp_path))
            
            # Convert to DataFrame
            df = logs_to_dataframe(parsed_logs)
            normalized_df = normalize_dataframe(df)
            
            # Create feature set
            X, y = create_feature_target_sets(normalized_df)
            
            # Call ML service
            logger.info(f"Sending {len(X)} logs to ML service")
            predictions = await self._call_ml_service(X.tolist())
            
            # Process predictions
            categories = {}
            
            for i, prediction in enumerate(predictions['predictions']):
                category = " ,".join(prediction.get("labels", ["unknown"])) if len(prediction.get("labels", [])) > 0 else "unknown"
                
                probabilities = prediction.get("probabilities", [])
                predictions['predictions'][i]["probabilities"] = probabilities
                predictions['predictions'][i]["labels"] = ["unknown"] if category == "unknown" else prediction.get("labels", [])

                if category not in categories:
                    categories[category] = {
                        "category": category,
                        "count": 0,
                        "log_indices": []
                    }
                categories[category]["count"] += 1
                categories[category]["log_indices"].append(i)
                
            normalized_df['new_categories'] = predictions['predictions']
            df_columns = normalized_df.columns.tolist()
            
            dataframe_dict = normalized_df.to_dict(orient='records')
            
            self.storage.add_logs(session_id, parsed_logs, categories, dataframe_dict)
            
            self.storage.update_session_status(
                session_id,
                status="completed",
                total_logs=len(normalized_df)
            )
            
            return LogClassificationResponse(
                session_id=session_id,
                total_logs=len(normalized_df),
                categories=sorted(categories.values(), key=lambda x: x["count"], reverse=True),
                columns=normalized_df.columns.tolist()
            )
        
        except Exception as e:
            logger.error(f"Error processing logs: {e}", exc_info=True)
            raise RuntimeError(f"Failed to process logs: {str(e)}")
        
        finally:
            if 'tmp_path' in locals():
                try:
                    os.unlink(tmp_path)
                except:
                    pass
    
    async def _call_ml_service(self, logs: List[str]) -> Dict[str, Any]:
        """
        Call ML classification service.
        
        Args:
            logs: List of formatted log strings
            
        Returns:
            Prediction results from ML service
        """
        data = {"logs": logs}
        data = json.dumps(data, indent=4)
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.ml_service_url}/predict",
                    data=data,
                    timeout=3600
                )
                
                if response.status_code != 200:
                    raise RuntimeError(f"ML service error: {response.status_code} - {response.text}")
                
                return response.json()
            
            except httpx.ConnectError:
                raise RuntimeError(f"Cannot connect to ML service at {self.ml_service_url}")
            except httpx.TimeoutException:
                raise RuntimeError("ML service timeout")
    
    def get_log_by_transaction(
        self,
        session_id: str,
        transaction_id: str
    ) -> Optional[LogDetailResponse]:
        """Get detailed log by transaction ID"""
        log_entry = self.storage.get_log_by_transaction_id(session_id, transaction_id)
        
        if not log_entry:
            return None
        
        return LogDetailResponse(
            session_id=session_id,
            transaction_id=transaction_id,
            log=log_entry
        )
    
    def get_filtered_logs(
        self,
        session_id: str,
        filters: LogFilter
    ) -> FilteredLogsResponse:
        """Get logs with filters applied using pandas (like original API)"""
        
        session_data = self.storage.get_session(session_id)
        
        if not session_data:
            raise ValueError("Session not found")
        
        # Get stored dataframe
        dataframe_dict = session_data.get("dataframe")
        if not dataframe_dict:
            # Fallback to simple response if no dataframe stored
            categories_dict = session_data.get("categories", {})
            total_logs = session_data.get("total_logs", 0)
            
            categories = [
                LogCategoryResponse(
                    category=cat,
                    count=count,
                    percentage=(count / total_logs * 100) if total_logs > 0 else 0
                )
                for cat, count in sorted(categories_dict.items(), key=lambda x: x[1], reverse=True)
            ]
            
            return FilteredLogsResponse(
                session_id=session_id,
                total_logs=total_logs,
                filtered_logs=total_logs,
                categories=categories,
                columns=self.storage.get_session_columns(session_id),
                applied_filters={
                    "start_time": filters.start_time,
                    "end_time": filters.end_time,
                    "columns": filters.columns
                }
            )
        
        # Convert dict back to DataFrame
        df = pd.DataFrame(dataframe_dict).copy()
        original_total = len(df)
        
        # Apply time filters
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'], errors='coerce', utc=True)
            if filters.start_time:
                filters.start_time = pd.to_datetime(filters.start_time, errors='coerce', utc=True)
                df = df[df['time'] >= filters.start_time]
            if filters.end_time:
                filters.end_time = pd.to_datetime(filters.end_time, errors='coerce', utc=True)
                df = df[df['time'] <= filters.end_time]
        
        # Apply column-based filters
        for column_filter in filters.columns:
            column_name = column_filter.get('name')
            filter_value = column_filter.get('value')
            filter_type = column_filter.get('type', 'exact')  # default to exact match

            if column_name in df.columns:
                if filter_type == 'contains':
                    df = df[df[column_name].astype(str).str.contains(str(filter_value), na=False)]
                elif filter_type == 'exact':
                    df = df[df[column_name] == filter_value]
                elif filter_type == 'greater_than':
                    df = df[df[column_name] > filter_value]
                elif filter_type == 'less_than':
                    df = df[df[column_name] < filter_value]
        
        # Recalculate categories based on filtered data
        filtered_categories = {}
        
        # Check for predicted_category column
        category_column = None
        if 'predicted_category' in df.columns:
            category_column = 'predicted_category'
        elif 'new_categories' in df.columns:
            category_column = 'new_categories'
        
        if category_column:
            for idx, row in df.iterrows():
                if category_column == 'new_categories' and isinstance(row[category_column], dict):
                    category = " ,".join(row[category_column].get("labels", ["unknown"]))
                else:
                    category = row[category_column] if row[category_column] else "unknown"
                
                if category not in filtered_categories:
                    filtered_categories[category] = {
                        "category": category,
                        "count": 0,
                        "log_indices": []
                    }
                filtered_categories[category]["count"] += 1
                filtered_categories[category]["log_indices"].append(int(idx))
        
        filtered_count = len(df)
        
        categories = [
            LogCategoryResponse(
                category=cat_data["category"],
                count=cat_data["count"],
                percentage=(cat_data["count"] / filtered_count * 100) if filtered_count > 0 else 0,
                log_indices=cat_data["log_indices"]
            )
            for cat_data in sorted(filtered_categories.values(), key=lambda x: x["count"], reverse=True)
        ]
          
        return FilteredLogsResponse(
            session_id=session_id,
            total_logs=original_total,
            filtered_logs=filtered_count,
            categories=categories,
            columns=list(df.columns),
            applied_filters={
                "start_time": filters.start_time.isoformat() if filters.start_time else None,
                "end_time": filters.end_time.isoformat() if filters.end_time else None,
                "columns": filters.columns
            }
        )
    
    def get_category_details(
        self,
        session_id: str,
        category: str,
        log_indices: List[int],
        limit: int = 100,
        offset: int = 0
    ) -> CategoryDetailsResponse:
        """Get detailed logs for a specific category"""
        session_data = self.storage.get_session(session_id)
        categories = session_data.get("categories", {})
        df = pd.DataFrame(session_data.get("dataframe", []))
        
        if category not in categories:
            raise RuntimeError("Category not found in session")
        
        # Get logs for this category
        log_indices = log_indices
        category_logs = []
        
        for idx in log_indices:
            log_data = df.iloc[idx].to_dict()
            
            category_logs.append(log_data)
        
        return CategoryDetailsResponse(
            session_id=session_id,
            category=category,
            total_count=categories[category]["count"],
            logs=category_logs
        )
    
    def get_user_sessions(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[LogAnalysisSessionResponse]:
        """Get all analysis sessions for a user"""
        sessions = self.storage.get_user_sessions(user_id, limit, offset)
        
        return [
            LogAnalysisSessionResponse(
                id=0, 
                session_id=s["session_id"],
                user_id=s["user_id"],
                configuration_id=s.get("configuration_id"),
                filename=s["filename"],
                file_size=s.get("file_size"),
                status=s["status"],
                total_logs=s.get("total_logs"),
                error_message=s.get("error_message"),
                created_at=s["created_at"],
                completed_at=s.get("completed_at"),
                categories=None  # Not included in list view
            )
            for s in sessions
        ]
    
    def delete_session(self, session_id: str, user_id: int) -> bool:
        """Delete a session (with authorization check)"""
        return self.storage.delete_session(session_id, user_id)