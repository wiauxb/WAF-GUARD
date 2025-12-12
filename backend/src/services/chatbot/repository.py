from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from .models import Conversation
from .schemas import MessageResponse
from typing import Optional, List
from datetime import datetime

class ConversationRepository:
    """
    Data access layer for Conversation operations.
    Handles both conversation metadata (PostgreSQL) and message history (LangGraph checkpointer).
    """

    def __init__(self, db: Session, checkpointer=None):
        """
        Initialize repository.

        Args:
            db: SQLAlchemy session for conversation metadata
            checkpointer: LangGraph checkpointer for message history (optional, for LangGraph integration)
        """
        self.db = db
        self.checkpointer = checkpointer

    # ==================== Conversation Metadata Operations ====================

    def create(
        self,
        user_id: int,
        thread_id: str,
        title: Optional[str] = None,
        configuration_id: Optional[int] = None
    ) -> Conversation:
        """Create a new conversation"""
        conversation = Conversation(
            user_id=user_id,
            thread_id=thread_id,
            title=title,
            configuration_id=configuration_id
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_by_id(self, conversation_id: int) -> Optional[Conversation]:
        """Get conversation by ID"""
        return self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

    def get_by_thread_id(self, thread_id: str) -> Optional[Conversation]:
        """Get conversation by thread_id"""
        return self.db.query(Conversation).filter(
            Conversation.thread_id == thread_id
        ).first()

    def get_user_conversations(
        self,
        user_id: int,
        configuration_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Conversation]:
        """Get user's conversations with optional filtering"""
        query = self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        )

        # Filter by configuration if provided
        if configuration_id is not None:
            query = query.filter(Conversation.configuration_id == configuration_id)

        # Order by most recent first
        query = query.order_by(desc(Conversation.updated_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        return query.all()

    def update_title(self, conversation: Conversation, title: str) -> Conversation:
        """Update conversation title"""
        conversation.title = title
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def update_timestamp(self, conversation: Conversation) -> Conversation:
        """Update conversation timestamp (called when new message is sent)"""
        conversation.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def delete(self, conversation: Conversation) -> bool:
        """
        Delete conversation metadata AND associated LangGraph checkpoints.

        Args:
            conversation: Conversation to delete

        Returns:
            True on success
        """
        thread_id = conversation.thread_id

        # Delete conversation metadata from PostgreSQL
        self.db.delete(conversation)
        self.db.commit()

        # Delete LangGraph checkpoints if checkpointer is available
        if self.checkpointer:
            self._delete_thread_checkpoints(thread_id)

        return True

    def thread_id_exists(self, thread_id: str) -> bool:
        """Check if thread_id already exists"""
        return self.db.query(Conversation).filter(
            Conversation.thread_id == thread_id
        ).count() > 0

    def verify_user_owns_conversation(self, conversation_id: int, user_id: int) -> bool:
        """Verify that the user owns the conversation"""
        conversation = self.db.query(Conversation).filter(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        ).first()
        return conversation is not None

    # ==================== LangGraph Checkpointer Operations ====================

    def get_thread_history(
        self,
        thread_id: str,
        limit: Optional[int] = None
    ) -> List[MessageResponse]:
        """
        Get message history for a thread from LangGraph checkpointer.

        Args:
            thread_id: LangGraph thread identifier
            limit: Optional limit on number of messages

        Returns:
            List of MessageResponse objects

        Note:
            Returns empty list if checkpointer is not initialized.
            Implement this when LangGraph is integrated.
        """
        if not self.checkpointer:
            # Checkpointer not initialized - return empty list
            return []

        # Get checkpoint for thread
        config = {"configurable": {"thread_id": thread_id}}

        try:
            checkpoint_tuple = self.checkpointer.get_tuple(config)
            if not checkpoint_tuple:
                return []

            # Extract messages from checkpoint
            checkpoint = checkpoint_tuple.checkpoint
            messages = checkpoint.get("channel_values", {}).get("messages", [])

            # Convert to MessageResponse objects
            message_responses = []
            for msg in messages:
                message_responses.append(MessageResponse(
                    role="user" if msg.type == "human" else "assistant",
                    content=msg.content,
                    timestamp=getattr(msg, "timestamp", datetime.utcnow())
                ))

            # Apply limit if specified
            if limit:
                message_responses = message_responses[-limit:]

            return message_responses

        except Exception as e:
            from logging import getLogger
            logger = getLogger(__name__)
            logger.error(f"Failed to get thread history for {thread_id}: {e}")
            return []

    def get_thread_message_count(self, thread_id: str) -> int:
        """
        Get total number of messages in a thread.

        Args:
            thread_id: LangGraph thread identifier

        Returns:
            Number of messages in the thread

        Note:
            Returns 0 if checkpointer is not initialized.
            Implement this when LangGraph is integrated.
        """
        if not self.checkpointer:
            return 0

        # Get message history and return count
        messages = self.get_thread_history(thread_id)
        return len(messages)

    def _delete_thread_checkpoints(self, thread_id: str) -> bool:
        """
        Delete all LangGraph checkpoints for a thread.

        Args:
            thread_id: LangGraph thread identifier

        Returns:
            True on success

        Note:
            This is called internally by delete() method.
            Implement this when LangGraph is integrated.
        """
        if not self.checkpointer:
            return True

        # TODO: Implement when LangGraph is integrated
        # Example implementation (depends on checkpointer API):
        # config = {"configurable": {"thread_id": thread_id}}
        # self.checkpointer.delete(config)
        # Or if using PostgresSaver:
        # self.checkpointer.delete_thread(thread_id)

        return True

    def thread_has_messages(self, thread_id: str) -> bool:
        """
        Check if a thread has any messages.

        Args:
            thread_id: LangGraph thread identifier

        Returns:
            True if thread has messages, False otherwise

        Note:
            Returns False if checkpointer is not initialized.
            Implement this when LangGraph is integrated.
        """
        if not self.checkpointer:
            return False

        # TODO: Implement when LangGraph is integrated
        # return self.get_thread_message_count(thread_id) > 0

        return False
