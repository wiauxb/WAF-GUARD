"""
Get Directives with Constant Tool

Tool to find directives that use a specific constant or variable.
"""

from langchain_core.tools import tool


@tool
def get_directives_with_constant(constant_name: str) -> dict:
    """
    Get the list of directives where a constant or variable is used.

    This tool traces all ModSecurity directives that reference the specified
    constant or variable name in the WAF configuration.

    Args:
        constant_name (str): The name of the constant/variable to search for

    Returns:
        dict: Dictionary containing directives using the constant

    Example:
        >>> get_directives_with_constant(constant_name="REQUEST_HEADERS")
        {
            "constant": "REQUEST_HEADERS",
            "directives": [
                {
                    "directive": "SecRule",
                    "rule_id": "950001",
                    "content": "SecRule REQUEST_HEADERS...",
                    "file": "/etc/modsecurity/rules.conf",
                    "line": 125
                }
            ],
            "status": "dummy_data"
        }
    """
    # DUMMY IMPLEMENTATION - Backend services not ready yet
    # Will be replaced with actual AnalysisService integration

    return {
        "constant": constant_name,
        "directives": [
            {
                "directive": "SecRule",
                "rule_id": "950001",
                "content": f"SecRule {constant_name} \"@rx .*\" \"id:950001,phase:2,deny,status:403,msg:'Blocked'\"",
                "file": "/etc/modsecurity/owasp-crs/rules.conf",
                "line": 125,
                "phase": 2,
                "action": "deny"
            },
            {
                "directive": "SecAction",
                "rule_id": "900001",
                "content": f"SecAction \"id:900001,phase:1,nolog,pass,setvar:{constant_name}=value\"",
                "file": "/etc/modsecurity/custom-rules.conf",
                "line": 42,
                "phase": 1,
                "action": "pass"
            },
            {
                "directive": "SecRuleUpdateTargetById",
                "rule_id": "950002",
                "content": f"SecRuleUpdateTargetById 950002 \"!{constant_name}\"",
                "file": "/etc/modsecurity/exclusions.conf",
                "line": 18,
                "phase": None,
                "action": "exclusion"
            }
        ],
        "total_count": 3,
        "usage_summary": {
            "total_rules": 2,
            "total_actions": 1,
            "total_exclusions": 1
        },
        "status": "dummy_data"
    }
