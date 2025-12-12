from sqlalchemy.orm import Session
from .repository import ConversationRepository
from .schemas import (
    ConversationCreateRequest,
    ConversationResponse,
    SendMessageRequest,
    ConversationHistoryResponse,
    MessageResponse,
    ConversationListFilters,
    ToolCallInfo
)
from .utils import parse_langchain_messages_to_responses
from typing import List, Optional
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class ChatbotService:
    """Business logic for chatbot and conversation management"""

    def __init__(self, db: Session, checkpointer=None):
        """
        Initialize ChatbotService.

        Args:
            db: SQLAlchemy session
            checkpointer: LangGraph checkpointer (optional, for LangGraph integration)
        """
        self.db = db
        self.checkpointer = checkpointer
        self.conversation_repo = ConversationRepository(db, checkpointer)

        # TODO: Initialize LangGraph components here
        # self.langgraph_app = ...

    def create_conversation(
        self,
        user_id: int,
        request: ConversationCreateRequest
    ) -> ConversationResponse:
        """
        Create a new conversation thread.

        Args:
            user_id: User creating the conversation
            request: Conversation creation data (title, configuration_id)

        Returns:
            ConversationResponse with thread metadata

        Raises:
            ValueError: If configuration_id is invalid
        """
        # Generate unique thread_id for LangGraph
        thread_id = f"thread_{uuid.uuid4().hex}"

        # Ensure thread_id is unique (very unlikely collision, but safety check)
        while self.conversation_repo.thread_id_exists(thread_id):
            thread_id = f"thread_{uuid.uuid4().hex}"

        # Create conversation metadata via repository
        conversation = self.conversation_repo.create(
            user_id=user_id,
            thread_id=thread_id,
            title=request.title,
            configuration_id=request.configuration_id
        )

        logger.info(f"Created conversation {conversation.id} with thread_id {thread_id}")

        return ConversationResponse.from_orm(conversation)

    def get_user_conversations(
        self,
        user_id: int,
        filters: Optional[ConversationListFilters] = None
    ) -> List[ConversationResponse]:
        """
        List user's conversations with optional filtering.

        Args:
            user_id: User identifier
            filters: Optional filters (configuration_id, limit, offset)

        Returns:
            List of ConversationResponse
        """
        if filters is None:
            filters = ConversationListFilters()

        # Get conversations via repository
        conversations = self.conversation_repo.get_user_conversations(
            user_id=user_id,
            configuration_id=filters.configuration_id,
            limit=filters.limit,
            offset=filters.offset
        )

        # TODO: Optionally join with configurations table to get configuration_name
        # For now, return without configuration_name
        return [ConversationResponse.from_orm(c) for c in conversations]

    def send_message(
        self,
        thread_id: str,
        message_request: SendMessageRequest,
        user_id: int
    ) -> MessageResponse:
        """
        Send message and get chatbot response.

        This method:
        1. Verifies user owns the conversation (via repository)
        2. Invokes LangGraph to process message (graph writes to checkpointer automatically)
        3. Updates conversation timestamp (via repository)
        4. Returns response

        Args:
            thread_id: LangGraph thread identifier
            message_request: Message content and optional configuration_id
            user_id: User sending the message

        Returns:
            MessageResponse with assistant's reply

        Raises:
            ValueError: If thread not found or user doesn't own conversation
        """
        # Get conversation metadata via repository
        conversation = self.conversation_repo.get_by_thread_id(thread_id)
        if not conversation:
            raise ValueError(f"Conversation with thread_id '{thread_id}' not found")

        # Verify ownership
        if conversation.user_id != user_id:
            raise ValueError("You don't have permission to access this conversation")

        # Import graph registry
        from .graphs.registry import get_graph

        # Get graph from registry
        graph_name = message_request.graph_name or "ui_graph_v1"
        try:
            graph = get_graph(
                name=graph_name,
                checkpointer=self.checkpointer
            )
        except ValueError as e:
            raise ValueError(f"Invalid graph name: {str(e)}")

        # Prepare input for LangGraph
        input_data = {
            "messages": [{"role": "user", "content": message_request.message}]
        }

        # Invoke graph (this automatically writes to checkpointer)
        config = {"configurable": {"thread_id": thread_id}}

        # Get current state to track existing messages count
        current_state = graph.get_state(config)
        existing_message_count = len(current_state.values.get("messages", []))

        response = graph.invoke(input_data, config)

        # Extract only NEW messages (from this exchange)
        all_messages = response["messages"]
        new_messages = all_messages[existing_message_count:]

        # Parse new messages to MessageResponse objects (with tool extraction)
        parsed_messages = parse_langchain_messages_to_responses(new_messages)

        # The last parsed message should be the assistant's response
        assistant_response = parsed_messages[-1] if parsed_messages else MessageResponse(
            role="assistant",
            content=all_messages[-1].content,
            timestamp=datetime.utcnow(),
            tools_used=None
        )

        # Update conversation timestamp via repository
        self.conversation_repo.update_timestamp(conversation)

        logger.info(f"Sent message to conversation {thread_id} using graph {graph_name}")

        return assistant_response

    def get_conversation_history(
        self,
        thread_id: str,
        user_id: int,
        limit: Optional[int] = None
    ) -> ConversationHistoryResponse:
        """
        Get full message history for a conversation.

        Args:
            thread_id: LangGraph thread identifier
            user_id: User requesting history
            limit: Optional limit on number of messages

        Returns:
            ConversationHistoryResponse with messages

        Raises:
            ValueError: If thread not found or user doesn't own conversation
        """
        # Get conversation metadata via repository
        conversation = self.conversation_repo.get_by_thread_id(thread_id)
        if not conversation:
            raise ValueError(f"Conversation with thread_id '{thread_id}' not found")

        # Verify ownership
        if conversation.user_id != user_id:
            raise ValueError("You don't have permission to access this conversation")

        # Get message history via repository
        messages = self.conversation_repo.get_thread_history(thread_id, limit)
        total_messages = self.conversation_repo.get_thread_message_count(thread_id)

        return ConversationHistoryResponse(
            conversation=ConversationResponse.from_orm(conversation),
            messages=messages,
            total_messages=total_messages
        )

    def delete_conversation(self, thread_id: str, user_id: int) -> bool:
        """
        Delete conversation metadata AND LangGraph checkpoints.

        Args:
            thread_id: LangGraph thread identifier
            user_id: User requesting deletion

        Returns:
            True on success

        Raises:
            ValueError: If thread not found or user doesn't own conversation
        """
        # Get conversation metadata via repository
        conversation = self.conversation_repo.get_by_thread_id(thread_id)
        if not conversation:
            raise ValueError(f"Conversation with thread_id '{thread_id}' not found")

        # Verify ownership
        if conversation.user_id != user_id:
            raise ValueError("You don't have permission to delete this conversation")

        # Delete via repository (handles both metadata and checkpoints)
        self.conversation_repo.delete(conversation)

        logger.info(f"Deleted conversation {thread_id} (metadata + checkpoints)")

        return True

    def rename_conversation(
        self,
        thread_id: str,
        new_title: str,
        user_id: int
    ) -> ConversationResponse:
        """
        Rename a conversation.

        Args:
            thread_id: LangGraph thread identifier
            new_title: New conversation title
            user_id: User requesting rename

        Returns:
            Updated ConversationResponse

        Raises:
            ValueError: If thread not found or user doesn't own conversation
        """
        # Get conversation metadata via repository
        conversation = self.conversation_repo.get_by_thread_id(thread_id)
        if not conversation:
            raise ValueError(f"Conversation with thread_id '{thread_id}' not found")

        # Verify ownership
        if conversation.user_id != user_id:
            raise ValueError("You don't have permission to rename this conversation")

        # Update title via repository
        conversation = self.conversation_repo.update_title(conversation, new_title)

        logger.info(f"Renamed conversation {thread_id} to '{new_title}'")

        return ConversationResponse.from_orm(conversation)

    async def send_message_stream(
        self,
        thread_id: str,
        message_request: SendMessageRequest,
        user_id: int
    ):
        """
        Send message and stream response in real-time.

        This method yields chunks as they're generated by the LLM,
        enabling real-time streaming to the frontend via Server-Sent Events (SSE).

        Args:
            thread_id: LangGraph thread identifier
            message_request: Message content and optional configuration_id
            user_id: User sending the message

        Yields:
            str: Content chunks as they're generated

        Raises:
            ValueError: If thread not found or user doesn't own conversation

        Note:
            After streaming completes, the conversation timestamp is updated.
            All messages are automatically persisted to the checkpointer.
        """
        # Get conversation metadata via repository
        conversation = self.conversation_repo.get_by_thread_id(thread_id)
        if not conversation:
            raise ValueError(f"Conversation with thread_id '{thread_id}' not found")

        # Verify ownership
        if conversation.user_id != user_id:
            raise ValueError("You don't have permission to access this conversation")

        # Import graph registry
        from .graphs.registry import get_graph

        # Get graph from registry
        graph_name = message_request.graph_name or "ui_graph_v1"
        try:
            graph = get_graph(
                name=graph_name,
                checkpointer=self.checkpointer
            )
        except ValueError as e:
            raise ValueError(f"Invalid graph name: {str(e)}")

        # Prepare input for LangGraph
        input_data = {
            "messages": [{"role": "user", "content": message_request.message}]
        }
        config = {"configurable": {"thread_id": thread_id}}

        # Stream with messages mode (LLM tokens)
        async for chunk, metadata in graph.astream(
            input_data,
            config,
            stream_mode="messages"
        ):
            # Filter for content chunks (not empty)
            if hasattr(chunk, 'content') and chunk.content:
                yield chunk.content

        # Update timestamp after streaming completes
        self.conversation_repo.update_timestamp(conversation)

        logger.info(f"Streamed message to conversation {thread_id} using graph {graph_name}")
