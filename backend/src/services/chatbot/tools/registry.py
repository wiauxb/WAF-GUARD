"""
Tool Registry

Central registry for managing LangChain tools by category.
Provides easy access to tools for different graph configurations.
"""

from typing import List, Callable
from .waf import (
    filter_rule,
    get_constant_info,
    get_directives_with_constant,
    get_macro_call_trace,
    removed_by
)


# Tool categories for different use cases
TOOL_CATEGORIES = {
    "waf": [
        filter_rule,
        get_constant_info,
        get_directives_with_constant,
        get_macro_call_trace,
        removed_by
    ],
    "config": [],  # Future: Configuration management tools
    "analysis": [],  # Future: Advanced analysis tools
}


def get_tools_for_categories(categories: List[str]) -> List[Callable]:
    """
    Get all tools for the specified categories.

    Args:
        categories (List[str]): List of category names (e.g., ["waf", "config"])

    Returns:
        List[Callable]: List of tool functions

    Example:
        >>> tools = get_tools_for_categories(["waf"])
        >>> len(tools)
        5

        >>> tools = get_tools_for_categories(["waf", "config"])
        >>> # Returns all WAF and config tools
    """
    tools = []
    for category in categories:
        if category in TOOL_CATEGORIES:
            tools.extend(TOOL_CATEGORIES[category])
        else:
            raise ValueError(
                f"Unknown tool category: {category}. "
                f"Available categories: {list(TOOL_CATEGORIES.keys())}"
            )
    return tools


def list_tool_categories() -> List[str]:
    """
    List all available tool categories.

    Returns:
        List[str]: List of category names
    """
    return list(TOOL_CATEGORIES.keys())


def get_all_tools() -> List[Callable]:
    """
    Get all registered tools across all categories.

    Returns:
        List[Callable]: List of all tool functions
    """
    all_tools = []
    for tools in TOOL_CATEGORIES.values():
        all_tools.extend(tools)
    return all_tools
