from fastapi import APIRouter, Depends, HTTPException, status
from services.auth.service import AuthService
from services.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    PasswordChangeRequest,
    SetActiveConfigRequest,
    UserInfo,
    TokenResponse
)
from shared.schemas import SuccessResponse
from api.dependencies import get_auth_service, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user account.

    - **username**: 3-255 characters, alphanumeric + underscore/hyphen only
    - **password**: Minimum 4 characters
    - **password_confirm**: Must match password

    Returns the created user information (without password).
    """
    try:
        return auth_service.register_user(request.username, request.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate user and get JWT access token.
    
    - **username**: Your username
    - **password**: Your password
    
    Returns JWT token to use in Authorization header for protected endpoints.
    Use as: `Authorization: Bearer <token>`
    """
    try:
        return auth_service.login(request.username, request.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    
    Requires valid JWT token in Authorization header.
    """
    return current_user

@router.put("/me/password", response_model=SuccessResponse)
async def change_password(
    request: PasswordChangeRequest,
    current_user: UserInfo = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Change current user's password.

    - **old_password**: Current password for verification
    - **new_password**: New password (minimum 4 characters)
    - **new_password_confirm**: Must match new_password

    Requires valid JWT token in Authorization header.
    """
    try:
        auth_service.update_user_password(
            current_user.id,
            request.old_password,
            request.new_password
        )
        return SuccessResponse(message="Password updated successfully")
    except ValueError as e:
        if "incorrect" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/me/active-config", response_model=SuccessResponse)
async def set_active_configuration(
    request: SetActiveConfigRequest,
    current_user: UserInfo = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Set user's active configuration.
    
    - **configuration_id**: ID of configuration to set as active
    
    Requires valid JWT token in Authorization header.
    """
    try:
        auth_service.set_user_active_configuration(
            current_user.id,
            request.configuration_id
        )
        return SuccessResponse(
            message=f"Active configuration set to {request.configuration_id}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )