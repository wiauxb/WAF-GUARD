from psycopg_pool import ConnectionPool
import os

# client=Client()

# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB_CHATBOT = os.getenv("POSTGRES_DB_CHATBOT", "chatbot")
POSTGRES_DB_FILES = os.getenv("POSTGRES_DB_FILES", "files")
connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}

# Connection pools with environment-based SSL
if ENVIRONMENT == "prod":
    _pool = ConnectionPool(
        conninfo=f"host={POSTGRES_HOST} port={POSTGRES_PORT} dbname={POSTGRES_DB_CHATBOT} user={DB_USER} password={DB_PASSWORD} sslmode=require",
        max_size=20,
        kwargs=connection_kwargs
    )

    _pool_files = ConnectionPool(
        conninfo=f"host={POSTGRES_HOST} port={POSTGRES_PORT} dbname={POSTGRES_DB_FILES} user={DB_USER} password={DB_PASSWORD} sslmode=require",
        max_size=20,
        kwargs=connection_kwargs
    )
else:
    _pool = ConnectionPool(
        conninfo=f"host={POSTGRES_HOST} port={POSTGRES_PORT} dbname={POSTGRES_DB_CHATBOT} user={DB_USER} password={DB_PASSWORD}",
        max_size=20,
        kwargs=connection_kwargs
    )

    _pool_files = ConnectionPool(
        conninfo=f"host={POSTGRES_HOST} port={POSTGRES_PORT} dbname={POSTGRES_DB_FILES} user={DB_USER} password={DB_PASSWORD}",
        max_size=20,
        kwargs=connection_kwargs
    )

def get_pool():
    return _pool

def get_files_pool():
    return _pool_files