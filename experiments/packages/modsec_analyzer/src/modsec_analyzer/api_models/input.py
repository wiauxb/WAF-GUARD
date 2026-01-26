"""
Input models for API/MCP requests.
"""

from typing import Optional

from pydantic import BaseModel, Field


class RuleFilter(BaseModel):
    """
    Filter criteria for selecting rules.

    All fields are optional; when multiple are specified,
    they are combined with AND logic.
    """

    rule_ids: Optional[list[int]] = Field(
        default=None,
        description="Filter by specific rule IDs",
    )

    id_range: Optional[tuple[int, int]] = Field(
        default=None,
        description="Filter by rule ID range (inclusive)",
    )

    phases: Optional[list[int]] = Field(
        default=None,
        description="Filter by processing phases (1-5)",
    )

    tags: Optional[list[str]] = Field(
        default=None,
        description="Filter by tags (rules must have ALL specified tags)",
    )

    any_tag: Optional[list[str]] = Field(
        default=None,
        description="Filter by tags (rules must have ANY specified tag)",
    )

    severities: Optional[list[str]] = Field(
        default=None,
        description="Filter by severity levels",
    )

    has_action: Optional[str] = Field(
        default=None,
        description="Filter rules that have a specific action",
    )

    search_text: Optional[str] = Field(
        default=None,
        description="Search in rule text (variables, operator, msg)",
    )


class AnalysisRequest(BaseModel):
    """
    Request for rule analysis.
    """

    source_path: Optional[str] = Field(
        default=None,
        description="Path to configuration file or directory",
    )

    config_content: Optional[str] = Field(
        default=None,
        description="Configuration content as string",
    )

    filter: Optional[RuleFilter] = Field(
        default=None,
        description="Optional filter to apply before analysis",
    )

    include_stats: bool = Field(
        default=True,
        description="Include statistics in the response",
    )

    include_rules: bool = Field(
        default=True,
        description="Include rule details in the response",
    )
