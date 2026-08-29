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

from typing import Any, Dict, List, Literal, Optional

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


# Columns the result set may be ordered by. A whitelist, not a free string: Cypher cannot
# parameterise ORDER BY, so the chosen name is interpolated into the query and must never
# come straight from the caller. `queries.SORT_FIELDS` maps these onto node properties.
SortField = Literal["node_id", "type", "rule_id", "phase", "host", "location"]

# Properties offering a searchable value list via GET /directives/values/{field}.
ValueField = Literal["tag", "host", "location", "type", "phase", "msg"]


class DirectiveSearchQuery(BaseModel):
    """
    Combinable directive filter — the one query behind the Directives page.

    Every criterion is AND-ed with the others. Within a single criterion the meaning
    depends on what the field means on a directive:

      - `types`, `phases`, `rule_ids` are SINGLE-valued on a directive, so listing several
        means OR: `phases=[1,2]` is "phase 1 or phase 2".
      - `tags` is MULTI-valued on a directive, so listing several means AND:
        `tags=["a","b"]` is "carries both tags" — the useful reading when narrowing down.

    Empty/omitted everywhere is legal and returns the whole configuration, ordered by
    `sort_by`.
    """
    # OR within the field
    types: List[str] = Field(default_factory=list, description="Directive types; any of")
    phases: List[int] = Field(default_factory=list, description="ModSecurity phases; any of")
    rule_ids: List[int] = Field(default_factory=list, description="ModSecurity ids; any of")

    # AND within the field
    tags: List[str] = Field(default_factory=list, description="Tags; must carry ALL of them")
    # Exact rule messages, any of. The stored value keeps the quotes the dump wrote
    # (`'Invalid input'`); there are only ~10 distinct messages in a real configuration.
    msgs: List[str] = Field(default_factory=list, description="Exact rule msg values; any of")

    # Exact host/location, any of. This is what the UI sends. The stored values keep the
    # quotes the dump used (`"*:80"`) and contain regex metacharacters, so the regex fields
    # below cannot express them. "" is a real value meaning "outside any block".
    hosts: List[str] = Field(default_factory=list, description="Exact VirtualHost values; any of")
    locations: List[str] = Field(default_factory=list, description="Exact Location values; any of")

    # single-valued
    node_id: Optional[int] = Field(default=None, description="Parser node_id — exact")
    # Regex variants, for programmatic callers. An invalid pattern returns 400.
    host: Optional[str] = Field(default=None, max_length=500, description="VirtualHost regex")
    location: Optional[str] = Field(default=None, max_length=500, description="Location regex")
    args_contains: Optional[str] = Field(
        default=None, max_length=500, description="Substring of the directive arguments"
    )
    msg_contains: Optional[str] = Field(
        default=None, max_length=500, description="Substring of the rule msg"
    )
    has_rule_id: Optional[bool] = Field(
        default=None,
        description="True = only directives declaring id:NNN, False = only those without, "
                    "null = both",
    )
    source: Optional[SourceLocationQuery] = Field(
        default=None, description="Only directives produced by this configuration line"
    )
    # Shorthand for `locations`: the server works out which containers cover this path and
    # filters on exactly those. Paste a URL from a log; scheme/host/query are ignored.
    url: Optional[str] = Field(
        default=None, max_length=2000,
        description="Request URL or path; matches the <Location>/<LocationMatch> blocks "
                    "covering it",
    )

    sort_by: SortField = "node_id"
    sort_dir: Literal["asc", "desc"] = "asc"


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
    # Which container produced `location`: "Location" (a literal path) or "LocationMatch"
    # (a regex). "" / None when the directive is outside any location block.
    location_kind: Optional[str] = None
    virtual_host: Optional[str] = None
    if_level: int = 0
    conditions: List[str] = Field(default_factory=list)
    phase: Optional[int] = None
    rule_id: Optional[int] = None          # ModSecurity id:NNN — NOT the node_id
    tags: List[str] = Field(default_factory=list)
    msg: Optional[str] = None
    constants: List[str] = Field(default_factory=list)
    variables: List[str] = Field(default_factory=list)
    # No `context` field: the parser's denormalised provenance string was truncated on
    # ~98.5% of directives and duplicated symbol_table. Use GET /nodes/{id}/metadata.


class DirectiveListResponse(BaseModel):
    """Paginated list of directives. total_count is the full match count, not the page."""
    configuration_id: int
    directives: List[DirectiveResponse]
    total_count: int
    limit: int
    offset: int


class FacetCount(BaseModel):
    """One distinct value of a directive property, with how many directives carry it."""
    value: Any
    count: int
    # Only the `location` value list populates this: "Location" | "LocationMatch", so the
    # caller can tell a literal path from a pattern.
    kind: Optional[str] = None


class FacetValuesResponse(BaseModel):
    """
    A searchable slice of one property's distinct values, commonest first.

    Only a page of matches, never the whole set: this configuration already has 56 distinct
    locations, so the search runs server-side and the caller sends `q` as the user types.

    `value` is raw — surrounding quotes included, and "" for "outside any block". That is
    the form the filter takes; prettifying it is the UI's job.
    """
    configuration_id: int
    field: str                             # tag | host | location
    query: str                             # the `q` that produced this
    values: List[FacetCount]


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


class ValueListQuery(BaseModel):
    """
    Ask for one property's values, counted inside the filters already applied.

    `filters` is the caller's current filter set. Facet counts are computed against it, so
    they say what adding a value would actually return rather than what it means in the
    configuration as a whole.
    """
    q: str = Field(default="", max_length=200,
                   description="Case-insensitive substring; empty = top by count")
    limit: int = Field(default=50, ge=1, le=500)
    filters: Optional["DirectiveSearchQuery"] = Field(
        default=None, description="Filters already applied; omit for whole-config counts"
    )


class UrlMatchRequest(BaseModel):
    """A URL or path from a log, to be matched against the location containers."""
    url: str = Field(min_length=1, max_length=2000)


class LocationMatchEntry(BaseModel):
    """One location container that covers the path, and how much lives inside it."""
    value: str                             # raw, as stored — feed straight back as a filter
    kind: str                              # Location | LocationMatch
    count: int


class LocationWarning(BaseModel):
    """A container that cannot match any request path, and why."""
    value: str
    kind: str
    reason: str


class UrlMatchResponse(BaseModel):
    """
    Which location containers cover a given request path.

    `matches` is ordered commonest first and its `value`s are exactly what
    `DirectiveSearchQuery.locations` expects, so the caller can drill into any single one.

    Directives with NO location apply to every path and are therefore *excluded* from
    `matches` and `total_directives` — they would be the same large block on every URL.
    `no_location_count` reports them so the omission is visible rather than silent.
    """
    configuration_id: int
    url: str                               # what was submitted
    path: str                              # the normalised path actually matched on
    matches: List[LocationMatchEntry]
    total_directives: int                  # sum over matches
    no_location_count: int
    warnings: List[LocationWarning]        # containers that can never match


class DirectiveStatsResponse(BaseModel):
    """
    A summary of the directives currently matched, for the statistics panel.

    Every figure describes the slice the table is showing, so all filters apply. That is
    the deliberate difference from `/directives/values/{field}`, which drops a field's own
    chips so another value stays addable — the panel summarises what IS, the dropdowns
    offer what could be added.
    """
    configuration_id: int
    total: int
    secrules: int
    with_rule_id: int
    in_location: int
    in_vhost: int
    distinct_tags: int
    distinct_locations: int

    # Ordered 1..5 then "(none)" — phase is ORDINAL (the request lifecycle), so this is
    # deliberately NOT sorted by count. The UI must render it in the order given.
    phases: List[FacetCount]
    # Top 8 plus an "Other" row, so the counts still sum to `total`.
    types: List[FacetCount]
    # Top 8. NOT part-to-whole: a directive carries several tags, so these sum to more
    # than `total` and must never be shown as shares.
    tags: List[FacetCount]
    locations: List[FacetCount]


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
