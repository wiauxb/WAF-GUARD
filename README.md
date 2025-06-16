# HTTPD to Neo4j

This tool parses Apache HTTPD configuration using a dump and the files from the configuration and imports the directives into a Neo4j database for analysis and visualization.

## Project

This project operate in two steps:
 - The parsing of the config
 - The exploitation and exploration of the extracted information

The first step is performed in the `config manager` page, the second one is enabled by the interfaces of the streamlit, neo4j and adminer docker services.

The project is structured as follows:
```
.
├── docker/                 # Docker configuration files and persistent data
├── src/                    # Source code for the project
│   ├── parser/             # Parser ressponsible for the analysis of the dumps
│   │                               and populating the DBs.
│   ├── waf_rest_api/       # WAF implementation (apache + modsecurity) + REST API endpoint
│   │                               responsible of dumping the configs
│   └── web_app/            # Streamlit web application for management, exploration and visualization
├── .env                    # Environment variables configuration
└── README.md               # Project documentation
```

This structure organizes the project into logical components, making it easier to maintain and extend.

### Services Architecture
![Architecture](images/architecture.png)

## Installation

### Environment
Create a `.env` file with the following content:

   ```
   PWD=<path-to-the-root-of-this-project>

   NEO4J_URL=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=<your-password>

   POSTGRES_URL=localhost
   POSTGRES_USER=admin
   POSTGRES_PASSWORD=<your-password>

   DOCKER_DATA_PATH=${PWD}/docker/docker_data
   EXPORT_DIR=${DOCKER_DATA_PATH}/db_exports
   SRC_PATH=${PWD}/src
   WEB_APP_PATH=${SRC_PATH}/web_app
   CHATBOT_PATH=${SRC_PATH}/chatbot
   ```

### Docker containers

1. Ensure Docker and Docker Compose are installed on your system. (the [docker engine](https://docs.docker.com/engine/install/) and the [compose](https://docs.docker.com/compose/install/) plugin or compose standalone)
1. Build and run the containers:
   ```
   docker compose up -d
   ```
1. You should see 7 services running:
```
[+] Running 7/7
 ✔ Container fastapi    Started
 ✔ Container parser     Started
 ✔ Container adminer    Started
 ✔ Container neo4j      Healthy
 ✔ Container waf        Started
 ✔ Container postgres   Healthy
 ✔ Container streamlit  Started
 ```

## Quick Start

1. Access the interface at `http://localhost:8501/config_manager` under the **_Add New Config_** section, choose a name for your config, drag&drop a zip of your configuration and click on the `Submit` button. This will save all the files of your configuration and generate a dump of your config. It might take up to 1 minute.
Your Zip file can eather contain the `conf` directory at its root, or directly the content of the `conf` directory.

2. A new entry is now available in the **_Known Configs_** section, select it and press the `Parse & Load Config`. This will trigger the analysis process, and will take a long time. **No feedback mechanism are currently implemented, meaning that the page will freeze saying _"running"_ for ages.** If you want to examin the process, please consult the logs of the `parser` service.
   ```console
   docker compose logs parser -f
   ```
   Once the process has finished parsing the configuration dump and populating the Neo4j and PostgreSQL databases with the directives, your entry will now be highlighted in yellow.

3. Access the interface at `http://localhost:8501` to query part of the Neo4j graph, filter directives by an http query or track what impact does a constant have.
   > You can directly query the neo4j database using the interface at `http://localhost:7474` and the postgresql database using the interface at `http://localhost:8080`.
