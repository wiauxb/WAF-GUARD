#!/bin/bash
# Usage: ./restore_dump.sh /path/to/dump

source ../.env

#test if dir already exists
if [ ! -d $1 ]; then
    echo "Directory does not exist. Please provide a valid directory."
    exit 1
fi

#check if neo4j container is running
started_container=false
if [ -z "$(docker ps -q -f name=neo4j)" ]; then
    echo "Neo4j container is not running. Starting it now."
    docker compose up -d --wait neo4j
    started_container=true
fi

docker compose cp $1 neo4j:/tmp 
docker compose exec -it neo4j chown -R neo4j:neo4j /tmp/$1
docker compose exec -it --user neo4j neo4j neo4j stop
docker compose exec -it --user neo4j neo4j neo4j-admin database load neo4j --from-path=/tmp/$1 --overwrite-destination
docker compose exec -it neo4j rm -rf /tmp/$1
docker compose exec -it --user neo4j neo4j neo4j start

docker compose exec -it postgres mkdir /tmp/$1
docker compose cp $1/cwaf.sql postgres:/tmp/$1
docker compose exec -it postgres bash -c "psql -U ${POSTGRES_USER} -d cwaf -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'"
docker compose exec -it postgres bash -c "psql -U ${POSTGRES_USER} -d cwaf -f /tmp/$1/cwaf.sql"
docker compose exec -it postgres rm -rf /tmp/$1

if [ $started_container = true ]; then
    echo "Stopping Neo4j container."
    docker compose down neo4j
fi