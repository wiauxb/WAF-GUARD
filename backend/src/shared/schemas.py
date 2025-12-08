"""
Common Pydantic schemas shared across all services.
"""
from pydantic import BaseModel
from typing import Optional, Dict, List


class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str
    error_code: Optional[str] = None
    field_errors: Optional[Dict[str, List[str]]] = None
