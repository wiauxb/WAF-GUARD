sudo systemctl stop neo4j
sudo su neo4j -c "neo4j-admin database load neo4j --from-path=$1 --overwrite-destination"
sudo systemctl start neo4j