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
Both are INTEGER in Neo4j — binding them as strings matches nothing.

DIRECTIVE_FIELDS is the projection every directive-returning query ends with, so the
repository can map rows to DirectiveResponse uniformly.
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
    n.variables    AS variables,
    n.Context      AS context
"""

# Deterministic ordering for every paginated list, so limit/offset can walk a
# result set without repeats or gaps.
ORDER_BY_NODE_ID = "ORDER BY n.node_id"


def _paginated(match_clause: str) -> str:
    """Wrap a MATCH into a counted, ordered, paginated projection."""
    return f"""
    {match_clause}
    WITH collect(DISTINCT n) AS nodes
    WITH nodes, size(nodes) AS total_count
    UNWIND nodes AS n
    WITH n, total_count
    {ORDER_BY_NODE_ID}
    SKIP $skip LIMIT $limit
    RETURN total_count, {DIRECTIVE_FIELDS}
    """


# ==================== Staleness guard ====================

# Cheap existence check backing the "marked parsed but the graph is empty" 409.
# Uses the per-label configuration_id indexes created by the parser.
HAS_ANY_NODE = """
MATCH (n {configuration_id: $cid})
RETURN count(n) > 0 AS has_nodes
LIMIT 1
"""


# ==================== Directive lookup ====================

# <- GET /directives/id/{nodeid}   (parser node_id)
DIRECTIVE_BY_NODE_ID = _paginated(
    "MATCH (n {configuration_id: $cid, node_id: $node_id})"
)

# <- GET /directives/id   (ModSecurity rule id)
DIRECTIVES_BY_RULE_ID = _paginated(
    """MATCH (n {configuration_id: $cid})-[:Has]->
             (:Id {value: $rule_id, configuration_id: $cid})"""
)

# <- GET /directives/tag
DIRECTIVES_BY_TAG = _paginated(
    """MATCH (n {configuration_id: $cid})-[:Has]->
             (:Tag {value: $tag, configuration_id: $cid})"""
)


# ==================== Request simulation ====================

# <- POST /parse_http_request + POST /cypher/to_json, collapsed into one call.
# location/host are regexes applied with =~ (bound as parameters, not interpolated).
# Ordering is execution order: phase, then IfLevel, then Location/VirtualHost
# specificity, then node_id -- matching the old query's ORDER BY.
DIRECTIVES_BY_REQUEST = f"""
MATCH (vh:VirtualHost {{configuration_id: $cid}})<-[:InVirtualHost]-(n)
      -[:AtLocation]->(l:Location {{configuration_id: $cid}})
WHERE vh.value =~ $host AND l.value =~ $location
WITH collect(DISTINCT n) AS nodes
WITH nodes, size(nodes) AS total_count
UNWIND nodes AS n
WITH n, total_count
ORDER BY n.phase, n.IfLevel, n.Location, n.VirtualHost, n.node_id
SKIP $skip LIMIT $limit
RETURN total_count, {DIRECTIVE_FIELDS}
"""


# ==================== Removal analysis ====================

# <- GET /directives/removed/{nodeid}
# Spans both id spaces on purpose: $node_id is a PARSER node_id identifying the victim,
# while the criterion node reached in between is either an (:Id) holding a MODSECURITY
# rule id, or a (:Regex) that Matches a (:Tag).
# `n.node_id > a.node_id` keeps only removers declared after the victim -- a directive
# cannot remove something declared later.
REMOVERS_OF_NODE = f"""
MATCH (n {{configuration_id: $cid}})-[:DoesRemove]->(crt)-[*..2]-
      (a {{node_id: $node_id, configuration_id: $cid}})
WHERE n.node_id > a.node_id
WITH DISTINCT n, crt
WITH collect({{n: n, crt: crt}}) AS rows
WITH rows, size(rows) AS total_count
UNWIND rows AS row
WITH row.n AS n, row.crt AS crt, total_count
ORDER BY n.node_id
SKIP $skip LIMIT $limit
RETURN total_count,
       labels(crt)[0] AS criterion_type,
       crt.value      AS criterion_value,
       {DIRECTIVE_FIELDS}
"""

# <- GET /directives/remove_by/id   (ModSecurity rule id)
DIRECTIVES_REMOVING_RULE_ID = _paginated(
    """MATCH (n:secruleremovebyid {configuration_id: $cid})-[:DoesRemove]->
             (:Id {value: $rule_id, configuration_id: $cid})"""
)

# <- GET /directives/remove_by/tag
# Two hops: RemoveByTag stores a pattern as (:Regex), and the parser pre-computes
# (:Regex)-[:Match]->(:Tag) at write time.
DIRECTIVES_REMOVING_TAG = _paginated(
    """MATCH (n:secruleremovebytag {configuration_id: $cid})-[*..2]->
             (:Tag {value: $tag, configuration_id: $cid})"""
)


# ==================== Constant / variable analysis ====================

# <- GET /search_var/{var_name}
# cstIndex is a GLOBAL fulltext index with no configuration_id, so results MUST be
# filtered afterwards or symbols from other configurations leak through.
SEARCH_SYMBOLS = """
CALL db.index.fulltext.queryNodes('cstIndex', $query) YIELD node, score
WHERE node.configuration_id = $cid
WITH node, score
ORDER BY score DESC
WITH collect({node: node, score: score}) AS rows
WITH rows, size(rows) AS total_count
UNWIND rows AS row
WITH row.node AS node, total_count
SKIP $skip LIMIT $limit
RETURN total_count,
       node.name  AS name,
       node.value AS value,
       labels(node) AS labels
"""

# <- POST /use_node
# value IS NULL means "the node that has no value", not "any value" -- preserved from
# the old semantics.
DIRECTIVES_USING_CONSTANT = _paginated(
    """MATCH (c {name: $name, configuration_id: $cid})<-[:Uses]-(n)
       WHERE ($value IS NULL AND c.value IS NULL) OR c.value = $value"""
)

# <- POST /get_setnode
DIRECTIVES_SETTING_CONSTANT = _paginated(
    """MATCH (c {name: $name, configuration_id: $cid})<-[:Sets|Define]-(n)
       WHERE ($value IS NULL AND c.value IS NULL) OR c.value = $value"""
)


# ==================== Source mapping ====================

# <- POST /get_node_ids (second half)
# Postgres resolves the node_ids; this fetches the matching graph nodes.
DIRECTIVES_BY_NODE_IDS = _paginated(
    "MATCH (n {configuration_id: $cid}) WHERE n.node_id IN $node_ids"
)
