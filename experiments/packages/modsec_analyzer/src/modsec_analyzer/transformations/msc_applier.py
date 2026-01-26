"""
Apply domain transformations to ModSecurity configurations.
"""

from pathlib import Path
from typing import Sequence

from ..domain.rules import Rule, SecRule
from ..domain.ruleset import RuleSet
from ..domain.transformations import (
    Transformation,
    AddTag,
    RemoveTag,
    SetSeverity,
    DisableRule,
)


class MscApplier:
    """
    Applies domain transformations and writes ModSecurity configurations.

    This class is responsible for taking domain transformation intentions
    and applying them to produce valid ModSecurity configuration output.
    """

    def apply(
        self,
        ruleset: RuleSet,
        transformations: Sequence[Transformation],
    ) -> RuleSet:
        """
        Apply transformations to a ruleset.

        Args:
            ruleset: The original ruleset
            transformations: Sequence of transformations to apply

        Returns:
            New RuleSet with transformations applied
        """
        # Create a copy of rules to modify
        modified_rules = list(ruleset.rules)

        for transformation in transformations:
            modified_rules = self._apply_single(modified_rules, transformation)

        return RuleSet(
            rules=modified_rules,
            name=ruleset.name,
            source=ruleset.source,
        )

    def _apply_single(
        self,
        rules: list[Rule],
        transformation: Transformation,
    ) -> list[Rule]:
        """Apply a single transformation to the rule list."""
        result = []

        for rule in rules:
            if transformation.applies_to(rule):
                modified = self._transform_rule(rule, transformation)
                result.append(modified)
            else:
                result.append(rule)

        return result

    def _transform_rule(self, rule: Rule, transformation: Transformation) -> Rule:
        """Apply a transformation to a single rule."""
        if isinstance(transformation, AddTag):
            return self._add_tag(rule, transformation)
        elif isinstance(transformation, RemoveTag):
            return self._remove_tag(rule, transformation)
        elif isinstance(transformation, SetSeverity):
            return self._set_severity(rule, transformation)
        elif isinstance(transformation, DisableRule):
            return self._disable_rule(rule, transformation)

        return rule

    def _add_tag(self, rule: Rule, transformation: AddTag) -> Rule:
        """Add a tag to a rule."""
        # TODO: Implement tag addition
        # This would create a new Action with the tag and add it to the rule
        return rule

    def _remove_tag(self, rule: Rule, transformation: RemoveTag) -> Rule:
        """Remove a tag from a rule."""
        # TODO: Implement tag removal
        return rule

    def _set_severity(self, rule: Rule, transformation: SetSeverity) -> Rule:
        """Set severity on a rule."""
        # TODO: Implement severity change
        return rule

    def _disable_rule(self, rule: Rule, transformation: DisableRule) -> Rule:
        """Mark a rule as disabled."""
        # TODO: Implement rule disabling
        return rule

    def write_file(self, ruleset: RuleSet, filepath: str | Path) -> None:
        """
        Write a ruleset to a ModSecurity configuration file.

        Args:
            ruleset: The ruleset to write
            filepath: Output file path
        """
        content = self.to_string(ruleset)
        Path(filepath).write_text(content)

    def to_string(self, ruleset: RuleSet) -> str:
        """
        Convert a ruleset to ModSecurity configuration string.

        Args:
            ruleset: The ruleset to convert

        Returns:
            Configuration as string
        """
        lines = []

        for rule in ruleset.rules:
            lines.append(self._rule_to_string(rule))

        return "\n".join(lines)

    def _rule_to_string(self, rule: Rule) -> str:
        """Convert a single rule to its string representation."""
        # TODO: Implement full rule serialization
        if isinstance(rule, SecRule):
            return f"SecRule {rule.variables} \"{rule.operator}\" ..."
        return str(rule)
