#!/bin/bash

source .env

# stop neo4j docker compose service
docker compose -f compose.yaml down neo4j

# remove neo4j data
echo "Removing neo4j data"
sudo rm -rf ${PWD}/docker/docker_data/neo4j/data/databases/neo4j/*
sudo rm -rf ${PWD}/docker/docker_data/neo4j/data/transactions/neo4j/*

# start neo4j docker compose service
docker compose -f compose.yaml up -d --wait neo4j