import hashlib
from pathlib import Path
import re
import sys
import time
import uuid
import zipfile

import requests
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from neo4j import GraphDatabase
from pyvis.network import Network
from dotenv import load_dotenv
import pandas as pd
import os
import psycopg2

load_dotenv()

WAF_URL = "http://waf:8000"
PARSER_URL = "http://parser:8000"
DELETE_BATCH_SIZE = 1000

app = FastAPI()

neo4jUser = os.getenv("NEO4J_USER")
neo4jPass = os.getenv("NEO4J_PASSWORD")

postgresUser = os.getenv("POSTGRES_USER")
postgresPass = os.getenv("POSTGRES_PASSWORD")

# Neo4j driver
neo4j_driver = GraphDatabase.driver("bolt://neo4j:7687", auth=(neo4jUser, neo4jPass))
neo4j_driver.verify_connectivity()

# PostgreSQL connection
parsed_conn = psycopg2.connect(
    host="postgres",
    user=postgresUser,
    password=postgresPass,
    database="cwaf"
)

files_conn = psycopg2.connect(
    host="postgres",
    user=postgresUser,
    password=postgresPass,
    database="files"
)

export_dir = os.getenv("EXPORT_DIR")


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

@app.get("/configs")
async def get_configs():
    cursor = files_conn.cursor()
    cursor.execute("SELECT * FROM configs")
    configs = cursor.fetchall()
    return {"configs": configs}

@app.get("/configs/selected")
async def get_selected_config():
    """Get the currently selected configuration."""
    cursor = files_conn.cursor()

    # Get the currently selected config
    cursor.execute("SELECT * FROM selected_config ORDER BY id DESC LIMIT 1")
    selected = cursor.fetchone()
    
    if not selected:
        return {"selected_config": None}
    
    return {"selected_config": selected}

@app.post("/configs/select/{config_id}")
async def select_config(config_id: int):
    """Set the selected configuration."""

    # Validate config exists
    cursor = files_conn.cursor()
    cursor.execute("SELECT * FROM configs WHERE id = %s", (config_id,))
    config = cursor.fetchone()
    if not config:
        raise HTTPException(status_code=404, detail="Config does not exist")
    # Set the selected config
    cursor.execute("UPDATE selected_config SET config_id = %s", (config_id,))
    files_conn.commit()
    return {"message": "Config selected successfully"}

@app.delete("/configs/{config_id}")
async def delete_config(config_id: int):
    """Delete a configuration."""
    cursor = files_conn.cursor()
    cursor.execute("DELETE FROM configs WHERE id = %s", (config_id,))
    files_conn.commit()
    return {"message": "Config deleted successfully"}

def extract_config(file, name=None):
    """
    Process the uploaded config archive file.
    This function should handle the extraction and parsing of the config files.
    """
    #save the uploaded file to a temporary location
    
    # Generate unique filename using timestamp and UUID
    if name:
        name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
        unique_filename = f"/tmp/config_{int(time.time())}_{name_hash}.zip"
    else:
        unique_filename = f"/tmp/config_{int(time.time())}_{uuid.uuid4().hex[:8]}.zip"
    
    # Save the uploaded file
    with open(unique_filename, "wb") as f:
        f.write(file.read())
    
    # Extract the zip file
    extract_path = Path(f"/tmp/{Path(unique_filename).stem}")
    with zipfile.ZipFile(unique_filename, "r") as zip_ref:
        extract_path.mkdir(exist_ok=True)
        zip_ref.extractall(extract_path)

    # Delete the zip file after extraction
    Path(unique_filename).unlink()
    
    return Path(extract_path).absolute().resolve()

@app.post("/store_config")
async def store_config(file: UploadFile = File(...), config_nickname: str = Form(...)):

    if not config_nickname:
        return {"error": "Invalid input"}
    
    # Store the config in PostgreSQL
    cursor = files_conn.cursor()
    cursor.execute("""
        INSERT INTO configs (nickname)
        VALUES (%s)
        RETURNING id
    """, (config_nickname, ))
    response = cursor.fetchone()
    if response is None:
        return {"error": "Failed to store config"}
    config_id = response[0]
    files_conn.commit()

    config_path = extract_config(file.file, config_nickname)

    # Process each file in the extracted directory
    for file_path in config_path.glob('**/*'):
        if file_path.is_file():
            # Get the relative path from the config_path
            relative_path = str(file_path.relative_to(config_path))
            
            # Read file content as binary
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Insert file info into the database
            cursor.execute("""
                INSERT INTO files (config_id, path, content)
                VALUES (%s, %s, %s)
            """, (config_id, relative_path, file_content))
    
    # Commit the transaction
    files_conn.commit()
    
    return {"config_id": config_id}

@app.post("/get_dump")
async def get_dump(file: UploadFile = File(...)):
    response = requests.post(f"{WAF_URL}/get_dump", files={"file": (file.filename, file.file, file.content_type)})
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to get config dump" + response.text)
    else:
        return response.json()

@app.post("/store_dump")
async def store_dump(request: Request):
    data = await request.json()
    config_id = data.get("config_id")
    dump = data.get("dump")

    # Store the config in PostgreSQL
    cursor = files_conn.cursor()
    cursor.execute("""
        INSERT INTO dumps (config_id, dump)
        VALUES (%s, %s)
    """, (config_id, dump))
    files_conn.commit()
    return {"status": "success"}

@app.post("/configs/parse/{config_id}")
async def parse_config(config_id: int):
    """Start parsing a configuration and return a task ID for progress tracking."""
    # Validate config exists
    cursor = files_conn.cursor()
    cursor.execute("SELECT * FROM configs WHERE id = %s", (config_id,))
    config = cursor.fetchone()
    if not config:
        raise HTTPException(status_code=404, detail="Config does not exist")
    
    # Create a new task entry
    task_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO parsing_tasks (id, config_id, status, progress) VALUES (%s, %s, %s, %s)",
        (task_id, config_id, "pending", 0)
    )
    files_conn.commit()
    
    # Send the task to the parser service asynchronously
    try:
        response = requests.post(f"{PARSER_URL}/process_configs/{config_id}")
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Failed to start parsing: {response.text}")
    except requests.RequestException as e:
        cursor.execute(
            "UPDATE parsing_tasks SET status = %s WHERE task_id = %s",
            ("failed", task_id)
        )
        files_conn.commit()
        raise HTTPException(status_code=500, detail=f"Failed to connect to parser service: {str(e)}")
    
    # update the parsed status of the config in the db
    cursor.execute(
        "UPDATE configs SET parsed = TRUE WHERE id = %s",
        (config_id,)
    )
    files_conn.commit()

    # Return the task ID that the client can use to query progress
    return {
        "task_id": task_id,
        "status": "pending",
        "progress_endpoint": f"/parsing_progress/{task_id}"
    }

@app.get("/configs/parse/{config_id}")
async def get_parsed_config(config_id: int):
    cursor = files_conn.cursor()
    cursor.execute("SELECT parsed FROM configs WHERE id = %s", (config_id,))
    result = cursor.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"parsed": result[0]}

@app.get("/parsing_progress/{task_id}")
async def get_parsing_progress(task_id: str):
    """Get the progress of a parsing task."""
    cursor = files_conn.cursor()
    cursor.execute(
        "SELECT status, progress FROM parsing_tasks WHERE task_id = %s",
        (task_id,)
    )
    result = cursor.fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status, progress = result
    return {
        "task_id": task_id,
        "status": status,
        "progress": progress
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

# Database Export/Import functions
@app.post("/database/export/{config_name}")
async def export_database(config_name: str):
    """
    Export Neo4j and Postgres databases for a specific configuration using APOC
    
    Args:
        config_name: Name of the configuration to export
        
    Returns:
        Dict with status and download URL
    """
    try:
        # Check if export already exists
        export_path = Path(f"/exports/{config_name}")
        if export_path.exists():
            return {"status": "success", "message": f"Export for {config_name} already exists."}

        # Create export directory
        export_path.mkdir(parents=True, exist_ok=True)
        
        # Ensure the export directory has the right permissions for Neo4j
        os.system(f"chown -R 7474:7474 {export_path}")
        os.system(f"chmod -R 755 {export_path}")

        # Export Neo4j database using APOC
        with neo4j_driver.session() as session:
            # Use APOC to export all data to GraphML format
            result = session.run(
                f"CALL apoc.export.graphml.all('{export_path}/neo4j_export.graphml', "
                f"{{useTypes: true, storeNodeIds: true}})"
            )
            # Check for successful execution
            done = result.single()["done"]
            if not done:
                raise HTTPException(status_code=500, detail="Failed to export Neo4j database")

        # Export Postgres database using SQL COPY
        # Create a directory for postgres exports
        postgres_export_path = Path(f"{export_path}/postgres")
        postgres_export_path.mkdir(exist_ok=True)

        # Export data from the 'cwaf' database
        cursor = parsed_conn.cursor()
        
        # Get all table names
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [table[0] for table in cursor.fetchall()]
        
        # Export each table to CSV
        for table in tables:
            output_file = f"{postgres_export_path}/{table}.csv"
            with open(output_file, 'w') as f:
                cursor.copy_expert(f"COPY {table} TO STDOUT WITH CSV HEADER", f)
        return {"status": "success"}
    except Exception as e:
        # remove the export directory if it was created for atomicity
        if export_path.exists():
            # for item in export_path.iterdir():
            #     item.unlink()
            export_path.rmdir()
        raise HTTPException(status_code=500, detail=f"Failed to export database: {str(e)}")

@app.post("/database/import/{config_name}")
async def import_database(config_name: str):
    """
    Import a previously exported database
    
    Args:
        config_name: Name to give to the imported configuration

    Returns:
        Dict with status and message
    """
    try:
        # Import the Neo4j database using APOC
        with neo4j_driver.session() as session:
            # Clear the database
            while True:
                result = session.run(f"""
                    MATCH (n)
                    WITH n LIMIT {DELETE_BATCH_SIZE}
                    DETACH DELETE n
                    RETURN count(n) as deleted
                """)
                deleted = result.single()["deleted"]
                if deleted == 0:
                    break
            
            # Import the data
            session.run(
                f"CALL apoc.import.graphml('/exports/{config_name}/neo4j_export.graphml', "
                f"{{useTypes: true, readLabels: true}})"
            )
        
        # Import the PostgreSQL database
        postgres_import_path = Path(f"/exports/{config_name}/postgres")
        if not postgres_import_path.exists():
            raise HTTPException(status_code=404, detail=f"PostgreSQL export data not found at {postgres_import_path}")
        
        # Import to 'cwaf' database
        cursor = parsed_conn.cursor()
        
        # First clear the tables
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [table[0] for table in cursor.fetchall()]
        
        # Disable foreign key checks for clean import
        cursor.execute("SET session_replication_role = 'replica'")
        
        # Truncate all tables
        for table in tables:
            try:
                cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
            except Exception as e:
                # Log issue but continue with other tables
                print(f"Error truncating table {table}: {str(e)}")
        
        # Import each table from CSV
        for csv_file in postgres_import_path.glob("*.csv"):
            table_name = csv_file.stem
            if "_files" not in table_name and table_name in tables:
                try:
                    with open(csv_file, 'r') as f:
                        cursor.copy_expert(f"COPY {table_name} FROM STDIN WITH CSV HEADER", f)
                except Exception as e:
                    print(f"Error importing {table_name}: {str(e)}")
        
        # Re-enable foreign key checks
        cursor.execute("SET session_replication_role = 'origin'")
        parsed_conn.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import database: {str(e)}")