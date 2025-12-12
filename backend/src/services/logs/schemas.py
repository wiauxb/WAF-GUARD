"""
Pydantic schemas for log analysis service.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ==================== Request Schemas ====================

class LogFilter(BaseModel):
    """Filters for querying log entries"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    columns: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-12-31T23:59:59Z",
                "columns": [
                    {"name": "predicted_category", "value": "SQL Injection", "type": "exact"},
                    {"name": "response_status_code", "value": 403, "type": "exact"}
                ]
            }
        }


class CategoryRequest(BaseModel):
    """Request for category details"""
    category: str
    log_indices: List[int]
    limit: Optional[int] = 100
    offset: Optional[int] = 0


# ==================== Response Schemas ====================

class LogCategoryResponse(BaseModel):
    """Category statistics"""
    category: str
    count: int
    percentage: Optional[float] = None
    log_indices: Optional[List[int]] = None
    
    class Config:
        from_attributes = True


class LogEntryResponse(BaseModel):
    """Individual log entry details"""
    id: str
    transaction_id: str
    timestamp: Optional[datetime] = None
    
    # Request info
    remote_address: Optional[str] = None
    remote_port: Optional[int] = None
    http_method: Optional[str] = None
    request_url: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Response info
    response_status_code: Optional[int] = None
    response_status: Optional[str] = None
    
    # Payload and analysis
    payload: Optional[str] = None
    messages: Optional[List[str]] = None
    message_tags: Optional[List[str]] = None
    
    # Classification
    predicted_category: Optional[str] = None
    prediction_probabilities: Optional[Dict[str, float]] = None
    
    formatted_log: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserSessionRequest(BaseModel):
    """Request to get user sessions"""
    limit: Optional[int] = 50
    offset: Optional[int] = 0


class LogAnalysisSessionResponse(BaseModel):
    """Log analysis session details"""
    id: int
    session_id: str
    user_id: int
    configuration_id: Optional[int] = None
    
    filename: str
    file_size: Optional[int] = None
    
    status: str
    total_logs: Optional[int] = None
    error_message: Optional[str] = None
    
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    # Include categories if loaded
    categories: Optional[List[LogCategoryResponse]] = None
    
    class Config:
        from_attributes = True


class LogClassificationResponse(BaseModel):
    """Response after log classification"""
    session_id: str
    total_logs: int
    categories: List[LogCategoryResponse]
    columns: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "total_logs": 1500,
                "categories": [
                    {"category": "SQL Injection", "count": 450, "log_indices": [1, 2, 3]},
                    {"category": "XSS", "count": 300, "log_indices": [4, 5, 6]}
                ],
                "columns": ["transaction_id", "timestamp", "http_method", "request_url"]
            }
        }


class FilteredLogsResponse(BaseModel):
    """Response for filtered log queries"""
    session_id: str
    total_logs: int
    filtered_logs: int
    categories: List[LogCategoryResponse]
    columns: List[str]
    applied_filters: Dict[str, Any]


class CategoryDetailsResponse(BaseModel):
    """Detailed logs for a specific category"""
    session_id: str
    category: str
    total_count: int
    logs: List[Dict[str, Any]]


class LogDetailResponse(BaseModel):
    """Single log detail with raw data"""
    session_id: str
    transaction_id: str
    log: Dict[str, Any]  # Raw parsed log data


# ==================== Internal Processing Schemas ====================

class ParsedLogData(BaseModel):
    """Internal schema for parsed log data before DB storage"""
    transaction_id: str
    timestamp: Optional[datetime] = None
    remote_address: Optional[str] = None
    remote_port: Optional[int] = None
    local_address: Optional[str] = None
    local_port: Optional[int] = None
    http_method: Optional[str] = None
    request_url: Optional[str] = None
    request_protocol: Optional[str] = None
    user_agent: Optional[str] = None
    response_status_code: Optional[int] = None
    response_status: Optional[str] = None
    payload: Optional[str] = None
    messages: Optional[List[str]] = None
    message_tags: Optional[List[str]] = None
    formatted_log: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


class PredictionResult(BaseModel):
    """Result from ML model prediction"""
    labels: List[str]
    probabilities: List[Dict[str, float]]


class ClassificationRequest(BaseModel):
    """Request to ML classification service"""
    logs: List[str]  # List of formatted log strings
