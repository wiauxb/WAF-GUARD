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
from api.dependencies import get_current_user, get_log_analysis_service

router = APIRouter(prefix="/logs", tags=["logs"])


@router.post("/classify", response_model=LogClassificationResponse, status_code=status.HTTP_201_CREATED)
async def classify_log_file(
    file: UploadFile = File(..., description="Log file (.san, .txt, or audit.log)"),
    configuration_id: Optional[int] = Query(None, description="Optional configuration context"),
    current_user: UserInfo = Depends(get_current_user),
    log_service: LogAnalysisService = Depends(get_log_analysis_service),
):
    """
    Upload and classify a log file.

    Two-step pipeline:
    1. Local ModernBERT model classifies every entry as false_positive / true_positive.
    2. True-positive entries only are sent to the attack-type model service.

    - **file**: Log file (max 500MB)
    - **configuration_id**: Optional link to a configuration

    Returns session ID, FP/TP counts and attack-category statistics.
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
    current_user: UserInfo = Depends(get_current_user),
    log_service: LogAnalysisService = Depends(get_log_analysis_service),
):
    """
    List all log analysis sessions for current user.

    - **limit**: Maximum number of sessions to return (1-100)
    - **offset**: Number of sessions to skip

    Returns list of sessions with status and summary information.
    """
    return log_service.get_user_sessions(
        user_id=current_user.id,
        limit=user_session.limit,
        offset=user_session.offset
    )


@router.get("/sessions/{session_id}/log/{transaction_id}", response_model=LogDetailResponse)
async def get_log_detail(
    session_id: str,
    transaction_id: str,
    current_user: UserInfo = Depends(get_current_user),
    log_service: LogAnalysisService = Depends(get_log_analysis_service),
):
    """
    Get detailed information for a specific log entry.

    - **session_id**: Analysis session UUID
    - **transaction_id**: ModSecurity transaction ID

    Returns the full parsed log, extracted features and classification result.
    """
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
    current_user: UserInfo = Depends(get_current_user),
    log_service: LogAnalysisService = Depends(get_log_analysis_service),
):
    """
    Apply filters to logs in a session.

    - **session_id**: Analysis session UUID
    - **filters**: Filter criteria
        - **prediction**: 'false_positive' or 'true_positive'
        - **category**: partial match on attack category label
        - **start_time** / **end_time**: filter logs by timestamp
        - **columns**: filters on any `features.*` field
            - type: 'exact', 'contains', 'greater_than', 'less_than'

    Returns filtered log statistics, categories and the full matching entries.
    """
    try:
        return log_service.get_filtered_logs(session_id, filters)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/sessions/{session_id}/categories", response_model=CategoryDetailsResponse)
async def get_category_logs(
    session_id: str,
    category_request: CategoryRequest,
    current_user: UserInfo = Depends(get_current_user),
    log_service: LogAnalysisService = Depends(get_log_analysis_service),
):
    """
    Get detailed logs for a specific attack category.

    - **session_id**: Analysis session UUID
    - **category**: Category name (e.g., "SQL Injection", "XSS")
    - **log_indices**: Indices returned in the category summary (from /classify or /filter)

    Returns list of log entries for the specified category.
    """
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
    current_user: UserInfo = Depends(get_current_user),
    log_service: LogAnalysisService = Depends(get_log_analysis_service),
):
    """
    Delete a log analysis session and all associated data.

    - **session_id**: Analysis session UUID

    Only the session owner can delete their sessions.
    """
    try:
        log_service.delete_session(session_id, current_user.id)
        return SuccessResponse(message="Session deleted successfully")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
