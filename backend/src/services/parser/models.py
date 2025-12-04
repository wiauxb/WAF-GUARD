from sqlalchemy import Column, Integer, String, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from shared.database import Base

class Symbol(Base):
    __tablename__ = "symbol_table"
    
    id = Column(Integer, primary_key=True, index=True)
    configuration_id = Column(
        Integer,
        ForeignKey("configurations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    node_id = Column(String(255), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    line_number = Column(Integer, nullable=False)
    
    # Relationships
    configuration = relationship("Configuration", back_populates="symbols")
    
    # Composite index for common queries
    __table_args__ = (
        Index('idx_symbol_config_file', 'configuration_id', 'file_path'),
        Index('idx_symboltable_config_node', 'configuration_id', 'node_id'),
    )


class MacroDefinition(Base):
    __tablename__ = "macro_definitions"
    
    id = Column(Integer, primary_key=True, index=True)
    configuration_id = Column(
        Integer,
        ForeignKey("configurations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = Column(String(255), nullable=False)
    symbol_id = Column(
        Integer,
        ForeignKey("symbol_table.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Relationships
    configuration = relationship("Configuration", back_populates="macro_definitions")
    symbol = relationship("Symbol")
    calls = relationship(
        "MacroCall",
        back_populates="macro_definition",
        cascade="all, delete-orphan"
    )
    
    # Unique constraint: macro name must be unique within a configuration
    __table_args__ = (
        UniqueConstraint('configuration_id', 'name', name='uq_macro_config_name'),
    )


class MacroCall(Base):
    __tablename__ = "macro_calls"
    
    id = Column(Integer, primary_key=True, index=True)
    configuration_id = Column(
        Integer,
        ForeignKey("configurations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    node_id = Column(String(255), nullable=False)
    macro_definition_id = Column(
        Integer,
        ForeignKey("macro_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    symbol_id = Column(
        Integer,
        ForeignKey("symbol_table.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Relationships
    configuration = relationship("Configuration", back_populates="macro_calls")
    macro_definition = relationship("MacroDefinition", back_populates="calls")
    symbol = relationship("Symbol")

    # Composite index for performance optimization (DOC.md line 777)
    __table_args__ = (
        Index('idx_macrocall_config_macro', 'configuration_id', 'macro_definition_id'),
    )