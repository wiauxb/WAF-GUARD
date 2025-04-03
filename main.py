import os
import sys
import time
import math
import argparse
from dotenv import load_dotenv
from src.parser.parser import parse_compiled_config
from src.parser.helper_classes.neo4j_interface import Neo4jDB
from src.parser.helper_classes.sql_interface import PostgresDB
from src.parser.helper_classes.timer import Timer


def initialize_databases(neo4j_url, neo4j_user, neo4j_pass, postgres_url, postgres_user, postgres_pass):
    """Initialize and clear Neo4j and PostgreSQL databases."""
    os.system("./reset_neo4j_db.sh")
    # sleep for 5 seconds to allow Neo4j to restart
    time.sleep(5)
    graph = Neo4jDB(neo4j_url, neo4j_user, neo4j_pass)
    sql_db = PostgresDB(postgres_url, postgres_user, postgres_pass, "cwaf")
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
    # loop_starting_time = time.perf_counter()
    loop_timer = Timer("Process Dirs")
    loop_timer.start()

    for i, directive in enumerate(directives):
        graph.add_neo4j(directive)
        sql_db.add_sql(directive)

        if (i + 1) % step == 0:
            elapsed = loop_timer.time()
            print(
                f"\rProgression: {math.ceil(100 * (i + 1) / len(directives))}% done. "
                f"Time elapsed: {f"{elapsed//60:.0f}m" if elapsed >= 60 else ""}{elapsed%60:02.0f}s "
                f"Time left: {estimate_time_left((i+1)/len(directives), elapsed)}",
                end="", flush=True
            )
    print()


def main(file_path):
    """Main function to parse configuration and populate databases."""
    load_dotenv()
    neo4j_url = os.getenv("NEO4J_URL")
    neo4j_user = os.getenv("NEO4J_USER")
    neo4j_pass = os.getenv("NEO4J_PASSWORD")
    postgres_url = os.getenv("POSTGRES_URL")
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
    parser = argparse.ArgumentParser(description="Parse Apache HTTPD configuration and populate Neo4j and PostgreSQL databases.")
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
