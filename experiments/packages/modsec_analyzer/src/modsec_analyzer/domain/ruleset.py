"""
RuleSet domain model.
"""

from collections import Counter
from dataclasses import dataclass, field
from functools import cached_property

from .rules import Rule, ActionRule


@dataclass
class RuleSet:
    """
    Collection of rules.

    Simple container for parsed rules from one or more files.
    """
    rules: list[Rule] = field(default_factory=list)

    def __repr__(self) -> str:
        total = len(self.rules)
        if total == 0:
            return "RuleSet(empty)"

        lines = [f"RuleSet ({total} rules from {len(self.files)} file(s))"]
        lines.append("  Types:")
        for rule_type, count in self.type_counts.most_common():
            lines.append(f"    {rule_type}: {count}")

        if self.action_rules:
            lines.append("")
            lines.append("  Tags:")
            for category in ["attack", "application", "language", "platform"]:
                lines.extend(self._format_tag_category(category))

        return "\n".join(lines)

    def _format_tag_category(self, category: str) -> list[str]:
        """Format tag summary lines for a category."""
        lines = [f"    {category}:"]
        dist = self.tag_distribution(category)
        untagged = dist.pop("(untagged)", 0)
        for sub_type, count in dist.most_common():
            lines.append(f"      {sub_type}: {count}")
        lines.append(f"      (no tag): {untagged}")
        return lines

    def __len__(self) -> int:
        return len(self.rules)

    def __iter__(self):
        return iter(self.rules)

    def __getitem__(self, index):
        return self.rules[index]

    @cached_property
    def action_rules(self) -> list[ActionRule]:
        """All rules that have actions (SecRule, SecAction)."""
        return [r for r in self.rules if isinstance(r, ActionRule)]

    @cached_property
    def tags(self) -> set[str]:
        """All unique tags across all ActionRules."""
        result: set[str] = set()
        for rule in self.action_rules:
            result.update(rule.tags)
        return result

    @cached_property
    def type_counts(self) -> "Counter[str]":
        """Count of rules by type."""
        return Counter(r.type for r in self.rules)

    @cached_property
    def files(self) -> set[str]:
        """All unique source file paths."""
        return {r.file_path for r in self.rules if r.file_path}

    @cached_property
    def tag_counts(self) -> "Counter[str]":
        """Count of each tag across all ActionRules."""
        counter: Counter[str] = Counter()
        for rule in self.action_rules:
            counter.update(rule.tags)
        return counter

    @cached_property
    def severity_distribution(self) -> "Counter[str]":
        """
        Distribution of action rules by severity level.

        Returns a Counter where keys are severity values (CRITICAL, WARNING, etc.)
        plus a "(none)" key for action rules without severity.

        This is a true partition: sum of all values == len(action_rules).
        """
        distribution: Counter[str] = Counter()
        for rule in self.action_rules:
            severity = rule.get_action("severity")
            distribution[severity or "(none)"] += 1
        return distribution

    def tag_distribution(self, category: str, depth: int | None = None) -> "Counter[str]":
        """
        Distribution of action rules by tag sub-type for a category.

        Args:
            category: Tag category prefix (e.g., "attack", "platform").
            depth: Number of sub-type segments to keep.
                Only applies to "attack" category (which has sub-sub-types).
                depth=1: "attack-injection-php" → "injection" (default for attack)
                depth=2: "attack-injection-php" → "injection-php"
                Ignored for other categories (full sub-type always used).

        Returns a Counter where keys are sub-types
        plus an "(untagged)" key for action rules with no tag in this category.

        A rule with multiple tags in the same category increments each sub-type.
        The "(untagged)" count is computed by iteration, not subtraction.
        """
        prefix = f"{category}-"
        # depth only applies to attack (has sub-sub-types like injection-php)
        effective_depth = depth if category == "attack" else None
        if effective_depth is None and category == "attack":
            effective_depth = 1

        distribution: Counter[str] = Counter()
        for tag, count in self.tag_counts.items():
            if tag.startswith(prefix):
                suffix = tag[len(prefix):]
                if effective_depth is not None:
                    suffix = "-".join(suffix.split("-")[:effective_depth])
                distribution[suffix] += count
        untagged = sum(
            1 for r in self.action_rules
            if not any(t.startswith(prefix) for t in r.tags)
        )
        distribution["(untagged)"] = untagged
        return distribution

    def filter(
        self,
        phase: int | None = None,
        filename: str | None = None,
        pl: int | None = None,
        action: str | None = None,
    ) -> "RuleSet":
        """
        Filtre les règles selon les critères spécifiés (cumulatifs).

        Args:
            phase: Filtrer par phase (1-5). Exclut les Directives sans phase.
            filename: Filtrer par chemin partiel (match si contenu dans file_path)
            pl: Paranoia level max (1-4). Exclut les règles des niveaux supérieurs.
                PL1 = règles sans tag paranoia-level
                PL2 = PL1 + règles paranoia-level/2
                PL3 = PL2 + règles paranoia-level/3
                PL4 = toutes les règles
            action: Filtrer par nom d'action (rules qui ont cette action).

        Returns:
            Nouveau RuleSet avec les règles filtrées
        """
        result = self.rules

        if phase is not None:
            result = [r for r in result if self._matches_phase(r, phase)]

        if filename is not None:
            result = [r for r in result if filename in r.file_path]

        if pl is not None:
            result = [r for r in result if self._matches_pl(r, pl)]

        if action is not None:
            result = [r for r in result if self._has_action(r, action)]

        return RuleSet(rules=result)

    def _matches_phase(self, rule: Rule, phase: int) -> bool:
        """Vérifie si une règle correspond à la phase spécifiée."""
        if isinstance(rule, ActionRule):
            rule_phase = rule.get_action("phase")
            return rule_phase == str(phase)
        return False

    def _matches_pl(self, rule: Rule, pl: int) -> bool:
        """
        Vérifie si une règle est incluse dans le paranoia level spécifié.

        Exclut les règles avec un tag paranoia-level/N où N > pl.
        Les règles sans tag paranoia-level sont considérées PL1.
        """
        if not isinstance(rule, ActionRule):
            return True  # Directives incluses à tous les niveaux

        tags = rule.tags
        # Exclure si la règle a un tag paranoia-level supérieur à pl
        for level in range(pl + 1, 5):  # niveaux supérieurs à pl
            if f"paranoia-level/{level}" in tags:
                return False
        return True

    def _has_action(self, rule: Rule, action: str) -> bool:
        """Vérifie si une règle contient l'action spécifiée."""
        if isinstance(rule, ActionRule):
            return rule.has_action(action)
        return False
