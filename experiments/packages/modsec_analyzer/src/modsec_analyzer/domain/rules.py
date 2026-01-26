"""
Rule domain models.

These dataclasses map 1:1 with msc_pyparser output format.
"""

from dataclasses import dataclass, field

from .components import Variable, Operator, Action, Argument


@dataclass
class Rule:
    """
    Base class for all rule/directive types.

    Common fields present in all msc_pyparser output items.
    """
    type: str               # "SecRule", "SecAction", "Comment", "include", etc.
    lineno: int
    file_path: str = ""     # Added during parsing (not from msc_pyparser)


@dataclass
class ActionRule(Rule):
    """
    Base class for rules with actions (SecRule, SecAction).

    Centralizes action-related logic.
    """
    actions: list[Action] = field(default_factory=list)

    def get_action(self, name: str) -> str | None:
        """Get first action value by name."""
        for a in self.actions:
            if a.act_name == name:
                return a.act_arg
        return None

    def get_all_actions(self, name: str) -> list[str]:
        """Get all action values by name (e.g., multiple tags)."""
        return [a.act_arg for a in self.actions if a.act_name == name]

    def has_action(self, name: str) -> bool:
        """Check if rule has an action with this name."""
        return any(a.act_name == name for a in self.actions)

    @property
    def tags(self) -> list[str]:
        """Get all tag values."""
        return self.get_all_actions("tag")


@dataclass
class SecRule(ActionRule):
    """
    A SecRule directive.

    Maps to msc_pyparser SecRule dict structure.
    Example:
        SecRule ARGS "@rx attack" "id:1,phase:2,deny"
    """
    variables: list[Variable] = field(default_factory=list)
    operator: Operator = field(default_factory=Operator)
    chained: bool = False

    def __repr__(self) -> str:
        rule_id = self.get_action("id") or "?"
        phase = self.get_action("phase") or "?"
        msg = self.get_action("msg")

        # Variables summary
        vars_str = "|".join(str(v) for v in self.variables[:3])
        if len(self.variables) > 3:
            vars_str += f"|...({len(self.variables)})"

        # Build output
        chain_marker = " [CHAIN]" if self.chained else ""
        lines = [f"SecRule #{rule_id} (phase:{phase}, line:{self.lineno}){chain_marker}"]
        lines.append(f"  Variables: {vars_str}")
        lines.append(f"  Operator:  {self.operator}")
        if msg:
            msg_display = msg if len(msg) <= 60 else msg[:57] + "..."
            lines.append(f"  Message:   {msg_display}")

        return "\n".join(lines)


@dataclass
class SecAction(ActionRule):
    """
    A SecAction directive.

    Like SecRule but always matches (no variables/operator).
    Maps to msc_pyparser SecAction dict structure.
    """

    def __repr__(self) -> str:
        rule_id = self.get_action("id") or "?"
        phase = self.get_action("phase") or "?"

        # Show first few actions
        actions_preview = ", ".join(str(a) for a in self.actions[:5])
        if len(self.actions) > 5:
            actions_preview += f", ...({len(self.actions)} total)"

        return f"SecAction #{rule_id} (phase:{phase}, line:{self.lineno})\n  Actions: {actions_preview}"


@dataclass
class Directive(Rule):
    """
    A generic directive (include, SecMarker, SecComponentSignature, etc.).

    Maps to msc_pyparser generic directive dict structure.
    Used for any directive that has 'arguments' field.
    """
    arguments: list[Argument] = field(default_factory=list)

    def __repr__(self) -> str:
        args_str = " ".join(str(a) for a in self.arguments)
        return f"{self.type} {args_str} (line:{self.lineno})"
