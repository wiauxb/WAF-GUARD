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
from fastapi import Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from sqlalchemy.orm import Session
from shared.database import get_postgres_db, get_neo4j_db, get_langgraph_checkpointer
from services.auth.service import AuthService
from services.auth.schemas import UserInfo
from services.configmanager.service import ConfigManagerService
from services.configmanager.repository import ConfigurationRepository
from services.chatbot.service import ChatbotService
from services.parser.service import ParserService
from services.analysis.service import AnalysisService
from services.analysis.repository import GraphQueryRepository

security = HTTPBearer()

def get_auth_service(db: Session = Depends(get_postgres_db)) -> AuthService:
    """Get AuthService instance"""
    return AuthService(db)

def get_config_manager(db: Session = Depends(get_postgres_db)) -> ConfigManagerService:
    """Get ConfigManagerService instance"""
    return ConfigManagerService(db)

def get_parser_service(db: Session = Depends(get_postgres_db)) -> ParserService:
    """Get ParserService instance"""
    return ParserService(db)

def get_analysis_service(
    db: Session = Depends(get_postgres_db),
    neo4j_session = Depends(get_neo4j_db)
) -> AnalysisService:
    """Get AnalysisService instance with both database sessions"""
    return AnalysisService(db, neo4j_session)

def get_chatbot_service(db: Session = Depends(get_postgres_db)) -> ChatbotService:
    """
    Get ChatbotService instance with LangGraph checkpointer.

    The checkpointer is a module-level singleton with its own connection pool,
    separate from the request-scoped SQLAlchemy session.
    """
    checkpointer = get_langgraph_checkpointer()
    return ChatbotService(db, checkpointer)

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


def get_analysis_configuration_id(
    configuration_id: Optional[int] = Query(
        None,
        gt=0,
        description="Configuration to query. Defaults to your active configuration.",
    ),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_postgres_db),
    neo4j_session = Depends(get_neo4j_db),
) -> int:
    """
    Resolve which configuration an analysis request targets, and prove it is queryable.

    Order: the explicit `configuration_id` query parameter, else the caller's
    `active_configuration_id` (set via PUT /auth/me/active-config).

    Raises:
        400: no configuration given and no active one set
        404: the configuration does not exist
        409: it exists but is not parsed, or is marked parsed with an empty graph
    """
    resolved = configuration_id or current_user.active_configuration_id

    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No configuration specified and no active configuration set. "
                "Pass ?configuration_id=<id> or select one via PUT /auth/me/active-config."
            ),
        )

    config = ConfigurationRepository(db).get_by_id(resolved)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration with id {resolved} not found",
        )

    if config.parsing_status != "parsed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Configuration {resolved} is not parsed (status: "
                f"'{config.parsing_status}'). Parse it first: POST /api/v1/parser/parse/{resolved}"
            ),
        )

    # Staleness guard. PostgreSQL keeps parsing_status='parsed' independently of Neo4j,
    # so a graph that was lost (e.g. the container recreated without a persistent volume)
    # would otherwise surface as empty results for a configuration that claims to be ready.
    if not GraphQueryRepository(neo4j_session, resolved).has_any_node():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Configuration {resolved} is marked parsed but its graph is empty. "
                f"Re-parse it: POST /api/v1/parser/reparse/{resolved}"
            ),
        )

    return resolved