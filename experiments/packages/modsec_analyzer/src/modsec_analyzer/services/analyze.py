"""
Analyzer service - Main use-case orchestrator.
"""

from pathlib import Path
from typing import Optional

from ..domain.rules import SecRule, CommentRule, SecAction
from ..domain.ruleset import RuleSet
from ..parsing.msc_adapter import MscAdapter
from ..api_models.input import AnalysisRequest, RuleFilter
from ..api_models.output import (
    AnalysisResult,
    RuleInfo,
    RuleStatistics,
    ActionInfo,
)


class AnalyzerService:
    """
    Main service for analyzing ModSecurity rules.

    Orchestrates parsing, filtering, and analysis operations.
    """

    def __init__(self, adapter: Optional[MscAdapter] = None):
        """
        Initialize the analyzer service.

        Args:
            adapter: Optional MscAdapter instance (creates default if not provided)
        """
        self.adapter = adapter or MscAdapter()

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        """
        Perform analysis based on the request.

        Args:
            request: Analysis request with source and filter options

        Returns:
            Complete analysis result
        """
        # Parse the rules
        ruleset = self._load_ruleset(request)

        # Apply filter if provided
        filtered_ruleset = ruleset
        filter_applied = False

        if request.filter:
            filtered_ruleset = self._apply_filter(ruleset, request.filter)
            filter_applied = True

        # Build result
        result = AnalysisResult(
            source=request.source_path,
            filter_applied=filter_applied,
            filtered_count=len(filtered_ruleset),
        )

        # Add statistics if requested
        if request.include_stats:
            result.statistics = self._compute_statistics(ruleset)

        # Add rule details if requested
        if request.include_rules:
            result.rules = [
                self._rule_to_info(rule)
                for rule in filtered_ruleset.sec_rules
            ]

        return result

    def _load_ruleset(self, request: AnalysisRequest) -> RuleSet:
        """Load ruleset from request source."""
        if request.config_content:
            return self.adapter.parse_string(request.config_content)
        elif request.source_path:
            return self.adapter.parse_file(request.source_path)
        else:
            raise ValueError("Either source_path or config_content must be provided")

    def _apply_filter(self, ruleset: RuleSet, filter: RuleFilter) -> RuleSet:
        """Apply filter criteria to ruleset."""
        result = ruleset

        if filter.rule_ids:
            result = result.filter(
                lambda r: isinstance(r, SecRule) and r.id in filter.rule_ids
            )

        if filter.id_range:
            start, end = filter.id_range
            result = result.by_id_range(start, end)

        if filter.phases:
            from ..domain.enums import Phase
            result = result.filter(
                lambda r: isinstance(r, SecRule)
                and r.phase is not None
                and r.phase.value in filter.phases
            )

        if filter.tags:
            # Must have ALL specified tags
            for tag in filter.tags:
                result = result.by_tag(tag)

        if filter.any_tag:
            # Must have ANY specified tag
            result = result.filter(
                lambda r: isinstance(r, SecRule)
                and any(tag in r.tags for tag in filter.any_tag)
            )

        if filter.severities:
            result = result.filter(
                lambda r: isinstance(r, SecRule)
                and r.severity in filter.severities
            )

        if filter.has_action:
            result = result.with_action(filter.has_action)

        return result

    def _compute_statistics(self, ruleset: RuleSet) -> RuleStatistics:
        """Compute statistics for a ruleset."""
        sec_rules = ruleset.sec_rules

        # Count by type
        secactions = sum(1 for r in ruleset.rules if isinstance(r, SecAction))
        comments = sum(1 for r in ruleset.rules if isinstance(r, CommentRule))

        # Count by phase
        by_phase: dict[int, int] = {}
        for rule in sec_rules:
            if rule.phase:
                phase_num = rule.phase.value
                by_phase[phase_num] = by_phase.get(phase_num, 0) + 1

        # Count by severity
        by_severity: dict[str, int] = {}
        for rule in sec_rules:
            if rule.severity:
                by_severity[rule.severity] = by_severity.get(rule.severity, 0) + 1

        # Count tags
        tag_counts: dict[str, int] = {}
        for rule in sec_rules:
            for tag in rule.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:10]

        # ID range
        ids = [r.id for r in sec_rules if r.id is not None]
        id_range = (min(ids), max(ids)) if ids else None

        return RuleStatistics(
            total_rules=len(ruleset),
            secrules=len(sec_rules),
            secactions=secactions,
            comments=comments,
            by_phase=by_phase,
            by_severity=by_severity,
            top_tags=top_tags,
            id_range=id_range,
        )

    def _rule_to_info(self, rule: SecRule) -> RuleInfo:
        """Convert a SecRule to RuleInfo output model."""
        actions = [
            ActionInfo(
                name=a.raw_name,
                value=str(a.value) if a.value else None,
                group=a.group.name,
            )
            for a in rule.actions
        ]

        return RuleInfo(
            id=rule.id,
            type=rule.rule_type,
            phase=rule.phase.value if rule.phase else None,
            variables=rule.variables,
            operator=rule.operator,
            msg=rule.msg,
            severity=rule.severity,
            tags=rule.tags,
            actions=actions,
            line_number=rule.line_number,
            is_chained=rule.is_chained,
            chain_count=len(rule.chained_rules),
        )
