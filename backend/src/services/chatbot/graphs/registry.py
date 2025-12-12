"""
Graph Registry

Central registry for managing LangGraph configurations.
Provides factory pattern for creating different graph types.
"""

from typing import Dict, Callable, Any
from .simple_graphs import build_ui_graph_v1


# Graph builder registry
GRAPH_BUILDERS: Dict[str, Callable] = {}


def register_graph(name: str):
    """
    Decorator to register graph builder functions.

    Args:
        name (str): Unique name for the graph

    Usage:
        >>> @register_graph("my_graph_v1")
        ... def build_my_graph(checkpointer, **kwargs):
        ...     return create_react_agent(...)
    """
    def decorator(func: Callable) -> Callable:
        GRAPH_BUILDERS[name] = func
        return func
    return decorator


def get_graph(name: str, checkpointer, **kwargs) -> Any:
    """
    Get a compiled graph by name.

    Args:
        name (str): Graph name (e.g., "ui_graph_v1")
        checkpointer: LangGraph PostgresSaver instance
        **kwargs: Additional arguments passed to graph builder

    Returns:
        CompiledGraph: Compiled LangGraph ready for invocation

    Raises:
        ValueError: If graph name is not registered

    Usage:
        >>> from shared.database import get_langgraph_checkpointer
        >>> checkpointer = get_langgraph_checkpointer()
        >>> graph = get_graph("ui_graph_v1", checkpointer)
        >>> response = graph.invoke({"messages": [...]}, config={...})
    """
    if name not in GRAPH_BUILDERS:
        raise ValueError(
            f"Unknown graph: '{name}'. "
            f"Available graphs: {list(GRAPH_BUILDERS.keys())}"
        )

    builder = GRAPH_BUILDERS[name]
    return builder(checkpointer=checkpointer, **kwargs)


def list_available_graphs() -> list[str]:
    """
    List all registered graph names.

    Returns:
        list[str]: List of graph names
    """
    return list(GRAPH_BUILDERS.keys())


def get_graph_info(name: str) -> Dict[str, Any]:
    """
    Get information about a specific graph.

    Args:
        name (str): Graph name

    Returns:
        dict: Graph metadata (name, builder function, docstring)

    Raises:
        ValueError: If graph name is not registered
    """
    if name not in GRAPH_BUILDERS:
        raise ValueError(
            f"Unknown graph: '{name}'. "
            f"Available graphs: {list(GRAPH_BUILDERS.keys())}"
        )

    builder = GRAPH_BUILDERS[name]
    return {
        "name": name,
        "builder": builder.__name__,
        "description": builder.__doc__ or "No description available",
    }


# Register built-in graphs
register_graph("ui_graph_v1")(build_ui_graph_v1)

# Future registrations (Phase 2 & 3):
# from .workflow_graphs import build_workflow_graph_v1
# register_graph("workflow_graph_v1")(build_workflow_graph_v1)
#
# from .multi_agent import build_multi_agent_v1
# register_graph("multi_agent_v1")(build_multi_agent_v1)
