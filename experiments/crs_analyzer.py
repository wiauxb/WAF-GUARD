#!/usr/bin/env python3
"""
CRS Configuration Analyzer

Provides statistical analysis tools for ModSecurity/CRS configurations.
Designed for use in Jupyter notebooks with visualization support.

Uses msc_pyparser directly for parsing, with lightweight dataclasses
for analysis.
"""

import glob
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import msc_pyparser

# =============================================================================
# Enums and Constants
# =============================================================================


class RuleLocation(Enum):
    """Classification of rule source location."""

    CRS_CORE = "crs_core"
    CRS_EXCLUSION = "crs_exclusion"
    CUSTOM_BEFORE = "custom_before"
    CUSTOM_AFTER = "custom_after"
    APP_SPECIFIC = "app_specific"
    SETUP = "setup"
    UNKNOWN = "unknown"


class Severity(Enum):
    """CRS Severity levels with default anomaly scores."""

    CRITICAL = 5
    ERROR = 4
    WARNING = 3
    NOTICE = 2


# Attack type labels for display
ATTACK_TYPE_LABELS = {
    "sqli": "SQL Injection",
    "xss": "Cross-Site Scripting",
    "rce": "Remote Code Execution",
    "lfi": "Local File Inclusion",
    "rfi": "Remote File Inclusion",
    "php": "PHP Injection",
    "java": "Java Attacks",
    "nodejs": "Node.js Attacks",
    "session-fixation": "Session Fixation",
    "protocol": "Protocol Violations",
    "reputation-ip": "IP Reputation",
    "reputation-scanner": "Scanner Detection",
    "generic": "Generic Attacks",
    "injection-generic": "Generic Injection",
    "dos": "Denial of Service",
}

# Phase names
PHASE_NAMES = {
    1: "Request Headers",
    2: "Request Body",
    3: "Response Headers",
    4: "Response Body",
    5: "Logging",
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class CRSRule:
    """Lightweight representation of a CRS rule for analysis."""

    rule_id: Optional[int]
    rule_type: str  # "SecRule" or "SecAction"
    lineno: int
    file_path: str
    tags: list[str] = field(default_factory=list)
    phase: Optional[int] = None
    severity: Optional[str] = None
    msg: Optional[str] = None
    paranoia_level: Optional[int] = None
    attack_types: list[str] = field(default_factory=list)
    operator: Optional[str] = None
    operator_argument: Optional[str] = None
    variables: list[str] = field(default_factory=list)
    chained: bool = False

    @classmethod
    def from_raw(cls, raw: dict, file_path: str) -> "CRSRule":
        """Create CRSRule from msc_pyparser raw dict."""
        rule_type = raw.get("type", "Unknown")

        # Extract actions info
        actions = raw.get("actions", [])
        rule_id = None
        tags = []
        phase = None
        severity = None
        msg = None

        for action in actions:
            act_name = action.get("act_name", "")
            act_arg = action.get("act_arg", "")

            if act_name == "id" and act_arg:
                try:
                    rule_id = int(act_arg)
                except ValueError:
                    pass
            elif act_name == "tag" and act_arg:
                tags.append(act_arg)
            elif act_name == "phase" and act_arg:
                try:
                    phase = int(act_arg)
                except ValueError:
                    pass
            elif act_name == "severity" and act_arg:
                severity = act_arg.upper()
            elif act_name == "msg" and act_arg:
                msg = act_arg

        # Extract paranoia level from tags
        paranoia_level = None
        attack_types = []
        for tag in tags:
            # Match paranoia-level/N
            pl_match = re.search(r"paranoia-level/(\d+)", tag)
            if pl_match:
                paranoia_level = int(pl_match.group(1))
            # Match attack-xxx
            attack_match = re.search(r"attack-(\S+)", tag)
            if attack_match:
                attack_types.append(attack_match.group(1))

        # Extract variables
        variables = []
        for var in raw.get("variables", []):
            var_name = var.get("variable", "")
            if var_name:
                variables.append(var_name)

        return cls(
            rule_id=rule_id,
            rule_type=rule_type,
            lineno=raw.get("lineno", 0),
            file_path=file_path,
            tags=tags,
            phase=phase,
            severity=severity,
            msg=msg,
            paranoia_level=paranoia_level,
            attack_types=attack_types,
            operator=raw.get("operator"),
            operator_argument=raw.get("operator_argument"),
            variables=variables,
            chained=raw.get("chained", False),
        )


@dataclass
class ParanoiaLevelStats:
    """Statistics for a specific paranoia level."""

    level: int
    total_rules: int = 0
    cumulative_rules: int = 0
    new_rules_at_level: int = 0
    rules_by_severity: dict[str, int] = field(default_factory=dict)
    rules_by_attack_type: dict[str, int] = field(default_factory=dict)
    rules_by_phase: dict[int, int] = field(default_factory=dict)


@dataclass
class AttackTypeStats:
    """Statistics for a specific attack type."""

    attack_type: str
    display_name: str
    total_rules: int = 0
    rules_by_paranoia: dict[int, int] = field(default_factory=dict)
    rules_by_severity: dict[str, int] = field(default_factory=dict)
    sample_rule_ids: list[int] = field(default_factory=list)


@dataclass
class LocationStats:
    """Statistics for a rule source location."""

    location: RuleLocation
    file_count: int = 0
    rule_count: int = 0
    files: list[str] = field(default_factory=list)


@dataclass
class PhaseStats:
    """Statistics for a processing phase."""

    phase: int
    phase_name: str
    total_rules: int = 0
    rules_by_severity: dict[str, int] = field(default_factory=dict)


# =============================================================================
# Configuration Loader
# =============================================================================


class CRSConfigLoader:
    """
    Loads ModSecurity/CRS configurations using msc_pyparser.

    Recursively resolves Include directives and converts raw dicts to CRSRule.
    """

    def __init__(self):
        self._raw_configs: dict[str, list[dict]] = {}
        self._rules: list[CRSRule] = []
        self._files: list[str] = []

    def load(self, entry_file: str) -> list[CRSRule]:
        """
        Load configuration starting from entry file.

        Args:
            entry_file: Path to main config file (e.g., setup.conf)

        Returns:
            List of CRSRule objects
        """
        self._raw_configs.clear()
        self._rules.clear()
        self._files.clear()

        entry_file = os.path.abspath(entry_file)
        if not os.path.isfile(entry_file):
            raise FileNotFoundError(f"Config file not found: {entry_file}")

        self._collect_configs(entry_file)
        self._convert_to_rules()

        return self._rules

    def _read_file(self, filepath: str) -> str:
        """Read file content."""
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def _parse_file(self, filepath: str) -> list[dict]:
        """Parse a single config file with msc_pyparser."""
        content = self._read_file(filepath)
        try:
            parser = msc_pyparser.MSCParser()
            parser.parser.parse(content)
            return parser.configlines
        except Exception as e:
            print(f"Warning: Failed to parse {filepath}: {e}")
            return []

    def _collect_configs(self, entry_file: str) -> None:
        """Recursively collect all config files."""
        includes = [entry_file]

        for filepath in includes:
            if filepath in self._raw_configs:
                continue

            self._raw_configs[filepath] = self._parse_file(filepath)
            self._files.append(filepath)

            # Find Include directives
            for directive in self._raw_configs[filepath]:
                if directive.get("type", "").lower() == "include":
                    args = directive.get("arguments", [])
                    if args:
                        include_pattern = args[0].get("argument", "")
                        if include_pattern:
                            # Handle relative paths
                            if not os.path.isabs(include_pattern):
                                base_dir = os.path.dirname(filepath)
                                include_pattern = os.path.join(base_dir, include_pattern)
                            # Expand glob
                            for f in sorted(glob.glob(include_pattern)):
                                if f not in includes:
                                    includes.append(f)

    def _convert_to_rules(self) -> None:
        """Convert raw configs to CRSRule objects."""
        for filepath, config_lines in self._raw_configs.items():
            for raw in config_lines:
                rule_type = raw.get("type", "")
                if rule_type in ("SecRule", "SecAction"):
                    self._rules.append(CRSRule.from_raw(raw, filepath))

    @property
    def files(self) -> list[str]:
        """Get list of all parsed files."""
        return self._files.copy()

    @property
    def rules(self) -> list[CRSRule]:
        """Get all parsed rules."""
        return self._rules


# =============================================================================
# Analyzers
# =============================================================================


class ParanoiaLevelAnalyzer:
    """Analyzer for paranoia level comparisons."""

    def __init__(self, rules: list[CRSRule]):
        self._rules = rules
        self._rules_by_pl: dict[int, list[CRSRule]] = defaultdict(list)
        self._classify_rules()

    def _classify_rules(self) -> None:
        """Classify rules by paranoia level."""
        for rule in self._rules:
            if rule.paranoia_level is not None:
                self._rules_by_pl[rule.paranoia_level].append(rule)

    def get_rules_at_level(self, level: int, cumulative: bool = True) -> list[CRSRule]:
        """
        Get rules active at a specific paranoia level.

        Args:
            level: Paranoia level (1-4)
            cumulative: If True, include rules from lower levels
        """
        if cumulative:
            result = []
            for pl in range(1, level + 1):
                result.extend(self._rules_by_pl.get(pl, []))
            return result
        return self._rules_by_pl.get(level, [])

    def get_stats_per_level(self) -> dict[int, ParanoiaLevelStats]:
        """Get comprehensive statistics for each paranoia level."""
        stats = {}

        for level in range(1, 5):
            level_rules = self.get_rules_at_level(level, cumulative=False)
            cumulative_rules = self.get_rules_at_level(level, cumulative=True)

            pl_stats = ParanoiaLevelStats(level=level)
            pl_stats.total_rules = len(level_rules)
            pl_stats.cumulative_rules = len(cumulative_rules)
            pl_stats.new_rules_at_level = len(level_rules)

            # Count by severity
            severity_counter: Counter[str] = Counter()
            attack_counter: Counter[str] = Counter()
            phase_counter: Counter[int] = Counter()

            for rule in level_rules:
                if rule.severity:
                    severity_counter[rule.severity] += 1
                for attack in rule.attack_types:
                    attack_counter[attack] += 1
                if rule.phase:
                    phase_counter[rule.phase] += 1

            pl_stats.rules_by_severity = dict(severity_counter)
            pl_stats.rules_by_attack_type = dict(attack_counter)
            pl_stats.rules_by_phase = dict(phase_counter)

            stats[level] = pl_stats

        return stats

    def get_coverage_delta(self, from_level: int, to_level: int) -> dict:
        """Get difference in coverage between two paranoia levels."""
        from_rules = set(r.rule_id for r in self.get_rules_at_level(from_level) if r.rule_id)
        to_rules = set(r.rule_id for r in self.get_rules_at_level(to_level) if r.rule_id)

        new_rule_ids = to_rules - from_rules
        new_rules = [r for r in self._rules if r.rule_id in new_rule_ids]

        # New attack types covered
        from_attacks = set()
        for r in self.get_rules_at_level(from_level):
            from_attacks.update(r.attack_types)

        to_attacks = set()
        for r in self.get_rules_at_level(to_level):
            to_attacks.update(r.attack_types)

        new_attacks = to_attacks - from_attacks

        # Severity breakdown of new rules
        severity_breakdown: Counter[str] = Counter()
        for rule in new_rules:
            if rule.severity:
                severity_breakdown[rule.severity] += 1

        return {
            "new_rules_count": len(new_rule_ids),
            "new_rule_ids": sorted(new_rule_ids),
            "new_attack_types": sorted(new_attacks),
            "severity_breakdown": dict(severity_breakdown),
        }

    def get_comparison_dataframe(self):
        """Get pandas DataFrame comparing all paranoia levels."""
        import pandas as pd

        stats = self.get_stats_per_level()
        data = []

        for level in range(1, 5):
            s = stats[level]
            data.append(
                {
                    "Paranoia Level": level,
                    "New Rules": s.new_rules_at_level,
                    "Cumulative Rules": s.cumulative_rules,
                    "CRITICAL": s.rules_by_severity.get("CRITICAL", 0),
                    "ERROR": s.rules_by_severity.get("ERROR", 0),
                    "WARNING": s.rules_by_severity.get("WARNING", 0),
                    "NOTICE": s.rules_by_severity.get("NOTICE", 0),
                }
            )

        return pd.DataFrame(data)


class AttackTypeAnalyzer:
    """Analyzer for attack type coverage."""

    def __init__(self, rules: list[CRSRule]):
        self._rules = rules
        self._rules_by_attack: dict[str, list[CRSRule]] = defaultdict(list)
        self._classify_rules()

    def _classify_rules(self) -> None:
        """Classify rules by attack type."""
        for rule in self._rules:
            for attack_type in rule.attack_types:
                self._rules_by_attack[attack_type].append(rule)

    def get_distribution(self) -> dict[str, int]:
        """Get rule count per attack type."""
        return {k: len(v) for k, v in sorted(self._rules_by_attack.items(), key=lambda x: -len(x[1]))}

    def get_stats_per_type(self) -> dict[str, AttackTypeStats]:
        """Get comprehensive statistics for each attack type."""
        stats = {}

        for attack_type, rules in self._rules_by_attack.items():
            display_name = ATTACK_TYPE_LABELS.get(attack_type, attack_type.replace("-", " ").title())

            attack_stats = AttackTypeStats(
                attack_type=attack_type,
                display_name=display_name,
                total_rules=len(rules),
            )

            # Count by paranoia level
            pl_counter: Counter[int] = Counter()
            severity_counter: Counter[str] = Counter()

            for rule in rules:
                if rule.paranoia_level:
                    pl_counter[rule.paranoia_level] += 1
                if rule.severity:
                    severity_counter[rule.severity] += 1

            attack_stats.rules_by_paranoia = dict(pl_counter)
            attack_stats.rules_by_severity = dict(severity_counter)
            attack_stats.sample_rule_ids = [r.rule_id for r in rules[:5] if r.rule_id]

            stats[attack_type] = attack_stats

        return stats

    def get_coverage_matrix(self):
        """Get attack type coverage matrix (attack types vs paranoia levels)."""
        import pandas as pd

        stats = self.get_stats_per_type()

        data = []
        for attack_type, s in stats.items():
            row = {
                "Attack Type": s.display_name,
                "PL1": s.rules_by_paranoia.get(1, 0),
                "PL2": s.rules_by_paranoia.get(2, 0),
                "PL3": s.rules_by_paranoia.get(3, 0),
                "PL4": s.rules_by_paranoia.get(4, 0),
                "Total": s.total_rules,
            }
            data.append(row)

        df = pd.DataFrame(data)
        df = df.sort_values("Total", ascending=False)
        return df


class RuleLocationAnalyzer:
    """Analyzer for classifying rules by source location."""

    def __init__(self, rules: list[CRSRule], base_path: str = ""):
        self._rules = rules
        self._base_path = base_path
        self._rules_by_location: dict[RuleLocation, list[CRSRule]] = defaultdict(list)
        self._classify_rules()

    def _classify_file_location(self, file_path: str) -> RuleLocation:
        """Determine location category for a file path."""
        path_lower = file_path.lower()

        if "crs_rules" in path_lower or "coreruleset" in path_lower:
            if "exclusion" in path_lower:
                return RuleLocation.CRS_EXCLUSION
            return RuleLocation.CRS_CORE
        elif "before-crs" in path_lower or "before_crs" in path_lower:
            return RuleLocation.CUSTOM_BEFORE
        elif "after-crs" in path_lower or "after_crs" in path_lower:
            return RuleLocation.CUSTOM_AFTER
        elif "/apps/" in path_lower or "/custom/apps" in path_lower:
            return RuleLocation.APP_SPECIFIC
        elif "setup" in path_lower or "crs-setup" in path_lower:
            return RuleLocation.SETUP

        return RuleLocation.UNKNOWN

    def _classify_rules(self) -> None:
        """Classify rules by their file location."""
        for rule in self._rules:
            location = self._classify_file_location(rule.file_path)
            self._rules_by_location[location].append(rule)

    def get_distribution(self) -> dict[str, int]:
        """Get rule count per location."""
        return {loc.value: len(rules) for loc, rules in self._rules_by_location.items()}

    def get_stats_per_location(self) -> dict[RuleLocation, LocationStats]:
        """Get statistics for each location."""
        stats = {}

        for location, rules in self._rules_by_location.items():
            files = list(set(r.file_path for r in rules))
            stats[location] = LocationStats(
                location=location,
                file_count=len(files),
                rule_count=len(rules),
                files=files,
            )

        return stats


class PhaseDistributionAnalyzer:
    """Analyzer for rule distribution across processing phases."""

    def __init__(self, rules: list[CRSRule]):
        self._rules = rules
        self._rules_by_phase: dict[int, list[CRSRule]] = defaultdict(list)
        self._classify_rules()

    def _classify_rules(self) -> None:
        """Classify rules by phase."""
        for rule in self._rules:
            if rule.phase:
                self._rules_by_phase[rule.phase].append(rule)

    def get_distribution(self) -> dict[int, int]:
        """Get rule count per phase."""
        return {phase: len(rules) for phase, rules in sorted(self._rules_by_phase.items())}

    def get_stats_per_phase(self) -> dict[int, PhaseStats]:
        """Get statistics for each phase."""
        stats = {}

        for phase, rules in self._rules_by_phase.items():
            severity_counter: Counter[str] = Counter()
            for rule in rules:
                if rule.severity:
                    severity_counter[rule.severity] += 1

            stats[phase] = PhaseStats(
                phase=phase,
                phase_name=PHASE_NAMES.get(phase, f"Phase {phase}"),
                total_rules=len(rules),
                rules_by_severity=dict(severity_counter),
            )

        return stats

    def get_dataframe(self):
        """Get phase distribution as pandas DataFrame."""
        import pandas as pd

        stats = self.get_stats_per_phase()
        data = []

        for phase in sorted(stats.keys()):
            s = stats[phase]
            data.append(
                {
                    "Phase": phase,
                    "Name": s.phase_name,
                    "Rules": s.total_rules,
                    "CRITICAL": s.rules_by_severity.get("CRITICAL", 0),
                    "ERROR": s.rules_by_severity.get("ERROR", 0),
                    "WARNING": s.rules_by_severity.get("WARNING", 0),
                    "NOTICE": s.rules_by_severity.get("NOTICE", 0),
                }
            )

        return pd.DataFrame(data)


class AnomalyScoreAnalyzer:
    """Analyzer for anomaly score impact analysis."""

    DEFAULT_SCORES = {
        "CRITICAL": 5,
        "ERROR": 4,
        "WARNING": 3,
        "NOTICE": 2,
    }

    def __init__(self, rules: list[CRSRule], scores: Optional[dict[str, int]] = None):
        self._rules = rules
        self._scores = scores or self.DEFAULT_SCORES

    def get_score_profile(self) -> dict[str, dict]:
        """Get anomaly score profile by severity."""
        severity_counts: Counter[str] = Counter()

        for rule in self._rules:
            if rule.severity:
                severity_counts[rule.severity] += 1

        profile = {}
        for severity, count in severity_counts.items():
            base_score = self._scores.get(severity, 0)
            profile[severity] = {
                "rule_count": count,
                "base_score": base_score,
                "max_potential_score": count * base_score,
            }

        return profile

    def get_threshold_analysis(self, thresholds: Optional[list[int]] = None):
        """Analyze what triggers blocking at various thresholds."""
        import pandas as pd

        if thresholds is None:
            thresholds = [5, 7, 10, 15, 20, 25]

        profile = self.get_score_profile()
        data = []

        for threshold in thresholds:
            row = {"Threshold": threshold}

            # Calculate minimum hits needed
            for severity in ["CRITICAL", "ERROR", "WARNING", "NOTICE"]:
                score = self._scores.get(severity, 0)
                if score > 0:
                    min_hits = (threshold + score - 1) // score  # Ceiling division
                    row[f"Min {severity}"] = min_hits
                else:
                    row[f"Min {severity}"] = "N/A"

            data.append(row)

        return pd.DataFrame(data)


# =============================================================================
# Visualization Helper
# =============================================================================


class CRSVisualizationHelper:
    """Helper class for generating visualizations."""

    # Color palettes
    PARANOIA_COLORS = ["#2ecc71", "#f39c12", "#e74c3c", "#9b59b6"]
    SEVERITY_COLORS = {
        "CRITICAL": "#e74c3c",
        "ERROR": "#e67e22",
        "WARNING": "#f39c12",
        "NOTICE": "#3498db",
    }

    @staticmethod
    def plot_paranoia_comparison(stats: dict[int, ParanoiaLevelStats], figsize=(12, 6)):
        """Create grouped bar chart comparing paranoia levels."""
        import matplotlib.pyplot as plt
        import numpy as np

        fig, ax = plt.subplots(figsize=figsize)

        levels = [1, 2, 3, 4]
        new_rules = [stats[l].new_rules_at_level for l in levels]
        cumulative = [stats[l].cumulative_rules for l in levels]

        x = np.arange(len(levels))
        width = 0.35

        bars1 = ax.bar(x - width / 2, new_rules, width, label="New Rules", color="#3498db")
        bars2 = ax.bar(x + width / 2, cumulative, width, label="Cumulative", color="#2ecc71")

        ax.set_xlabel("Paranoia Level")
        ax.set_ylabel("Number of Rules")
        ax.set_title("Rules per Paranoia Level")
        ax.set_xticks(x)
        ax.set_xticklabels([f"PL{l}" for l in levels])
        ax.legend()

        # Add value labels
        for bar in bars1:
            height = bar.get_height()
            ax.annotate(
                f"{int(height)}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                ha="center",
                va="bottom",
            )
        for bar in bars2:
            height = bar.get_height()
            ax.annotate(
                f"{int(height)}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                ha="center",
                va="bottom",
            )

        plt.tight_layout()
        return fig

    @staticmethod
    def plot_paranoia_stacked_severity(stats: dict[int, ParanoiaLevelStats], figsize=(10, 6)):
        """Create stacked bar chart showing severity distribution per PL."""
        import matplotlib.pyplot as plt
        import numpy as np

        fig, ax = plt.subplots(figsize=figsize)

        levels = [1, 2, 3, 4]
        severities = ["CRITICAL", "ERROR", "WARNING", "NOTICE"]
        colors = [CRSVisualizationHelper.SEVERITY_COLORS[s] for s in severities]

        x = np.arange(len(levels))
        width = 0.6

        bottom = np.zeros(len(levels))
        for i, severity in enumerate(severities):
            values = [stats[l].rules_by_severity.get(severity, 0) for l in levels]
            ax.bar(x, values, width, label=severity, bottom=bottom, color=colors[i])
            bottom += np.array(values)

        ax.set_xlabel("Paranoia Level")
        ax.set_ylabel("Number of Rules")
        ax.set_title("Severity Distribution by Paranoia Level")
        ax.set_xticks(x)
        ax.set_xticklabels([f"PL{l}" for l in levels])
        ax.legend()

        plt.tight_layout()
        return fig

    @staticmethod
    def plot_attack_type_pie(distribution: dict[str, int], figsize=(10, 10), top_n: int = 10):
        """Create pie chart of attack type distribution."""
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=figsize)

        # Get top N and group others
        sorted_items = sorted(distribution.items(), key=lambda x: -x[1])
        top_items = sorted_items[:top_n]
        other_count = sum(count for _, count in sorted_items[top_n:])

        labels = [ATTACK_TYPE_LABELS.get(k, k) for k, _ in top_items]
        sizes = [v for _, v in top_items]

        if other_count > 0:
            labels.append("Other")
            sizes.append(other_count)

        colors = plt.cm.Set3(range(len(labels)))

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct="%1.1f%%",
            colors=colors,
            pctdistance=0.8,
        )

        ax.set_title("Attack Type Distribution")

        plt.tight_layout()
        return fig

    @staticmethod
    def plot_attack_coverage_heatmap(coverage_df, figsize=(12, 8)):
        """Create heatmap showing attack type coverage across paranoia levels."""
        import matplotlib.pyplot as plt
        import seaborn as sns

        fig, ax = plt.subplots(figsize=figsize)

        # Prepare data for heatmap
        heatmap_data = coverage_df.set_index("Attack Type")[["PL1", "PL2", "PL3", "PL4"]]

        sns.heatmap(
            heatmap_data,
            annot=True,
            fmt="d",
            cmap="YlOrRd",
            ax=ax,
            cbar_kws={"label": "Rule Count"},
        )

        ax.set_title("Attack Type Coverage by Paranoia Level")
        ax.set_xlabel("Paranoia Level")
        ax.set_ylabel("Attack Type")

        plt.tight_layout()
        return fig

    @staticmethod
    def plot_phase_distribution(stats: dict[int, PhaseStats], figsize=(10, 6)):
        """Create horizontal bar chart of phase distribution."""
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=figsize)

        phases = sorted(stats.keys())
        names = [stats[p].phase_name for p in phases]
        counts = [stats[p].total_rules for p in phases]

        colors = plt.cm.viridis([i / len(phases) for i in range(len(phases))])

        bars = ax.barh(names, counts, color=colors)

        ax.set_xlabel("Number of Rules")
        ax.set_title("Rule Distribution by Processing Phase")

        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax.annotate(
                f"{int(width)}",
                xy=(width, bar.get_y() + bar.get_height() / 2),
                ha="left",
                va="center",
                xytext=(5, 0),
                textcoords="offset points",
            )

        plt.tight_layout()
        return fig

    @staticmethod
    def plot_severity_donut(severity_counts: dict[str, int], figsize=(8, 8)):
        """Create donut chart of severity distribution."""
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=figsize)

        severities = ["CRITICAL", "ERROR", "WARNING", "NOTICE"]
        sizes = [severity_counts.get(s, 0) for s in severities]
        colors = [CRSVisualizationHelper.SEVERITY_COLORS[s] for s in severities]

        # Filter out zero values
        non_zero = [(s, sz, c) for s, sz, c in zip(severities, sizes, colors) if sz > 0]
        if not non_zero:
            ax.text(0.5, 0.5, "No severity data", ha="center", va="center")
            return fig

        severities, sizes, colors = zip(*non_zero)

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=severities,
            autopct="%1.1f%%",
            colors=colors,
            pctdistance=0.75,
            wedgeprops=dict(width=0.5),
        )

        ax.set_title("Severity Distribution")

        plt.tight_layout()
        return fig

    @staticmethod
    def plot_location_bar(stats: dict[RuleLocation, LocationStats], figsize=(10, 6)):
        """Create bar chart of rule location distribution."""
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=figsize)

        # Filter locations with rules
        locations = [(loc, s) for loc, s in stats.items() if s.rule_count > 0]
        locations.sort(key=lambda x: -x[1].rule_count)

        names = [loc.value.replace("_", " ").title() for loc, _ in locations]
        counts = [s.rule_count for _, s in locations]

        colors = plt.cm.Pastel1(range(len(locations)))

        bars = ax.bar(names, counts, color=colors)

        ax.set_ylabel("Number of Rules")
        ax.set_title("Rules by Location")
        plt.xticks(rotation=45, ha="right")

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"{int(height)}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                ha="center",
                va="bottom",
            )

        plt.tight_layout()
        return fig


# =============================================================================
# Main Analyzer (Facade)
# =============================================================================


class CRSAnalyzer:
    """
    Main facade for CRS configuration analysis.

    Usage:
        analyzer = CRSAnalyzer()
        analyzer.load("/path/to/config/setup.conf")

        # Access sub-analyzers
        pl_stats = analyzer.paranoia.get_stats_per_level()
        attack_dist = analyzer.attacks.get_distribution()
    """

    def __init__(self):
        self._loader = CRSConfigLoader()
        self._rules: list[CRSRule] = []
        self._files: list[str] = []

        # Sub-analyzers (initialized after load)
        self._paranoia: Optional[ParanoiaLevelAnalyzer] = None
        self._attacks: Optional[AttackTypeAnalyzer] = None
        self._locations: Optional[RuleLocationAnalyzer] = None
        self._phases: Optional[PhaseDistributionAnalyzer] = None
        self._anomaly: Optional[AnomalyScoreAnalyzer] = None

    def load(self, entry_file: str) -> "CRSAnalyzer":
        """Load configuration and initialize analyzers."""
        self._rules = self._loader.load(entry_file)
        self._files = self._loader.files

        # Initialize sub-analyzers
        self._paranoia = ParanoiaLevelAnalyzer(self._rules)
        self._attacks = AttackTypeAnalyzer(self._rules)
        self._locations = RuleLocationAnalyzer(self._rules, os.path.dirname(entry_file))
        self._phases = PhaseDistributionAnalyzer(self._rules)
        self._anomaly = AnomalyScoreAnalyzer(self._rules)

        return self

    @property
    def rules(self) -> list[CRSRule]:
        """Get all parsed rules."""
        return self._rules

    @property
    def files(self) -> list[str]:
        """Get all parsed files."""
        return self._files

    @property
    def paranoia(self) -> ParanoiaLevelAnalyzer:
        """Get paranoia level analyzer."""
        if self._paranoia is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._paranoia

    @property
    def attacks(self) -> AttackTypeAnalyzer:
        """Get attack type analyzer."""
        if self._attacks is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._attacks

    @property
    def locations(self) -> RuleLocationAnalyzer:
        """Get rule location analyzer."""
        if self._locations is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._locations

    @property
    def phases(self) -> PhaseDistributionAnalyzer:
        """Get phase distribution analyzer."""
        if self._phases is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._phases

    @property
    def anomaly(self) -> AnomalyScoreAnalyzer:
        """Get anomaly score analyzer."""
        if self._anomaly is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._anomaly

    def summary(self) -> dict:
        """Get summary statistics."""
        severity_counts: Counter[str] = Counter()
        for rule in self._rules:
            if rule.severity:
                severity_counts[rule.severity] += 1

        return {
            "total_files": len(self._files),
            "total_rules": len(self._rules),
            "rules_by_type": {
                "SecRule": sum(1 for r in self._rules if r.rule_type == "SecRule"),
                "SecAction": sum(1 for r in self._rules if r.rule_type == "SecAction"),
            },
            "rules_by_severity": dict(severity_counts),
            "unique_attack_types": len(self._attacks.get_distribution()) if self._attacks else 0,
        }
