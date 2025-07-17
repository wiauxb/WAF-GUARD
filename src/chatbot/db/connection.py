from psycopg_pool import ConnectionPool
import os

# client=Client()

DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}

_pool = ConnectionPool(
    conninfo=f"host={POSTGRES_HOST} port={POSTGRES_PORT} dbname=chatbot user={DB_USER} password={DB_PASSWORD}",
    max_size=20,
    kwargs=connection_kwargs
    )

_pool_files = ConnectionPool(
    conninfo=f"host={POSTGRES_HOST} port={POSTGRES_PORT} dbname=files user={DB_USER} password={DB_PASSWORD}",
    max_size=20,
    kwargs=connection_kwargs
    )

def get_pool():
    return _pool

def get_files_pool():
    return _pool_files