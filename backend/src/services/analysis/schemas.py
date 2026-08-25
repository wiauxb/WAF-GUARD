"""
Pydantic schemas for AnalysisService.

Naming rule: nothing is ever called bare `id`. There are two independent identifier
spaces and both can appear on the same directive:

  node_id  - assigned by the parser, present on EVERY directive, unique per configuration
  rule_id  - the ModSecurity `id:NNN`, present only where declared, one-to-many
             (a chained SecRule spans several directives sharing one rule_id)

Their numeric ranges overlap, which is fine as long as each field and parameter says
which space it means. The old API had `/directives/id` and `/directives/id/{nodeid}`
meaning different things.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Shared pagination bounds
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000


# ==================== Request Schemas ====================

class HttpRequestFilter(BaseModel):
    """
    Filter directives by simulated request target.

    Both fields are regexes matched with Cypher's `=~`. They are bound as query
    parameters, never interpolated, but a pathological pattern is still expensive to
    evaluate, hence the length cap.
    """
    location: str = Field(default=".*", max_length=500)
    host: str = Field(default=".*", max_length=500)


class ConstantQuery(BaseModel):
    """
    Look up a constant or variable by name.

    value=None means "the node that has no value set", not "any value" — the same
    semantics as the old /use_node and /get_setnode endpoints. A name can have several
    distinct nodes distinguished by value.
    """
    name: str = Field(min_length=1, max_length=500)
    value: Optional[str] = Field(default=None, max_length=2000)


class SourceLocationQuery(BaseModel):
    """Reverse lookup: which directives did this line of configuration produce?"""
    file_path: str = Field(min_length=1, max_length=500)
    line_number: int = Field(gt=0)


# ==================== Response Schemas ====================

class DirectiveResponse(BaseModel):
    """
    One directive node.

    Carries BOTH identifier spaces so a caller can always map between them:
    `node_id` is the parser's, `rule_id` is ModSecurity's (None when the directive
    declares no id).
    """
    node_id: int
    type: str                              # lowercased directive name == the Neo4j label
    args: str
    location: Optional[str] = None
    virtual_host: Optional[str] = None
    if_level: int = 0
    conditions: List[str] = Field(default_factory=list)
    phase: Optional[int] = None
    rule_id: Optional[int] = None          # ModSecurity id:NNN — NOT the node_id
    tags: List[str] = Field(default_factory=list)
    msg: Optional[str] = None
    constants: List[str] = Field(default_factory=list)
    variables: List[str] = Field(default_factory=list)
    context: Optional[str] = None          # "file:line", or the macro chain


class DirectiveListResponse(BaseModel):
    """Paginated list of directives. total_count is the full match count, not the page."""
    configuration_id: int
    directives: List[DirectiveResponse]
    total_count: int
    limit: int
    offset: int


class RemoverEntry(BaseModel):
    """One reason a directive was removed."""
    criterion_type: str                    # "Id" | "Regex"
    criterion_value: Any                   # the rule_id (int) or the tag pattern (str)
    directive: DirectiveResponse           # the SecRuleRemoveBy* that did it


class RemoverListResponse(BaseModel):
    configuration_id: int
    node_id: int                           # the victim — a parser node_id
    removers: List[RemoverEntry]
    total_count: int
    limit: int
    offset: int


class SymbolMatch(BaseModel):
    name: str
    value: Optional[str] = None
    labels: List[str] = Field(default_factory=list)   # Constant | Variable | Collection


class SymbolSearchResponse(BaseModel):
    configuration_id: int
    query: str
    matches: List[SymbolMatch]
    total_count: int
    limit: int
    offset: int


class NodeMetadataEntry(BaseModel):
    """
    One frame of a directive's context chain.

    macro_name is "/" for the frame that sits directly in a file (the outermost one).
    """
    macro_name: str
    file_path: str
    line_number: int


class NodeMetadataResponse(BaseModel):
    configuration_id: int
    node_id: int
    frames: List[NodeMetadataEntry]        # innermost call first, defining file last


class MacroTraceFrame(BaseModel):
    macro_name: str
    file_path: str
    line_number: int
    content: str                           # the <Macro> body, or the `Use` line


class MacroTraceResponse(BaseModel):
    configuration_id: int
    node_id: int
    frames: List[MacroTraceFrame]
    formatted: str                         # pre-rendered text, for the chatbot tool
