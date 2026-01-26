"""
Domain components - Building blocks for ModSecurity rules.

These dataclasses map 1:1 with msc_pyparser output format.
"""

from dataclasses import dataclass


@dataclass
class Variable:
    """
    A variable in a SecRule.

    Maps to msc_pyparser 'variable' dict structure.
    Example: &!ARGS:foo → variable="ARGS", variable_part="foo", negated=True, counter=True
    """
    variable: str                   # "TX", "ARGS", "REQUEST_HEADERS", etc.
    variable_part: str = ""         # Sub-part (e.g., "EXECUTING_PARANOIA_LEVEL")
    quote_type: str = "no_quote"    # "no_quote", "quotes", "quoted"
    negated: bool = False           # True if prefixed with !
    counter: bool = False           # True if prefixed with &

    def __repr__(self) -> str:
        prefix = ""
        if self.counter:
            prefix += "&"
        if self.negated:
            prefix += "!"
        if self.variable_part:
            return f"{prefix}{self.variable}:{self.variable_part}"
        return f"{prefix}{self.variable}"


@dataclass
class Operator:
    """
    An operator in a SecRule.

    Groups operator-related fields from msc_pyparser.
    Example: !@rx pattern → operator="@rx", operator_argument="pattern", operator_negated=True
    """
    operator: str = ""              # "@rx", "@lt", "@eq", "@pm", etc.
    operator_argument: str = ""     # The pattern or value
    operator_negated: bool = False  # True if operator has !
    oplineno: int = 0               # Line number of operator

    def __repr__(self) -> str:
        neg = "!" if self.operator_negated else ""
        op = self.operator or "@rx"
        arg = self.operator_argument
        if len(arg) > 50:
            arg = arg[:47] + "..."
        return f'{neg}{op} "{arg}"'


@dataclass
class Action:
    """
    An action in a SecRule or SecAction.

    Maps to msc_pyparser 'action' dict structure.

    Examples:
        id:920001         → act_name="id", act_arg="920001"
        setvar:tx.test=1  → act_name="setvar", act_arg="tx.test", act_arg_val="1"
        t:lowercase       → act_name="t", act_arg="lowercase"
        deny              → act_name="deny", act_arg=""
    """
    act_name: str                       # "id", "phase", "tag", "setvar", "t", "deny", etc.
    lineno: int = 0
    act_quote: str = "no_quote"         # Quote type for argument
    act_arg: str = ""                   # Main argument
    act_arg_val: str = ""               # For name=value patterns (ctl, setvar)
    act_arg_val_param: str = ""         # Additional parameter
    act_arg_val_param_val: str = ""     # Additional parameter value

    def __repr__(self) -> str:
        if not self.act_arg:
            return self.act_name
        if self.act_arg_val:
            return f"{self.act_name}:{self.act_arg}={self.act_arg_val}"
        return f"{self.act_name}:{self.act_arg}"


@dataclass
class Argument:
    """
    An argument for generic directives (include, SecMarker, etc.).

    Maps to msc_pyparser 'argument' dict structure.
    Example: Include "/path/*.conf"
    """
    argument: str
    quote_type: str = "no_quote"

    def __repr__(self) -> str:
        return self.argument
