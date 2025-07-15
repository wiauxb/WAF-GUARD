from langgraph.store.postgres import PostgresStore
from db.connection import get_pool


def add_to_store(update,user_id):
    """
    Update the Postgres store with the latest changes.
    This function is called when the application starts or when there are changes to the graph.
    """
    pool = get_pool()
    store = PostgresStore(pool)
    store.put(("users",user_id),"global", {"language":"english","theme":"dark"})
    
    return store

add_to_store("update", "3")