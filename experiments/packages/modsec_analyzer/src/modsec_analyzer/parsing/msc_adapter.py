"""
Parsing module for ModSecurity configuration files.

Uses msc_pyparser to parse files and converts output to domain models.
"""

import glob
import os
from pathlib import Path

import msc_pyparser

from ..domain.components import Variable, Operator, Action, Argument
from ..domain.rules import Rule, SecRule, SecAction, Directive
from ..domain.ruleset import RuleSet


def parse_file(
    filepath: str,
    resolve_includes: bool = False,
    include_comments: bool = False,
) -> RuleSet:
    """
    Parse a ModSecurity configuration file and return a RuleSet.

    Args:
        filepath: Path to the configuration file
        resolve_includes: If True, recursively resolve include directives
        include_comments: If True, include Comment directives (default: False)

    Returns:
        RuleSet containing all parsed rules in execution order
    """
    rules = []

    if resolve_includes:
        files_data = _resolve_includes(filepath)
    else:
        files_data = [(filepath, _parse_single_file(filepath))]

    for file_path, configlines in files_data:
        for item in configlines:
            # Skip comments if not requested
            if not include_comments and item.get("type") == "Comment":
                continue
            rule = _convert_item(item, file_path)
            rules.append(rule)

    return RuleSet(rules=rules)


def _parse_single_file(filepath: str) -> list[dict]:
    """
    Parse a single file and return raw configlines from msc_pyparser.

    Args:
        filepath: Path to the file

    Returns:
        List of parsed directive dicts
    """
    content = Path(filepath).read_text()
    mparser = msc_pyparser.MSCParser()
    mparser.parser.parse(content)
    return mparser.configlines


def _resolve_includes(entry_file: str) -> list[tuple[str, list[dict]]]:
    """
    Recursively resolve include directives and return files in execution order.

    Uses depth-first traversal to match ModSecurity's execution order:
    when an include is encountered, those files are processed before
    continuing with the rest of the current file.

    Args:
        entry_file: Path to the entry point configuration file

    Returns:
        List of (filepath, configlines) tuples in execution order
    """
    result = []
    visited = set()
    to_process = [os.path.abspath(entry_file)]

    while to_process:
        filepath = to_process.pop(0)

        if filepath in visited:
            continue
        visited.add(filepath)

        configlines = _parse_single_file(filepath)
        result.append((filepath, configlines))

        # Find include directives and collect files to insert
        includes_to_add = []
        for item in configlines:
            if item.get("type", "").lower() == "include":
                args = item.get("arguments", [])
                if args:
                    pattern = args[0].get("argument", "")
                    if pattern:
                        # Resolve relative path from current file's directory
                        if not os.path.isabs(pattern):
                            base_dir = os.path.dirname(filepath)
                            pattern = os.path.join(base_dir, pattern)

                        # Expand glob and add files
                        for f in sorted(glob.glob(pattern)):
                            if f not in visited:
                                includes_to_add.append(f)

        # Insert at beginning for depth-first processing
        to_process = includes_to_add + to_process

    return result


def _convert_item(item: dict, file_path: str) -> Rule:
    """
    Convert a raw msc_pyparser dict to a domain Rule object.

    Args:
        item: Raw parsed dict from msc_pyparser
        file_path: Source file path

    Returns:
        Appropriate Rule subclass instance
    """
    item_type = item.get("type", "")
    lineno = item.get("lineno", 0)

    if item_type == "SecRule":
        return SecRule(
            type=item_type,
            lineno=lineno,
            file_path=file_path,
            variables=[_convert_variable(v) for v in item.get("variables", [])],
            operator=_convert_operator(item),
            actions=[_convert_action(a) for a in item.get("actions", [])],
            chained=item.get("chained", False),
        )

    elif item_type == "SecAction":
        return SecAction(
            type=item_type,
            lineno=lineno,
            file_path=file_path,
            actions=[_convert_action(a) for a in item.get("actions", [])],
        )

    else:
        # Generic directive (include, SecMarker, Comment, etc.)
        return Directive(
            type=item_type,
            lineno=lineno,
            file_path=file_path,
            arguments=[_convert_argument(a) for a in item.get("arguments", [])],
        )


def _convert_variable(raw: dict) -> Variable:
    """Convert a raw variable dict to Variable dataclass."""
    return Variable(
        variable=raw.get("variable", ""),
        variable_part=raw.get("variable_part", ""),
        quote_type=raw.get("quote_type", "no_quote"),
        negated=raw.get("negated", False),
        counter=raw.get("counter", False),
    )


def _convert_operator(item: dict) -> Operator:
    """Extract operator fields from a SecRule dict and create Operator dataclass."""
    return Operator(
        operator=item.get("operator", ""),
        operator_argument=item.get("operator_argument", ""),
        operator_negated=item.get("operator_negated", False),
        oplineno=item.get("oplineno", 0),
    )


def _convert_action(raw: dict) -> Action:
    """Convert a raw action dict to Action dataclass."""
    return Action(
        act_name=raw.get("act_name", ""),
        lineno=raw.get("lineno", 0),
        act_quote=raw.get("act_quote", "no_quote"),
        act_arg=raw.get("act_arg", ""),
        act_arg_val=raw.get("act_arg_val", ""),
        act_arg_val_param=raw.get("act_arg_val_param", ""),
        act_arg_val_param_val=raw.get("act_arg_val_param_val", ""),
    )


def _convert_argument(raw: dict) -> Argument:
    """Convert a raw argument dict to Argument dataclass."""
    return Argument(
        argument=raw.get("argument", ""),
        quote_type=raw.get("quote_type", "no_quote"),
    )
