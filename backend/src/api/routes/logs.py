from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body, Query
from typing import List, Optional
from services.logs.service import LogAnalysisService
from services.logs.schemas import (
    LogClassificationResponse,
    LogAnalysisSessionResponse,
    FilteredLogsResponse,
    CategoryDetailsResponse,
    LogDetailResponse,
    LogFilter,
    CategoryRequest,
    UserSessionRequest
)
from services.auth.schemas import UserInfo
from shared.schemas import SuccessResponse
from api.dependencies import get_current_user

router = APIRouter(prefix="/logs", tags=["logs"])


@router.post("/classify", response_model=LogClassificationResponse, status_code=status.HTTP_201_CREATED)
async def classify_log_file(
    file: UploadFile = File(..., description="Log file (.san, .txt, or audit.log)"),
    configuration_id: Optional[int] = Query(None, description="Optional configuration context"),
    current_user: UserInfo = Depends(get_current_user)
):
    log_service = LogAnalysisService()
    """
    Upload and classify a log file.
    
    Process:
    1. Parse ModSecurity audit logs
    2. Normalize and format log entries
    3. Send to ML service for classification
    4. Store results in database
    
    - **file**: Log file (max 500MB)
    - **configuration_id**: Optional link to a configuration
    
    Returns session ID and category statistics.
    """
    try:
        return await log_service.classify_logs(
            user_id=current_user.id,
            file=file,
            configuration_id=configuration_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/sessions", response_model=List[LogAnalysisSessionResponse])
async def list_user_sessions(
    user_session: UserSessionRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    List all log analysis sessions for current user.
    
    - **limit**: Maximum number of sessions to return (1-100)
    - **offset**: Number of sessions to skip
    
    Returns list of sessions with status and summary information.
    """

    log_service = LogAnalysisService()
    return log_service.get_user_sessions(
        user_id=current_user.id,
        limit=user_session.limit,
        offset=user_session.offset
    )


@router.get("/sessions/{session_id}/log/{transaction_id}", response_model=LogDetailResponse)
async def get_log_detail(
    session_id: str,
    transaction_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get detailed information for a specific log entry.
    
    - **session_id**: Analysis session UUID
    - **transaction_id**: ModSecurity transaction ID
    
    Returns complete log data including raw parsed structure.
    """

    log_service = LogAnalysisService()
    result = log_service.get_log_by_transaction(session_id, transaction_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log not found"
        )
    
    return result


@router.post("/sessions/{session_id}/filter", response_model=FilteredLogsResponse)
async def filter_logs(
    session_id: str,
    filters: LogFilter = Body(default=LogFilter()),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Apply filters to logs in a session using pandas.
    
    - **session_id**: Analysis session UUID
    - **filters**: Filter criteria
        - **start_time**: Filter logs after this timestamp
        - **end_time**: Filter logs before this timestamp
        - **columns**: Column-based filters with name, value, and type
            - type: 'exact', 'contains', 'greater_than', 'less_than'
    
    Returns filtered log statistics and categories with log indices.
    """

    log_service = LogAnalysisService()
    try:
        return log_service.get_filtered_logs(session_id, filters)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/sessions/{session_id}/categories", response_model=CategoryDetailsResponse)
async def get_category_logs(
    session_id: str,
    category_request: CategoryRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get detailed logs for a specific category.
    
    - **session_id**: Analysis session UUID
    - **category**: Category name (e.g., "SQL Injection", "XSS")
    
    Returns list of log entries for the specified category.
    """

    log_service = LogAnalysisService()
    try:
        return log_service.get_category_details(
            session_id=session_id,
            category=category_request.category,
            log_indices=category_request.log_indices,
            limit=category_request.limit,
            offset=category_request.offset
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def delete_session(
    session_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Delete a log analysis session and all associated data.
    
    - **session_id**: Analysis session UUID
    
    Only the session owner can delete their sessions.
    """

    log_service = LogAnalysisService()
    try:
        log_service.delete_session(session_id, current_user.id)
        return SuccessResponse(message="Session deleted successfully")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
