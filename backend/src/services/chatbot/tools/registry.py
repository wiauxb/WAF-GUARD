"""
Tool registry.

One category today. The previously-declared `config` and `analysis` categories were empty
placeholders and have been dropped — an empty category is a promise the code does not keep.
"""

from typing import Callable, List

from .waf import ALL_TOOLS

TOOL_CATEGORIES = {
    "waf": ALL_TOOLS,
}


def get_tools_for_categories(categories: List[str]) -> List[Callable]:
    """Tools for the named categories. An unknown category is a programming error."""
    tools: List[Callable] = []
    for category in categories:
        if category not in TOOL_CATEGORIES:
            raise ValueError(
                f"Unknown tool category: {category}. "
                f"Available: {list(TOOL_CATEGORIES)}"
            )
        tools.extend(TOOL_CATEGORIES[category])
    return tools


def get_all_tools() -> List[Callable]:
    return [t for tools in TOOL_CATEGORIES.values() for t in tools]


def list_tool_categories() -> List[str]:
    return list(TOOL_CATEGORIES)
