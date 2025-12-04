from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from shared.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    active_configuration_id = Column(
        Integer, 
        ForeignKey("configurations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships (use strings to avoid circular imports)
    active_configuration = relationship(
        "Configuration",
        foreign_keys=[active_configuration_id],
        primaryjoin="User.active_configuration_id == Configuration.id"
    )
    conversations = relationship(
        "Conversation",
        back_populates="user"
    )