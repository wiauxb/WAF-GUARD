"""
Analysis routes — read-only queries over a parsed configuration.

Every endpoint accepts an optional `?configuration_id=`; when omitted it falls back to
the caller's active configuration (see get_analysis_configuration_id, which also returns
400/404/409 when the target is missing or not queryable).

Two identifier spaces appear in these paths and must not be confused:
  {node_id}  - the PARSER id, present on every directive
  {rule_id}  - the MODSECURITY id:NNN, present only where declared, one-to-many
"""

from fastapi import APIRouter, Depends, Path, Query, status

from api.dependencies import get_analysis_configuration_id, get_analysis_service
from services.analysis.schemas import (
    ConstantQuery,
    DEFAULT_LIMIT,
    DirectiveListResponse,
    DirectiveSearchQuery,
    DirectiveStatsResponse,
    HttpRequestFilter,
    MacroTraceResponse,
    MAX_LIMIT,
    FacetValuesResponse,
    NodeMetadataResponse,
    RemoverListResponse,
    SourceLocationQuery,
    SymbolSearchResponse,
    UrlMatchRequest,
    ValueListQuery,
    UrlMatchResponse,
    ValueField,
)
from services.analysis.service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _limit(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Max results per page"),
) -> int:
    return limit


def _offset(offset: int = Query(0, ge=0, description="Results to skip")) -> int:
    return offset


# ==========================================================================
# Directive lookup
#
# ORDERING MATTERS: the literal-prefix routes (/search, /values,
# /by-rule-id, /by-tag, /filter) MUST be declared before /directives/{node_id}. FastAPI matches
# in declaration order, and with node_id typed as int a request to
# /directives/by-rule-id/5 would otherwise hit the {node_id} route and fail
# validation with 422.
# ==========================================================================

@router.post("/directives/search", response_model=DirectiveListResponse)
async def search_directives(
    query: DirectiveSearchQuery = DirectiveSearchQuery(),
    configuration_id: int = Depends(get_analysis_configuration_id),
    limit: int = Depends(_limit),
    offset: int = Depends(_offset),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """
    Directives matching any combination of criteria, in any supported order.

    Criteria are AND-ed together. Within one criterion the meaning follows the property:

    - **types**, **phases**, **rule_ids** — *any of* (a directive has one type, one phase)
    - **tags** — *all of* (a directive carries a list, so listing two narrows to both)

    An empty body returns the whole configuration ordered by `node_id`.

    Sorting is server-side over the FULL match set, not the page. Directives with no value
    for the sort column (most have no phase and no rule id) sort last in both directions.
    """
    return analysis.search_directives(configuration_id, query, limit, offset)


@router.post("/locations/match-url", response_model=UrlMatchResponse)
async def match_url(
    query: UrlMatchRequest,
    configuration_id: int = Depends(get_analysis_configuration_id),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """
    Which `<Location>` / `<LocationMatch>` blocks cover a URL from a log?

    Paste a URL or path — `https://host/jira/x?a=1` or `/jira/x`. Scheme, host, query and
    fragment are ignored: `VirtualHost` holds bind specs (`*:80`), not hostnames, so a
    log's host has nothing to match against.

    Matching follows Apache: `<Location>` is a **path-component prefix** (`/wp` covers
    `/wp/admin` but not `/wpfoo`), `<LocationMatch>` is an **unanchored PCRE search**.

    `matches[].value` is the raw stored value, so it can be handed straight back as
    `locations` on `/directives/search` to drill into one container. The same result is
    available in one step via that endpoint's `url` field.

    Directives with **no** location apply to every path and are excluded from `matches` —
    they would be the same large block on every URL — but reported as `no_location_count`.

    `warnings` names containers that can never match a request, most usefully a
    `<Location>` written with regex syntax: Apache matches those literally, so the block is
    dead. That is a configuration bug, and this is the only place it surfaces.
    """
    return analysis.match_url(configuration_id, query.url)


@router.post("/directives/stats", response_model=DirectiveStatsResponse)
async def get_directive_stats(
    query: DirectiveSearchQuery = DirectiveSearchQuery(),
    configuration_id: int = Depends(get_analysis_configuration_id),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """
    A summary of the directives a filter set matches — headline counts and distributions.

    Every figure honours the **whole** filter set, because this describes the slice on
    screen. That is the deliberate difference from `/directives/values/{field}`, which
    drops a field's own chips so another value stays addable: the panel summarises what is,
    the dropdowns offer what could be added next.

    `phases` is ordered **1..5 then null**, not by count — phase is the request lifecycle
    and reading it in order is the point. `types` carries an `Other` row so it still sums to
    `total`. `tags` does **not**: a directive carries several, so those counts sum to more
    than `total` and are occurrences, never shares.
    """
    return analysis.get_directive_stats(configuration_id, query)


@router.post("/directives/values/{field}", response_model=FacetValuesResponse)
async def get_directive_values(
    field: ValueField = Path(..., description="tag | host | location | type | phase | msg"),
    query: ValueListQuery = ValueListQuery(),
    configuration_id: int = Depends(get_analysis_configuration_id),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """
    The values a property takes, **counted within the filters already applied**.

    Populates every filter dropdown. Each count answers one question: *how many results if
    I add this value?* — so a value whose count would be zero simply is not listed, and the
    list narrows as you filter. With `phase 2` applied, `type` drops from 196 values to the
    2 that still have directives.

    Two readings, because the two semantics differ:

    - **OR fields** (`type`, `phase`, `host`, `location`, `msg`) are counted with their OWN
      chips excluded. Adding a value widens the result, so counting with them applied would
      collapse the list to what is already picked and you could never add a second value.
      A consequence worth knowing: these counts do **not** sum to the table total.
    - **`tag`** keeps every chip, because adding a tag narrows — each candidate's count
      within the current results is exactly what picking it would give.

    The clauses come from the same builder `/directives/search` uses, so a count here always
    matches what applying it returns. POST rather than GET because a filter set does not
    belong in a query string.
    """
    return analysis.get_directive_values(
        configuration_id, field, query.q, query.limit, query.filters
    )


@router.get("/directives/by-rule-id/{rule_id}", response_model=DirectiveListResponse)
async def get_directives_by_rule_id(
    rule_id: int = Path(..., description="ModSecurity rule id (id:NNN) — NOT the node_id"),
    configuration_id: int = Depends(get_analysis_configuration_id),
    limit: int = Depends(_limit),
    offset: int = Depends(_offset),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """
    Directives declaring a given ModSecurity rule id.

    Returns several directives when a rule is chained — a `chain` action spans multiple
    directives that all carry the same id.
    """
    return analysis.get_directives_by_rule_id(configuration_id, rule_id, limit, offset)


@router.get("/directives/by-tag/{tag}", response_model=DirectiveListResponse)
async def get_directives_by_tag(
    tag: str = Path(..., description="Exact tag value"),
    configuration_id: int = Depends(get_analysis_configuration_id),
    limit: int = Depends(_limit),
    offset: int = Depends(_offset),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """Directives carrying a given tag."""
    return analysis.get_directives_by_tag(configuration_id, tag, limit, offset)


@router.post("/directives/filter", response_model=DirectiveListResponse)
async def filter_directives_by_request(
    filters: HttpRequestFilter = HttpRequestFilter(),
    configuration_id: int = Depends(get_analysis_configuration_id),
    limit: int = Depends(_limit),
    offset: int = Depends(_offset),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """
    Directives applying to a host/location, in execution order.

    - **location**, **host**: regexes. Use `.*` to match everything.

    Ordered by phase, then `<If>` depth, then location/vhost, then node_id — the order
    Apache and ModSecurity would actually evaluate them in.
    """
    return analysis.filter_directives_by_request(
        configuration_id, filters.location, filters.host, limit, offset
    )


@router.get("/directives/{node_id}/removed-by", response_model=RemoverListResponse)
async def get_removers_of_node(
    node_id: int = Path(..., description="Parser node_id of the removed directive"),
    configuration_id: int = Depends(get_analysis_configuration_id),
    limit: int = Depends(_limit),
    offset: int = Depends(_offset),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """
    What removed this directive, and on what grounds?

    Handles removal both by id and by tag. Each entry names the criterion
    (`Id` with a ModSecurity rule id, or `Regex` with a tag pattern) and the directive
    that did the removing.
    """
    return analysis.get_removers_of_node(configuration_id, node_id, limit, offset)


@router.get("/directives/{node_id}", response_model=DirectiveListResponse)
async def get_directive_by_node_id(
    node_id: int = Path(..., description="Parser node_id — NOT the ModSecurity rule id"),
    configuration_id: int = Depends(get_analysis_configuration_id),
    limit: int = Depends(_limit),
    offset: int = Depends(_offset),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """Single directive by its parser node_id."""
    return analysis.get_directive_by_node_id(configuration_id, node_id, limit, offset)


# ==================== Removal analysis ====================

@router.get("/removals/by-rule-id/{rule_id}", response_model=DirectiveListResponse)
async def get_directives_removing_rule_id(
    rule_id: int = Path(..., description="ModSecurity rule id being removed"),
    configuration_id: int = Depends(get_analysis_configuration_id),
    limit: int = Depends(_limit),
    offset: int = Depends(_offset),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """
    `SecRuleRemoveById` directives targeting a rule id.

    The targeted rule need not exist here — removals often reference rules that were
    never loaded in this configuration.
    """
    return analysis.get_directives_removing_rule_id(configuration_id, rule_id, limit, offset)


@router.get("/removals/by-tag/{tag}", response_model=DirectiveListResponse)
async def get_directives_removing_tag(
    tag: str = Path(..., description="Tag value being removed"),
    configuration_id: int = Depends(get_analysis_configuration_id),
    limit: int = Depends(_limit),
    offset: int = Depends(_offset),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """`SecRuleRemoveByTag` directives whose pattern matches a given tag."""
    return analysis.get_directives_removing_tag(configuration_id, tag, limit, offset)


# ==================== Constant / variable analysis ====================

@router.get("/symbols/search", response_model=SymbolSearchResponse)
async def search_symbols(
    q: str = Query(..., min_length=1, max_length=500, description="Search terms"),
    configuration_id: int = Depends(get_analysis_configuration_id),
    limit: int = Depends(_limit),
    offset: int = Depends(_offset),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """
    Fuzzy fulltext search over constants, variables and collections.

    Each match reports its labels so you can tell a `Constant` from a `Variable`.
    """
    return analysis.search_symbols(configuration_id, q, limit, offset)


@router.post("/symbols/used-by", response_model=DirectiveListResponse)
async def get_directives_using_constant(
    query: ConstantQuery,
    configuration_id: int = Depends(get_analysis_configuration_id),
    limit: int = Depends(_limit),
    offset: int = Depends(_offset),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """
    Directives that *read* a constant or variable.

    Omitting **value** matches the node with no value set — not "any value". A name can
    have several distinct nodes differing only by value.
    """
    return analysis.get_directives_using_constant(
        configuration_id, query.name, query.value, limit, offset
    )


@router.post("/symbols/set-by", response_model=DirectiveListResponse)
async def get_directives_setting_constant(
    query: ConstantQuery,
    configuration_id: int = Depends(get_analysis_configuration_id),
    limit: int = Depends(_limit),
    offset: int = Depends(_offset),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """Directives that *set or define* a constant or variable (`setvar`, `setenv`, `Define`)."""
    return analysis.get_directives_setting_constant(
        configuration_id, query.name, query.value, limit, offset
    )


# ==================== Source mapping ====================

@router.post("/nodes/at-source", response_model=DirectiveListResponse)
async def get_nodes_at_source(
    query: SourceLocationQuery,
    configuration_id: int = Depends(get_analysis_configuration_id),
    limit: int = Depends(_limit),
    offset: int = Depends(_offset),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """
    Which directives did a given configuration line produce?

    The inverse of `/nodes/{node_id}/metadata`. One line inside a macro can expand into
    many directives.
    """
    return analysis.get_nodes_at_source(
        configuration_id, query.file_path, query.line_number, limit, offset
    )


@router.get("/nodes/{node_id}/metadata", response_model=NodeMetadataResponse)
async def get_node_metadata(
    node_id: int = Path(..., description="Parser node_id"),
    configuration_id: int = Depends(get_analysis_configuration_id),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """
    Source file/line chain for a directive.

    Frames run innermost-first; `macro_name` is `/` for the frame that sits directly in
    a file.
    """
    return analysis.get_node_metadata(configuration_id, node_id)


@router.get("/nodes/{node_id}/macro-trace", response_model=MacroTraceResponse)
async def get_macro_call_trace(
    node_id: int = Path(..., description="Parser node_id"),
    configuration_id: int = Depends(get_analysis_configuration_id),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """
    Full macro call stack for a directive, with the source text of each frame.

    Reads the extracted configuration files to pull each `<Macro>` body and the `Use`
    site that invoked it. `formatted` is a pre-rendered version for display.
    """
    return analysis.get_macro_call_trace(configuration_id, node_id)
