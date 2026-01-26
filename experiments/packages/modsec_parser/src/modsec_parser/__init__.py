"""
modsec_parser - ModSecurity Configuration Parser

A Python library for parsing, filtering, and analyzing ModSecurity configurations.

Example usage:
    from modsec_parser import ModSecParser

    parser = ModSecParser()
    config = parser.parse("/path/to/modsecurity.conf")

    # Get statistics
    stats = parser.get_statistics()
    print(f"Total rules: {stats.total_rules}")

    # Filter rules
    sqli_rules = parser.get_rules().filter().by_tag("sqli").execute()
"""

from .collection import RuleCollection, RuleFilter
from .loader import ConfigurationLoader
from .models import (
    Action,
    Directive,
    Operator,
    ParsedConfiguration,
    ParsedDirective,
    Rule,
    SecAction,
    SecMarker,
    SecRule,
    Variable,
)
from .statistics import ConfigurationStatistics, FileStatistics, StatisticsCalculator

__version__ = "0.1.0"
__all__ = [
    # Main entry point
    "ModSecParser",
    # Models
    "Action",
    "Variable",
    "Operator",
    "SecRule",
    "SecAction",
    "SecMarker",
    "Directive",
    "Rule",
    "ParsedDirective",
    "ParsedConfiguration",
    # Loader
    "ConfigurationLoader",
    # Collection
    "RuleCollection",
    "RuleFilter",
    # Statistics
    "ConfigurationStatistics",
    "FileStatistics",
    "StatisticsCalculator",
]


class ModSecParser:
    """
    Main entry point for parsing ModSecurity configurations.

    Provides a simple interface to parse configurations, access rules
    with filtering capabilities, and compute statistics.

    Example:
        parser = ModSecParser()
        config = parser.parse("/path/to/modsecurity.conf")

        # Access rules with filtering
        rules = parser.get_rules()
        sqli_rules = rules.filter().by_tag("attack-sqli").execute()

        # Get statistics
        stats = parser.get_statistics()
        print(stats.total_rules)
    """

    def __init__(self):
        """Initialize the parser."""
        self._loader = ConfigurationLoader()
        self._config: ParsedConfiguration | None = None
        self._statistics: ConfigurationStatistics | None = None

    def parse(self, entry_file: str) -> ParsedConfiguration:
        """
        Parse a ModSecurity configuration.

        Loads the entry file and recursively parses all included
        configuration files.

        Args:
            entry_file: Path to the main configuration file.

        Returns:
            ParsedConfiguration with all parsed data.

        Raises:
            FileNotFoundError: If the entry file doesn't exist.
            ValueError: If parsing fails.
        """
        self._config = self._loader.load(entry_file)
        self._statistics = None  # Reset cached statistics
        return self._config

    @property
    def config(self) -> ParsedConfiguration | None:
        """Get the currently loaded configuration."""
        return self._config

    def get_rules(self) -> RuleCollection:
        """
        Get a RuleCollection for filtering rules.

        Returns:
            RuleCollection with filtering capabilities.

        Raises:
            ValueError: If no configuration has been parsed.
        """
        if not self._config:
            raise ValueError("No configuration loaded. Call parse() first.")
        return RuleCollection(self._config.rules)

    def get_statistics(self) -> ConfigurationStatistics:
        """
        Get statistics for the loaded configuration.

        Statistics are cached after first calculation.

        Returns:
            ConfigurationStatistics with computed metrics.

        Raises:
            ValueError: If no configuration has been parsed.
        """
        if not self._config:
            raise ValueError("No configuration loaded. Call parse() first.")

        if not self._statistics:
            self._statistics = StatisticsCalculator.calculate(self._config)

        return self._statistics

    def get_report(self, detailed: bool = False) -> str:
        """
        Generate a human-readable statistics report.

        Args:
            detailed: If True, include per-file breakdown.

        Returns:
            Formatted report string.

        Raises:
            ValueError: If no configuration has been parsed.
        """
        stats = self.get_statistics()
        return StatisticsCalculator.format_report(stats, detailed=detailed)

    def get_raw_configs(self) -> dict[str, list[dict]]:
        """
        Get the raw msc_pyparser output for all parsed files.

        Useful for debugging or accessing unparsed data.

        Returns:
            Dictionary mapping file paths to lists of raw directive dicts.
        """
        return self._loader.get_raw_configs()

    def export_json(self, include_raw: bool = False) -> dict:
        """
        Export the configuration as a JSON-serializable dictionary.

        Args:
            include_raw: If True, include raw msc_pyparser output.

        Returns:
            Dictionary representation of the configuration.

        Raises:
            ValueError: If no configuration has been parsed.
        """
        if not self._config:
            raise ValueError("No configuration loaded. Call parse() first.")

        result = self._config.model_dump()

        if include_raw:
            result["raw"] = self.get_raw_configs()

        return result
