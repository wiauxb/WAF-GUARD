from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from .models import Configuration
from typing import Optional, List

class ConfigurationRepository:
    """Data access layer for Configuration operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        name: str,
        description: Optional[str],
        file_path: str,
        file_hash: Optional[str],
        file_size: Optional[int],
        created_by_user_id: int
    ) -> Configuration:
        """Create a new configuration"""
        config = Configuration(
            name=name,
            description=description,
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            parsing_status="not_parsed",
            created_by_user_id=created_by_user_id
        )
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config
    
    def get_by_id(self, config_id: int) -> Optional[Configuration]:
        """Get configuration by ID"""
        return self.db.query(Configuration).filter(Configuration.id == config_id).first()
    
    def get_by_name(self, name: str) -> Optional[Configuration]:
        """Get configuration by name"""
        return self.db.query(Configuration).filter(Configuration.name == name).first()
    
    def get_all(self, order_by: str = "created_at", order_desc: bool = True) -> List[Configuration]:
        """Get all configurations with sorting"""
        query = self.db.query(Configuration)
        
        # Apply sorting
        order_column = getattr(Configuration, order_by, Configuration.created_at)
        if order_desc:
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        return query.all()
    
    def update(self, config: Configuration) -> Configuration:
        """Update configuration"""
        self.db.commit()
        self.db.refresh(config)
        return config
    
    def delete(self, config: Configuration) -> bool:
        """Delete configuration"""
        self.db.delete(config)
        self.db.commit()
        return True
    
    def name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        """Check if configuration name exists (excluding specific ID)"""
        query = self.db.query(Configuration).filter(Configuration.name == name)
        if exclude_id:
            query = query.filter(Configuration.id != exclude_id)
        return query.count() > 0