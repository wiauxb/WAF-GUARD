# modsec-parser

A Python library for parsing, filtering, and analyzing ModSecurity configurations.

## Installation

```bash
pip install -e .
```

## Usage

### Python API

```python
from modsec_parser import ModSecParser

parser = ModSecParser()
config = parser.parse("/path/to/rules.conf")

# Get statistics
stats = parser.get_statistics()
print(f"Total rules: {stats.total_rules}")
print(parser.get_report())

# Filter rules
rules = parser.get_rules()
sqli_rules = rules.filter().by_tag("sqli").by_phase(2).execute()

# Get specific rule
rule = rules.by_id(942100)

# Export to JSON
data = parser.export_json()
```

### CLI

```bash
# Parse and export to JSON
modsec-parser parse /path/to/config.conf -o output.json

# Show statistics
modsec-parser stats /path/to/config.conf --by-tag

# Filter rules
modsec-parser filter /path/to/config.conf --tag "sqli" --phase 2

# List tags
modsec-parser tags /path/to/config.conf

# Show rule details
modsec-parser rule /path/to/config.conf 942100
```

## Features

- Parse ModSecurity configurations with Include resolution
- Pydantic models for type safety
- Fluent filtering API
- Statistics and reporting
- CLI interface
