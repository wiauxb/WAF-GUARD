from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from shared.database import Base
from datetime import datetime

class Configuration(Base):
    __tablename__ = "configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=False)
    file_hash = Column(String(64), nullable=True)
    file_size = Column(Integer, nullable=True)
    parsing_status = Column(String(50), default="not_parsed", index=True)
    parsing_error = Column(Text, nullable=True)
    created_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    parsed_at = Column(DateTime, nullable=True)
    
    # Relationships (use strings to avoid circular imports)
    created_by = relationship(
        "User",
        foreign_keys=[created_by_user_id],
        primaryjoin="Configuration.created_by_user_id == User.id"
    )
    
    # Relationships to parser tables
    symbols = relationship(
        "Symbol",
        back_populates="configuration",
        cascade="all, delete-orphan"
    )
    macro_definitions = relationship(
        "MacroDefinition",
        back_populates="configuration",
        cascade="all, delete-orphan"
    )
    macro_calls = relationship(
        "MacroCall",
        back_populates="configuration",
        cascade="all, delete-orphan"
    )