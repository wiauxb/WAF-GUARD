# main.py
"""
FastAPI application entry point.
"""
import logging
import httpx
import torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


from shared.config import settings, setup_logging, ensure_storage_directories
from shared.database import (
    close_databases,
    check_database_health,
    init_postgres_db
)
from api.routes import auth, configs, parser, analysis, chatbot, logs
from services.logs.fp_classifier import FPClassifier
# from api.middleware import LoggingMiddleware



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    try:
        # Initialize storage directories
        ensure_storage_directories()

        # Initialize databases
        init_postgres_db()

        # Check database health
        health = check_database_health()
        logger.info(f"Database health check: {health}")

        if not all(health.values()):
            logger.warning("Some databases are not healthy!")

        # Load the local FP/TP log classifier once. Not versioned (571 MB) -- may be absent
        # on a fresh clone, so a missing model degrades /logs/classify to a 503 rather than
        # crashing the whole backend.
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_dir = settings.FP_MODEL_DIR_RESOLVED
        try:
            logger.info(f"Loading FP/TP log classifier from {model_dir} on {device}")
            app.state.fp_classifier = FPClassifier(
                model_dir, device, max_seq_len=settings.LOG_CLASSIFIER_MAX_SEQ_LEN
            )
            logger.info("FP/TP log classifier loaded")
        except Exception as exc:
            app.state.fp_classifier = None
            logger.warning(
                f"FP/TP log classifier unavailable at {model_dir} -- /logs/classify will "
                f"503 until it is populated (see README): {exc}"
            )
        app.state.log_http_client = httpx.AsyncClient(timeout=30.0)

        logger.info("Application startup done")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield  # Application runs here

    # Shutdown
    # logger.info("Shutting down application")
    await app.state.log_http_client.aclose()
    close_databases()
    # logger.info("Application shutdown complete")

# # Setup logging first
logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

uvicorn_logger = logging.getLogger("uvicorn")
info_handler = logging.getLogger("INFO")
# info_handler.handlers.clear()
# uvicorn_logger.handlers.clear()
info_handler.propagate = False
uvicorn_logger.propagate = False
logger = logging.getLogger(__name__)


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Web Application Firewall configuration management and analysis platform",
    lifespan=lifespan,
    debug=settings.DEBUG
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Add custom middleware
# app.add_middleware(LoggingMiddleware)

# Register API routes
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(configs.router, prefix=settings.API_V1_PREFIX)
app.include_router(parser.router, prefix=settings.API_V1_PREFIX)
app.include_router(analysis.router, prefix=settings.API_V1_PREFIX)
app.include_router(chatbot.router, prefix=settings.API_V1_PREFIX)
app.include_router(logs.router, prefix=settings.API_V1_PREFIX)




@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
def health():
    """Health check endpoint"""
    db_health = check_database_health()
    
    return {
        "status": "healthy" if all(db_health.values()) else "degraded",
        "databases": db_health,
        "version": settings.APP_VERSION
    }

