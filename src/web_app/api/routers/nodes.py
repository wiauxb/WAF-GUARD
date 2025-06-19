import pandas as pd
from fastapi import APIRouter

from ..db.connections import neo4j_driver, parsed_conn
from ..models.models import HttpRequest, FileContextQuery, ConstantQuery

router = APIRouter(tags=["Node Operations"])


@router.post("/parse_http_request")
async def parse_http_request(request: HttpRequest):
    location = request.location
    host = request.host
    # FIXME: This is vulnerable to "SQL" injection
    cypher_query = f"MATCH (vh:VirtualHost WHERE vh.value =~ '{host}')<-[:InVirtualHost]-(n)-[:AtLocation]->(l:Location WHERE l.value =~ '{location}') RETURN n ORDER BY n.phase, n.IfLevel, n.Location, n.VirtualHost, n.node_id"
    return {"cypher_query": cypher_query}


@router.get("/get_metadata/{node_id}")
async def get_metadata(node_id: str):
    cursor = parsed_conn.cursor()
    cursor.execute(
        """
        SELECT macro_name, file_path, line_number
        FROM (
        SELECT mc.id as id, mc.macro_name, st.file_path, st.line_number FROM macrocall mc, symboltable st WHERE mc.nodeid = %s and mc.ruleid = st.id
        UNION
        SELECT -1 as id,'/' as macro_name, file_path, line_number FROM symboltable WHERE node_id = %s
        ORDER BY id DESC
        )
        """,
        (node_id, node_id))
    metadata = cursor.fetchall()
    return {"metadata": metadata}


@router.get("/search_var/{var_name}")
async def search_var(var_name: str):
    terms = var_name.split()
    name_query = "~ ".join(terms)+"~"
    name_query = name_query.replace('"', '\\"')
    property = f'name: \\"{name_query}\\"'
    with neo4j_driver.session() as session:
        result = session.run(f"""
                            CALL db.index.fulltext.queryNodes('cstIndex', $name_query)
                            YIELD node RETURN node""", {"name_query": property})
        records = [record["node"] for record in result]
    formatted_records = []
    for record in records:
       tmp = dict(record)
       tmp["labels"] = list(record.labels)
       formatted_records.append(tmp)
    return {"records": formatted_records}


@router.post("/get_setnode")
async def get_setnode(query: ConstantQuery):
    var_name = query.var_name
    var_value = query.var_value
    if var_value is None:
        return await local_get_setnode(f"MATCH (c {{name: $name}})<-[:Sets|Define]-(n) WHERE c.value IS NULL return n", {'name': var_name})
    return await local_get_setnode(f"MATCH (c {{name: $name, value: $value}})<-[:Sets|Define]-(n) return n", {'name': var_name, 'value': var_value})


async def local_get_setnode(query: str, params):
    with neo4j_driver.session() as session:
        result = session.run(query, params)
        records = [r["n"] for r in result]
        df = pd.DataFrame(records).fillna(-1)
    return {"results" : df.to_dict(orient="records")}


@router.post("/use_node")
async def use_node(query: ConstantQuery):
    var_name = query.var_name
    var_value = query.var_value
    if var_value is None:
        return await get_use_node(f"MATCH (c {{name: '{var_name}'}})<-[:Uses]-(n) WHERE c.value IS NULL return n")
    return await get_use_node(f"MATCH (c {{name: '{var_name}', value: '{var_value}'}})<-[:Uses]-(n) return n")


async def get_use_node(query: str):
    with neo4j_driver.session() as session:
        result = session.run(query)
        records = [r["n"] for r in result]
        df = pd.DataFrame(records).fillna(-1)
    return {"results" : df.to_dict(orient="records")}


@router.post("/get_node_ids")
async def get_node_ids(query: FileContextQuery):
    file_path = query.file_path
    line_number = query.line_num
    cursor = parsed_conn.cursor()
    cursor.execute("""
SELECT mc.nodeid
FROM symboltable as st, macrocall as mc
WHERE st.file_path = %(fp)s AND st.line_number = %(ln)s AND st.id = mc.ruleid
UNION
SELECT node_id
FROM symboltable
WHERE file_path = %(fp)s AND line_number = %(ln)s AND node_id IS NOT NULL
""", {"fp":file_path, "ln": line_number})
    node_ids = cursor.fetchall()
    node_ids = [node_id[0] for node_id in node_ids]
    # get the neo4j nodes for the node_ids
    with neo4j_driver.session() as session:
        result = session.run(f"MATCH (n) WHERE n.node_id in $ids RETURN n", {"ids": node_ids})
        records = [r["n"] for r in result]
        df = pd.DataFrame(records).fillna(-1)
    return {"results" : df.to_dict(orient="records")}
