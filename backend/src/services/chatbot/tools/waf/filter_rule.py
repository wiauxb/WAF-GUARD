"""
WAF Rule Filtering Tool

Tool to filter ModSecurity rules based on location and host patterns.
"""

from langchain_core.tools import tool


@tool
def filter_rule(location: str, host: str) -> dict:
    """
    Filter rules of the WAF configuration based on location and host.

    The arguments are used in regex patterns to match rules.
    If the request is not explicit about exact match, use .* to match all
    locations/hosts that contain the string.

    Args:
        location (str): Regex pattern to filter the location (e.g., "/api.*", "/admin")
        host (str): Regex pattern to filter the host (e.g., "example.com.*", ".*")

    Returns:
        dict: Dictionary containing filtered rules and metadata

    Example:
        >>> filter_rule(location="/api.*", host=".*")
        {
            "rules": [
                {
                    "id": "rule_001",
                    "location": "/api/users",
                    "host": "api.example.com",
                    "action": "deny",
                    "rule_id": "ModSec_001",
                    "description": "Block SQL injection in API"
                }
            ],
            "total_count": 1,
            "status": "dummy_data"
        }
    """
    # DUMMY IMPLEMENTATION - Backend services not ready yet
    # Will be replaced with actual AnalysisService integration

    return {
        "rules": [
            {
                "id": "rule_001",
                "location": f"{location if location != '.*' else '/api/users'}",
                "host": f"{host if host != '.*' else 'api.example.com'}",
                "action": "deny",
                "rule_id": "ModSec_001",
                "description": "Block SQL injection attempts",
                "execution_order": 1
            },
            {
                "id": "rule_002",
                "location": f"{location if location != '.*' else '/api/admin'}",
                "host": f"{host if host != '.*' else 'admin.example.com'}",
                "action": "allow",
                "rule_id": "ModSec_002",
                "description": "Allow authenticated admin access",
                "execution_order": 2
            }
        ],
        "total_count": 2,
        "filters_applied": {
            "location": location,
            "host": host
        },
        "status": "dummy_data"
    }
