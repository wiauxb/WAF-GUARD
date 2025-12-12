"""
Simple Graph Implementations

Simple ReAct agents using LangGraph's built-in create_react_agent().
Following LangGraph best practices: use built-in patterns, not custom classes.
"""

from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from shared.config import settings
from services.chatbot.tools.registry import get_tools_for_categories
from services.chatbot.prompts.agent_prompts import get_system_prompt


def build_ui_graph_v1(
    checkpointer,
    model_name: str = None,
    temperature: float = None
):
    """
    Build a simple ReAct agent for WAF configuration assistance.

    This is the recommended approach from LangGraph documentation:
    - Uses create_react_agent() (built-in, optimized)
    - No custom agent classes needed
    - Automatic tool calling and conversation management
    - Checkpointer handles persistence automatically

    Args:
        checkpointer: LangGraph PostgresSaver instance for conversation persistence
        model_name (str): OpenAI model name (default: from settings.OPENAI_MODEL)
        temperature (float): Model temperature for response generation (default: from settings.CHATBOT_TEMPERATURE)

    Returns:
        CompiledGraph: Compiled LangGraph ready for invocation

    Usage:
        >>> from shared.database import get_langgraph_checkpointer
        >>> checkpointer = get_langgraph_checkpointer()
        >>> graph = build_ui_graph_v1(checkpointer)
        >>>
        >>> # Invoke with thread_id for conversation persistence
        >>> config = {"configurable": {"thread_id": "thread_abc123"}}
        >>> response = graph.invoke(
        ...     {"messages": [{"role": "user", "content": "Filter rules for /api"}]},
        ...     config
        ... )
        >>> print(response["messages"][-1].content)

    Architecture:
        User Message → Model (with tools) → Tool Execution → Model → Response
                         ↑                                            ↓
                         └────────── Checkpointer Persistence ───────┘
    """
    # Use configuration defaults if not specified
    if model_name is None:
        model_name = settings.OPENAI_MODEL
    if temperature is None:
        temperature = settings.CHATBOT_TEMPERATURE

    # Get WAF tools from registry
    tools = get_tools_for_categories(["waf"])

    # Create model
    model = ChatOpenAI(model=model_name, temperature=temperature)

    # Get system prompt
    system_prompt = get_system_prompt("ui_graph_v1")

    # Create ReAct agent with system prompt
    # The 'prompt' parameter accepts a string or SystemMessage
    graph = create_react_agent(
        model=model,
        tools=tools,
        checkpointer=checkpointer,
        prompt=system_prompt
    )

    return graph


# Future graph builders (Phase 2 & 3):
# def build_workflow_graph_v1(checkpointer, **kwargs):
#     """Workflow graph with routing and orchestration"""
#     pass
#
# def build_multi_agent_v1(checkpointer, **kwargs):
#     """Multi-agent supervisor with subgraphs"""
#     pass
