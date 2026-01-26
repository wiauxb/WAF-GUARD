"""
Output models for API/MCP responses.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ActionInfo(BaseModel):
    """Information about a single action."""

    name: str = Field(description="Action name (e.g., 'deny', 'log')")
    value: Optional[str] = Field(default=None, description="Action value if any")
    group: str = Field(description="Action group (DISRUPTIVE, METADATA, etc.)")


class RuleInfo(BaseModel):
    """
    Detailed information about a single rule.
    """

    id: Optional[int] = Field(default=None, description="Rule ID")
    type: str = Field(description="Rule type (SecRule, SecAction, etc.)")
    phase: Optional[int] = Field(default=None, description="Processing phase")

    variables: Optional[str] = Field(
        default=None,
        description="Variables being inspected",
    )

    operator: Optional[str] = Field(
        default=None,
        description="Operator and pattern",
    )

    msg: Optional[str] = Field(
        default=None,
        description="Rule message",
    )

    severity: Optional[str] = Field(
        default=None,
        description="Severity level",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Associated tags",
    )

    actions: list[ActionInfo] = Field(
        default_factory=list,
        description="All actions on this rule",
    )

    line_number: Optional[int] = Field(
        default=None,
        description="Line number in source file",
    )

    is_chained: bool = Field(
        default=False,
        description="Whether this rule is part of a chain",
    )

    chain_count: int = Field(
        default=0,
        description="Number of chained rules",
    )


class RuleStatistics(BaseModel):
    """Statistics about a ruleset."""

    total_rules: int = Field(description="Total number of rules")
    secrules: int = Field(description="Number of SecRule directives")
    secactions: int = Field(description="Number of SecAction directives")
    comments: int = Field(description="Number of comments")

    by_phase: dict[int, int] = Field(
        default_factory=dict,
        description="Rule count by phase",
    )

    by_severity: dict[str, int] = Field(
        default_factory=dict,
        description="Rule count by severity",
    )

    top_tags: list[tuple[str, int]] = Field(
        default_factory=list,
        description="Most common tags with counts",
    )

    id_range: Optional[tuple[int, int]] = Field(
        default=None,
        description="Min and max rule IDs",
    )


class AnalysisResult(BaseModel):
    """
    Complete analysis result.
    """

    source: Optional[str] = Field(
        default=None,
        description="Source file or identifier",
    )

    statistics: Optional[RuleStatistics] = Field(
        default=None,
        description="Ruleset statistics",
    )

    rules: list[RuleInfo] = Field(
        default_factory=list,
        description="Analyzed rules (may be filtered)",
    )

    filter_applied: bool = Field(
        default=False,
        description="Whether a filter was applied",
    )

    filtered_count: int = Field(
        default=0,
        description="Number of rules after filtering",
    )
