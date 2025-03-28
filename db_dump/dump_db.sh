#!/bin/bash
# Usage: ./dump_db.sh /path/to/dump

source ../.env

#test if dir already exists
if [ -d $1 ]; then
    echo "Directory already exists. Please provide a new directory."
    exit 1
fi

#check if neo4j container is running
started_container=false
if [ -z "$(docker ps -q -f name=neo4j)" ]; then
    echo "Neo4j container is not running. Starting it now."
    docker compose up -d --wait neo4j
    started_container=true
fi

# mkdir $1
docker compose exec -it neo4j mkdir /tmp/$1
docker compose exec -it neo4j neo4j stop
docker compose exec -it neo4j neo4j-admin database dump neo4j --to-path=/tmp/$1
docker compose cp neo4j:/tmp/$1 .
docker compose exec -it neo4j neo4j start

docker compose exec -it postgres mkdir /tmp/$1
docker compose exec -it postgres bash -c "pg_dump -U ${POSTGRES_USER} cwaf > /tmp/$1/cwaf.sql"
docker compose cp postgres:/tmp/$1 .

if [ $started_container = true ]; then
    echo "Stopping Neo4j container."
    docker compose down neo4j
fi