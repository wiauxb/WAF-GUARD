from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Index
from sqlalchemy.orm import relationship
from shared.database import Base
from datetime import datetime

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    configuration_id = Column(
        Integer,
        ForeignKey("configurations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    thread_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    configuration = relationship("Configuration")
    
    # Composite index for user + config queries
    __table_args__ = (
        Index('idx_conversation_user_config', 'user_id', 'configuration_id'),
    )