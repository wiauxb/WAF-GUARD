import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..db.connections import neo4j_driver, parsed_conn, files_conn, DELETE_BATCH_SIZE

router = APIRouter(prefix="/database", tags=["Database Management"])


@router.post("/export/{config_name}")
async def export_database(config_name: str):
    """
    Export Neo4j and Postgres databases for a specific configuration using APOC
    
    Args:
        config_name: Name of the configuration to export
        
    Returns:
        Dict with status and download URL
    """
    try:
        # Check if export already exists
        export_path = Path(f"/exports/{config_name}")
        if export_path.exists():
            return {"status": "success", "message": f"Export for {config_name} already exists."}

        # Create export directory
        export_path.mkdir(parents=True, exist_ok=True)
        
        # Ensure the export directory has the right permissions for Neo4j
        os.system(f"chown -R 7474:7474 {export_path}")
        os.system(f"chmod -R 755 {export_path}")

        # Export Neo4j database using APOC
        with neo4j_driver.session() as session:
            # Use APOC to export all data to GraphML format
            result = session.run(
                f"CALL apoc.export.graphml.all('{export_path}/neo4j_export.graphml', "
                f"{{useTypes: true, storeNodeIds: true}})"
            )
            # Check for successful execution
            done = result.single()["done"]
            if not done:
                raise HTTPException(status_code=500, detail="Failed to export Neo4j database")

        # Export Postgres database using SQL COPY
        # Create a directory for postgres exports
        postgres_export_path = Path(f"{export_path}/postgres")
        postgres_export_path.mkdir(exist_ok=True)

        # Export data from the 'cwaf' database
        cursor = parsed_conn.cursor()
        
        # Get all table names
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [table[0] for table in cursor.fetchall()]
        
        # Export each table to CSV
        for table in tables:
            output_file = f"{postgres_export_path}/{table}.csv"
            with open(output_file, 'w') as f:
                cursor.copy_expert(f"COPY {table} TO STDOUT WITH CSV HEADER", f)
        return {"status": "success"}
    except Exception as e:
        # remove the export directory if it was created for atomicity
        if export_path.exists():
            # for item in export_path.iterdir():
            #     item.unlink()
            export_path.rmdir()
        raise HTTPException(status_code=500, detail=f"Failed to export database: {str(e)}")


@router.post("/import/{config_name}")
async def import_database(config_name: str):
    """
    Import a previously exported database
    
    Args:
        config_name: Name to give to the imported configuration

    Returns:
        Dict with status and message
    """
    try:
        # Import the Neo4j database using APOC
        with neo4j_driver.session() as session:
            # Clear the database
            while True:
                result = session.run(f"""
                    MATCH (n)
                    WITH n LIMIT {DELETE_BATCH_SIZE}
                    DETACH DELETE n
                    RETURN count(n) as deleted
                """)
                deleted = result.single()["deleted"]
                if deleted == 0:
                    break
            
            # Import the data
            session.run(
                f"CALL apoc.import.graphml('/exports/{config_name}/neo4j_export.graphml', "
                f"{{useTypes: true, readLabels: true}})"
            )
        
        # Import the PostgreSQL database
        postgres_import_path = Path(f"/exports/{config_name}/postgres")
        if not postgres_import_path.exists():
            raise HTTPException(status_code=404, detail=f"PostgreSQL export data not found at {postgres_import_path}")
        
        # Import to 'cwaf' database
        cursor = parsed_conn.cursor()
        
        # First clear the tables
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [table[0] for table in cursor.fetchall()]
        
        # Disable foreign key checks for clean import
        cursor.execute("SET session_replication_role = 'replica'")
        
        # Truncate all tables
        for table in tables:
            try:
                cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
            except Exception as e:
                # Log issue but continue with other tables
                print(f"Error truncating table {table}: {str(e)}")
        
        # Import each table from CSV
        for csv_file in postgres_import_path.glob("*.csv"):
            table_name = csv_file.stem
            if "_files" not in table_name and table_name in tables:
                try:
                    with open(csv_file, 'r') as f:
                        cursor.copy_expert(f"COPY {table_name} FROM STDIN WITH CSV HEADER", f)
                except Exception as e:
                    print(f"Error importing {table_name}: {str(e)}")
        
        # Re-enable foreign key checks
        cursor.execute("SET session_replication_role = 'origin'")
        parsed_conn.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import database: {str(e)}")
