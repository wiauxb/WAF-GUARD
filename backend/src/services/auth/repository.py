from sqlalchemy.orm import Session
from .models import User
from typing import Optional

class UserRepository:
    """Data access layer for User operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()
    
    def create(self, username: str, hashed_password: str, is_admin: bool = False) -> User:
        """Create a new user"""
        user = User(
            username=username,
            hashed_password=hashed_password,
            is_admin=is_admin
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update_password(self, user: User, hashed_password: str) -> User:
        """Update user password"""
        user.hashed_password = hashed_password
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def set_active_configuration(self, user: User, configuration_id: Optional[int]) -> User:
        """Set user's active configuration"""
        user.active_configuration_id = configuration_id
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def username_exists(self, username: str) -> bool:
        """Check if username already exists"""
        return self.db.query(User).filter(User.username == username).count() > 0