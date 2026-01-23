#!/usr/bin/python3

import glob
import json
import os
import sys
from collections import defaultdict

import msc_pyparser


# =============================================================================
# File Reading and Parsing
# =============================================================================

def read_file(filepath):
    """Read and return the content of a file."""
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Can't open file: {filepath}")
        print(e)
        sys.exit(1)


def parse_file(filepath):
    """Parse a ModSecurity configuration file and return the parsed config lines."""
    content = read_file(filepath)
    try:
        mparser = msc_pyparser.MSCParser()
        mparser.parser.parse(content)
    except Exception as e:
        print(f"Can't parse file: {filepath}")
        print(e)
        sys.exit(1)
    return mparser.configlines


def expand_path(filepath):
    """Expand a filepath to its absolute form."""
    dname = os.path.dirname(filepath)
    fname = os.path.basename(filepath)
    if os.path.isdir(dname):
        absdir = dname
    else:
        absdir = "./"
    return os.path.join(absdir, fname)


def collect_configs(entry_file):
    """
    Parse the entry config file and recursively collect all included configs.
    Returns a dict mapping filepath -> parsed config lines.
    """
    configs = {}
    includes = [expand_path(entry_file)]

    for filepath in includes:
        configs[filepath] = parse_file(filepath)
        for directive in configs[filepath]:
            if directive['type'].lower() == "include":
                include_pattern = directive['arguments'][0]['argument']
                if include_pattern[0] != "/":
                    dname = os.path.dirname(filepath)
                    include_pattern = os.path.join(dname, include_pattern)
                for f in glob.glob(include_pattern):
                    includes.append(f)

    return configs


# =============================================================================
# Statistics Extraction
# =============================================================================

def extract_rules(config_lines):
    """Extract all SecRule and SecAction directives from config lines."""
    return [d for d in config_lines if d.get('type') in ('SecRule', 'SecAction')]


def extract_secmarkers(config_lines):
    """Extract all SecMarker directives from config lines."""
    return [d for d in config_lines if d.get('type') == 'SecMarker']


def extract_directives(config_lines):
    """Extract all other directives (excluding SecRule, SecAction, SecMarker, and Comments)."""
    excluded_types = ('SecRule', 'SecAction', 'SecMarker', 'Comment')
    return [d for d in config_lines if d.get('type') not in excluded_types]


def extract_tags_from_rule(rule):
    """Extract all tags from a single rule."""
    tags = []
    for action in rule.get('actions', []):
        if action.get('act_name') == 'tag':
            tags.append(action.get('act_arg', ''))
    return tags


def compute_file_stats(config_lines):
    """
    Compute statistics for a single file.
    Returns: (rule_count, secmarker_count, directive_count, tags_stats_dict)
    tags_stats_dict: {tag: {'rules': count, 'secmarkers': count, 'directives': count}}
    """
    rules = extract_rules(config_lines)
    secmarkers = extract_secmarkers(config_lines)
    directives = extract_directives(config_lines)
    tags_stats = defaultdict(lambda: {'rules': 0, 'secmarkers': 0, 'directives': 0})

    for rule in rules:
        for tag in extract_tags_from_rule(rule):
            tags_stats[tag]['rules'] += 1

    for secmarker in secmarkers:
        for tag in extract_tags_from_rule(secmarker):
            tags_stats[tag]['secmarkers'] += 1

    for directive in directives:
        for tag in extract_tags_from_rule(directive):
            tags_stats[tag]['directives'] += 1

    # Convert to regular dict
    return len(rules), len(secmarkers), len(directives), {k: dict(v) for k, v in tags_stats.items()}


def compute_global_stats(configs):
    """
    Compute global statistics across all config files.
    Returns: {
        'total_rules': int,
        'total_secmarkers': int,
        'total_directives': int,
        'total_tags': set,
        'stats_per_tag': {tag: {'rules': int, 'secmarkers': int, 'directives': int}},
        'per_file': {filepath: {'rules': int, 'secmarkers': int, 'directives': int, 'tags': dict}}
    }
    """
    stats = {
        'total_rules': 0,
        'total_secmarkers': 0,
        'total_directives': 0,
        'total_tags': set(),
        'stats_per_tag': defaultdict(lambda: {'rules': 0, 'secmarkers': 0, 'directives': 0}),
        'per_file': {}
    }

    for filepath, config_lines in configs.items():
        rule_count, secmarker_count, directive_count, tags_stats = compute_file_stats(config_lines)

        stats['per_file'][filepath] = {
            'rules': rule_count,
            'secmarkers': secmarker_count,
            'directives': directive_count,
            'tags': tags_stats
        }

        stats['total_rules'] += rule_count
        stats['total_secmarkers'] += secmarker_count
        stats['total_directives'] += directive_count
        for tag, counts in tags_stats.items():
            stats['total_tags'].add(tag)
            stats['stats_per_tag'][tag]['rules'] += counts['rules']
            stats['stats_per_tag'][tag]['secmarkers'] += counts['secmarkers']
            stats['stats_per_tag'][tag]['directives'] += counts['directives']

    stats['stats_per_tag'] = {k: dict(v) for k, v in stats['stats_per_tag'].items()}
    return stats


# =============================================================================
# Report Generation
# =============================================================================

def print_separator(char='=', length=70):
    print(char * length)


def print_header(title):
    print_separator()
    print(f" {title}")
    print_separator()


def print_report(stats):
    """Print a formatted statistics report."""
    print()
    print_header("MODSECURITY CONFIGURATION STATISTICS REPORT")
    print()

    # Global summary
    print_header("GLOBAL SUMMARY")
    print(f"  Total configuration files: {len(stats['per_file'])}")
    print(f"  Total rules (SecRule + SecAction): {stats['total_rules']}")
    print(f"  Total SecMarkers:          {stats['total_secmarkers']}")
    print(f"  Total other directives:    {stats['total_directives']}")
    print(f"  Total unique tags:         {len(stats['total_tags'])}")
    print()

    # # All tags list
    # print_header("ALL TAGS")
    # if stats['total_tags']:
    #     for tag in sorted(stats['total_tags']):
    #         print(f"  - {tag}")
    # else:
    #     print("  (no tags found)")
    # print()

    # Stats per tag (global)
    print_header("STATS PER TAG (GLOBAL)")
    if stats['stats_per_tag']:
        max_tag_len = max(len(tag) for tag in stats['stats_per_tag'])
        for tag, counts in sorted(stats['stats_per_tag'].items(), key=lambda x: -(x[1]['rules'] + x[1]['secmarkers'] + x[1]['directives'])):
            print(f"  {tag:<{max_tag_len}}  Rules: {counts['rules']:>5}  |  SecMarker: {counts['secmarkers']:>5}  |  Directives: {counts['directives']:>5}")
    else:
        print("  (no tags found)")
    print()

    # Per-file statistics
    print_header("PER-FILE STATISTICS")
    for filepath in sorted(stats['per_file'].keys()):
        file_stats = stats['per_file'][filepath]
        if file_stats['rules'] == 0 and file_stats['secmarkers'] == 0 and file_stats['directives'] == 0:
            continue

        print()
        print(f"  [{filepath}]")
        print(f"    Rules: {file_stats['rules']}  |  SecMarker: {file_stats['secmarkers']}  |  Directives: {file_stats['directives']}")
        if file_stats['tags']:
            print(f"    Tags:")
            max_tag_len = max(len(tag) for tag in file_stats['tags'])
            for tag, counts in sorted(file_stats['tags'].items(), key=lambda x: -(x[1]['rules'] + x[1]['secmarkers'] + x[1]['directives'])):
                print(f"      {tag:<{max_tag_len}}  Rules: {counts['rules']:>5}  |  SecMarker: {counts['secmarkers']:>5}  |  Directives: {counts['directives']:>5}")
    print()
    print_separator()


# =============================================================================
# Main
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: parser.py <config_file>")
        sys.exit(1)

    entry_file = sys.argv[1]

    # Parse all configuration files
    configs = collect_configs(entry_file)

    # Compute statistics
    stats = compute_global_stats(configs)

    # Print report
    print_report(stats)

    # Export raw data to JSON
    output_file = "output.json"
    with open(output_file, "w") as fp:
        fp.write(json.dumps(configs, indent=4))


if __name__ == "__main__":
    main()
