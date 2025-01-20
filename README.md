# HTTPD to Neo4j

## Install

 Create a virtual environnement for python and install needed depedencies:
 ```console
 python -m venv venv
 source ./venv/bin/activate
 pip install -r requirements.txt
 ```

 In a `.env` file, write the connection information for your neo4j DB. Usually looks like this:
```
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<THEPASSWORD>
```

 ## Run

In [dump_parse.py](dump_parse.py) write the file path to your config dump. You can obtain a dump by doing a `httpd -t -DDUMP_CONFIG` on your apache instance.

Running the DB generation is as easy as
```console
python dump_parse.py
```
 