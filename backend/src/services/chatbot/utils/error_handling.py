"""
Error Handling Utilities

Utilities for handling errors in LangGraph tool execution.
Migrated from old chatbot implementation.
"""

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda
from langgraph.prebuilt import ToolNode


def handle_tool_error(state) -> dict:
    """
    Handle tool execution errors by creating ToolMessages.

    This function is called when a tool raises an exception during execution.
    It creates error messages for all tool calls in the most recent message.

    Args:
        state: Graph state containing error information

    Returns:
        dict: State update with error messages
    """
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls

    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\nPlease fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }


def create_tool_node_with_fallback(tools: list) -> ToolNode:
    """
    Create a ToolNode with error handling fallback.

    This wraps the standard ToolNode with error handling, so that tool
    execution errors are caught and converted to error messages rather
    than crashing the graph.

    Args:
        tools (list): List of LangChain tool functions

    Returns:
        ToolNode: Tool node with fallback error handling

    Usage:
        >>> from tools.registry import get_tools_for_categories
        >>> tools = get_tools_for_categories(["waf"])
        >>> tool_node = create_tool_node_with_fallback(tools)
    """
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )


def _print_event(event: dict, _printed: set, max_length: int = 1500):
    """
    Print graph events for debugging (utility function).

    This is a helper for debugging graph execution by printing messages
    as they flow through the graph.

    Args:
        event (dict): Graph event
        _printed (set): Set of message IDs already printed
        max_length (int): Maximum message length before truncation
    """
    current_state = event.get("dialog_state")
    # Uncomment for debugging:
    # if current_state:
    #     print("Currently in: ", current_state[-1])

    message = event.get("messages")
    if message:
        if isinstance(message, list):
            message = message[-1]
        if message.id not in _printed:
            msg_repr = message.pretty_repr(html=True)
            if len(msg_repr) > max_length:
                msg_repr = msg_repr[:max_length] + " ... (truncated)"
            # Uncomment for debugging:
            # print(msg_repr)
            _printed.add(message.id)
