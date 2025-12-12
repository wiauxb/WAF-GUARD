"""
Constant Information Tool

Tool to retrieve information about constants and variables in the WAF configuration.
"""

from langchain_core.tools import tool


@tool
def get_constant_info(constant_name: str) -> dict:
    """
    Get information about constants and variables in the configuration that contain constant_name.

    This tool searches for variable definitions, includes, and constants that match
    the provided name pattern.

    Args:
        constant_name (str): The name of the constant/variable to find (supports partial matching)

    Returns:
        dict: Dictionary containing matching constants and their definitions

    Example:
        >>> get_constant_info(constant_name="API_KEY")
        {
            "constants": [
                {
                    "name": "API_KEY_HEADER",
                    "value": "X-API-Key",
                    "type": "variable",
                    "file": "/etc/modsecurity/variables.conf",
                    "line": 15
                }
            ],
            "status": "dummy_data"
        }
    """
    # DUMMY IMPLEMENTATION - Backend services not ready yet
    # Will be replaced with actual AnalysisService integration

    return {
        "search_term": constant_name,
        "constants": [
            {
                "name": f"{constant_name}_HEADER",
                "value": "X-Custom-Header",
                "type": "variable",
                "file": "/etc/modsecurity/variables.conf",
                "line": 15,
                "scope": "global"
            },
            {
                "name": f"{constant_name}_TIMEOUT",
                "value": "3600",
                "type": "constant",
                "file": "/etc/modsecurity/constants.conf",
                "line": 42,
                "scope": "global"
            },
            {
                "name": f"DEFAULT_{constant_name}",
                "value": "enabled",
                "type": "variable",
                "file": "/etc/modsecurity/defaults.conf",
                "line": 8,
                "scope": "server"
            }
        ],
        "total_count": 3,
        "status": "dummy_data"
    }
