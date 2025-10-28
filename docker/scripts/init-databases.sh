#!/bin/bash
set -e

# This script runs during PostgreSQL container initialization
# It creates the required databases and tables if they don't exist

echo "Starting database initialization..."

# Function to check if database exists
database_exists() {
    local db_name=$1
    psql -U "$POSTGRES_USER" -lqt | cut -d \| -f 1 | grep -qw "$db_name"
}

# Function to check if database has tables (to avoid re-initialization)
database_has_tables() {
    local db_name=$1
    local table_count=$(psql -U "$POSTGRES_USER" -d "$db_name" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
    [ "$table_count" -gt 0 ]
}

# Function to create database if it doesn't exist
create_database_if_not_exists() {
    local db_name=$1
    local sql_file=$2
    
    if database_exists "$db_name"; then
        echo "Database '$db_name' already exists."
        if database_has_tables "$db_name"; then
            echo "Database '$db_name' already has tables, skipping initialization."
            return 0
        else
            echo "Database '$db_name' exists but has no tables, initializing..."
        fi
    else
        echo "Creating database '$db_name'..."
        createdb -U "$POSTGRES_USER" "$db_name"
    fi
    
    if [ -f "$sql_file" ]; then
        echo "Initializing database '$db_name' with schema from $sql_file..."
        # Remove the \connect command from the SQL file and execute it
        sed '/\\connect/d' "$sql_file" | psql -U "$POSTGRES_USER" -d "$db_name"
        echo "Database '$db_name' initialized successfully."
    else
        echo "Warning: SQL file $sql_file not found, database created but not initialized."
    fi
}

# Wait for PostgreSQL to be ready
until pg_isready -d "$POSTGRES_DB" -U "$POSTGRES_USER"; do
    echo "Waiting for PostgreSQL to be ready..."
    sleep 2
done

echo "PostgreSQL is ready. Initializing databases..."

# Create databases
create_database_if_not_exists "${POSTGRES_DB_CWAF}" "/init/cwaf_db.sql"
create_database_if_not_exists "${POSTGRES_DB_FILES}" "/init/files_db.sql"
create_database_if_not_exists "${POSTGRES_DB_CHATBOT}" "/init/chatbot_db.sql"

echo "Database initialization completed."
