"""
Pydantic models for ModSecurity configuration elements.

These models provide typed representations of SecRule, SecAction, and other
ModSecurity directives parsed by msc_pyparser.
"""

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class Action(BaseModel):
    """Represents a single ModSecurity action within a rule."""

    name: str = Field(..., description="Action name (e.g., 'deny', 'tag', 'id')")
    argument: Optional[str] = Field(None, description="Action argument value")
    quote_type: Optional[str] = Field(None, description="Quote type used for argument")

    @classmethod
    def from_raw(cls, raw: dict) -> "Action":
        """Convert msc_pyparser action dict to Action model."""
        return cls(
            name=raw.get("act_name", ""),
            argument=raw.get("act_arg"),
            quote_type=raw.get("act_quote"),
        )


class Variable(BaseModel):
    """Represents a ModSecurity variable in a SecRule."""

    name: str = Field(..., description="Variable name (e.g., 'ARGS', 'REQUEST_HEADERS')")
    selector: Optional[str] = Field(
        None, description="Variable selector/part (e.g., 'id' for ARGS:id)"
    )
    negated: bool = Field(False, description="Whether variable is negated with !")
    count: bool = Field(False, description="Whether variable uses count operator &")

    @classmethod
    def from_raw(cls, raw: dict) -> "Variable":
        """Convert msc_pyparser variable dict to Variable model."""
        return cls(
            name=raw.get("variable", ""),
            selector=raw.get("variable_part"),
            negated=raw.get("negated", False),
            count=raw.get("counter", False),
        )


class Operator(BaseModel):
    """Represents a ModSecurity operator in a SecRule."""

    name: str = Field(..., description="Operator name (e.g., '@rx', '@pm', '@contains')")
    argument: str = Field("", description="Operator argument/pattern")
    negated: bool = Field(False, description="Whether operator is negated with !")

    @classmethod
    def from_raw(cls, operator: str, argument: str, negated: bool = False) -> "Operator":
        """Create Operator from msc_pyparser fields."""
        return cls(name=operator or "", argument=argument or "", negated=negated)


class SecRule(BaseModel):
    """Represents a SecRule directive."""

    type: Literal["SecRule"] = "SecRule"
    variables: list[Variable] = Field(default_factory=list)
    operator: Operator
    actions: list[Action] = Field(default_factory=list)
    chained: bool = Field(False, description="Whether this rule chains to the next")
    lineno: int = Field(..., description="Line number in source file")
    file_path: Optional[str] = Field(None, description="Source file path")

    # Convenience fields extracted from actions
    rule_id: Optional[int] = Field(None, description="Rule ID from 'id' action")
    tags: list[str] = Field(default_factory=list, description="Tags from 'tag' actions")
    phase: Optional[int] = Field(None, description="Processing phase from 'phase' action")
    severity: Optional[str] = Field(None, description="Severity from 'severity' action")
    msg: Optional[str] = Field(None, description="Message from 'msg' action")

    @model_validator(mode="after")
    def extract_action_fields(self) -> "SecRule":
        """Extract convenience fields from actions list."""
        for action in self.actions:
            if action.name == "id" and action.argument:
                try:
                    self.rule_id = int(action.argument)
                except ValueError:
                    pass
            elif action.name == "tag" and action.argument:
                self.tags.append(action.argument)
            elif action.name == "phase" and action.argument:
                try:
                    self.phase = int(action.argument)
                except ValueError:
                    pass
            elif action.name == "severity" and action.argument:
                self.severity = action.argument
            elif action.name == "msg" and action.argument:
                self.msg = action.argument
        return self

    @classmethod
    def from_raw(cls, raw: dict, file_path: Optional[str] = None) -> "SecRule":
        """Convert msc_pyparser SecRule dict to SecRule model."""
        variables = [Variable.from_raw(v) for v in raw.get("variables", [])]

        operator = Operator.from_raw(
            raw.get("operator", ""),
            raw.get("operator_argument", ""),
            raw.get("operneg", False),
        )

        actions = [Action.from_raw(a) for a in raw.get("actions", [])]

        return cls(
            variables=variables,
            operator=operator,
            actions=actions,
            chained=raw.get("chained", False),
            lineno=raw.get("lineno", 0),
            file_path=file_path,
        )


class SecAction(BaseModel):
    """Represents a SecAction directive."""

    type: Literal["SecAction"] = "SecAction"
    actions: list[Action] = Field(default_factory=list)
    lineno: int = Field(..., description="Line number in source file")
    file_path: Optional[str] = Field(None, description="Source file path")

    # Convenience fields extracted from actions
    rule_id: Optional[int] = Field(None, description="Rule ID from 'id' action")
    tags: list[str] = Field(default_factory=list, description="Tags from 'tag' actions")
    phase: Optional[int] = Field(None, description="Processing phase from 'phase' action")

    @model_validator(mode="after")
    def extract_action_fields(self) -> "SecAction":
        """Extract convenience fields from actions list."""
        for action in self.actions:
            if action.name == "id" and action.argument:
                try:
                    self.rule_id = int(action.argument)
                except ValueError:
                    pass
            elif action.name == "tag" and action.argument:
                self.tags.append(action.argument)
            elif action.name == "phase" and action.argument:
                try:
                    self.phase = int(action.argument)
                except ValueError:
                    pass
        return self

    @classmethod
    def from_raw(cls, raw: dict, file_path: Optional[str] = None) -> "SecAction":
        """Convert msc_pyparser SecAction dict to SecAction model."""
        actions = [Action.from_raw(a) for a in raw.get("actions", [])]

        return cls(
            actions=actions,
            lineno=raw.get("lineno", 0),
            file_path=file_path,
        )


class SecMarker(BaseModel):
    """Represents a SecMarker directive."""

    type: Literal["SecMarker"] = "SecMarker"
    name: str = Field(..., description="Marker name")
    lineno: int = Field(..., description="Line number in source file")
    file_path: Optional[str] = Field(None, description="Source file path")

    @classmethod
    def from_raw(cls, raw: dict, file_path: Optional[str] = None) -> "SecMarker":
        """Convert msc_pyparser SecMarker dict to SecMarker model."""
        # SecMarker name is in arguments
        arguments = raw.get("arguments", [])
        name = arguments[0].get("argument", "") if arguments else ""

        return cls(
            name=name,
            lineno=raw.get("lineno", 0),
            file_path=file_path,
        )


class Directive(BaseModel):
    """Represents a generic ModSecurity directive (non-rule)."""

    type: str = Field(..., description="Directive type (e.g., 'SecAuditEngine')")
    arguments: list[str] = Field(default_factory=list, description="Directive arguments")
    lineno: int = Field(..., description="Line number in source file")
    file_path: Optional[str] = Field(None, description="Source file path")

    @classmethod
    def from_raw(cls, raw: dict, file_path: Optional[str] = None) -> "Directive":
        """Convert msc_pyparser directive dict to Directive model."""
        arguments = [
            arg.get("argument", "") for arg in raw.get("arguments", [])
        ]

        return cls(
            type=raw.get("type", "Unknown"),
            arguments=arguments,
            lineno=raw.get("lineno", 0),
            file_path=file_path,
        )


# Type alias for any rule (SecRule or SecAction)
Rule = Union[SecRule, SecAction]

# Type alias for any parsed directive
ParsedDirective = Union[SecRule, SecAction, SecMarker, Directive]


class ParsedConfiguration(BaseModel):
    """Represents a fully parsed ModSecurity configuration."""

    entry_file: str = Field(..., description="Entry configuration file path")
    files: list[str] = Field(default_factory=list, description="All parsed file paths")
    rules: list[Rule] = Field(default_factory=list, description="All SecRule and SecAction directives")
    markers: list[SecMarker] = Field(default_factory=list, description="All SecMarker directives")
    directives: list[Directive] = Field(default_factory=list, description="Other directives")

    @property
    def total_rules(self) -> int:
        """Total number of rules (SecRule + SecAction)."""
        return len(self.rules)

    @property
    def total_secrules(self) -> int:
        """Number of SecRule directives."""
        return sum(1 for r in self.rules if r.type == "SecRule")

    @property
    def total_secactions(self) -> int:
        """Number of SecAction directives."""
        return sum(1 for r in self.rules if r.type == "SecAction")

    def get_rule_by_id(self, rule_id: int) -> Optional[Rule]:
        """Get a rule by its ID."""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def get_all_tags(self) -> set[str]:
        """Get all unique tags across all rules."""
        tags = set()
        for rule in self.rules:
            tags.update(rule.tags)
        return tags
