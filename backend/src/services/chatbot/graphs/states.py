"""
Graph State Definitions

State schemas for different LangGraph implementations.
Following LangGraph best practices: store raw data, not formatted text.
"""

from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages


class MessagesState(TypedDict):
    """
    Simple state for ReAct agent (Phase 1 MVP).

    This minimal state is used with create_react_agent() for basic
    conversational interactions with tools.

    **Best Practice**: Store raw data only. Formatting happens in nodes/prompts.
    """
    messages: Annotated[list, add_messages]


class WAFAnalysisState(TypedDict):
    """
    Enhanced state for workflow graphs (Phase 2 - Future).

    This state adds context and routing information for more complex
    workflow patterns with multiple processing paths.

    **Best Practice**:
    - Store raw data only (query_type, tool_results)
    - Do NOT store formatted text (formatted_response, summary, etc.)
    - Compute formatted output on-demand in nodes
    """
    messages: Annotated[list, add_messages]
    configuration_id: Optional[int]  # WAF configuration being analyzed
    query_type: Optional[str]  # Classification result (e.g., "rule_filter", "macro_trace")
    tool_results: dict  # Raw tool outputs (unformatted)
    # NOT: formatted_response, summary, analysis_text (compute these in nodes)


# Future states for Phase 3 multi-agent workflows
# class MultiAgentState(TypedDict):
#     """State for multi-agent supervisor pattern"""
#     messages: Annotated[list, add_messages]
#     next_agent: Optional[str]  # Routing decision
#     agent_outputs: dict  # Raw outputs from specialist agents
#     configuration_id: Optional[int]
