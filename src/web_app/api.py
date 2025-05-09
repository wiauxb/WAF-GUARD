import re
import sys

import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from neo4j import GraphDatabase
from pyvis.network import Network
from dotenv import load_dotenv
import pandas as pd
import os
import psycopg2

load_dotenv()

WAF_URL = "http://waf:8000"

app = FastAPI()

neo4jUser = os.getenv("NEO4J_USER")
neo4jPass = os.getenv("NEO4J_PASSWORD")

postgresUser = os.getenv("POSTGRES_USER")
postgresPass = os.getenv("POSTGRES_PASSWORD")

# Neo4j driver
neo4j_driver = GraphDatabase.driver("bolt://neo4j:7687", auth=(neo4jUser, neo4jPass))
neo4j_driver.verify_connectivity()

# PostgreSQL connection
postgres_conn = psycopg2.connect(
    host="postgres",
    user=postgresUser,
    password=postgresPass,
    database="cwaf"
)


class CypherQuery(BaseModel):
    query: str


class HttpRequest(BaseModel):
    location: str
    host: str

class FileContextQuery(BaseModel):
    file_path: str
    line_num: int

class ConstantQuery(BaseModel):
    var_name: str
    var_value: str = None


@app.post("/run_cypher")
async def run_cypher(query: CypherQuery):
    with neo4j_driver.session() as session:
        result = session.run(query.query)
        graph = result.graph()
        net = Network()
        for node in graph.nodes:
            net.add_node(node.element_id, label=list(node.labels)[0],
                         title="\n".join(
                             [f"{k}: {v if len(str(v)) < 50 else f'{str(v)[:47]}...'}" for k, v in node.items()]))
        for rel in graph.relationships:
            net.add_edge(rel.nodes[0].element_id, rel.nodes[1].element_id, label=rel.type)
    net.set_options("""
const options = {
  "edges": {
    "arrows": {
      "to": {
        "enabled": true
      }
    }
  },
  "physics": {
    "barnesHut": {
      "gravitationalConstant": -9950
    },
    "minVelocity": 0.75
  }
}
                    """)
    # net.show_buttons()
    net.show("tmp.html", notebook=False)
    with open("tmp.html", "r") as f:
        res = f.read()
    return {"html": res}


@app.post("/run_cypher_to_json")
async def run_cypher_to_json(query: CypherQuery):
    with neo4j_driver.session() as session:
        result = session.run(query.query)
        res_col = result.keys()[0]
        records = [record[res_col] for record in result]
        df = pd.DataFrame(records).fillna(-1)
    return {"df": df.to_dict(orient="records")}


@app.post("/parse_http_request")
async def parse_http_request(request: HttpRequest):
    location = request.location
    host = request.host
    #FIXME: This is vulnerable to "SQL" injection
    cypher_query = f"MATCH (vh:VirtualHost WHERE vh.value =~ '{host}')<-[:InVirtualHost]-(n)-[:AtLocation]->(l:Location WHERE l.value =~ '{location}') RETURN n ORDER BY n.phase, n.IfLevel, n.Location, n.VirtualHost, n.node_id"
    return {"cypher_query": cypher_query}


@app.get("/get_metadata/{node_id}")
async def get_metadata(node_id: str):
    cursor = postgres_conn.cursor()
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


@app.get("/search_var/{var_name}")
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

@app.post("/get_setnode")
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

@app.post("/use_node")
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


#get node_ids from a file_path and line_number
@app.post("/get_node_ids")
async def get_node_ids(query: FileContextQuery):
    file_path = query.file_path
    line_number = query.line_num
    cursor = postgres_conn.cursor()
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

# @app.post("/store_config")
# async def store_config(request: Request):
#     data = await request.json()
#     config_name = data.get("name")
#     config_nickname = data.get("nickname")
#     config_path = data.get("path")
#     if not config_name or not config_nickname or not config_path:
#         return {"error": "Invalid input"}
    
#     # Store the config in PostgreSQL
#     cursor = postgres_conn.cursor()
#     cursor.execute("""
#         INSERT INTO configs (name, nickname, path)
#         VALUES (%s, %s, %s)
#         RETURNING id
#     """, (config_name, config_nickname, config_path))
#     config_id = cursor.fetchone()[0]
#     postgres_conn.commit()
    
#     return {"config_id": config_id}

# @app.get("/configs")
# async def get_configs():
#     cursor = postgres_conn.cursor()
#     cursor.execute("SELECT * FROM configs")
#     configs = cursor.fetchall()
#     return {"configs": configs}

# @app.get("/configs/name/{config_name}")
# async def get_config_by_nickname(config_name: str):
#     cursor = postgres_conn.cursor()
#     cursor.execute("SELECT * FROM configs WHERE name = %s", (config_name,))
#     config = cursor.fetchone()
#     if config:
#         return {"config": config}
# @app.post("/store_config")
# async def store_config(request: Request):
#     data = await request.json()
#     config_name = data.get("name")
#     config_nickname = data.get("nickname")
#     config_path = data.get("path")
#     if not config_name or not config_nickname or not config_path:
#         return {"error": "Invalid input"}
    
#     # Store the config in PostgreSQL
#     cursor = postgres_conn.cursor()
#     cursor.execute("""
#         INSERT INTO configs (name, nickname, path)
#         VALUES (%s, %s, %s)
#         RETURNING id
#     """, (config_name, config_nickname, config_path))
#     config_id = cursor.fetchone()[0]
#     postgres_conn.commit()
    
#     return {"config_id": config_id}

# @app.get("/configs")
# async def get_configs():
#     cursor = postgres_conn.cursor()
#     cursor.execute("SELECT * FROM configs")
#     configs = cursor.fetchall()
#     return {"configs": configs}

# @app.get("/configs/name/{config_name}")
# async def get_config_by_nickname(config_name: str):
#     cursor = postgres_conn.cursor()
#     cursor.execute("SELECT * FROM configs WHERE name = %s", (config_name,))
#     config = cursor.fetchone()
#     if config:
#         return {"config": config}

@app.post("/get_dump")
async def get_dump(file: UploadFile = File(...)):
    response = requests.post(f"{WAF_URL}/get_dump", files={"file": (file.filename, file.file, file.content_type)})
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to get config dump" + response.text)
    else:
        return response.json()

@app.get("/health")
async def health():
    return {"status": "ok"}
