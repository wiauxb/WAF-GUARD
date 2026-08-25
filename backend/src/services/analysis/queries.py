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
