import os
from neo4j import GraphDatabase
import psycopg2

# Environment variables for connections
neo4jUser = os.getenv("NEO4J_USER")
neo4jPass = os.getenv("NEO4J_PASSWORD")
neo4jUrl = os.getenv("NEO4J_URL")

postgres_host = os.getenv("POSTGRES_HOST")
postgresUser = os.getenv("POSTGRES_USER")
postgresPass = os.getenv("POSTGRES_PASSWORD")

# API URLs
WAF_URL = os.getenv("WAF_URL")
ANALYZER_URL = os.getenv("ANALYZER_URL")
DELETE_BATCH_SIZE = os.getenv("DELETE_BATCH_SIZE")

export_dir = os.getenv("EXPORT_DIR")

# Neo4j driver
neo4j_driver = GraphDatabase.driver(neo4jUrl, auth=(neo4jUser, neo4jPass))
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




