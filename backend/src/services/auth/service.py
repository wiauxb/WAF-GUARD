from sqlalchemy.orm import Session
from .repository import UserRepository
from .schemas import UserInfo, TokenResponse
from .utils import hash_password, verify_password, create_access_token, decode_access_token
from datetime import timedelta
from shared.config import settings

class AuthService:
    """Business logic for authentication and user management"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
    
    def register_user(self, username: str, password: str) -> UserInfo:
        """
        Register a new user.
        
        Args:
            username: Unique username
            password: Plain text password (will be hashed)
        
        Returns:
            UserInfo with created user details
        
        Raises:
            ValueError: If username already exists
        """
        # Check if username exists
        if self.user_repo.username_exists(username):
            raise ValueError(f"Username '{username}' already exists")
        
        # Hash password
        hashed_password = hash_password(password)
        
        # Create user
        user = self.user_repo.create(username, hashed_password)
        
        return UserInfo.from_orm(user)
    
    def login(self, username: str, password: str) -> TokenResponse:
        """
        Authenticate user and generate JWT token.
        
        Args:
            username: Username
            password: Plain text password
        
        Returns:
            TokenResponse with JWT access token
        
        Raises:
            ValueError: If credentials are invalid
        """
        # Get user by username
        user = self.user_repo.get_by_username(username)
        if not user:
            raise ValueError("Invalid username or password")
        
        # Verify password
        if not verify_password(password, user.hashed_password):
            raise ValueError("Invalid username or password")
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
        )
    
    def verify_token(self, token: str) -> UserInfo:
        """
        Verify JWT token and return user information.
        
        Args:
            token: JWT access token
        
        Returns:
            UserInfo of the authenticated user
        
        Raises:
            ValueError: If token is invalid or user not found
        """
        try:
            # Decode token
            payload = decode_access_token(token)
            username: str = payload.get("sub")
            
            if username is None:
                raise ValueError("Invalid token payload")
            
            # Get user
            user = self.user_repo.get_by_username(username)
            if user is None:
                raise ValueError("User not found")
            
            return UserInfo.from_orm(user)
        
        except Exception as e:
            raise ValueError(f"Invalid token: {str(e)}")
    
    def get_user_by_id(self, user_id: int) -> UserInfo:
        """
        Get user by ID.
        
        Args:
            user_id: User identifier
        
        Returns:
            UserInfo
        
        Raises:
            ValueError: If user not found
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        return UserInfo.from_orm(user)
    
    def update_user_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """
        Change user password.
        
        Args:
            user_id: User identifier
            old_password: Current password for verification
            new_password: New password
        
        Returns:
            True on success
        
        Raises:
            ValueError: If user not found or old password incorrect
        """
        # Get user
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Verify old password
        if not verify_password(old_password, user.hashed_password):
            raise ValueError("Old password is incorrect")
        
        # Hash new password
        hashed_password = hash_password(new_password)
        
        # Update password
        self.user_repo.update_password(user, hashed_password)
        
        return True
    
    def set_user_active_configuration(self, user_id: int, configuration_id: int) -> bool:
        """
        Set user's active configuration.
        
        Args:
            user_id: User identifier
            configuration_id: Configuration identifier
        
        Returns:
            True on success
        
        Raises:
            ValueError: If user not found
        """
        # Get user
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Note: We don't verify configuration exists here - that's Config Manager's responsibility
        # The FK constraint will prevent invalid configuration_id
        
        # Set active configuration
        self.user_repo.set_active_configuration(user, configuration_id)
        
        return True