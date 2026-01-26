"""
Configuration loader for ModSecurity files.

Handles parsing of ModSecurity configuration files using msc_pyparser,
including recursive resolution of Include directives.
"""

import glob
import os
from typing import Any

import msc_pyparser

from .models import (
    Directive,
    ParsedConfiguration,
    ParsedDirective,
    Rule,
    SecAction,
    SecMarker,
    SecRule,
)


class ConfigurationLoader:
    """
    Loads and parses ModSecurity configuration files.

    Handles recursive Include resolution and converts raw msc_pyparser
    output to typed Pydantic models.
    """

    def __init__(self, base_path: str | None = None):
        """
        Initialize the loader.

        Args:
            base_path: Optional base path for resolving relative includes.
                       If not provided, uses the directory of the entry file.
        """
        self.base_path = base_path
        self._raw_configs: dict[str, list[dict]] = {}

    def load(self, entry_file: str) -> ParsedConfiguration:
        """
        Load a ModSecurity configuration starting from the entry file.

        Recursively resolves all Include directives and parses all
        referenced configuration files.

        Args:
            entry_file: Path to the main configuration file.

        Returns:
            ParsedConfiguration with all parsed directives.

        Raises:
            FileNotFoundError: If the entry file doesn't exist.
            ValueError: If parsing fails.
        """
        self._raw_configs.clear()

        # Normalize entry file path
        entry_file = self._expand_path(entry_file)

        if not os.path.isfile(entry_file):
            raise FileNotFoundError(f"Configuration file not found: {entry_file}")

        # Collect all configs recursively
        self._collect_configs(entry_file)

        # Convert to models
        return self._build_configuration(entry_file)

    def _expand_path(self, filepath: str) -> str:
        """Expand a filepath to its absolute form."""
        return os.path.abspath(filepath)

    def _read_file(self, filepath: str) -> str:
        """Read and return the content of a file."""
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def _parse_file(self, filepath: str) -> list[dict]:
        """
        Parse a single ModSecurity configuration file.

        Args:
            filepath: Path to the configuration file.

        Returns:
            List of raw directive dictionaries from msc_pyparser.

        Raises:
            ValueError: If parsing fails.
        """
        content = self._read_file(filepath)
        try:
            parser = msc_pyparser.MSCParser()
            parser.parser.parse(content)
            return parser.configlines
        except Exception as e:
            raise ValueError(f"Failed to parse {filepath}: {e}") from e

    def _collect_configs(self, entry_file: str) -> None:
        """
        Parse the entry config and recursively collect all included configs.

        Args:
            entry_file: Path to the entry configuration file.
        """
        includes = [entry_file]

        for filepath in includes:
            if filepath in self._raw_configs:
                continue

            self._raw_configs[filepath] = self._parse_file(filepath)

            # Find and resolve Include directives
            for directive in self._raw_configs[filepath]:
                if directive.get("type", "").lower() == "include":
                    include_pattern = self._get_include_path(directive, filepath)
                    if include_pattern:
                        # Expand glob patterns
                        matched_files = glob.glob(include_pattern)
                        for f in sorted(matched_files):
                            if f not in includes:
                                includes.append(f)

    def _get_include_path(self, directive: dict, source_file: str) -> str | None:
        """
        Extract and resolve the include path from an Include directive.

        Args:
            directive: The Include directive dictionary.
            source_file: Path to the file containing the Include.

        Returns:
            Resolved include path or pattern, or None if invalid.
        """
        arguments = directive.get("arguments", [])
        if not arguments:
            return None

        include_path = arguments[0].get("argument", "")
        if not include_path:
            return None

        # Handle relative paths
        if not os.path.isabs(include_path):
            base_dir = os.path.dirname(source_file)
            include_path = os.path.join(base_dir, include_path)

        return include_path

    def _build_configuration(self, entry_file: str) -> ParsedConfiguration:
        """
        Build a ParsedConfiguration from collected raw configs.

        Args:
            entry_file: Path to the entry configuration file.

        Returns:
            ParsedConfiguration with all parsed and converted directives.
        """
        rules: list[Rule] = []
        markers: list[SecMarker] = []
        directives: list[Directive] = []
        files = list(self._raw_configs.keys())

        for filepath, config_lines in self._raw_configs.items():
            for raw in config_lines:
                directive_type = raw.get("type", "")

                if directive_type == "SecRule":
                    rules.append(SecRule.from_raw(raw, filepath))
                elif directive_type == "SecAction":
                    rules.append(SecAction.from_raw(raw, filepath))
                elif directive_type == "SecMarker":
                    markers.append(SecMarker.from_raw(raw, filepath))
                elif directive_type not in ("Comment", ""):
                    # Skip comments and empty entries
                    directives.append(Directive.from_raw(raw, filepath))

        return ParsedConfiguration(
            entry_file=entry_file,
            files=files,
            rules=rules,
            markers=markers,
            directives=directives,
        )

    def get_raw_configs(self) -> dict[str, list[dict]]:
        """
        Get the raw msc_pyparser output for all parsed files.

        Useful for debugging or accessing unparsed data.

        Returns:
            Dictionary mapping file paths to lists of raw directive dicts.
        """
        return self._raw_configs.copy()
