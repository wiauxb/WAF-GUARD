import os
from neo4j import GraphDatabase
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Environment variables for connections
neo4jUser = os.getenv("NEO4J_USER")
neo4jPass = os.getenv("NEO4J_PASSWORD")

postgresUser = os.getenv("POSTGRES_USER")
postgresPass = os.getenv("POSTGRES_PASSWORD")

# Neo4j driver
neo4j_driver = GraphDatabase.driver("bolt://neo4j:7687", auth=(neo4jUser, neo4jPass))
neo4j_driver.verify_connectivity()

# PostgreSQL connections
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

# API URLs
WAF_URL = "http://waf:8000"
PARSER_URL = "http://parser:8000"
DELETE_BATCH_SIZE = 1000
