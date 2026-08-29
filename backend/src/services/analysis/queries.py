"""
Cypher templates for AnalysisService.

Every template is fully parameterized. The old API interpolated user input straight into
Cypher strings and carried an explicit `# FIXME: This is vulnerable to "SQL" injection`
(old/api/routers/nodes.py:14); `use_node` did the same with var_name/var_value.

Two id spaces appear here and must not be confused:
  - node_id  : assigned by the parser, present on EVERY directive, unique per config.
               Stored as the `node_id` property on directive nodes.
  - rule_id  : the ModSecurity `id:NNN`, present only on directives that declare one,
               one-to-many (a chained SecRule spans several directives sharing an id).
               Stored as the `id` property, and as (:Id {value}) nodes.
Both are INTEGER in Neo4j -- binding them as strings matches nothing.

Every list query comes as a PAIR: `<NAME>_PAGE` and `<NAME>_COUNT`. They share one MATCH
clause but are executed separately -- see _page() for why.
"""

# Projection shared by every query that returns directive nodes.
# n.id -> rule_id: never surfaced as bare "id", to keep the two spaces distinct.
DIRECTIVE_FIELDS = """
    n.node_id      AS node_id,
    n.type         AS type,
    n.args         AS args,
    n.Location     AS location,
    n.LocationKind AS location_kind,
    n.VirtualHost  AS virtual_host,
    n.IfLevel      AS if_level,
    n.conditions   AS conditions,
    n.phase        AS phase,
    n.id           AS rule_id,
    n.tags         AS tags,
    n.msg          AS msg,
    n.constants    AS constants,
    n.variables    AS variables
"""
# NOTE: n.Context is deliberately NOT projected. It was the parser's denormalised string
# form of a directive's provenance -- truncated to "line N of " on 98.5% of directives by
# a precedence bug, and redundant with symbol_table. Provenance is served accurately by
# /nodes/{id}/metadata. See PARSER.md.

# Deterministic ordering so limit/offset can walk a result set without repeats or gaps.
ORDER_BY_NODE_ID = "ORDER BY n.node_id"

# The order Apache/ModSecurity actually evaluates directives in.
ORDER_BY_EXECUTION = "ORDER BY n.phase, n.IfLevel, n.Location, n.VirtualHost, n.node_id"


def _page(match_clause: str, order_by: str = ORDER_BY_NODE_ID) -> str:
    """
    One page of directives.

    Streams: DISTINCT + ORDER BY + SKIP/LIMIT lets Neo4j discard rows as it goes. The
    previous form collected every match into a list just to size it, materialising all
    properties (args reaches 10 KB) -- 1.45 GB on a 12k-directive configuration, against
    a 2.6 GiB transaction cap. The count now comes from _count() instead.
    Measured: 1.45 GB -> 1.4 MB, and flat at deep offsets.
    """
    return f"""
    {match_clause}
    WITH DISTINCT n
    {order_by}
    SKIP $skip LIMIT $limit
    RETURN {DIRECTIVE_FIELDS}
    """


def _count(match_clause: str) -> str:
    """Total match count. Touches no properties, so it stays cheap at any size."""
    return f"""
    {match_clause}
    RETURN count(DISTINCT n) AS total_count
    """


# ==================== Combinable search ====================

# Whitelist mapping a SortField onto the node property it orders by.
#
# Cypher cannot parameterise ORDER BY -- `ORDER BY $field` is a syntax error -- so the
# column has to be interpolated into the query text. This dict is the only thing that ever
# reaches that interpolation, which is what keeps a caller-supplied sort from becoming an
# injection point.
SORT_FIELDS = {
    "node_id": "n.node_id",
    "type": "n.type",
    "rule_id": "n.id",
    "phase": "n.phase",
    "host": "n.VirtualHost",
    "location": "n.Location",
}

# Sort columns where "absent" is stored as the empty string rather than null: the parser
# initialises Location and VirtualHost to "" and never to None (dump_parser.py). Sorting
# them on the null test alone leaves "" as the smallest string, so an ascending sort opens
# on a page of blanks -- 71,236 of them for Location. These get a blank test covering both.
_EMPTY_MEANS_BLANK = {"type", "host", "location"}

# Clause fragments, keyed by the criterion they implement. Kept here rather than in the
# service so that every piece of Cypher in AnalysisService lives in this one file.
#
# Note the two readings of a multi-value criterion, which follow from what the property is:
#   - type/phase/rule_id are single-valued on a directive  -> IN  (any of)
#   - tags is a list on the directive                      -> ALL (carries every one)
CLAUSES = {
    "types": "n.type IN $types",
    "phases": "n.phase IN $phases",
    "rule_ids": "n.id IN $rule_ids",
    "tags": "ALL(t IN $tags WHERE t IN n.tags)",
    "msgs": "n.msg IN $msgs",
    "node_id": "n.node_id = $node_id",
    # Exact, and the form the UI uses. The stored values carry their quotes (`"*:80"`) and
    # contain regex metacharacters, so `=~` cannot express them: `*:80` is not even a valid
    # pattern. And now that the parser tracks <LocationMatch>, Location values themselves
    # ARE regexes, which makes regex-matching them meaningless as well.
    # "" is a real value meaning "outside any block", so IN [""] filters to exactly those.
    "hosts": "n.VirtualHost IN $hosts",
    "locations": "n.Location IN $locations",
    # Regex forms, kept for programmatic callers. Not reachable from the UI.
    "host": "n.VirtualHost =~ $host",
    "location": "n.Location =~ $location",
    # CONTAINS is case-sensitive in Cypher; a search box should not be. No index is given
    # up by the toLower() -- directive nodes have none on any of these properties.
    "args_contains": "toLower(n.args) CONTAINS toLower($args_contains)",
    "msg_contains": "toLower(n.msg) CONTAINS toLower($msg_contains)",
    "has_rule_id_true": "n.id IS NOT NULL",
    "has_rule_id_false": "n.id IS NULL",
    "source_node_ids": "n.node_id IN $source_node_ids",
}

# `configuration_id` scopes the graph, but it is NOT only on directives -- every value node
# the parser MERGEs (Id, Tag, Constant, Variable, Collection, Location, VirtualHost, Phase,
# Regex, Predicate) carries it too. On a full configuration that is ~4,500 extra nodes, so
# an unfiltered search over-counted by that much and deep pages showed blank rows.
#
# `node_id` is the discriminator: the parser assigns one to every directive and to no value
# node. It costs nothing and needs no re-parse -- unlike a shared :Directive label, which
# would let this become an index seek but only after re-parsing.
#
# The single-purpose queries above never had this problem: each constrains `n` through a
# relationship, which already implies a directive.
SEARCH_MATCH = """MATCH (n {configuration_id: $cid})
WHERE n.node_id IS NOT NULL"""


def build_directive_search(
    clauses: list[str], sort_by: str = "node_id", sort_dir: str = "asc"
) -> tuple[str, str]:
    """
    Assemble the (page, count) pair for a combinable directive search.

    All clauses are AND-ed onto the base MATCH, so this composes any subset of the criteria
    without a query per combination.

    Two things the ORDER BY has to get right:

    - BLANKS. Neo4j orders null as the LARGEST value, so a plain `phase DESC` opens on a
      full page of blanks -- ~87% of directives declare no phase. Sorting on the blank test
      first (false < true) parks them at the bottom whichever direction is asked for.
      "Blank" is not just null: Location and VirtualHost store absence as "", which sorts
      FIRST ascending, so those columns test for both. See _EMPTY_MEANS_BLANK.
    - TIES. Page and count run as separate statements and SKIP/LIMIT walks the page query
      repeatedly; without a unique tiebreaker, equal sort keys order arbitrarily between
      calls and paging repeats or drops rows. node_id is unique per configuration, so it
      settles every tie.
    """
    # SEARCH_MATCH already opens the WHERE with the directive restriction, so every
    # criterion joins it with AND rather than starting a clause of its own.
    match = SEARCH_MATCH
    for clause in clauses:
        match += f"\n  AND {clause}"

    field = SORT_FIELDS[sort_by]              # KeyError here means an unvalidated caller
    direction = "DESC" if sort_dir == "desc" else "ASC"

    blank = (
        f"({field} IS NULL OR {field} = '')"
        if sort_by in _EMPTY_MEANS_BLANK
        else f"({field} IS NULL)"
    )
    keys = [blank, f"{field} {direction}"]
    if field != "n.node_id":
        keys.append("n.node_id")
    order_by = "ORDER BY " + ", ".join(keys)

    return _page(match, order_by), _count(match)


# Distinct values present in a configuration, for the filter dropdowns. Both aggregate
# over one property and materialise nothing else, so they stay cheap at any size.
# ==================== Value suggestions ====================

# Backs GET /directives/values/{field}: the searchable dropdowns for tag, host and location.
#
# These aggregate the node PROPERTY, deliberately NOT the value nodes that mirror it.
# Measured: tag "security" counts 41,995 via n.tags but 41,956 via (:Tag)<-[:Has]- -- Tag
# nodes and their edges are only written by the generic/secrule modules, so some directives
# carry the property with no edge. Since the FILTER matches the property, a suggestion count
# taken from the nodes would disagree with the result the user gets after clicking it.
#
# `value` is returned raw, including any surrounding quotes the dump preserved (`"*:80"`).
# That raw form is what the filter needs; stripping is a display concern for the UI.
# The empty string is a genuine value meaning "outside any block" and is returned like the
# rest, so "(none)" needs no sentinel.

# How each facetable field is projected to a `value` to group on. `location` also carries
# `kind` so the combobox can mark a regex -- `<LocationMatch ^>` covers 14,138 directives
# and reads as a typo without it; grouping on (value, kind) keeps the count honest if the
# same text ever appears as both.
#
# `tags` is a list property, so it is flattened with UNWIND rather than projected. That is
# also why a directive with several tags contributes to several rows, which is correct: the
# count is "directives carrying this tag".
_VALUE_PROJECTION = {
    "tag": ("UNWIND n.tags AS value", "n.tags IS NOT NULL", ["value"]),
    "host": ("WITH n.VirtualHost AS value", "n.VirtualHost IS NOT NULL", ["value"]),
    "location": ("WITH n.Location AS value, n.LocationKind AS kind",
                 "n.Location IS NOT NULL", ["value", "kind"]),
    "type": ("WITH n.type AS value", "n.type IS NOT NULL", ["value"]),
    "phase": ("WITH n.phase AS value", "n.phase IS NOT NULL", ["value"]),
    "msg": ("WITH n.msg AS value", "n.msg IS NOT NULL", ["value"]),
}

# The whitelist: an unknown field 422s before ever reaching Cypher.
VALUE_FIELDS = tuple(_VALUE_PROJECTION)


def build_value_query(field: str, clauses: list[str]) -> str:
    """
    Distinct values of one property WITHIN the current filter set, with counts.

    The clauses come from the same builder the search uses, so a dropdown can never
    advertise a number the search would not reproduce. Values whose count would be zero
    simply do not appear -- there is no row to group.

    `field` indexes a fixed dict, so it can never reach the query as text.
    """
    projection, not_null, group_keys = _VALUE_PROJECTION[field]

    # SEARCH_MATCH already opens the WHERE with the directive restriction.
    where = "".join(f"\n      AND {c}" for c in [not_null] + list(clauses))
    keys = ", ".join(group_keys)

    # Projection and aggregation are separate steps: UNWIND cannot carry an aggregate, so
    # `UNWIND n.tags AS value, count(*)` is a syntax error. Splitting them keeps one shape
    # for the list property and the scalar ones alike.
    return f"""
    {SEARCH_MATCH}{where}
    {projection}
    WITH {keys}, count(*) AS count
    WHERE $q = '' OR toLower(toString(value)) CONTAINS toLower($q)
    RETURN {keys}, count
    ORDER BY count DESC, value
    LIMIT $limit
    """

# ==================== Statistics panel ====================

# Scalar counts for the stats panel. Each is the caller's clause list plus one extra
# predicate, so they describe exactly the slice the table is showing.
#
# Note these take the FULL filter set -- unlike the dropdown value lists, which drop the
# field's own chips so a second value stays addable. The panel summarises what is on
# screen; the dropdowns offer what could be added next. Different questions.
# The scalar headline counts, all in ONE statement. Conditional aggregation gets every
# figure from a single scan -- as five separate count queries this was five round trips and
# roughly half the panel's latency.
#
# Note these take the FULL filter set, unlike the dropdown value lists which drop the
# field's own chips so a second value stays addable. The panel summarises what is on
# screen; the dropdowns offer what could be added next. Different questions.
def build_stats_counts(clauses: list[str]) -> str:
    """Every headline count for the filtered set, in one scan."""
    where = "".join(f"\n      AND {c}" for c in clauses)
    return f"""
    {SEARCH_MATCH}{where}
    RETURN count(n)                                          AS total,
           count(CASE WHEN n.type = 'secrule'   THEN 1 END)  AS secrules,
           count(CASE WHEN n.id IS NOT NULL     THEN 1 END)  AS with_rule_id,
           count(CASE WHEN n.Location <> ''     THEN 1 END)  AS in_location,
           count(CASE WHEN n.VirtualHost <> ''  THEN 1 END)  AS in_vhost
    """


def build_distinct_count(field: str, clauses: list[str]) -> str:
    """
    How many DISTINCT values of a property the filtered set contains.

    `tags` is a list, so it is flattened first -- otherwise this would count distinct
    lists rather than distinct tags.
    """
    projection, not_null, _ = _VALUE_PROJECTION[field]
    where = "".join(f"\n      AND {c}" for c in [not_null] + list(clauses))
    return f"""
    {SEARCH_MATCH}{where}
    {projection}
    RETURN count(DISTINCT value) AS count
    """


# Every distinct location container, uncapped -- the input to URL matching. Unlike
# VALUES_LOCATION this takes no `q` and no LIMIT: the matcher has to test the URL against
# ALL of them, and a truncated list would silently under-report which rules apply.
# 601 rows on a full configuration.
ALL_LOCATIONS = """
MATCH (n {configuration_id: $cid})
WHERE n.node_id IS NOT NULL AND n.Location <> ''
RETURN n.Location AS value, n.LocationKind AS kind, count(*) AS count
ORDER BY count DESC, value
"""

# Directives outside every location container. They apply to any path, so the URL matcher
# reports the figure even though it deliberately excludes them from the result set.
NO_LOCATION_COUNT = """
MATCH (n {configuration_id: $cid})
WHERE n.node_id IS NOT NULL AND n.Location = ''
RETURN count(n) AS count
"""


# ==================== Staleness guard ====================

# Cheap existence check backing the "marked parsed but the graph is empty" 409.
HAS_ANY_NODE = """
MATCH (n {configuration_id: $cid})
RETURN count(n) > 0 AS has_nodes
LIMIT 1
"""


# ==================== Directive lookup ====================

# <- GET /directives/id/{nodeid}   (parser node_id)
_BY_NODE_ID = "MATCH (n {configuration_id: $cid, node_id: $node_id})"
DIRECTIVE_BY_NODE_ID_PAGE = _page(_BY_NODE_ID)
DIRECTIVE_BY_NODE_ID_COUNT = _count(_BY_NODE_ID)

# <- GET /directives/id   (ModSecurity rule id)
_BY_RULE_ID = """MATCH (n {configuration_id: $cid})-[:Has]->
                       (:Id {value: $rule_id, configuration_id: $cid})"""
DIRECTIVES_BY_RULE_ID_PAGE = _page(_BY_RULE_ID)
DIRECTIVES_BY_RULE_ID_COUNT = _count(_BY_RULE_ID)

# <- GET /directives/tag
_BY_TAG = """MATCH (n {configuration_id: $cid})-[:Has]->
                   (:Tag {value: $tag, configuration_id: $cid})"""
DIRECTIVES_BY_TAG_PAGE = _page(_BY_TAG)
DIRECTIVES_BY_TAG_COUNT = _count(_BY_TAG)

# <- POST /get_node_ids (second half): Postgres resolves the ids, this fetches the nodes.
_BY_NODE_IDS = "MATCH (n {configuration_id: $cid}) WHERE n.node_id IN $node_ids"
DIRECTIVES_BY_NODE_IDS_PAGE = _page(_BY_NODE_IDS)
DIRECTIVES_BY_NODE_IDS_COUNT = _count(_BY_NODE_IDS)


# ==================== Request simulation ====================

# <- POST /parse_http_request + POST /cypher/to_json, collapsed into one call.
# location/host are regexes applied with =~ (bound as parameters, not interpolated).
_BY_REQUEST = """MATCH (vh:VirtualHost {configuration_id: $cid})<-[:InVirtualHost]-(n)
                       -[:AtLocation]->(l:Location {configuration_id: $cid})
                 WHERE vh.value =~ $host AND l.value =~ $location"""
DIRECTIVES_BY_REQUEST_PAGE = _page(_BY_REQUEST, ORDER_BY_EXECUTION)
DIRECTIVES_BY_REQUEST_COUNT = _count(_BY_REQUEST)


# ==================== Removal analysis ====================

# <- GET /directives/removed/{nodeid}
# Spans both id spaces on purpose: $node_id is a PARSER node_id identifying the victim,
# while the criterion node reached in between is either an (:Id) holding a MODSECURITY
# rule id, or a (:Regex) that Matches a (:Tag).
# `n.node_id > a.node_id` keeps only removers declared after the victim -- a directive
# cannot remove something declared later.
_REMOVERS = """MATCH (n {configuration_id: $cid})-[:DoesRemove]->(crt)-[*..2]-
                     (a {node_id: $node_id, configuration_id: $cid})
               WHERE n.node_id > a.node_id"""

# Carries the criterion alongside the directive, so it cannot reuse _page().
REMOVERS_OF_NODE_PAGE = f"""
{_REMOVERS}
WITH DISTINCT n, crt
ORDER BY n.node_id
SKIP $skip LIMIT $limit
RETURN labels(crt)[0] AS criterion_type,
       crt.value      AS criterion_value,
       {DIRECTIVE_FIELDS}
"""

REMOVERS_OF_NODE_COUNT = f"""
{_REMOVERS}
WITH DISTINCT n, crt
RETURN count(*) AS total_count
"""

# <- GET /directives/remove_by/id   (ModSecurity rule id)
_REMOVING_RULE_ID = """MATCH (n:secruleremovebyid {configuration_id: $cid})-[:DoesRemove]->
                             (:Id {value: $rule_id, configuration_id: $cid})"""
DIRECTIVES_REMOVING_RULE_ID_PAGE = _page(_REMOVING_RULE_ID)
DIRECTIVES_REMOVING_RULE_ID_COUNT = _count(_REMOVING_RULE_ID)

# <- GET /directives/remove_by/tag
# Two hops: RemoveByTag stores a pattern as (:Regex), and the parser pre-computes
# (:Regex)-[:Match]->(:Tag) at write time.
_REMOVING_TAG = """MATCH (n:secruleremovebytag {configuration_id: $cid})-[*..2]->
                         (:Tag {value: $tag, configuration_id: $cid})"""
DIRECTIVES_REMOVING_TAG_PAGE = _page(_REMOVING_TAG)
DIRECTIVES_REMOVING_TAG_COUNT = _count(_REMOVING_TAG)


# ==================== Constant / variable analysis ====================

# <- GET /search_var/{var_name}
# cstIndex is a GLOBAL fulltext index with no configuration_id, so results MUST be
# filtered afterwards or symbols from other configurations leak through.
SEARCH_SYMBOLS_PAGE = """
CALL db.index.fulltext.queryNodes('cstIndex', $query) YIELD node, score
WHERE node.configuration_id = $cid
WITH node, score
ORDER BY score DESC, node.name
SKIP $skip LIMIT $limit
RETURN node.name    AS name,
       node.value   AS value,
       labels(node) AS labels
"""

SEARCH_SYMBOLS_COUNT = """
CALL db.index.fulltext.queryNodes('cstIndex', $query) YIELD node
WHERE node.configuration_id = $cid
RETURN count(node) AS total_count
"""

# <- POST /use_node
# value IS NULL means "the node that has no value", not "any value" -- preserved from
# the old semantics.
_USING = """MATCH (c {name: $name, configuration_id: $cid})<-[:Uses]-(n)
            WHERE ($value IS NULL AND c.value IS NULL) OR c.value = $value"""
DIRECTIVES_USING_CONSTANT_PAGE = _page(_USING)
DIRECTIVES_USING_CONSTANT_COUNT = _count(_USING)

# <- POST /get_setnode
_SETTING = """MATCH (c {name: $name, configuration_id: $cid})<-[:Sets|Define]-(n)
              WHERE ($value IS NULL AND c.value IS NULL) OR c.value = $value"""
DIRECTIVES_SETTING_CONSTANT_PAGE = _page(_SETTING)
DIRECTIVES_SETTING_CONSTANT_COUNT = _count(_SETTING)
