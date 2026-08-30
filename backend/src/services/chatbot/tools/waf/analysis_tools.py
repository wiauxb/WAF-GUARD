"""
The WAF analysis tools.

Nine capability tools over AnalysisService, mirroring what the Directives page can do.
Deliberately not one wrapper per HTTP route: several routes differ by a single argument,
and a model choosing between seventeen near-identical options chooses badly.

Every tool resolves against the configuration the CONVERSATION is bound to, read from the
typed runtime context — never the user's active configuration. See ..context.

Two conventions hold throughout:
  - results are capped (see clamp) because they re-enter the context window each turn;
  - a configuration that cannot be queried yields a SENTENCE, not an exception, so the
    agent can explain it instead of the turn dying.
"""

import logging
from typing import List, Optional, Union

from langchain.tools import ToolRuntime, tool

from services.analysis.schemas import DirectiveSearchQuery
from ...context import (
    ChatContext,
    as_list,
    ConfigurationUnavailable,
    clamp,
    compact_directive,
    analysis_for,
)

logger = logging.getLogger(__name__)


def _guarded(runtime: ToolRuntime[ChatContext], fn):
    """
    Run `fn(service, config)` against the bound configuration.

    Turns both failure modes into something the model can act on: an unavailable
    configuration becomes an explanation, and an unexpected error becomes a short report
    rather than a stack trace ending the turn.
    """
    cid = runtime.context.configuration_id
    try:
        with analysis_for(cid) as (service, config):
            return fn(service, config)
    except ConfigurationUnavailable as e:
        return {"error": str(e)}
    except Exception as e:                       # noqa: BLE001 - the agent must survive it
        logger.exception("Chatbot tool failed on configuration %s", cid)
        return {"error": f"That query failed: {type(e).__name__}: {e}"}


@tool
def search_directives(
    runtime: ToolRuntime[ChatContext],
    types: Optional[Union[str, List[str]]] = None,
    phases: Optional[Union[int, List[int]]] = None,
    tags: Optional[Union[str, List[str]]] = None,
    hosts: Optional[Union[str, List[str]]] = None,
    locations: Optional[Union[str, List[str]]] = None,
    rule_ids: Optional[Union[int, List[int]]] = None,
    node_id: Optional[int] = None,
    url: Optional[str] = None,
    args_contains: Optional[str] = None,
    has_rule_id: Optional[bool] = None,
    limit: int = 20,
) -> dict:
    """
    Find directives matching any combination of criteria. The main analysis tool.

    Criteria are AND-ed together. WITHIN one criterion the meaning follows the property:
      - types, phases, hosts, locations, rule_ids: ANY of them (a directive has one type,
        one phase, one host, one location, one id)
      - tags: ALL of them (a directive carries a list, so two tags means "carries both")

    Use `list_values` first to discover real tag/host/location/type values — guessing a tag
    name that does not exist returns zero and looks like a real answer.

    Args:
        types: directive types, e.g. ["secrule", "secaction"]
        phases: ModSecurity phases 1-5
        tags: must carry ALL of these
        hosts: exact VirtualHost values. They keep their quotes, e.g. '"*:80"'. Use "" for
            directives outside every VirtualHost (server-level/global config).
        locations: exact Location values. Use "" for directives outside every Location
            block (they apply to all paths).
        rule_ids: ModSecurity id:NNN values — NOT node_ids
        node_id: the parser's own id, unique per directive — NOT a rule_id
        url: a URL or path from a log; expands to whichever location blocks cover it
        args_contains: case-insensitive substring of the directive's arguments
        has_rule_id: True = only directives declaring id:NNN, False = only those without
        limit: max rows returned (capped at 50)

    Returns:
        total_count (the FULL match count, not the page) and up to `limit` directives.
    """
    def run(service, config):
        q = DirectiveSearchQuery(
            types=as_list(types), phases=as_list(phases), tags=as_list(tags),
            hosts=as_list(hosts), locations=as_list(locations), rule_ids=as_list(rule_ids),
            node_id=node_id, url=url, args_contains=args_contains,
            has_rule_id=has_rule_id,
        )
        n = clamp(limit)
        res = service.search_directives(runtime.context.configuration_id, q, n, 0)
        return {
            "configuration": config.name,
            "total_count": res.total_count,
            "returned": len(res.directives),
            "directives": [compact_directive(d) for d in res.directives],
        }
    return _guarded(runtime, run)


@tool
def get_statistics(
    runtime: ToolRuntime[ChatContext],
    types: Optional[Union[str, List[str]]] = None,
    phases: Optional[Union[int, List[int]]] = None,
    tags: Optional[Union[str, List[str]]] = None,
    locations: Optional[Union[str, List[str]]] = None,
    url: Optional[str] = None,
) -> dict:
    """
    Summarise a slice of the configuration: headline counts and distributions.

    Use this for "how is it made up / what does it look like" questions instead of pulling
    directives and counting them yourself. Accepts the same filters as search_directives;
    omit them all to describe the whole configuration.

    Returns totals (directives, SecRules, how many declare a rule id, location and vhost
    coverage, distinct tags and locations) plus the distribution over phases, types, tags
    and locations.

    Note phases are returned in lifecycle order 1..5 then null, and tag counts are
    OCCURRENCES: a directive carries several tags, so they sum to more than the total.
    """
    def run(service, config):
        q = DirectiveSearchQuery(
            types=as_list(types), phases=as_list(phases), tags=as_list(tags),
            locations=as_list(locations), url=url,
        )
        s = service.get_directive_stats(runtime.context.configuration_id, q)
        pack = lambda rows: {("(none)" if r.value is None else str(r.value)): r.count for r in rows}
        return {
            "configuration": config.name,
            "total": s.total,
            "secrules": s.secrules,
            "declare_a_rule_id": s.with_rule_id,
            "inside_a_location": s.in_location,
            "inside_a_vhost": s.in_vhost,
            "distinct_tags": s.distinct_tags,
            "distinct_locations": s.distinct_locations,
            "by_phase": pack(s.phases),
            "by_type": pack(s.types),
            "top_tags_occurrences": pack(s.tags),
            "top_locations": pack(s.locations),
        }
    return _guarded(runtime, run)


@tool
def list_values(
    runtime: ToolRuntime[ChatContext],
    field: str,
    search: str = "",
    limit: int = 20,
) -> dict:
    """
    Discover what values a field actually takes, with directive counts.

    Call this BEFORE filtering on a tag, host, location, type or message you are not sure
    exists. It is the difference between a real answer and a confident zero.

    Args:
        field: one of "tag", "host", "location", "type", "phase", "msg"
        search: case-insensitive substring to narrow the list; empty returns the commonest
        limit: max values returned (capped at 50)

    Returns each value with how many directives carry it. Location values additionally
    report `kind`: "LocationMatch" values are REGEXES, "Location" values are literal paths.
    """
    def run(service, config):
        if field not in ("tag", "host", "location", "type", "phase", "msg"):
            return {"error": f"Unknown field {field!r}. Use tag, host, location, type, "
                             f"phase or msg."}
        res = service.get_directive_values(
            runtime.context.configuration_id, field, search, clamp(limit)
        )
        return {
            "configuration": config.name,
            "field": field,
            "values": [
                {"value": v.value, "directives": v.count, **({"kind": v.kind} if v.kind else {})}
                for v in res.values
            ],
        }
    return _guarded(runtime, run)


@tool
def match_url(runtime: ToolRuntime[ChatContext], url: str) -> dict:
    """
    Which <Location>/<LocationMatch> blocks cover a URL from a log?

    Give it a URL or path — "https://host/jira/x?a=1" or "/jira/x". Scheme, host, query and
    fragment are ignored, because VirtualHost holds bind specs like "*:80", not hostnames.

    Matching follows Apache: <Location> is a path-component prefix ("/wp" covers
    "/wp/admin" but not "/wpfoo"); <LocationMatch> is an unanchored regex.

    Directives with NO location apply to every path and are reported separately as
    `directives_with_no_location` rather than mixed in — they would otherwise dominate
    every answer.
    """
    def run(service, config):
        m = service.match_url(runtime.context.configuration_id, url)
        return {
            "configuration": config.name,
            "path_matched": m.path,
            "blocks": [
                {"value": e.value, "kind": e.kind, "directives": e.count} for e in m.matches
            ],
            "directives_in_those_blocks": m.total_directives,
            "directives_with_no_location": m.no_location_count,
        }
    return _guarded(runtime, run)


@tool
def search_symbols(runtime: ToolRuntime[ChatContext], name: str, limit: int = 20) -> dict:
    """
    Fuzzy full-text search over constants, variables and collections by name.

    Use it to find the exact name and value of a variable before asking who reads or writes
    it. A name can have SEVERAL entries differing only by value.
    """
    def run(service, config):
        res = service.search_symbols(runtime.context.configuration_id, name, clamp(limit), 0)
        return {
            "configuration": config.name,
            "total_count": res.total_count,
            "matches": [
                {"name": m.name, "value": m.value, "kind": (m.labels or [None])[0]}
                for m in res.matches
            ],
        }
    return _guarded(runtime, run)


@tool
def who_uses(
    runtime: ToolRuntime[ChatContext],
    name: str,
    value: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """
    Which directives READ a constant or variable.

    `value` omitted means the entry with NO value set — not "any value". Use search_symbols
    first to see which (name, value) entries exist.
    """
    def run(service, config):
        res = service.get_directives_using_constant(
            runtime.context.configuration_id, name, value, clamp(limit), 0
        )
        return {
            "configuration": config.name,
            "total_count": res.total_count,
            "directives": [compact_directive(d) for d in res.directives],
        }
    return _guarded(runtime, run)


@tool
def who_sets(
    runtime: ToolRuntime[ChatContext],
    name: str,
    value: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """
    Which directives SET or DEFINE a constant or variable (setvar, setenv, Define).

    `value` omitted means the entry with NO value set — not "any value".
    """
    def run(service, config):
        res = service.get_directives_setting_constant(
            runtime.context.configuration_id, name, value, clamp(limit), 0
        )
        return {
            "configuration": config.name,
            "total_count": res.total_count,
            "directives": [compact_directive(d) for d in res.directives],
        }
    return _guarded(runtime, run)


@tool
def what_removes(
    runtime: ToolRuntime[ChatContext],
    rule_id: Optional[int] = None,
    tag: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """
    Which SecRuleRemoveById / SecRuleRemoveByTag directives target a rule id or a tag.

    Give exactly one of `rule_id` or `tag`. `rule_id` is a ModSecurity id:NNN, not a
    node_id. The targeted rule need NOT exist in this configuration — removals often
    reference rules that were never loaded, and that is itself worth knowing.
    """
    def run(service, config):
        if (rule_id is None) == (tag is None):
            return {"error": "Give exactly one of rule_id or tag."}
        n = clamp(limit)
        res = (
            service.get_directives_removing_rule_id(runtime.context.configuration_id, rule_id, n, 0)
            if rule_id is not None
            else service.get_directives_removing_tag(runtime.context.configuration_id, tag, n, 0)
        )
        return {
            "configuration": config.name,
            "target": {"rule_id": rule_id} if rule_id is not None else {"tag": tag},
            "total_count": res.total_count,
            "directives": [compact_directive(d) for d in res.directives],
        }
    return _guarded(runtime, run)


@tool
def removed_by(runtime: ToolRuntime[ChatContext], node_id: int, limit: int = 20) -> dict:
    """
    What removed this directive, and on what grounds?

    Takes a PARSER node_id (not a rule_id). Each entry names the criterion — an `Id` holding
    a ModSecurity rule id, or a `Regex` matching a tag — and the directive that did the
    removing. Only removals declared AFTER the target count; a directive cannot remove
    something declared later.
    """
    def run(service, config):
        res = service.get_removers_of_node(
            runtime.context.configuration_id, node_id, clamp(limit), 0
        )
        return {
            "configuration": config.name,
            "node_id": node_id,
            "total_count": res.total_count,
            "removers": [
                {
                    "criterion_type": r.criterion_type,
                    "criterion_value": r.criterion_value,
                    "directive": compact_directive(r.directive),
                }
                for r in res.removers
            ],
        }
    return _guarded(runtime, run)


@tool
def get_provenance(runtime: ToolRuntime[ChatContext], node_id: int) -> dict:
    """
    Where does this directive come from? Source file, line, and the macro call stack.

    Takes a PARSER node_id (not a rule_id). Returns the file/line chain and, where the
    directive came out of a macro, the source text of each frame — the `Use` site and each
    enclosing <Macro> definition. This is how you answer "why does this rule exist" and
    "which file do I edit".
    """
    def run(service, config):
        meta = service.get_node_metadata(runtime.context.configuration_id, node_id)
        if not meta.frames:
            return {"error": f"No source recorded for node_id {node_id}. Is it a node_id "
                             f"rather than a rule_id?"}
        trace = service.get_macro_call_trace(runtime.context.configuration_id, node_id)
        return {
            "configuration": config.name,
            "node_id": node_id,
            "source_chain": [
                {"macro": f.macro_name, "file": f.file_path, "line": f.line_number}
                for f in meta.frames
            ],
            "macro_trace": [
                {
                    "macro": f.macro_name,
                    "file": f.file_path,
                    "line": f.line_number,
                    "source": (f.content or "")[:220],
                }
                for f in trace.frames
            ],
        }
    return _guarded(runtime, run)


ALL_TOOLS = [
    search_directives,
    get_statistics,
    list_values,
    match_url,
    search_symbols,
    who_uses,
    who_sets,
    what_removes,
    removed_by,
    get_provenance,
]
