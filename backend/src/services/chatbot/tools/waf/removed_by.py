"""
Removed By Tool

Tool to find which directives removed a specific configuration node.
"""

from langchain_core.tools import tool


@tool
def removed_by(node_id: int) -> dict:
    """
    Get the list of directives that removed a node based on its ID.

    This tool helps trace which configuration directives caused a particular
    node to be removed or disabled in the WAF configuration.

    Args:
        node_id (int): The ID of the node to investigate

    Returns:
        dict: Dictionary containing directives that removed the node

    Example:
        >>> removed_by(node_id=12345)
        {
            "node_id": 12345,
            "removed_by_directives": [
                {
                    "directive": "SecRuleRemoveById",
                    "target_rule_id": "950001",
                    "file": "/etc/modsecurity/custom.conf",
                    "line": 42
                }
            ],
            "status": "dummy_data"
        }
    """
    # DUMMY IMPLEMENTATION - Backend services not ready yet
    # Will be replaced with actual AnalysisService integration

    return {
        "node_id": node_id,
        "removed_by_directives": [
            {
                "directive": "SecRuleRemoveById",
                "target_rule_id": "950001",
                "file": "/etc/modsecurity/custom-rules.conf",
                "line": 42,
                "reason": "Rule causes false positives for API endpoints"
            },
            {
                "directive": "SecRuleRemoveByTag",
                "target_tag": "OWASP_CRS/WEB_ATTACK/SQL_INJECTION",
                "file": "/etc/modsecurity/exclusions.conf",
                "line": 18,
                "reason": "Excluded for specific application compatibility"
            }
        ],
        "total_count": 2,
        "status": "dummy_data"
    }
