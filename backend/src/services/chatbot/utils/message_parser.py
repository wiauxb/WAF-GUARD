"""Message parsing utilities for converting LangChain messages to MessageResponse"""

from typing import List
from datetime import datetime
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
from ..schemas import MessageResponse, ToolCallInfo



def message_text(msg) -> str:
    """
    The visible prose of a message, whatever shape the provider returned.

    Chat Completions gives `content` as a string. The Responses API — which the GPT-5
    family requires for function calling — gives a LIST of blocks: reasoning blocks
    carrying an `encrypted_content` blob, then the text block. Passing that list on
    raises AttributeError on `.strip()`, and stringifying it dumps kilobytes of
    ciphertext into the UI and the database.

    `.text` takes the text blocks and nothing else.
    """
    text = getattr(msg, "text", None)
    if isinstance(text, str):               # current langchain: a property
        return text
    if callable(text):                      # older langchain exposed it as a method
        try:
            called = text()
        except Exception:                   # noqa: BLE001 - fall through to content
            called = None
        if isinstance(called, str):
            return called
    content = getattr(msg, "content", "")
    if isinstance(content, list):
        return "".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return content or ""


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
            text = message_text(msg)
            if text and text.strip():
                message_responses.append(MessageResponse(
                    role="assistant",
                    content=text,
                    timestamp=getattr(msg, "timestamp", datetime.utcnow()),
                    tools_used=(pending_tools or []) + tools
                ))
                pending_tools = None
            else:
                # No content yet - carry the tools forward to the message that answers.
                # ACCUMULATE: one turn commonly runs several rounds of tool calls, e.g.
                # match_url -> get_provenance -> read_config_file, each its own AIMessage.
                # Assigning here instead of extending dropped every round but the last, so a
                # reloaded conversation showed one tool where the live stream had shown six.
                pending_tools = (pending_tools or []) + tools
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
            content=message_text(msg),
            timestamp=timestamp,
            tools_used=tools_used
        ))

    return message_responses
