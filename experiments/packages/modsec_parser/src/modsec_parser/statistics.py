"""
Statistics calculation for ModSecurity configurations.

Provides comprehensive statistics about parsed configurations,
including rule counts, tag distributions, operator usage, etc.
"""

from collections import Counter
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .models import ParsedConfiguration, SecRule

if TYPE_CHECKING:
    pass


class FileStatistics(BaseModel):
    """Statistics for a single configuration file."""

    file_path: str
    rule_count: int = 0
    secrule_count: int = 0
    secaction_count: int = 0
    secmarker_count: int = 0
    directive_count: int = 0
    tags: dict[str, int] = Field(default_factory=dict)


class ConfigurationStatistics(BaseModel):
    """Comprehensive statistics for a ModSecurity configuration."""

    # File counts
    total_files: int = 0

    # Directive counts
    total_rules: int = 0
    total_secrules: int = 0
    total_secactions: int = 0
    total_secmarkers: int = 0
    total_directives: int = 0

    # Chain statistics
    chained_rules_count: int = 0

    # Distributions
    rules_by_phase: dict[int, int] = Field(default_factory=dict)
    rules_by_severity: dict[str, int] = Field(default_factory=dict)
    rules_by_tag: dict[str, int] = Field(default_factory=dict)
    rules_by_file: dict[str, int] = Field(default_factory=dict)

    # Usage statistics
    operators_used: dict[str, int] = Field(default_factory=dict)
    variables_used: dict[str, int] = Field(default_factory=dict)
    actions_used: dict[str, int] = Field(default_factory=dict)

    # Lists
    unique_tags: list[str] = Field(default_factory=list)
    unique_operators: list[str] = Field(default_factory=list)
    unique_variables: list[str] = Field(default_factory=list)

    # Per-file breakdown
    per_file: dict[str, FileStatistics] = Field(default_factory=dict)


class StatisticsCalculator:
    """Calculates statistics from a parsed configuration."""

    @staticmethod
    def calculate(config: ParsedConfiguration) -> ConfigurationStatistics:
        """
        Calculate comprehensive statistics for a configuration.

        Args:
            config: Parsed configuration to analyze.

        Returns:
            ConfigurationStatistics with all computed metrics.
        """
        stats = ConfigurationStatistics()

        # File count
        stats.total_files = len(config.files)

        # Basic counts
        stats.total_rules = len(config.rules)
        stats.total_secrules = config.total_secrules
        stats.total_secactions = config.total_secactions
        stats.total_secmarkers = len(config.markers)
        stats.total_directives = len(config.directives)

        # Initialize counters
        phase_counter: Counter[int] = Counter()
        severity_counter: Counter[str] = Counter()
        tag_counter: Counter[str] = Counter()
        file_counter: Counter[str] = Counter()
        operator_counter: Counter[str] = Counter()
        variable_counter: Counter[str] = Counter()
        action_counter: Counter[str] = Counter()

        # Per-file stats initialization
        for filepath in config.files:
            stats.per_file[filepath] = FileStatistics(file_path=filepath)

        # Process rules
        for rule in config.rules:
            # File statistics
            if rule.file_path:
                file_counter[rule.file_path] += 1
                if rule.file_path in stats.per_file:
                    stats.per_file[rule.file_path].rule_count += 1
                    if isinstance(rule, SecRule):
                        stats.per_file[rule.file_path].secrule_count += 1
                    else:
                        stats.per_file[rule.file_path].secaction_count += 1

            # Phase
            if rule.phase is not None:
                phase_counter[rule.phase] += 1

            # Severity (SecRule only)
            if isinstance(rule, SecRule) and rule.severity:
                severity_counter[rule.severity] += 1

            # Tags
            for tag in rule.tags:
                tag_counter[tag] += 1
                if rule.file_path and rule.file_path in stats.per_file:
                    file_stats = stats.per_file[rule.file_path]
                    file_stats.tags[tag] = file_stats.tags.get(tag, 0) + 1

            # Chained rules
            if isinstance(rule, SecRule) and rule.chained:
                stats.chained_rules_count += 1

            # Operators and variables (SecRule only)
            if isinstance(rule, SecRule):
                if rule.operator.name:
                    operator_counter[rule.operator.name] += 1
                for var in rule.variables:
                    variable_counter[var.name] += 1

            # Actions
            for action in rule.actions:
                action_counter[action.name] += 1

        # Process markers for per-file stats
        for marker in config.markers:
            if marker.file_path and marker.file_path in stats.per_file:
                stats.per_file[marker.file_path].secmarker_count += 1

        # Process directives for per-file stats
        for directive in config.directives:
            if directive.file_path and directive.file_path in stats.per_file:
                stats.per_file[directive.file_path].directive_count += 1

        # Convert counters to dicts and lists
        stats.rules_by_phase = dict(sorted(phase_counter.items()))
        stats.rules_by_severity = dict(
            sorted(severity_counter.items(), key=lambda x: -x[1])
        )
        stats.rules_by_tag = dict(sorted(tag_counter.items(), key=lambda x: -x[1]))
        stats.rules_by_file = dict(sorted(file_counter.items()))

        stats.operators_used = dict(sorted(operator_counter.items(), key=lambda x: -x[1]))
        stats.variables_used = dict(sorted(variable_counter.items(), key=lambda x: -x[1]))
        stats.actions_used = dict(sorted(action_counter.items(), key=lambda x: -x[1]))

        stats.unique_tags = sorted(tag_counter.keys())
        stats.unique_operators = sorted(operator_counter.keys())
        stats.unique_variables = sorted(variable_counter.keys())

        return stats

    @staticmethod
    def format_report(stats: ConfigurationStatistics, detailed: bool = False) -> str:
        """
        Format statistics as a human-readable report.

        Args:
            stats: Statistics to format.
            detailed: If True, include per-file breakdown.

        Returns:
            Formatted report string.
        """
        lines = []

        def separator(char: str = "=", length: int = 70) -> str:
            return char * length

        def header(title: str) -> list[str]:
            return [separator(), f" {title}", separator()]

        # Title
        lines.extend(header("MODSECURITY CONFIGURATION STATISTICS REPORT"))
        lines.append("")

        # Global summary
        lines.extend(header("GLOBAL SUMMARY"))
        lines.append(f"  Total configuration files: {stats.total_files}")
        lines.append(f"  Total rules (SecRule + SecAction): {stats.total_rules}")
        lines.append(f"    - SecRules:    {stats.total_secrules}")
        lines.append(f"    - SecActions:  {stats.total_secactions}")
        lines.append(f"  Total SecMarkers:          {stats.total_secmarkers}")
        lines.append(f"  Total other directives:    {stats.total_directives}")
        lines.append(f"  Chained rules:             {stats.chained_rules_count}")
        lines.append(f"  Unique tags:               {len(stats.unique_tags)}")
        lines.append("")

        # Rules by phase
        if stats.rules_by_phase:
            lines.extend(header("RULES BY PHASE"))
            for phase, count in sorted(stats.rules_by_phase.items()):
                lines.append(f"  Phase {phase}: {count:>5} rules")
            lines.append("")

        # Top tags
        if stats.rules_by_tag:
            lines.extend(header("TOP TAGS (BY RULE COUNT)"))
            max_tag_len = max(len(tag) for tag in list(stats.rules_by_tag.keys())[:20])
            for tag, count in list(stats.rules_by_tag.items())[:20]:
                lines.append(f"  {tag:<{max_tag_len}}  {count:>5} rules")
            if len(stats.rules_by_tag) > 20:
                lines.append(f"  ... and {len(stats.rules_by_tag) - 20} more tags")
            lines.append("")

        # Top operators
        if stats.operators_used:
            lines.extend(header("OPERATORS USED"))
            max_op_len = max(len(op) for op in stats.operators_used.keys())
            for op, count in list(stats.operators_used.items())[:15]:
                lines.append(f"  {op:<{max_op_len}}  {count:>5} uses")
            lines.append("")

        # Top variables
        if stats.variables_used:
            lines.extend(header("TOP VARIABLES"))
            max_var_len = max(len(v) for v in list(stats.variables_used.keys())[:15])
            for var, count in list(stats.variables_used.items())[:15]:
                lines.append(f"  {var:<{max_var_len}}  {count:>5} uses")
            lines.append("")

        # Per-file statistics
        if detailed and stats.per_file:
            lines.extend(header("PER-FILE STATISTICS"))
            for filepath in sorted(stats.per_file.keys()):
                file_stats = stats.per_file[filepath]
                if file_stats.rule_count == 0 and file_stats.secmarker_count == 0:
                    continue

                lines.append("")
                lines.append(f"  [{filepath}]")
                lines.append(
                    f"    Rules: {file_stats.rule_count}  |  "
                    f"SecMarkers: {file_stats.secmarker_count}  |  "
                    f"Directives: {file_stats.directive_count}"
                )
                if file_stats.tags:
                    lines.append("    Tags:")
                    max_tag_len = max(len(t) for t in file_stats.tags.keys())
                    for tag, count in sorted(
                        file_stats.tags.items(), key=lambda x: -x[1]
                    )[:10]:
                        lines.append(f"      {tag:<{max_tag_len}}  {count:>3} rules")

        lines.append("")
        lines.append(separator())

        return "\n".join(lines)
