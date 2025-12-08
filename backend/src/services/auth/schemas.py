from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional

# Request Schemas
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=255, pattern=r'^[a-zA-Z0-9_-]+$')
    password: str = Field(min_length=4, max_length=255)
    password_confirm: str = Field(min_length=4, max_length=255)
    
    @validator('password_confirm')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=4, max_length=255)


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(min_length=4, max_length=255)
    new_password: str = Field(min_length=4, max_length=255)
    new_password_confirm: str = Field(min_length=4, max_length=255)
    
    @validator('new_password_confirm')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class SetActiveConfigRequest(BaseModel):
    configuration_id: int = Field(gt=0)


# Response Schemas
class UserInfo(BaseModel):
    id: int
    username: str
    is_admin: bool
    active_configuration_id: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int