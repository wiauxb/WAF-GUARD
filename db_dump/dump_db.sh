#!/bin/bash
# Usage: ./dump_db.sh /path/to/dump

#test if dir already exists
if [ -d $1 ]; then
    echo "Directory already exists. Please provide a new directory."
    exit 1
fi
mkdir $1
sudo chown neo4j:$(whoami) $1
sudo systemctl stop neo4j
sudo su neo4j -c "neo4j-admin database dump neo4j --to-path=$1"
sudo systemctl start neo4j