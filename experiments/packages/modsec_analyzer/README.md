# ModSecurity Analyzer

A domain-driven ModSecurity rules analyzer for parsing, transforming, and analyzing CRS (Core Rule Set) configurations.

## Architecture

This package follows a clean architecture pattern:

```
modsec_analyzer/
├── domain/                     # Pure business logic
│   ├── enums.py               # Phase, ActionType, ActionGroup...
│   ├── actions.py             # Action dataclass
│   ├── rules.py               # Rule, SecRule, CommentRule...
│   ├── ruleset.py             # RuleSet + expressive filters
│   ├── knowledge/             # ModSecurity documentation → code
│   │   └── action_groups.py
│   └── transformations.py     # Business transformations (AddTag, etc.)
│
├── parsing/                    # Input (msc_pyparser → domain)
│   └── msc_adapter.py
│
├── transformations/            # Output (domain → msc_writer)
│   └── msc_applier.py
│
├── api_models/                 # External boundaries (Pydantic)
│   ├── input.py               # User filters
│   └── output.py              # API/MCP responses
│
└── services/                   # Orchestration (use-cases)
    └── analyze.py
```

## Installation

```bash
# From the package directory
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

## Usage

```python
from modsec_analyzer.services.analyze import AnalyzerService
from modsec_analyzer.parsing.msc_adapter import MscAdapter

# Parse rules from file
adapter = MscAdapter()
ruleset = adapter.parse_file("rules.conf")

# Analyze
service = AnalyzerService()
result = service.analyze(ruleset)
```

## Development

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=modsec_analyzer
```
