import os
import sys
import time
import math
import argparse
from tqdm import tqdm

from .analyzer import parse_compiled_config
from .helper_classes.neo4j_interface import Neo4jDB
from .helper_classes.sql_interface import PostgresDB
from .helper_classes.timer import Timer

DELETE_BATCH_SIZE = os.getenv("DELETE_BATCH_SIZE")

def reset_neo4j(neo4j_url, neo4j_user, neo4j_pass):
    graph = Neo4jDB(neo4j_url, neo4j_user, neo4j_pass)
    while True:
        result = graph.query(f"""
            MATCH (n)
            WITH n LIMIT {DELETE_BATCH_SIZE}
            DETACH DELETE n
            RETURN count(n) as deleted
        """)
        deleted = result[0]["deleted"]
        print(f"\033[33mNeo4j | \033[0mDeleted {deleted} relationships")
        if deleted == 0:
            break

def initialize_databases(neo4j_url, neo4j_user, neo4j_pass, postgres_url, postgres_user, postgres_pass):
    """Initialize and clear Neo4j and PostgreSQL databases."""
    reset_neo4j(neo4j_url, neo4j_user, neo4j_pass)
    # sleep for 5 seconds to allow Neo4j to restart
    # time.sleep(5) #FIXME remove ?
    graph = Neo4jDB(neo4j_url, neo4j_user, neo4j_pass)
    sql_db = PostgresDB(postgres_url, postgres_user, postgres_pass, "cwaf") #FIXME: why not create a new schema for each config ?
    sql_db.execute("DROP SCHEMA public CASCADE")
    sql_db.execute("CREATE SCHEMA public")
    sql_db.init_tables()
    return graph, sql_db


def estimate_time_left(progress, time_taken):
    time_left = (time_taken / progress) - time_taken
    return f"{time_left//60:02.0f}m{time_left%60:02.0f}s"

def process_directives(directives, graph, sql_db):
    """Process directives and populate databases."""
    
    step = len(directives) // 100 or 1
    
    if os.getenv("RUNNING_IN_DOCKER"):
        print("Running in Docker, using tqdm workaround.")
        it = tqdm(total=len(directives), desc="Processing Directives", unit="directives")
        print(it)
        for i, directive in enumerate(directives):
            graph.add_neo4j(directive)
            sql_db.add_sql(directive)
            it.update(1)
            if i % step == 0:
                print()
    else:
        print("Running outside Docker, using standard tqdm.")
        for directive in tqdm(directives, desc="Processing Directives", unit="directives"):
            graph.add_neo4j(directive)
            sql_db.add_sql(directive)

def main(file_path):
    """Main function to analyze configuration and populate databases."""
    if os.getenv("RUNNING_IN_DOCKER"):
        neo4j_url = "bolt://neo4j:7687"
        postgres_url = "postgres"
    else:
        neo4j_url = os.getenv("NEO4J_URL")
        postgres_url = os.getenv("POSTGRES_HOST")
    neo4j_user = os.getenv("NEO4J_USER")
    neo4j_pass = os.getenv("NEO4J_PASSWORD")
    postgres_user = os.getenv("POSTGRES_USER")
    postgres_pass = os.getenv("POSTGRES_PASSWORD")

    with Timer("Total Execution"):
        with Timer("Parsing Config"):
            print(f"Parsing {file_path}...", end="", flush=True)
            directives = parse_compiled_config(file_path)
            print(f"\rFound {len(directives)} directives in {file_path}.")
        # exit()

        with Timer("Clearing Databases"):
            graph, sql_db = initialize_databases(neo4j_url, neo4j_user, neo4j_pass, postgres_url, postgres_user, postgres_pass)
            # graph, sql_db = None, None 

        with Timer("Processing Directives"):
            process_directives(directives, graph, sql_db)

        with Timer("Create Indexes"):
            graph.create_indexes()

        graph.close()
        sql_db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Apache HTTPD configuration and populate Neo4j and PostgreSQL databases.")
    parser.add_argument(
        "file_path",
        type=str,
        help="Path to the Apache HTTPD configuration dump file (e.g., dump.txt)."
    )
    parser.add_argument(
        "-c",
        "--config-root",
        type=str,
        default=os.getcwd(),
        help="Path to the root directory of the Apache HTTPD configuration (where conf/* is). Defaults to the current working directory."
    )
    args = parser.parse_args()

    os.environ["CONFIG_ROOT"] = args.config_root

    try:
        main(args.file_path)
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.", file=sys.stderr)
