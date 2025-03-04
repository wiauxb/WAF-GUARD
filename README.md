# HTTPD to Neo4j

This tool parses Apache HTTPD configuration using a dump and the files from the configuration and imports the directives into a Neo4j database for analysis and visualization.

## Install

### Neo4j

1. Download and install Neo4j from the [official website](https://neo4j.com/download/).
2. Follow the installation instructions for your operating system.
3. Start the Neo4j server:
```console
neo4j start
```
4. Access the Neo4j browser at [http://localhost:7474](http://localhost:7474) and set up your database credentials.

### Python Environment

Create a virtual environment for Python and install the needed dependencies:
```console
python -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
```

In a `.env` file, write the connection information for your Neo4j and PostgreSQL DB. It should look like this:
```
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<THEPASSWORD>

POSTGRES_URL=localhost
POSTGRES_USER=admin
POSTGRES_PASSWORD=<THEPASSWORD>

DOCKER_DATA_PATH=./docker_data
```

## Run

1. Obtain a configuration dump from your Apache instance by running:
```console
httpd -t -DDUMP_CONFIG > dump.txt
```

2. In [dump_parse.py](dump_parse.py), ensure the file path to your config dump is correct.

3. Run the DB generation script:
```console
python dump_parse.py
```

This will parse the configuration dump and populate the Neo4j database with the directives.
