"""
Pydantic schemas for log analysis service.

Two-step classification (FP/TP locally, then attack-type via the model service).
Class names are kept stable across the port so routes and the frontend contract
don't need to be renamed wholesale — only their fields changed.
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


# ==================== Parsed log structure (parser.transform_entry output) ====================

class ParsedSectionA(BaseModel):
    """Section A — timestamp and connection metadata."""
    Time: str = ""
    Transaction_id: str = ""
    Remote_address: str = ""
    Remote_port: int = 0
    Local_address: str = ""
    Local_port: int = 0


class ParsedSectionB(BaseModel):
    """Section B — HTTP request line + request headers (dynamic keys allowed)."""
    model_config = ConfigDict(extra="allow")

    Http_request: str = ""
    Request_url: str = ""
    Request_protocol: str = ""


class ParsedSectionH(BaseModel):
    """Section H — WAF messages + metadata (dynamic keys allowed)."""
    model_config = ConfigDict(extra="allow")

    Messages: List[str] = []


class ParsedLog(BaseModel):
    """Full structured representation of a single audit log entry."""
    id: str = ""
    A: ParsedSectionA = ParsedSectionA()
    B: ParsedSectionB = ParsedSectionB()
    C: Dict[str, Any] = {}   # payload
    F: Dict[str, Any] = {}   # HTTP response + response headers
    H: ParsedSectionH = ParsedSectionH()
    I: Dict[str, Any] = {}   # request body (production WAF)
    J: Dict[str, Any] = {}   # upload info (production WAF)


# ==================== Extracted features (26 fields) ====================

class LogFeatures(BaseModel):
    """All 26 structured features extracted from a parsed log entry."""
    transaction_id: str = ""
    timestamp: str = ""
    remote_address: str = ""
    request_method: str = ""
    request_url: str = ""
    request_protocol: str = ""
    host: str = ""
    user_agent: str = ""
    cookie: str = ""
    payload: str = ""
    response_status_code: str = ""
    response_status: str = ""
    rule_ids: str = ""
    rule_count: int = 0
    severities: str = ""
    max_severity: str = ""
    tags: str = ""
    messages: str = ""
    matched_data: str = ""
    matched_locations: str = ""
    has_bot_rule: bool = False
    has_access_denied: bool = False
    action: str = ""
    webapp_info: str = ""
    h_raw: str = ""


# ==================== Attack type (step 2 — model service) ====================

class AttackTypeResult(BaseModel):
    """Attack category returned by the model service.

    `probabilities` is passed through as-is from the service — may be a list
    of floats or a list of {label: score} dicts depending on the service version.
    """
    labels: List[str] = []
    probabilities: List[Any] = []


# ==================== Full log entry (parsed + features + classification) ====================

class LogEntryResponse(BaseModel):
    """Full record for one audit log entry stored in a session."""
    parsed: ParsedLog
    features: LogFeatures
    prediction: Literal["false_positive", "true_positive"]
    confidence: float
    fp_probability: float
    tp_probability: float
    attack_type: Optional[AttackTypeResult] = None

    class Config:
        from_attributes = True


# ==================== Category summary ====================

class LogCategoryResponse(BaseModel):
    """Aggregated count for a predicted attack category (true positives only)."""
    category: str
    count: int
    percentage: Optional[float] = None
    log_indices: Optional[List[int]] = None

    class Config:
        from_attributes = True


# ==================== /classify response ====================

class LogClassificationResponse(BaseModel):
    """Response after two-step log classification."""
    session_id: str
    filename: str
    total_logs: int
    false_positives: int
    true_positives: int
    categories: List[LogCategoryResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "audit.log",
                "total_logs": 1500,
                "false_positives": 420,
                "true_positives": 1080,
                "categories": [
                    {"category": "SQL Injection", "count": 450, "log_indices": [1, 2, 3]},
                    {"category": "XSS", "count": 300, "log_indices": [4, 5, 6]},
                ],
            }
        }


# ==================== Filtering ====================

class ColumnFilter(BaseModel):
    """Filter on a single field of LogFeatures."""
    name: str
    value: Any
    type: Literal["exact", "contains", "greater_than", "less_than"] = "exact"


class LogFilter(BaseModel):
    """Filters for querying log entries within a session."""
    prediction: Optional[Literal["false_positive", "true_positive"]] = None
    category: Optional[str] = None  # partial match on attack_type.labels
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    columns: List[Dict[str, Any]] = Field(default_factory=list)  # filters on features.* fields

    class Config:
        json_schema_extra = {
            "example": {
                "prediction": "true_positive",
                "category": "SQL Injection",
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-12-31T23:59:59Z",
                "columns": [
                    {"name": "response_status_code", "value": 403, "type": "exact"},
                ],
            }
        }


class FilteredLogsResponse(BaseModel):
    """Response for filtered log queries within a session."""
    session_id: str
    total_logs: int
    filtered_logs: int
    categories: List[LogCategoryResponse]
    results: List[LogEntryResponse]


class CategoryRequest(BaseModel):
    """Request for category details"""
    category: str
    log_indices: List[int]
    limit: Optional[int] = 100
    offset: Optional[int] = 0


class CategoryDetailsResponse(BaseModel):
    """Detailed logs for a specific category"""
    session_id: str
    category: str
    total_count: int
    logs: List[LogEntryResponse]


class LogDetailResponse(BaseModel):
    """Single log detail by transaction ID"""
    session_id: str
    transaction_id: str
    log: LogEntryResponse


# ==================== Sessions ====================

class UserSessionRequest(BaseModel):
    """Request to get user sessions"""
    limit: Optional[int] = 50
    offset: Optional[int] = 0


class LogAnalysisSessionResponse(BaseModel):
    """Log analysis session details"""
    id: int = 0
    session_id: str
    user_id: int
    configuration_id: Optional[int] = None

    filename: str
    file_size: Optional[int] = None

    status: str
    total_logs: Optional[int] = None
    false_positives: Optional[int] = None
    true_positives: Optional[int] = None
    error_message: Optional[str] = None

    created_at: str
    completed_at: Optional[str] = None

    categories: Optional[List[LogCategoryResponse]] = None

    class Config:
        from_attributes = True
