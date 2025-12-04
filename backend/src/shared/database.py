# shared/database.py
"""
Database configuration and connection management.
Supports both PostgreSQL (SQLAlchemy) and Neo4j (Neo4j Python Driver).
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool
from neo4j import GraphDatabase, Session as Neo4jSession
from langgraph.checkpoint.postgres import PostgresSaver
from typing import Generator
import logging

from .config import settings

# Configure logging
logger = logging.getLogger(__name__)

# ==================== PostgreSQL Setup ====================

# Create PostgreSQL engine with connection pooling
postgres_engine = create_engine(
    settings.POSTGRES_URL,
    echo=settings.DATABASE_ECHO,  # Log SQL queries (False in production)
    pool_size=settings.POSTGRES_POOL_SIZE,
    max_overflow=settings.POSTGRES_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args={
        "options": "-c timezone=utc"  # Use UTC timezone
    }
)

# Create session factory for PostgreSQL
PostgresSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=postgres_engine
)

# Create base class for SQLAlchemy models
Base = declarative_base()

# Event listener for connection pool events (optional, useful for debugging)
@event.listens_for(postgres_engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log when a new connection is established"""
    logger.debug("PostgreSQL connection established")

@event.listens_for(postgres_engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log when a connection is checked out from the pool"""
    logger.debug("PostgreSQL connection checked out from pool")


def get_postgres_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a PostgreSQL database session.
    Automatically commits on success and rolls back on error.
    Always closes the session after request.
    
    Usage in FastAPI routes:
        @router.get("/items")
        def get_items(db: Session = Depends(get_postgres_db)):
            return db.query(Item).all()
    """
    db = PostgresSessionLocal()
    try:
        yield db
        db.commit()  # Commit if no exceptions
    except Exception as e:
        db.rollback()  # Rollback on error
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()


# ==================== Neo4j Setup ====================

class Neo4jConnection:
    """
    Neo4j database connection manager.
    Uses connection pooling internally via Neo4j driver.
    """
    
    def __init__(self):
        """Initialize Neo4j driver with connection pooling"""
        self._driver = None
        self._initialize_driver()
    
    def _initialize_driver(self):
        """Create Neo4j driver instance"""
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URL,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                max_connection_pool_size=settings.NEO4J_POOL_SIZE,
                connection_timeout=30.0,
                max_connection_lifetime=3600,  # 1 hour
                connection_acquisition_timeout=60.0,
                encrypted=settings.NEO4J_ENCRYPTED,
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            logger.info("Neo4j connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close the Neo4j driver and all connections"""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed")
    
    def get_session(self, database: str = None) -> Neo4jSession:
        """
        Get a Neo4j session.
        
        Args:
            database: Optional database name (default: neo4j default database)
        
        Returns:
            Neo4j session object
        """
        if not self._driver:
            self._initialize_driver()
        
        return self._driver.session(database=database or settings.NEO4J_DATABASE)
    
    def verify_connectivity(self):
        """Verify that the connection to Neo4j is working"""
        if self._driver:
            self._driver.verify_connectivity()


# Create singleton Neo4j connection instance
neo4j_connection = Neo4jConnection()


def get_neo4j_db() -> Generator[Neo4jSession, None, None]:
    """
    FastAPI dependency that provides a Neo4j database session.
    Automatically closes the session after request.
    
    Usage in FastAPI routes:
        @router.get("/graph")
        def get_graph(neo4j: Neo4jSession = Depends(get_neo4j_db)):
            result = neo4j.run("MATCH (n) RETURN n LIMIT 10")
            return [record.data() for record in result]
    """
    session = neo4j_connection.get_session()
    try:
        yield session
    except Exception as e:
        logger.error(f"Neo4j error: {e}")
        raise
    finally:
        session.close()


def get_langgraph_checkpointer():
    """
    Get LangGraph checkpointer instance.
    Can be used as a dependency or in services.

    Returns a context manager that should be used with 'with' statement.
    """
    # Convert SQLAlchemy URL format to psycopg format (remove +psycopg dialect)
    psycopg_url = settings.POSTGRES_URL.replace("postgresql+psycopg://", "postgresql://")
    return PostgresSaver.from_conn_string(psycopg_url)


# ==================== Database Initialization ====================

def init_postgres_db():
    """
    Initialize PostgreSQL database.
    Creates all tables defined in SQLAlchemy models.

    Call this at application startup in main.py
    """
    try:
        logger.info("Initializing PostgreSQL database...")

        # Import all models to ensure they're registered with Base
        # NOTE: Imports are inside function to avoid circular imports
        from services.auth.models import User  # noqa: F401
        from services.configmanager.models import Configuration  # noqa: F401
        from services.parser.models import Symbol, MacroDefinition, MacroCall  # noqa: F401
        from services.chatbot.models import Conversation  # noqa: F401

        # Create all application tables
        Base.metadata.create_all(bind=postgres_engine)
        logger.info("✓ Application tables created/verified successfully")

        # Setup LangGraph checkpoint tables
        # Convert SQLAlchemy URL format to psycopg format (remove +psycopg dialect)
        psycopg_url = settings.POSTGRES_URL.replace("postgresql+psycopg://", "postgresql://")
        with PostgresSaver.from_conn_string(psycopg_url) as checkpointer:
            checkpointer.setup()
        logger.info("✓ LangGraph checkpoint tables created/verified successfully")

        logger.info("PostgreSQL database initialization complete")
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL database: {e}")
        raise


# def init_neo4j_db():
#     """
#     Initialize Neo4j database.
#     Creates constraints and indexes for optimal performance.
    
#     Call this at application startup in main.py
#     """
#     try:
#         with neo4j_connection.get_session() as session:
#             # Create constraints (ensures uniqueness and creates index)
#             constraints = [
#                 "CREATE CONSTRAINT config_id_unique IF NOT EXISTS FOR (c:Config) REQUIRE c.id IS UNIQUE",
#                 "CREATE CONSTRAINT log_id_unique IF NOT EXISTS FOR (l:Log) REQUIRE l.id IS UNIQUE",
#                 "CREATE CONSTRAINT rule_id_unique IF NOT EXISTS FOR (r:Rule) REQUIRE r.id IS UNIQUE",
#             ]
            
#             for constraint in constraints:
#                 session.run(constraint)
            
#             # Create additional indexes for performance
#             indexes = [
#                 "CREATE INDEX config_type_idx IF NOT EXISTS FOR (c:Config) ON (c.type)",
#                 "CREATE INDEX log_timestamp_idx IF NOT EXISTS FOR (l:Log) ON (l.timestamp)",
#             ]
            
#             for index in indexes:
#                 session.run(index)
            
#             logger.info("Neo4j constraints and indexes created successfully")
#     except Exception as e:
#         logger.error(f"Failed to initialize Neo4j database: {e}")
#         raise


def close_databases():
    """
    Close all database connections.
    Call this at application shutdown in main.py
    """
    try:
        postgres_engine.dispose()
        logger.info("PostgreSQL connections closed")
    except Exception as e:
        logger.error(f"Error closing PostgreSQL: {e}")
    
    try:
        neo4j_connection.close()
        logger.info("Neo4j connections closed")
    except Exception as e:
        logger.error(f"Error closing Neo4j: {e}")


# ==================== Utility Functions ====================

def get_postgres_session() -> Session:
    """
    Get a PostgreSQL session outside of FastAPI context.
    Useful for background tasks, scripts, or testing.
    
    Remember to close the session manually:
        db = get_postgres_session()
        try:
            # Your code here
            db.commit()
        finally:
            db.close()
    """
    return PostgresSessionLocal()


def get_neo4j_session() -> Neo4jSession:
    """
    Get a Neo4j session outside of FastAPI context.
    Useful for background tasks, scripts, or testing.
    
    Remember to close the session manually:
        neo4j = get_neo4j_session()
        try:
            # Your code here
        finally:
            neo4j.close()
    """
    return neo4j_connection.get_session()


# ==================== Health Check ====================

def check_postgres_health() -> bool:
    """Check if PostgreSQL is accessible"""
    try:
        db = PostgresSessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
        return False


def check_neo4j_health() -> bool:
    """Check if Neo4j is accessible"""
    try:
        neo4j_connection.verify_connectivity()
        return True
    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")
        return False


def check_database_health() -> dict:
    """
    Check health of all databases.
    Returns dict with status of each database.
    """
    return {
        "postgres": check_postgres_health(),
        "neo4j": check_neo4j_health()
    }
