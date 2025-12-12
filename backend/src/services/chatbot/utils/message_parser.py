"""Message parsing utilities for converting LangChain messages to MessageResponse"""

from typing import List
from datetime import datetime
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
from ..schemas import MessageResponse, ToolCallInfo


def parse_langchain_messages_to_responses(messages: list) -> List[MessageResponse]:
    """
    Convert LangChain messages to MessageResponse objects with tool extraction.

    This function handles the LangGraph tool usage pattern:
    1. Builds a map of tool results (ToolMessage.tool_call_id -> result)
    2. When an AIMessage has tool_calls, stores them to attach to the next AI response
    3. Combines tool_calls with the subsequent AIMessage that contains the actual response
    4. Skips ToolMessage instances (they're metadata, not user-facing messages)
    5. Skips AIMessages that only contain tool_calls without content

    Args:
        messages: List of LangChain messages (HumanMessage, AIMessage, ToolMessage)

    Returns:
        List of MessageResponse objects with tools properly associated with their responses

    Example:
        When tools are used, LangGraph creates:
        - AIMessage(tool_calls=[...], content="")  <- tool invocation
        - ToolMessage(result=...)                  <- tool execution
        - AIMessage(content="final response")      <- final answer

        These get combined into one MessageResponse with both content and tools_used.
    """
    message_responses = []

    # Step 1: Build a map of tool call IDs to their results
    tool_results = {}
    for msg in messages:
        if isinstance(msg, ToolMessage):
            tool_results[msg.tool_call_id] = msg.content

    # Step 2: Convert messages, combining tool calls with their responses
    pending_tools = None  # Store tool calls waiting to be attached to next AI response

    for msg in messages:
        # Skip ToolMessage - they're metadata, not user-facing messages
        if isinstance(msg, ToolMessage):
            continue

        # Handle AIMessage with tool calls
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            # Extract tool info
            tools = []
            for tool_call in msg.tool_calls:
                tool_info = ToolCallInfo(
                    name=tool_call.get('name', 'unknown'),
                    arguments=tool_call.get('args', {}),
                    result=tool_results.get(tool_call.get('id'), None)
                )
                tools.append(tool_info)

            # If this message has actual content, include it with tools
            if msg.content and msg.content.strip():
                message_responses.append(MessageResponse(
                    role="assistant",
                    content=msg.content,
                    timestamp=getattr(msg, "timestamp", datetime.utcnow()),
                    tools_used=tools
                ))
            else:
                # No content yet - store tools to attach to next AI message
                pending_tools = tools
            continue

        # Handle regular messages (user or AI without tool calls)
        if isinstance(msg, HumanMessage) or msg.type == "human":
            role = "user"
            tools_used = None
        else:
            role = "assistant"
            # Attach pending tools if this is the AI response after tool execution
            tools_used = pending_tools
            pending_tools = None  # Clear pending tools after attaching

        # Extract timestamp
        timestamp = getattr(msg, "timestamp", datetime.utcnow())

        # Create MessageResponse
        message_responses.append(MessageResponse(
            role=role,
            content=msg.content,
            timestamp=timestamp,
            tools_used=tools_used
        ))

    return message_responses
