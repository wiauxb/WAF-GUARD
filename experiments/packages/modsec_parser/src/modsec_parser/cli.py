"""
Command-line interface for modsec_parser.

Provides commands for parsing, analyzing, and filtering
ModSecurity configurations.
"""

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import ModSecParser
from .statistics import StatisticsCalculator

app = typer.Typer(
    name="modsec-parser",
    help="ModSecurity Configuration Parser - Parse, filter, and analyze ModSecurity configs.",
    add_completion=False,
)

console = Console()


def get_parser(config_file: str) -> ModSecParser:
    """Parse a configuration file and return the parser."""
    parser = ModSecParser()
    try:
        parser.parse(config_file)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Parse error:[/red] {e}")
        raise typer.Exit(1)
    return parser


@app.command()
def parse(
    config_file: str = typer.Argument(..., help="Entry configuration file path"),
    output: Optional[str] = typer.Option(
        None, "-o", "--output", help="Output JSON file path"
    ),
    include_raw: bool = typer.Option(
        False, "--raw", help="Include raw msc_pyparser output in JSON"
    ),
    quiet: bool = typer.Option(False, "-q", "--quiet", help="Suppress output messages"),
):
    """
    Parse a ModSecurity configuration and export to JSON.

    Parses the entry configuration file and all included files,
    converting to structured JSON output.
    """
    parser = get_parser(config_file)
    config = parser.config

    if not quiet:
        console.print(f"[green]Parsed {len(config.files)} file(s)[/green]")
        console.print(f"  Rules: {config.total_rules}")
        console.print(f"  Markers: {len(config.markers)}")
        console.print(f"  Directives: {len(config.directives)}")

    data = parser.export_json(include_raw=include_raw)

    if output:
        with open(output, "w") as f:
            json.dump(data, f, indent=2, default=str)
        if not quiet:
            console.print(f"[green]Exported to {output}[/green]")
    else:
        console.print_json(data=data)


@app.command()
def stats(
    config_file: str = typer.Argument(..., help="Entry configuration file path"),
    by_tag: bool = typer.Option(False, "--by-tag", help="Show stats by tag"),
    by_file: bool = typer.Option(False, "--by-file", help="Show stats by file"),
    by_phase: bool = typer.Option(False, "--by-phase", help="Show stats by phase"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Show statistics for a ModSecurity configuration.

    Displays summary statistics including rule counts, tag distributions,
    operator usage, and more.
    """
    parser = get_parser(config_file)
    stats_data = parser.get_statistics()

    if json_output:
        console.print_json(data=stats_data.model_dump())
        return

    # Default: show text report
    detailed = by_file
    report = StatisticsCalculator.format_report(stats_data, detailed=detailed)
    console.print(report)

    # Additional breakdowns if requested
    if by_tag and not by_file:
        console.print("\n[bold]All Tags:[/bold]")
        table = Table(show_header=True)
        table.add_column("Tag", style="cyan")
        table.add_column("Rules", justify="right")
        for tag, count in sorted(stats_data.rules_by_tag.items(), key=lambda x: -x[1]):
            table.add_row(tag, str(count))
        console.print(table)

    if by_phase:
        console.print("\n[bold]Rules by Phase:[/bold]")
        table = Table(show_header=True)
        table.add_column("Phase", justify="center")
        table.add_column("Rules", justify="right")
        for phase, count in sorted(stats_data.rules_by_phase.items()):
            table.add_row(str(phase), str(count))
        console.print(table)


@app.command(name="filter")
def filter_rules(
    config_file: str = typer.Argument(..., help="Entry configuration file path"),
    rule_id: Optional[int] = typer.Option(None, "--id", help="Filter by rule ID"),
    id_range: Optional[str] = typer.Option(
        None, "--id-range", help="Filter by ID range (e.g., '941000-941999')"
    ),
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag (substring)"),
    variable: Optional[str] = typer.Option(
        None, "--var", help="Filter by variable name"
    ),
    operator: Optional[str] = typer.Option(None, "--op", help="Filter by operator"),
    action: Optional[str] = typer.Option(None, "--action", help="Filter by action"),
    phase: Optional[int] = typer.Option(None, "--phase", help="Filter by phase"),
    file_pattern: Optional[str] = typer.Option(
        None, "--file", help="Filter by file pattern"
    ),
    chained: Optional[bool] = typer.Option(None, "--chained", help="Filter chained rules"),
    output_format: str = typer.Option(
        "table", "--format", "-f", help="Output format (table/json/ids)"
    ),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum results to show"),
):
    """
    Filter rules by various criteria.

    Supports filtering by rule ID, tags, variables, operators, actions,
    phase, file location, and chain status.
    """
    parser = get_parser(config_file)
    rules = parser.get_rules()
    filter_chain = rules.filter()

    # Apply filters
    if rule_id is not None:
        filter_chain = filter_chain.by_id(rule_id)

    if id_range:
        try:
            start, end = map(int, id_range.split("-"))
            filter_chain = filter_chain.by_id_range(start, end)
        except ValueError:
            console.print("[red]Error:[/red] Invalid ID range format. Use 'START-END'")
            raise typer.Exit(1)

    if tag:
        filter_chain = filter_chain.by_tag(tag)

    if variable:
        filter_chain = filter_chain.by_variable(variable)

    if operator:
        filter_chain = filter_chain.by_operator(operator)

    if action:
        filter_chain = filter_chain.by_action(action)

    if phase is not None:
        filter_chain = filter_chain.by_phase(phase)

    if file_pattern:
        filter_chain = filter_chain.by_file(file_pattern)

    if chained is not None:
        if chained:
            filter_chain = filter_chain.chained_only()
        else:
            filter_chain = filter_chain.not_chained()

    # Execute filter
    results = filter_chain.execute()
    total = len(results)

    # Output
    if output_format == "json":
        data = [r.model_dump() for r in results[:limit]]
        console.print_json(data={"total": total, "results": data})

    elif output_format == "ids":
        ids = [r.rule_id for r in results if r.rule_id is not None]
        for rid in ids[:limit]:
            console.print(rid)
        if total > limit:
            console.print(f"... and {total - limit} more", style="dim")

    else:  # table
        console.print(f"\n[bold]Found {total} matching rule(s)[/bold]\n")

        table = Table(show_header=True)
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Phase", justify="center")
        table.add_column("Tags", style="yellow", max_width=40)
        table.add_column("File", style="dim", max_width=30)

        for rule in results[:limit]:
            rule_id_str = str(rule.rule_id) if rule.rule_id else "-"
            phase_str = str(rule.phase) if rule.phase else "-"
            tags_str = ", ".join(rule.tags[:3])
            if len(rule.tags) > 3:
                tags_str += f" (+{len(rule.tags) - 3})"
            file_str = Path(rule.file_path).name if rule.file_path else "-"

            table.add_row(rule_id_str, rule.type, phase_str, tags_str, file_str)

        console.print(table)

        if total > limit:
            console.print(f"\n[dim]Showing {limit} of {total} results. Use --limit to show more.[/dim]")


@app.command()
def tags(
    config_file: str = typer.Argument(..., help="Entry configuration file path"),
    sort_by: str = typer.Option(
        "count", "--sort", help="Sort by 'count' or 'name'"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    List all unique tags in the configuration.

    Shows all tags found across all rules, with rule counts.
    """
    parser = get_parser(config_file)
    stats_data = parser.get_statistics()

    if json_output:
        console.print_json(data=stats_data.rules_by_tag)
        return

    console.print(f"\n[bold]Found {len(stats_data.unique_tags)} unique tag(s)[/bold]\n")

    table = Table(show_header=True)
    table.add_column("Tag", style="cyan")
    table.add_column("Rules", justify="right")

    items = stats_data.rules_by_tag.items()
    if sort_by == "name":
        items = sorted(items, key=lambda x: x[0])
    else:
        items = sorted(items, key=lambda x: -x[1])

    for tag, count in items:
        table.add_row(tag, str(count))

    console.print(table)


@app.command()
def files(
    config_file: str = typer.Argument(..., help="Entry configuration file path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    List all parsed configuration files.

    Shows all files that were parsed, including those from Include directives.
    """
    parser = get_parser(config_file)
    config = parser.config
    stats_data = parser.get_statistics()

    if json_output:
        data = {
            "total_files": len(config.files),
            "files": [
                {
                    "path": f,
                    "rules": stats_data.per_file.get(f, {}).rule_count
                    if f in stats_data.per_file
                    else 0,
                }
                for f in config.files
            ],
        }
        console.print_json(data=data)
        return

    console.print(f"\n[bold]Parsed {len(config.files)} file(s)[/bold]\n")

    table = Table(show_header=True)
    table.add_column("File", style="cyan")
    table.add_column("Rules", justify="right")
    table.add_column("Markers", justify="right")
    table.add_column("Directives", justify="right")

    for filepath in config.files:
        file_stats = stats_data.per_file.get(filepath)
        if file_stats:
            table.add_row(
                filepath,
                str(file_stats.rule_count),
                str(file_stats.secmarker_count),
                str(file_stats.directive_count),
            )
        else:
            table.add_row(filepath, "0", "0", "0")

    console.print(table)


@app.command()
def rule(
    config_file: str = typer.Argument(..., help="Entry configuration file path"),
    rule_id: int = typer.Argument(..., help="Rule ID to look up"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Show details for a specific rule by ID.

    Displays full rule information including variables, operator, and actions.
    """
    parser = get_parser(config_file)
    found_rule = parser.get_rules().by_id(rule_id)

    if not found_rule:
        console.print(f"[red]Rule {rule_id} not found[/red]")
        raise typer.Exit(1)

    if json_output:
        console.print_json(data=found_rule.model_dump())
        return

    console.print(f"\n[bold]Rule {rule_id}[/bold]\n")
    console.print(f"  Type: {found_rule.type}")
    console.print(f"  File: {found_rule.file_path}")
    console.print(f"  Line: {found_rule.lineno}")

    if found_rule.phase:
        console.print(f"  Phase: {found_rule.phase}")

    if found_rule.tags:
        console.print(f"  Tags: {', '.join(found_rule.tags)}")

    if hasattr(found_rule, "severity") and found_rule.severity:
        console.print(f"  Severity: {found_rule.severity}")

    if hasattr(found_rule, "msg") and found_rule.msg:
        console.print(f"  Message: {found_rule.msg}")

    if hasattr(found_rule, "operator"):
        console.print(f"\n  Operator: {found_rule.operator.name}")
        if found_rule.operator.argument:
            arg = found_rule.operator.argument
            if len(arg) > 100:
                arg = arg[:100] + "..."
            console.print(f"  Pattern: {arg}")

    if hasattr(found_rule, "variables") and found_rule.variables:
        console.print("\n  Variables:")
        for var in found_rule.variables:
            prefix = ""
            if var.negated:
                prefix += "!"
            if var.count:
                prefix += "&"
            selector = f":{var.selector}" if var.selector else ""
            console.print(f"    - {prefix}{var.name}{selector}")

    console.print("\n  Actions:")
    for action in found_rule.actions:
        if action.argument:
            console.print(f"    - {action.name}:{action.argument}")
        else:
            console.print(f"    - {action.name}")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
