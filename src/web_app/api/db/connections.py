import os
from neo4j import GraphDatabase
import psycopg2

# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

# Environment variables for connections
neo4jUser = os.getenv("NEO4J_USER")
neo4jPass = os.getenv("NEO4J_PASSWORD")
neo4jUrl = os.getenv("NEO4J_URL")
neo4jUrlProd = os.getenv("NEO4J_URL_PROD")

postgres_host = os.getenv("POSTGRES_HOST")
postgresUser = os.getenv("POSTGRES_USER")
postgresPass = os.getenv("POSTGRES_PASSWORD")

postgres_db_cwaf = os.getenv("POSTGRES_DB_CWAF", "cwaf")
postgres_db_files = os.getenv("POSTGRES_DB_FILES", "files")

# API URLs
WAF_URL = os.getenv("WAF_URL")
ANALYZER_URL = os.getenv("ANALYZER_URL")
DELETE_BATCH_SIZE = os.getenv("DELETE_BATCH_SIZE")

export_dir = os.getenv("EXPORT_DIR")

# Neo4j driver with environment-based configuration
if ENVIRONMENT == "prod":
    neo4j_driver = GraphDatabase.driver(neo4jUrlProd, auth=(neo4jUser, neo4jPass))
else:
    neo4j_driver = GraphDatabase.driver(neo4jUrl, auth=(neo4jUser, neo4jPass))

neo4j_driver.verify_connectivity()

# PostgreSQL connections with environment-based SSL
if ENVIRONMENT == "prod":
    parsed_conn = psycopg2.connect(
        host=postgres_host,
        user=postgresUser,
        password=postgresPass,
        database=postgres_db_cwaf,
        sslmode='require'
    )

    files_conn = psycopg2.connect(
        host=postgres_host,
        user=postgresUser,
        password=postgresPass,
        database=postgres_db_files,
        sslmode='require'
    )
else:
    parsed_conn = psycopg2.connect(
        host=postgres_host,
        user=postgresUser,
        password=postgresPass,
        database=postgres_db_cwaf
    )

    files_conn = psycopg2.connect(
        host=postgres_host,
        user=postgresUser,
        password=postgresPass,
        database=postgres_db_files
    )




