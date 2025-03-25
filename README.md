# HTTPD to Neo4j

This tool parses Apache HTTPD configuration using a dump and the files from the configuration and imports the directives into a Neo4j database for analysis and visualization.

## Project

This project operate in two steps:
 - The parsing of the config
 - The exploitation and exploration of the extracted information

The first step is performed thanks to the [main.py](main.py) python file, the second one is enabled by the interfaces of the streamlit, neo4j and adminer docker services.

The project is structured as follows:

```
.
├── docker/                 # Docker configuration files and persistant data
├── src/                    # Source code for the project
│   main.py                 # Main script to parse and import directives
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables configuration
└── README.md               # Project documentation
```

This structure organizes the project into logical components, making it easier to maintain and extend.

## Installation

### Python Environment

1. Create a virtual environment for Python and install the needed dependencies:
   ```console
   python -m venv venv
   source ./venv/bin/activate
   pip install -r requirements.txt
   ```
2. Create a `.env` file with the following content:
   ```
   PWD=<PATH_TO_THE_ROOT_OF_THIS_PROJECT>

   NEO4J_URL=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=<YOUR_PASSWORD>

   POSTGRES_URL=localhost
   POSTGRES_USER=admin
   POSTGRES_PASSWORD=<YOUR_PASSWORD>

   DOCKER_DATA_PATH=${PWD}/docker/docker_data
   WEB_APP_PATH=${PWD}/src/web_app
   ```

### Docker containers

1. Ensure Docker and Docker Compose are installed on your system. (the [docker engine](https://docs.docker.com/engine/install/) and the [compose](https://docs.docker.com/compose/install/) plugin or compose standalone)
1. Build and run the containers:
   ```
   docker compose up -d
   ```
1. You should see 5 services running:
```
[+] Running 5/5
 ✔ Container postgres   Healthy
 ✔ Container adminer    Running
 ✔ Container neo4j      Healthy
 ✔ Container fastapi    Running
 ✔ Container streamlit  Running 
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

3 . Access the interface at `http://localhost:8501` to query part of the Neo4j graph, filter directives by an http query or track what impact does a constant have.
   > You can directly query the neo4j database using the interface at `http://localhost:7474` and the postgresql database using the interface at `http://localhost:8080`.