# api/dependencies.py
# from fastapi import Depends
# from sqlalchemy.orm import Session
# from langgraph.checkpoint.postgres import PostgresSaver
# from shared.database import get_postgres_db, get_langgraph_checkpointer
# from services.chatbot.service import ChatbotService

# def get_chatbot_service(
#     db: Session = Depends(get_postgres_db)
# ) -> ChatbotService:
#     """Dependency that provides ChatbotService with checkpointer"""
#     checkpointer = get_langgraph_checkpointer()
#     return ChatbotService(db, checkpointer)


from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from shared.database import get_postgres_db
from services.auth.service import AuthService
from services.auth.schemas import UserInfo

security = HTTPBearer()

def get_auth_service(db: Session = Depends(get_postgres_db)) -> AuthService:
    """Get AuthService instance"""
    return AuthService(db)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserInfo:
    """
    Verify JWT token and return current user.
    
    This dependency extracts the JWT token from the Authorization header,
    verifies it, and returns the authenticated user's information.
    
    Raises:
        HTTPException 401: If token is invalid or expired
    """
    try:
        return auth_service.verify_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_admin_user(
    current_user: UserInfo = Depends(get_current_user)
) -> UserInfo:
    """
    Verify user is admin.
    
    Raises:
        HTTPException 403: If user is not admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user