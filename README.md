# HTTPD to Neo4j

This tool parses Apache HTTPD configuration using a dump and the files from the configuration and imports the directives into a Neo4j database for analysis and visualization.

## Installation

### Neo4j

1. Ensure Docker and Docker Compose are installed on your system.
2. Start the Neo4j service using the provided Docker Compose file:
   ```console
   docker compose up -d
   ```
> Note: This will start Neo4j and any other required services in the background.
3. Access the Neo4j browser at [http://localhost:7474](http://localhost:7474) and your database credentials are already set up in the `.env` file.

### Python Environment

1. Create a virtual environment for Python and install the needed dependencies:
   ```console
   python -m venv venv
   source ./venv/bin/activate
   pip install -r requirements.txt
   ```
2. Create a `.env` file with the following content:
   ```
   NEO4J_URL=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=<YOUR_PASSWORD>

   POSTGRES_URL=localhost
   POSTGRES_USER=admin
   POSTGRES_PASSWORD=<YOUR_PASSWORD>

   DOCKER_DATA_PATH=./docker_data
   ```

## Usage

1. Obtain a configuration dump from your Apache instance:
   ```console
   httpd -t -DDUMP_CONFIG > dump.txt
   ```

2. Run the main script with the path to the dump file:
   ```console
   python main.py dump.txt
   ```

This will parse the configuration dump and populate the Neo4j and PostgreSQL databases with the directives.
