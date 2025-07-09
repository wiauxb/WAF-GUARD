from psycopg_pool import ConnectionPool
import os

from dotenv import load_dotenv
load_dotenv()
# client=Client()

DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}

_pool = ConnectionPool(
    conninfo=f"host=postgres port=5432 dbname=chatbot user={DB_USER} password={DB_PASSWORD}",
    max_size=20,
    kwargs=connection_kwargs
    )

_pool_files = ConnectionPool(
    conninfo=f"host=postgres port=5432 dbname=files user={DB_USER} password={DB_PASSWORD}",
    max_size=20,
    kwargs=connection_kwargs
    )

def get_pool():
    return _pool

def get_files_pool():
    return _pool_files