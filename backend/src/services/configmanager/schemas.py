from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Optional, List, Dict, Any

# Request Schemas
class ConfigurationUploadRequest(BaseModel):
    """Data extracted from multipart form for configuration upload"""
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class ConfigurationUpdateRequest(BaseModel):
    """Request to update configuration metadata"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    
    @model_validator(mode='after')
    def at_least_one_field(self):
        if not any([self.name, self.description]):
            raise ValueError('Must provide at least one field to update')
        return self


class FileUpdateRequest(BaseModel):
    """Request to update a configuration file"""
    content: str = Field(min_length=1, max_length=1_000_000)  # 1MB limit


# Response Schemas
class ConfigurationResponse(BaseModel):
    """Configuration metadata response"""
    id: int
    name: str
    description: Optional[str]
    file_path: str
    file_hash: Optional[str]
    file_size: Optional[int]
    parsing_status: str  # "not_parsed", "parsing", "parsed", "error"
    parsing_error: Optional[str]
    created_by_user_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    parsed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ConfigurationListResponse(BaseModel):
    """List of configurations with count"""
    configurations: List[ConfigurationResponse]
    total: int


class ConfigTreeNode(BaseModel):
    """Single node in file tree"""
    name: str
    type: str  # "file" or "directory"
    size: Optional[int] = None  # Only for files


class ConfigTreeResponse(BaseModel):
    """File tree or file content response"""
    is_file: bool
    path: str
    # If directory:
    children: Optional[List[ConfigTreeNode]] = None
    # If file:
    content: Optional[str] = None
    size: Optional[int] = None