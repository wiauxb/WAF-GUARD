# shared/config.py
"""
Application configuration.
Loads settings from environment variables (provided by Docker Compose).
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
import logging
import sys

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All values are provided by Docker Compose environment variables.
    """
    
    # ==================== Application Settings ====================
    APP_NAME: str = "WAF-GUARD"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    WAF_URL: str

    
    # ==================== PostgreSQL Settings ====================
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "postgres"  # Docker Compose service name
    POSTGRES_PORT: int = 5432
    POSTGRES_DB_CWAF: str

    # Connection pool settings
    POSTGRES_POOL_SIZE: int = 20
    POSTGRES_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False  # Set to True to log all SQL queries
    DELETE_BATCH_SIZE: int = 1000
    
    @property
    def POSTGRES_URL(self) -> str:
        """Construct PostgreSQL connection URL"""
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB_CWAF}"
        )
    
    # ==================== Neo4j Settings ====================
    NEO4J_URL: str = "bolt://neo4j:7687"  # Docker Compose service name
    NEO4J_URL_PROD: str = "bolt+ssc://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str
    NEO4J_DATABASE: str = "neo4j"  # Default database name
    NEO4J_POOL_SIZE: int = 50
    NEO4J_ENCRYPTED: bool = False  # Set to True for production with SSL
    
    # ==================== Authentication Settings ====================
    JWT_SECRET_KEY: str="my_secret_key"  # Used for JWT token signing
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ==================== File Storage Settings ====================
    STORAGE_ROOT: str = "/app/storage"  # Container path
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_CONFIG_EXTENSIONS: list[str] = [".conf", ".config", ".txt", ".rules"]
    
    # ==================== LLM Settings ====================
    OPENAI_API_KEY: Optional[str] = None
    LLM_API_URL: Optional[str] = None
    LLM_MODEL: str = "gpt-4"
    LLM_MAX_TOKENS: int = 2000
    LLM_TEMPERATURE: float = 0.7

    # Chatbot-specific LLM settings (LangGraph)
    OPENAI_MODEL: str = "gpt-4o-mini"  # Model for chatbot agent
    CHATBOT_TEMPERATURE: float = 0.7  # Temperature for chatbot responses
    
    # ==================== API Settings ====================
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["*"]  # Configure properly for production
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]
    
    # ==================== Rate Limiting ====================
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # ==================== Logging Settings ====================
    LOG_FILE: Optional[str] = "/app/logs/app.log"
    LOG_ROTATION: str = "500 MB"
    LOG_RETENTION: str = "30 days"
    
    class Config:
        # No .env file - all values from Docker environment
        case_sensitive = True
        # You can still use .env file for local development if needed
        # env_file = ".env"


# Create settings instance
settings = Settings()


# ==================== Logging Configuration ====================

class InterceptHandler(logging.Handler):
    def emit(self, record):
        # get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # find caller from where originated the logged message
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging():
    # intercept everything at the root logger
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(settings.LOG_LEVEL)

    # remove every other logger's handlers
    # and propagate to root logger
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # configure loguru
    logger.configure(handlers=[{"sink": sys.stdout, "serialize": False}])


# ==================== Storage Initialization ====================

def ensure_storage_directories():
    """
    Ensure all necessary storage directories exist.
    Call this at application startup in main.py

    Note: Individual config directories (config_{id}) are created dynamically
    by ConfigFileStorage when configurations are uploaded.
    """
    storage_root = Path(settings.STORAGE_ROOT)

    directories = [
        storage_root / "configs",
        storage_root / "logs",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(__name__)
    logger.info(f"Storage directories initialized at {storage_root}")