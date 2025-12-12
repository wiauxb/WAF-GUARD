from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Any, Dict

# Request Schemas
class ConversationCreateRequest(BaseModel):
    """Request to create a new conversation"""
    title: Optional[str] = Field(None, max_length=255)
    configuration_id: Optional[int] = Field(None, gt=0)


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation"""
    message: str = Field(min_length=1, max_length=10000)
    configuration_id: Optional[int] = Field(None, gt=0)
    graph_name: Optional[str] = Field(default="ui_graph_v1", description="LangGraph configuration to use")
    stream: bool = Field(default=False, description="Enable streaming response")


class ConversationListFilters(BaseModel):
    """Filters for listing conversations"""
    configuration_id: Optional[int] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ConversationRenameRequest(BaseModel):
    """Request to rename a conversation"""
    title: str = Field(min_length=1, max_length=255)


# Response Schemas
class ConversationResponse(BaseModel):
    """Conversation metadata response"""
    id: int
    user_id: int
    configuration_id: Optional[int]
    thread_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    configuration_name: Optional[str] = None  # Joined from configurations

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Individual message in a conversation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime


class ToolCallInfo(BaseModel):
    """Information about a tool call made during message generation"""
    name: str = Field(description="Name of the tool that was called")
    arguments: Dict[str, Any] = Field(description="Arguments passed to the tool")
    result: Any = Field(description="Result returned by the tool")


class ChatResponse(BaseModel):
    """Response after sending a message"""
    message: str
    thread_id: str
    configuration_id: Optional[int]
    created_at: datetime
    tools_used: List[ToolCallInfo] = Field(default_factory=list, description="List of tools used to generate the response")


class ConversationHistoryResponse(BaseModel):
    """Full conversation history with messages"""
    conversation: ConversationResponse
    messages: List[MessageResponse]
    total_messages: int
