#!/bin/bash

# stop neo4j docker compose service
docker compose exec -T neo4j neo4j stop

# remove neo4j data
echo "Removing neo4j data"
docker compose exec -T neo4j bash -c "rm -rf /data/databases/neo4j/*"
docker compose exec -T neo4j bash -c "rm -rf /data/transactions/neo4j/*"

# start neo4j docker compose service
docker compose exec -T neo4j neo4j start
docker compose up -d --wait neo4j
docker compose restart fastapi