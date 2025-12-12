from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
from services.chatbot.service import ChatbotService
from services.chatbot.schemas import (
    ConversationCreateRequest,
    ConversationResponse,
    SendMessageRequest,
    ChatResponse,
    ConversationHistoryResponse,
    ConversationListFilters,
    ConversationRenameRequest
)
from services.auth.schemas import UserInfo
from shared.schemas import SuccessResponse
from api.dependencies import get_current_user, get_chatbot_service

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: ConversationCreateRequest,
    current_user: UserInfo = Depends(get_current_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Create a new conversation thread.

    - **title**: Optional conversation title
    - **configuration_id**: Optional configuration to link with this conversation

    Returns conversation metadata including unique thread_id for LangGraph.
    """
    try:
        return chatbot_service.create_conversation(current_user.id, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    configuration_id: Optional[int] = Query(None, description="Filter by configuration ID"),
    limit: int = Query(20, ge=1, le=100, description="Maximum conversations to return"),
    offset: int = Query(0, ge=0, description="Number of conversations to skip"),
    current_user: UserInfo = Depends(get_current_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    List user's conversations with optional filtering.

    - **configuration_id**: Filter conversations linked to specific configuration
    - **limit**: Maximum number of conversations to return (1-100, default: 20)
    - **offset**: Number of conversations to skip for pagination (default: 0)

    Returns list of conversations sorted by most recent first.
    """
    filters = ConversationListFilters(
        configuration_id=configuration_id,
        limit=limit,
        offset=offset
    )
    return chatbot_service.get_user_conversations(current_user.id, filters)


@router.post("/conversations/{thread_id}/messages", response_model=ChatResponse)
async def send_message(
    thread_id: str,
    request: SendMessageRequest,
    current_user: UserInfo = Depends(get_current_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Send a message to a conversation and get chatbot response.

    - **thread_id**: LangGraph thread identifier
    - **message**: Message content (1-10000 characters)
    - **configuration_id**: Optional configuration context for this message

    Uses LangGraph for conversation state management.
    Returns assistant's response.
    """
    try:
        return chatbot_service.send_message(thread_id, request, current_user.id)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        elif "permission" in str(e):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/conversations/{thread_id}/messages/stream")
async def send_message_stream(
    thread_id: str,
    request: SendMessageRequest,
    current_user: UserInfo = Depends(get_current_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Send a message and stream the response in real-time.

    Returns Server-Sent Events (SSE) stream of response chunks.

    - **thread_id**: LangGraph thread identifier
    - **message**: Message content (1-10000 characters)
    - **configuration_id**: Optional configuration context for this message
    - **graph_name**: Optional graph type to use (default: "ui_graph_v1")

    Uses LangGraph streaming to provide real-time response generation.
    Frontend should use EventSource to receive streaming chunks.

    Example frontend usage:
    ```javascript
    const eventSource = new EventSource('/api/v1/chatbot/conversations/{thread_id}/messages/stream');
    eventSource.onmessage = (event) => {
        console.log(event.data); // Response chunk
    };
    ```
    """
    try:
        # Verify ownership upfront
        conversation = chatbot_service.conversation_repo.get_by_thread_id(thread_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation with thread_id '{thread_id}' not found"
            )
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this conversation"
            )

        # Create streaming generator
        async def generate():
            try:
                async for chunk in chatbot_service.send_message_stream(
                    thread_id, request, current_user.id
                ):
                    # SSE format: data: {content}\n\n
                    yield f"data: {chunk}\n\n"
            except Exception as e:
                # Send error as SSE event
                yield f"data: [ERROR] {str(e)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )

    except HTTPException:
        raise
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        elif "permission" in str(e):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/conversations/{thread_id}/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    thread_id: str,
    limit: Optional[int] = Query(None, ge=1, description="Limit number of messages"),
    current_user: UserInfo = Depends(get_current_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Get full message history for a conversation.

    - **thread_id**: LangGraph thread identifier
    - **limit**: Optional limit on number of messages to return

    Returns conversation metadata and full message history from LangGraph.
    """
    try:
        return chatbot_service.get_conversation_history(thread_id, current_user.id, limit)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        elif "permission" in str(e):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/conversations/{thread_id}", response_model=SuccessResponse)
async def delete_conversation(
    thread_id: str,
    current_user: UserInfo = Depends(get_current_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Delete a conversation.

    - **thread_id**: LangGraph thread identifier

    Note: This deletes the conversation metadata from the database.
    LangGraph checkpoints remain in the checkpointer (intentional design).
    """
    try:
        chatbot_service.delete_conversation(thread_id, current_user.id)
        return SuccessResponse(message=f"Conversation {thread_id} deleted successfully")
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        elif "permission" in str(e):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/conversations/{thread_id}/title", response_model=ConversationResponse)
async def rename_conversation(
    thread_id: str,
    request: ConversationRenameRequest,
    current_user: UserInfo = Depends(get_current_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Rename a conversation.

    - **thread_id**: LangGraph thread identifier
    - **title**: New conversation title (1-255 characters)

    Returns updated conversation metadata.
    """
    try:
        return chatbot_service.rename_conversation(thread_id, request.title, current_user.id)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        elif "permission" in str(e):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
