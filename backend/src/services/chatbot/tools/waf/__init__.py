"""
WAF analysis tools.

The previous five tools here returned hardcoded fake data; they are gone. These call
AnalysisService against the configuration the conversation is bound to.

Two families, answering different questions:
  - `analysis_tools` query the COMPILED configuration (the macro-expanded dump) — what
    Apache actually loaded;
  - `source_tools` read the ORIGINAL files it was compiled from — what a human edits.

Both resolve against the conversation's bound configuration, and neither can write.
"""

from .analysis_tools import (
    ALL_TOOLS as ANALYSIS_TOOLS,
    get_provenance,
    get_statistics,
    list_values,
    match_url,
    removed_by,
    search_directives,
    search_symbols,
    what_removes,
    who_sets,
    who_uses,
)
from .source_tools import (
    SOURCE_TOOLS,
    glob_config,
    grep_config,
    read_config_file,
)

ALL_TOOLS = ANALYSIS_TOOLS + SOURCE_TOOLS

__all__ = [
    "ALL_TOOLS",
    "ANALYSIS_TOOLS",
    "SOURCE_TOOLS",
    "search_directives",
    "get_statistics",
    "list_values",
    "match_url",
    "search_symbols",
    "who_uses",
    "who_sets",
    "what_removes",
    "removed_by",
    "get_provenance",
    "grep_config",
    "glob_config",
    "read_config_file",
]
