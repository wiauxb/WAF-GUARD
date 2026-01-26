"""
Rule collection with fluent filtering API.

Provides a chainable interface for filtering ModSecurity rules
by various criteria (ID, tags, variables, operators, etc.).
"""

import fnmatch
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

from .models import Rule, SecAction, SecRule

if TYPE_CHECKING:
    pass


class RuleFilter:
    """
    Fluent interface for building rule filters.

    Supports chaining multiple filter conditions that are
    combined with AND logic.

    Example:
        rules.filter()\\
            .by_tag("attack-sqli")\\
            .by_phase(2)\\
            .by_action("deny")\\
            .execute()
    """

    def __init__(self, rules: list[Rule]):
        """
        Initialize a new filter chain.

        Args:
            rules: List of rules to filter.
        """
        self._rules = rules
        self._filters: list[Callable[[Rule], bool]] = []

    def by_id(self, rule_id: int) -> "RuleFilter":
        """
        Filter by exact rule ID.

        Args:
            rule_id: The rule ID to match.

        Returns:
            Self for chaining.
        """
        self._filters.append(lambda r: r.rule_id == rule_id)
        return self

    def by_id_range(self, start: int, end: int) -> "RuleFilter":
        """
        Filter by rule ID range (inclusive).

        Args:
            start: Minimum rule ID (inclusive).
            end: Maximum rule ID (inclusive).

        Returns:
            Self for chaining.
        """
        self._filters.append(
            lambda r: r.rule_id is not None and start <= r.rule_id <= end
        )
        return self

    def by_tag(self, tag: str, exact: bool = False) -> "RuleFilter":
        """
        Filter by tag.

        Args:
            tag: Tag to search for.
            exact: If True, require exact match. If False (default),
                   match as substring (case-insensitive).

        Returns:
            Self for chaining.
        """
        if exact:
            self._filters.append(lambda r: tag in r.tags)
        else:
            tag_lower = tag.lower()
            self._filters.append(
                lambda r, t=tag_lower: any(t in rt.lower() for rt in r.tags)
            )
        return self

    def by_tags_any(self, tags: list[str]) -> "RuleFilter":
        """
        Filter rules that have any of the specified tags.

        Args:
            tags: List of tags to match (any).

        Returns:
            Self for chaining.
        """
        tags_set = set(tags)
        self._filters.append(lambda r: bool(set(r.tags) & tags_set))
        return self

    def by_tags_all(self, tags: list[str]) -> "RuleFilter":
        """
        Filter rules that have all of the specified tags.

        Args:
            tags: List of tags that must all be present.

        Returns:
            Self for chaining.
        """
        tags_set = set(tags)
        self._filters.append(lambda r: tags_set.issubset(set(r.tags)))
        return self

    def by_variable(self, var_name: str) -> "RuleFilter":
        """
        Filter by variable used in the rule.

        Args:
            var_name: Variable name to search for (e.g., 'ARGS', 'REQUEST_HEADERS').

        Returns:
            Self for chaining.
        """

        def has_variable(r: Rule) -> bool:
            if not isinstance(r, SecRule):
                return False
            return any(v.name == var_name for v in r.variables)

        self._filters.append(has_variable)
        return self

    def by_variable_contains(self, var_substring: str) -> "RuleFilter":
        """
        Filter by variable name containing a substring.

        Args:
            var_substring: Substring to search for in variable names.

        Returns:
            Self for chaining.
        """
        var_lower = var_substring.lower()

        def has_variable(r: Rule) -> bool:
            if not isinstance(r, SecRule):
                return False
            return any(var_lower in v.name.lower() for v in r.variables)

        self._filters.append(has_variable)
        return self

    def by_operator(self, op_name: str) -> "RuleFilter":
        """
        Filter by operator name.

        Args:
            op_name: Operator name (e.g., '@rx', '@pm', '@contains').

        Returns:
            Self for chaining.
        """

        def has_operator(r: Rule) -> bool:
            if not isinstance(r, SecRule):
                return False
            return r.operator.name == op_name

        self._filters.append(has_operator)
        return self

    def by_action(self, action_name: str) -> "RuleFilter":
        """
        Filter by action name.

        Args:
            action_name: Action name (e.g., 'deny', 'block', 'pass').

        Returns:
            Self for chaining.
        """
        self._filters.append(lambda r: any(a.name == action_name for a in r.actions))
        return self

    def by_phase(self, phase: int) -> "RuleFilter":
        """
        Filter by processing phase.

        Args:
            phase: Phase number (1-5).

        Returns:
            Self for chaining.
        """
        self._filters.append(lambda r: r.phase == phase)
        return self

    def by_severity(self, severity: str) -> "RuleFilter":
        """
        Filter by severity level.

        Args:
            severity: Severity string (e.g., 'CRITICAL', 'WARNING').

        Returns:
            Self for chaining.
        """
        severity_lower = severity.lower()
        self._filters.append(
            lambda r: isinstance(r, SecRule)
            and r.severity is not None
            and r.severity.lower() == severity_lower
        )
        return self

    def by_file(self, pattern: str) -> "RuleFilter":
        """
        Filter by file path pattern.

        Args:
            pattern: Glob pattern or substring to match file paths.

        Returns:
            Self for chaining.
        """

        def matches_file(r: Rule) -> bool:
            if not r.file_path:
                return False
            # Try glob pattern first, fall back to substring
            if fnmatch.fnmatch(r.file_path, pattern):
                return True
            return pattern in r.file_path

        self._filters.append(matches_file)
        return self

    def chained_only(self) -> "RuleFilter":
        """
        Filter only chained rules (rules that chain to next rule).

        Returns:
            Self for chaining.
        """
        self._filters.append(lambda r: isinstance(r, SecRule) and r.chained)
        return self

    def not_chained(self) -> "RuleFilter":
        """
        Filter only non-chained rules.

        Returns:
            Self for chaining.
        """
        self._filters.append(lambda r: not isinstance(r, SecRule) or not r.chained)
        return self

    def secrules_only(self) -> "RuleFilter":
        """
        Filter only SecRule directives (exclude SecAction).

        Returns:
            Self for chaining.
        """
        self._filters.append(lambda r: isinstance(r, SecRule))
        return self

    def secactions_only(self) -> "RuleFilter":
        """
        Filter only SecAction directives.

        Returns:
            Self for chaining.
        """
        self._filters.append(lambda r: isinstance(r, SecAction))
        return self

    def with_id(self) -> "RuleFilter":
        """
        Filter rules that have an ID defined.

        Returns:
            Self for chaining.
        """
        self._filters.append(lambda r: r.rule_id is not None)
        return self

    def without_id(self) -> "RuleFilter":
        """
        Filter rules that don't have an ID defined.

        Returns:
            Self for chaining.
        """
        self._filters.append(lambda r: r.rule_id is None)
        return self

    def custom(self, predicate: Callable[[Rule], bool]) -> "RuleFilter":
        """
        Add a custom filter predicate.

        Args:
            predicate: Function that takes a Rule and returns True to include.

        Returns:
            Self for chaining.
        """
        self._filters.append(predicate)
        return self

    # Execution methods

    def execute(self) -> list[Rule]:
        """
        Execute all filters and return matching rules.

        Returns:
            List of rules matching all filter conditions.
        """
        result = self._rules
        for f in self._filters:
            result = [r for r in result if f(r)]
        return result

    def __iter__(self) -> Iterator[Rule]:
        """Allow iteration over filtered results."""
        return iter(self.execute())

    def __len__(self) -> int:
        """Return count of matching rules."""
        return len(self.execute())

    def count(self) -> int:
        """
        Return count of matching rules.

        Returns:
            Number of rules matching all filter conditions.
        """
        return len(self.execute())

    def first(self) -> Rule | None:
        """
        Return first matching rule or None.

        Returns:
            First matching rule, or None if no matches.
        """
        results = self.execute()
        return results[0] if results else None

    def ids(self) -> list[int]:
        """
        Return list of rule IDs from matching rules.

        Returns:
            List of rule IDs (excludes rules without IDs).
        """
        return [r.rule_id for r in self.execute() if r.rule_id is not None]


class RuleCollection:
    """
    Collection of rules with filtering capabilities.

    Provides a convenient interface for accessing and filtering
    ModSecurity rules from a parsed configuration.
    """

    def __init__(self, rules: list[Rule]):
        """
        Initialize the collection.

        Args:
            rules: List of rules (SecRule and SecAction).
        """
        self._rules = rules

    def filter(self) -> RuleFilter:
        """
        Start a new filter chain.

        Returns:
            RuleFilter for building filter conditions.
        """
        return RuleFilter(self._rules)

    def all(self) -> list[Rule]:
        """
        Get all rules.

        Returns:
            Copy of the rules list.
        """
        return self._rules.copy()

    def __len__(self) -> int:
        """Return total number of rules."""
        return len(self._rules)

    def __iter__(self) -> Iterator[Rule]:
        """Iterate over all rules."""
        return iter(self._rules)

    def __getitem__(self, index: int) -> Rule:
        """Get rule by index."""
        return self._rules[index]

    # Convenience methods

    def by_id(self, rule_id: int) -> Rule | None:
        """
        Quick lookup by rule ID.

        Args:
            rule_id: The rule ID to find.

        Returns:
            Matching rule or None.
        """
        return self.filter().by_id(rule_id).first()

    def by_tag(self, tag: str) -> list[Rule]:
        """
        Quick filter by tag.

        Args:
            tag: Tag to filter by.

        Returns:
            List of matching rules.
        """
        return self.filter().by_tag(tag).execute()

    def get_all_tags(self) -> set[str]:
        """
        Get all unique tags across all rules.

        Returns:
            Set of unique tag strings.
        """
        tags = set()
        for rule in self._rules:
            tags.update(rule.tags)
        return tags

    def get_all_ids(self) -> list[int]:
        """
        Get all rule IDs.

        Returns:
            Sorted list of rule IDs.
        """
        ids = [r.rule_id for r in self._rules if r.rule_id is not None]
        return sorted(ids)

    def group_by_file(self) -> dict[str, list[Rule]]:
        """
        Group rules by their source file.

        Returns:
            Dictionary mapping file paths to lists of rules.
        """
        grouped: dict[str, list[Rule]] = {}
        for rule in self._rules:
            path = rule.file_path or "unknown"
            if path not in grouped:
                grouped[path] = []
            grouped[path].append(rule)
        return grouped

    def group_by_phase(self) -> dict[int | None, list[Rule]]:
        """
        Group rules by their processing phase.

        Returns:
            Dictionary mapping phase numbers to lists of rules.
        """
        grouped: dict[int | None, list[Rule]] = {}
        for rule in self._rules:
            phase = rule.phase
            if phase not in grouped:
                grouped[phase] = []
            grouped[phase].append(rule)
        return grouped

    def group_by_tag(self) -> dict[str, list[Rule]]:
        """
        Group rules by their tags.

        Note: A rule with multiple tags will appear in multiple groups.

        Returns:
            Dictionary mapping tags to lists of rules.
        """
        grouped: dict[str, list[Rule]] = {}
        for rule in self._rules:
            for tag in rule.tags:
                if tag not in grouped:
                    grouped[tag] = []
                grouped[tag].append(rule)
        return grouped
