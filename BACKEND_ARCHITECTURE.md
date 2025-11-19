# WAF-GUARD Backend Architecture

## Overview

This document describes the backend architecture for WAF-GUARD, organized as a **modular monolith** with clear separation of concerns. The backend consolidates the analyzer, chatbot, and API services into a unified application while maintaining modularity for easy maintenance and potential future extraction.

## Architecture Principles

1. **Layered Architecture**: Clear separation between API, Services, and Data Access
2. **Centralized Data Access**: Single source of truth for all database operations
3. **Dependency Injection**: Loose coupling through constructor injection
4. **Domain-Driven Design**: Business logic in services, data access separated
5. **Shared Infrastructure**: Common concerns (auth, config, database) centralized

## Why Monolith Instead of Microservices?

We chose a unified backend container because:
- ✅ **Tight coupling**: Analyzer populates databases → Chatbot queries them → API serves them
- ✅ **Same tech stack**: All Python + FastAPI
- ✅ **Shared databases**: All services use the same Neo4j and PostgreSQL instances
- ✅ **Simpler deployment**: One container, one process, easier orchestration
- ✅ **Easier development**: No inter-service communication complexity
- ✅ **Reduced overhead**: No service discovery, no API gateways
- ✅ **Eliminate code duplication**: Database connections and utilities truly shared

The modular structure still allows easy extraction to separate services if needed in the future.

## Complete Folder Structure

```
backend/
├── Dockerfile
├── main.py                          # Application entry point
├── requirements.txt
├── .env
└── src/
    ├── common/                      # Shared infrastructure & utilities
    │   ├── __init__.py
    │   ├── config.py                # Application settings (Pydantic)
    │   │
    │   ├── auth/                    # Authentication & authorization
    │   │   ├── __init__.py
    │   │   ├── dependencies.py      # FastAPI dependencies (get_current_user)
    │   │   ├── jwt.py               # JWT token creation/validation
    │   │   └── password.py          # Password hashing (bcrypt)
    │   │
    │   ├── database/                # All database-related code
    │   │   ├── __init__.py
    │   │   │
    │   │   ├── connections/         # Connection management (infrastructure)
    │   │   │   ├── __init__.py
    │   │   │   ├── neo4j.py         # Neo4j driver singleton
    │   │   │   └── postgres.py      # PostgreSQL connection pools
    │   │   │
    │   │   └── access/              # Data access layer (query logic)
    │   │       ├── __init__.py
    │   │       ├── configs.py       # Config CRUD & queries
    │   │       ├── directives.py    # Directive queries (Neo4j)
    │   │       ├── users.py         # User authentication & management
    │   │       ├── threads.py       # Chatbot thread management
    │   │       └── files.py         # File storage operations
    │   │
    │   ├── models/                  # Shared domain models
    │   │   ├── __init__.py
    │   │   ├── base.py              # Base classes (timestamps, etc.)
    │   │   └── domain.py            # Business entities (User, Config, Directive, Thread, Message)
    │   │
    │   └── utils/                   # Shared utilities
    │       ├── __init__.py
    │       └── file_utils.py        # File extraction, management
    │
    ├── api/                         # HTTP/API layer
    │   ├── __init__.py
    │   ├── main.py                  # FastAPI app creation & configuration
    │   ├── dependencies.py          # Dependency injection setup
    │   │
    │   ├── schemas/                 # API request/response models (DTOs)
    │   │   ├── __init__.py
    │   │   ├── requests.py          # API request schemas
    │   │   └── responses.py         # API response schemas
    │   │
    │   └── routers/                 # API endpoints (one file per resource)
    │       ├── __init__.py
    │       ├── auth.py              # POST /auth/login, /auth/register
    │       ├── configs.py           # Config CRUD endpoints
    │       ├── analyzer.py          # POST /analyze/{config_id}
    │       ├── chatbot.py           # POST /chat, thread management
    │       ├── cypher.py            # POST /cypher (Neo4j query execution)
    │       ├── directives.py        # GET /directives
    │       ├── nodes.py             # Neo4j node operations
    │       └── storage.py           # File upload/download
    │
    └── services/                    # Business logic layer
        ├── __init__.py
        │
        ├── analyzer/                # Config analysis service
        │   ├── __init__.py
        │   ├── service.py           # Main analysis orchestration
        │   │
        │   ├── models/              # Analyzer-specific models
        │   │   ├── __init__.py
        │   │   ├── context.py       # ParseContext (parsing state)
        │   │   └── macro.py         # Macro handling
        │   │
        │   └── parsers/             # Parsing implementations
        │       ├── __init__.py
        │       ├── apache.py        # Apache HTTPD directive parser
        │       ├── modsec.py        # ModSecurity rule parser
        │       └── rule_parsing.py  # Rule parsing utilities
        │
        └── chatbot/                 # AI chatbot service
            ├── __init__.py
            ├── service.py           # Chat orchestration logic
            │
            ├── models/              # Chatbot-specific models
            │   ├── __init__.py
            │   └── graph_state.py   # LangGraph state models
            │
            └── graph/               # LangGraph implementation
                ├── __init__.py
                ├── ui_graph.py      # Main graph definition
                └── base_graph.py    # Base graph class
```

## Layer Responsibilities

### 1. Common Layer (`common/`)

**Purpose**: Shared infrastructure and cross-cutting concerns used by all services.

#### `common/config.py`
Application configuration using Pydantic Settings for type-safe, validated configuration.

```python
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    # Environment
    environment: Literal["dev", "prod"] = "dev"

    # Neo4j
    neo4j_url: str
    neo4j_url_prod: str
    neo4j_user: str
    neo4j_password: str

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str
    postgres_password: str
    postgres_db_cwaf: str = "cwaf"
    postgres_db_files: str = "files"
    postgres_db_chatbot: str = "chatbot"

    # JWT Authentication
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30

    # API URLs
    api_url: str = "http://localhost:8000"
    waf_url: str

    class Config:
        env_file = ".env"
        case_sensitive = False

# Singleton instance
settings = Settings()
```

**Usage:**
```python
from common.config import settings

# Type-safe access
neo4j_url = settings.neo4j_url
is_production = settings.environment == "prod"
```

#### `common/auth/`
Centralized authentication - **not a service**, it's infrastructure.

**Key concept**: Authentication is a cross-cutting concern, not business logic. All endpoints that need auth use the same dependencies.

```python
# common/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from common.auth.jwt import verify_token
from common.models.domain import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Reusable authentication dependency"""
    user = verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return user
```

**Usage in any router:**
```python
from common.auth.dependencies import get_current_user

@router.get("/configs")
async def get_configs(current_user: User = Depends(get_current_user)):
    # If we get here, user is authenticated
    ...
```

#### `common/database/`

The database package is organized into two subpackages:

##### `connections/` - Infrastructure Layer
Low-level connection management. Handles connection pools, driver singletons, and environment-specific configuration.

```python
# common/database/connections/postgres.py
from psycopg_pool import ConnectionPool
from common.config import settings

_pools = {}

def get_postgres_pool(db_name: str) -> ConnectionPool:
    """
    Get or create a connection pool for a PostgreSQL database.

    Args:
        db_name: Database name ('cwaf', 'files', or 'chatbot')

    Returns:
        ConnectionPool instance
    """
    if db_name not in _pools:
        db_attr = f"postgres_db_{db_name}"
        database = getattr(settings, db_attr)

        conninfo = (
            f"host={settings.postgres_host} "
            f"port={settings.postgres_port} "
            f"dbname={database} "
            f"user={settings.postgres_user} "
            f"password={settings.postgres_password}"
        )

        # Production uses SSL
        if settings.environment == "prod":
            conninfo += " sslmode=require"

        _pools[db_name] = ConnectionPool(
            conninfo,
            min_size=1,
            max_size=10
        )

    return _pools[db_name]
```

```python
# common/database/connections/neo4j.py
from neo4j import GraphDatabase
from common.config import settings

_driver = None

def get_neo4j_driver():
    """Get or create Neo4j driver singleton"""
    global _driver
    if _driver is None:
        url = (settings.neo4j_url_prod
               if settings.environment == "prod"
               else settings.neo4j_url)

        _driver = GraphDatabase.driver(
            url,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

    return _driver

def close_neo4j_driver():
    """Close Neo4j driver (call on shutdown)"""
    global _driver
    if _driver:
        _driver.close()
        _driver = None
```

##### `access/` - Data Access Layer
High-level query logic. All database queries live here - this is the **single source of truth** for data operations.

**Key principle**: Services never write SQL or Cypher queries. They call methods from the access layer.

```python
# common/database/access/configs.py
from typing import List, Optional
from common.database.connections.neo4j import get_neo4j_driver
from common.database.connections.postgres import get_postgres_pool
from common.models.domain import Config, Directive

class ConfigAccess:
    """
    Data access layer for WAF configurations.
    Handles both PostgreSQL (config metadata) and Neo4j (directive graph).
    """

    def __init__(self):
        self.neo4j = get_neo4j_driver()
        self.postgres_pool = get_postgres_pool('files')

    def get_by_id(self, config_id: int) -> Optional[Config]:
        """Fetch config by ID from PostgreSQL"""
        with self.postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, content, uploaded_at FROM configs WHERE id = %s",
                    (config_id,)
                )
                row = cur.fetchone()
                if not row:
                    return None

                return Config(
                    id=row[0],
                    name=row[1],
                    content=row[2],
                    uploaded_at=row[3]
                )

    def get_all(self) -> List[Config]:
        """Get all configs"""
        with self.postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, content, uploaded_at FROM configs ORDER BY uploaded_at DESC"
                )
                return [
                    Config(id=row[0], name=row[1], content=row[2], uploaded_at=row[3])
                    for row in cur.fetchall()
                ]

    def create(self, name: str, content: str) -> Config:
        """Create new config"""
        with self.postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO configs (name, content) VALUES (%s, %s) RETURNING id, uploaded_at",
                    (name, content)
                )
                row = cur.fetchone()
                conn.commit()

                return Config(
                    id=row[0],
                    name=name,
                    content=content,
                    uploaded_at=row[1]
                )

    def get_directives(self, config_id: int) -> List[Directive]:
        """Fetch directives from Neo4j graph"""
        with self.neo4j.session() as session:
            result = session.run(
                """
                MATCH (c:Config {id: $config_id})-[:CONTAINS]->(d:Directive)
                RETURN d.id as id, d.type as type, d.value as value
                ORDER BY d.id
                """,
                config_id=config_id
            )
            return [
                Directive(
                    id=record["id"],
                    type=record["type"],
                    value=record["value"]
                )
                for record in result
            ]

    def save_directives_to_graph(self, config_id: int, directives: List[Directive]):
        """Save parsed directives to Neo4j (batch operation)"""
        with self.neo4j.session() as session:
            # Clear existing directives
            session.run(
                "MATCH (c:Config {id: $id})-[r:CONTAINS]->() DELETE r",
                id=config_id
            )

            # Batch insert new directives
            session.run(
                """
                UNWIND $directives as dir
                MATCH (c:Config {id: $config_id})
                CREATE (d:Directive {id: dir.id, type: dir.type, value: dir.value})
                CREATE (c)-[:CONTAINS]->(d)
                """,
                config_id=config_id,
                directives=[{"id": d.id, "type": d.type, "value": d.value} for d in directives]
            )

    def delete(self, config_id: int) -> bool:
        """Delete config from both databases"""
        # Delete from Neo4j first
        with self.neo4j.session() as session:
            session.run(
                "MATCH (c:Config {id: $id}) DETACH DELETE c",
                id=config_id
            )

        # Delete from PostgreSQL
        with self.postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM configs WHERE id = %s", (config_id,))
                deleted = cur.rowcount > 0
                conn.commit()
                return deleted
```

**Why this is better than per-service repositories:**
- ✅ No duplication - `get_config()` exists in ONE place
- ✅ Both analyzer and chatbot use the same `ConfigAccess`
- ✅ Easy to optimize queries - change once, all services benefit
- ✅ Consistent data access patterns

#### `common/models/`

**Domain models** - the true representation of business entities. These are shared by all services.

```python
# common/models/domain.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class User(BaseModel):
    """User account"""
    id: int
    username: str
    email: str
    hashed_password: str
    created_at: datetime
    is_active: bool = True

class Config(BaseModel):
    """WAF Configuration"""
    id: int
    name: str
    content: str
    uploaded_at: datetime
    analysis_status: Optional[str] = None

class Directive(BaseModel):
    """Apache/ModSecurity directive"""
    id: str
    type: str  # e.g., "SecRule", "ServerName", "VirtualHost"
    value: str
    line_number: Optional[int] = None

class Thread(BaseModel):
    """Chatbot conversation thread"""
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime

class Message(BaseModel):
    """Chat message"""
    id: int
    thread_id: int
    role: str  # "user" or "assistant"
    content: str
    created_at: datetime
```

### 2. API Layer (`api/`)

**Purpose**: HTTP interface - handles requests/responses, validation, and routing.

#### `api/main.py`
FastAPI application setup and configuration.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import auth, configs, analyzer, chatbot, cypher, directives, nodes, storage
from common.database.connections.neo4j import close_neo4j_driver

app = FastAPI(
    title="WAF-GUARD API",
    description="Unified API for WAF configuration management, analysis, and AI assistance",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8002"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(configs.router, prefix="/configs", tags=["Configs"])
app.include_router(analyzer.router, prefix="/analyze", tags=["Analyzer"])
app.include_router(chatbot.router, prefix="/chat", tags=["Chatbot"])
app.include_router(cypher.router, prefix="/cypher", tags=["Cypher"])
app.include_router(directives.router, prefix="/directives", tags=["Directives"])
app.include_router(nodes.router, prefix="/nodes", tags=["Nodes"])
app.include_router(storage.router, prefix="/storage", tags=["Storage"])

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    close_neo4j_driver()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

#### `api/schemas/`
**API contracts** - Request and response models (DTOs - Data Transfer Objects).

These are **different from domain models** because:
- API schemas have different validation rules
- They may expose only subset of fields (security)
- They may combine multiple domain models
- They're versioned with the API

```python
# api/schemas/requests.py
from pydantic import BaseModel, EmailStr, constr

class UserRegisterRequest(BaseModel):
    """User registration request"""
    username: constr(min_length=3, max_length=50)
    email: EmailStr
    password: constr(min_length=8)

class ConfigCreateRequest(BaseModel):
    """Config creation request"""
    name: str
    content: str

class CypherQueryRequest(BaseModel):
    """Cypher query execution request"""
    query: str
    parameters: dict = {}

class ChatMessageRequest(BaseModel):
    """Chat message request"""
    thread_id: int
    message: str
```

```python
# api/schemas/responses.py
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from common.models.domain import Config, User

class UserResponse(BaseModel):
    """User response (no password!)"""
    id: int
    username: str
    email: str
    created_at: datetime

    @classmethod
    def from_domain(cls, user: User):
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at
        )

class ConfigResponse(BaseModel):
    """Config response"""
    id: int
    name: str
    uploaded_at: datetime
    analysis_status: Optional[str]

    @classmethod
    def from_domain(cls, config: Config):
        return cls(
            id=config.id,
            name=config.name,
            uploaded_at=config.uploaded_at,
            analysis_status=config.analysis_status
        )

class AnalysisResponse(BaseModel):
    """Analysis result response"""
    config_id: int
    directive_count: int
    status: str
```

#### `api/routers/`
API endpoints - one file per resource. Routers should be **thin** - they delegate to services.

```python
# api/routers/configs.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from api.dependencies import get_config_access
from api.schemas.requests import ConfigCreateRequest
from api.schemas.responses import ConfigResponse
from common.database.access.configs import ConfigAccess
from common.auth.dependencies import get_current_user
from common.models.domain import User

router = APIRouter()

@router.get("/", response_model=List[ConfigResponse])
async def get_all_configs(
    current_user: User = Depends(get_current_user),
    config_access: ConfigAccess = Depends(get_config_access)
):
    """Get all configs"""
    configs = config_access.get_all()
    return [ConfigResponse.from_domain(c) for c in configs]

@router.get("/{config_id}", response_model=ConfigResponse)
async def get_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    config_access: ConfigAccess = Depends(get_config_access)
):
    """Get config by ID"""
    config = config_access.get_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return ConfigResponse.from_domain(config)

@router.post("/", response_model=ConfigResponse)
async def create_config(
    request: ConfigCreateRequest,
    current_user: User = Depends(get_current_user),
    config_access: ConfigAccess = Depends(get_config_access)
):
    """Create new config"""
    config = config_access.create(request.name, request.content)
    return ConfigResponse.from_domain(config)
```

```python
# api/routers/analyzer.py
from fastapi import APIRouter, Depends, HTTPException
from api.dependencies import get_analyzer_service
from api.schemas.responses import AnalysisResponse
from services.analyzer.service import AnalyzerService
from common.auth.dependencies import get_current_user
from common.models.domain import User

router = APIRouter()

@router.post("/{config_id}", response_model=AnalysisResponse)
async def analyze_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    analyzer: AnalyzerService = Depends(get_analyzer_service)
):
    """
    Analyze Apache/ModSecurity configuration.
    Parses directives and populates Neo4j graph.
    """
    try:
        directives = analyzer.analyze_config(config_id)
        return AnalysisResponse(
            config_id=config_id,
            directive_count=len(directives),
            status="completed"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
```

#### `api/dependencies.py`
**Dependency Injection** - Factory functions that create and wire up objects.

```python
# api/dependencies.py
from fastapi import Depends
from common.database.access.configs import ConfigAccess
from common.database.access.users import UserAccess
from common.database.access.threads import ThreadAccess
from services.analyzer.service import AnalyzerService
from services.chatbot.service import ChatbotService

# Data access factories
def get_config_access() -> ConfigAccess:
    """Create ConfigAccess instance"""
    return ConfigAccess()

def get_user_access() -> UserAccess:
    """Create UserAccess instance"""
    return UserAccess()

def get_thread_access() -> ThreadAccess:
    """Create ThreadAccess instance"""
    return ThreadAccess()

# Service factories
def get_analyzer_service(
    config_access: ConfigAccess = Depends(get_config_access)
) -> AnalyzerService:
    """Create AnalyzerService with dependencies"""
    return AnalyzerService(config_access)

def get_chatbot_service(
    config_access: ConfigAccess = Depends(get_config_access),
    thread_access: ThreadAccess = Depends(get_thread_access)
) -> ChatbotService:
    """Create ChatbotService with dependencies"""
    return ChatbotService(config_access, thread_access)
```

**Why Dependency Injection?**
1. ✅ **Easy testing**: Override dependencies with mocks
2. ✅ **Loose coupling**: Routers don't know how to create services
3. ✅ **Centralized configuration**: Change wiring in one place
4. ✅ **Reusability**: Same pattern for all endpoints

### 3. Services Layer (`services/`)

**Purpose**: Business logic - orchestrates operations, implements domain rules.

**Key principles:**
- Services are **stateless** - receive dependencies via constructor
- Services contain **pure business logic** - no HTTP concerns
- Services **never write queries** - use data access layer
- Services are **framework-independent** - could work with Flask, Django, CLI

#### `services/analyzer/`

```python
# services/analyzer/service.py
from typing import List
from common.database.access.configs import ConfigAccess
from common.models.domain import Config, Directive
from services.analyzer.parsers.apache import ApacheParser
from services.analyzer.parsers.modsec import ModSecParser

class AnalyzerService:
    """
    Configuration analysis service.
    Parses Apache HTTPD and ModSecurity configurations.
    """

    def __init__(self, config_access: ConfigAccess):
        self.config_access = config_access
        self.apache_parser = ApacheParser()
        self.modsec_parser = ModSecParser()

    def analyze_config(self, config_id: int) -> List[Directive]:
        """
        Analyze a configuration file.

        Args:
            config_id: ID of config to analyze

        Returns:
            List of parsed directives

        Raises:
            ValueError: If config not found
        """
        # Get config data
        config = self.config_access.get_by_id(config_id)
        if not config:
            raise ValueError(f"Config {config_id} not found")

        # Business logic: Parse configuration
        apache_directives = self.apache_parser.parse(config.content)
        modsec_directives = self.modsec_parser.parse(config.content)

        all_directives = apache_directives + modsec_directives

        # Save to graph database
        self.config_access.save_directives_to_graph(config_id, all_directives)

        return all_directives
```

**Service-specific models** (internal to analyzer):

```python
# services/analyzer/models/context.py
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ParseContext:
    """
    Maintains state during configuration parsing.
    NOT shared with other services - internal to analyzer.
    """
    current_file: str
    line_number: int
    scope_stack: List[str]
    variables: Dict[str, str]
    in_virtual_host: bool = False
```

#### `services/chatbot/`

```python
# services/chatbot/service.py
from typing import List, Dict
from common.database.access.configs import ConfigAccess
from common.database.access.threads import ThreadAccess
from common.models.domain import Message
from services.chatbot.graph.ui_graph import UIGraph

class ChatbotService:
    """
    AI chatbot service using LangGraph.
    Provides WAF configuration assistance.
    """

    def __init__(
        self,
        config_access: ConfigAccess,
        thread_access: ThreadAccess
    ):
        self.config_access = config_access
        self.thread_access = thread_access
        self.graph = UIGraph()

    def chat(
        self,
        thread_id: int,
        user_message: str,
        user_id: int
    ) -> str:
        """
        Process chat message and generate response.

        Args:
            thread_id: Conversation thread ID
            user_message: User's message
            user_id: User ID

        Returns:
            Assistant's response
        """
        # Verify thread belongs to user
        thread = self.thread_access.get_by_id(thread_id)
        if not thread or thread.user_id != user_id:
            raise ValueError("Thread not found or access denied")

        # Save user message
        self.thread_access.add_message(thread_id, "user", user_message)

        # Get conversation context
        history = self.thread_access.get_messages(thread_id)

        # Business logic: Generate AI response
        response = self.graph.invoke(
            message=user_message,
            thread_id=thread_id,
            history=history
        )

        # Save assistant message
        self.thread_access.add_message(thread_id, "assistant", response)

        return response
```

## Complete Data Flow Example

Let's trace a request through all layers:

### Request: Analyze a Config

```
1. HTTP Request
   POST /analyze/123
   Authorization: Bearer eyJ0eXAi...

   ↓

2. API Router (api/routers/analyzer.py)
   - Validates JWT token (via get_current_user dependency)
   - Injects AnalyzerService (via get_analyzer_service dependency)
   - Calls service.analyze_config(123)

   ↓

3. Service Layer (services/analyzer/service.py)
   - Gets config from data access: config_access.get_by_id(123)
   - Parses config (business logic)
   - Saves to graph: config_access.save_directives_to_graph(123, directives)

   ↓

4. Data Access Layer (common/database/access/configs.py)
   - Executes PostgreSQL query to get config
   - Executes Neo4j Cypher to save directives
   - Returns domain models

   ↓

5. Connection Layer (common/database/connections/)
   - Provides connection pool/driver
   - Handles connection lifecycle

   ↓

6. Database
   - PostgreSQL: Config metadata
   - Neo4j: Directive graph
```

## Model Organization Strategy

### Three Types of Models:

#### 1. Domain Models (`common/models/domain.py`)
- **Purpose**: Business entities - true representation
- **Shared by**: All services
- **Examples**: `User`, `Config`, `Directive`, `Thread`, `Message`

#### 2. API Schemas (`api/schemas/`)
- **Purpose**: API contracts - request/response shapes
- **Used in**: API layer only
- **Examples**: `ConfigCreateRequest`, `ConfigResponse`, `UserResponse`
- **Why separate?**: Different validation, security filtering, versioning

#### 3. Service Models (`services/{service}/models/`)
- **Purpose**: Internal service logic
- **Used in**: Single service only
- **Examples**: `ParseContext`, `MacroState`, `GraphState`

### Decision Tree: Where Does a Model Go?

```
Is this model used by MULTIPLE services?
│
├─ YES → common/models/domain.py
│         Examples: User, Config, Thread, Directive
│
└─ NO → Is it used in API requests/responses?
    │
    ├─ YES → api/schemas/
    │         Examples: ConfigUploadRequest, DirectiveResponse
    │
    └─ NO → services/{service_name}/models/
              Examples: ParseContext, DirectiveFactory, GraphState
```

## Import Patterns

### ✅ Correct Imports

```python
# Configuration
from common.config import settings

# Authentication
from common.auth.dependencies import get_current_user
from common.auth.jwt import create_access_token
from common.auth.password import hash_password

# Database connections
from common.database.connections.neo4j import get_neo4j_driver
from common.database.connections.postgres import get_postgres_pool

# Data access
from common.database.access.configs import ConfigAccess
from common.database.access.users import UserAccess
from common.database.access.directives import DirectiveAccess

# Domain models
from common.models.domain import User, Config, Directive, Thread

# Services
from services.analyzer.service import AnalyzerService
from services.chatbot.service import ChatbotService

# API schemas
from api.schemas.requests import ConfigCreateRequest
from api.schemas.responses import ConfigResponse

# Dependencies
from api.dependencies import get_analyzer_service
```

### ❌ Wrong Patterns (Anti-patterns)

```python
# DON'T: Services importing from routers
from api.routers.configs import some_function  # ❌ Reverse dependency

# DON'T: Services accessing database directly
from neo4j import GraphDatabase
driver = GraphDatabase.driver(...)  # ❌ Use data access layer

# DON'T: Common importing from services
# In common/database/access/configs.py:
from services.analyzer.service import AnalyzerService  # ❌ Circular dependency

# DON'T: Creating connections in services
# In services/analyzer/service.py:
self.conn = psycopg.connect(...)  # ❌ Use connection layer
```

## Dependency Direction Rules

```
┌─────────────────────────────────────────────────────────┐
│                  Dependency Flow                         │
│                                                          │
│  api/ ──→ services/ ──→ common/database/access/         │
│    ↓         ↓                    ↓                      │
│  schemas/  models/           models/                     │
│           (service)          (domain)                    │
│                                   ↓                      │
│                        common/database/connections/      │
│                                   ↓                      │
│                            (external libs)               │
└─────────────────────────────────────────────────────────┘
```

**Rules:**
1. ✅ API layer can import from Services and Common
2. ✅ Services can import from Common (database/access, models, utils)
3. ✅ Data Access can import from Connections and Models
4. ❌ **Reverse imports forbidden** (common should NEVER import from services)
5. ❌ **No circular dependencies** between packages

## Testing Strategy

### Unit Tests

**Services** - Mock data access layer:
```python
# tests/services/test_analyzer.py
from unittest.mock import Mock
from services.analyzer.service import AnalyzerService
from common.models.domain import Config

def test_analyze_config():
    # Mock data access
    mock_access = Mock()
    mock_access.get_by_id.return_value = Config(
        id=1,
        name="test.conf",
        content="ServerName example.com",
        uploaded_at=datetime.now()
    )

    # Test service
    service = AnalyzerService(mock_access)
    directives = service.analyze_config(1)

    # Assertions
    assert len(directives) > 0
    assert mock_access.get_by_id.called_with(1)
    assert mock_access.save_directives_to_graph.called
```

**Data Access** - Use test database:
```python
# tests/database/test_config_access.py
import pytest
from common.database.access.configs import ConfigAccess

@pytest.fixture
def test_db():
    # Setup test database
    ...

def test_get_by_id(test_db):
    access = ConfigAccess()
    config = access.get_by_id(1)
    assert config.id == 1
```

**API** - Mock services:
```python
# tests/api/test_analyzer_router.py
from fastapi.testclient import TestClient
from api.main import app
from api.dependencies import get_analyzer_service

def test_analyze_endpoint():
    # Override dependency with mock
    mock_service = Mock()
    mock_service.analyze_config.return_value = [...]

    app.dependency_overrides[get_analyzer_service] = lambda: mock_service

    client = TestClient(app)
    response = client.post("/analyze/1")

    assert response.status_code == 200
    assert mock_service.analyze_config.called
```

### Integration Tests

Test full flow: API → Service → Data Access → Database

```python
# tests/integration/test_full_flow.py
def test_config_analysis_flow(test_containers):
    # Uses real databases (via Docker testcontainers)
    client = TestClient(app)

    # Upload config
    response = client.post("/configs", json={
        "name": "test.conf",
        "content": "ServerName example.com"
    })
    config_id = response.json()["id"]

    # Analyze
    response = client.post(f"/analyze/{config_id}")
    assert response.status_code == 200
    assert response.json()["directive_count"] > 0

    # Verify in database
    access = ConfigAccess()
    directives = access.get_directives(config_id)
    assert len(directives) > 0
```

## Environment Configuration

### Development (`.env`)
```env
ENVIRONMENT=dev

# Neo4j
NEO4J_URL=bolt://localhost:7687
NEO4J_URL_PROD=bolt+s://neo4j.production.com:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=waf_user
POSTGRES_PASSWORD=password
POSTGRES_DB_CWAF=cwaf
POSTGRES_DB_FILES=files
POSTGRES_DB_CHATBOT=chatbot

# JWT
JWT_SECRET_KEY=dev-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30

# API
API_URL=http://localhost:8000
WAF_URL=http://localhost:9090
```

### Production
```env
ENVIRONMENT=prod

# Neo4j (SSL enabled)
NEO4J_URL_PROD=bolt+s://neo4j-prod.example.com:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<strong-password>

# PostgreSQL (SSL enabled)
POSTGRES_HOST=postgres-prod.example.com
POSTGRES_PORT=5432
POSTGRES_USER=waf_user
POSTGRES_PASSWORD=<strong-password>
# SSL mode is automatically set to 'require' when ENVIRONMENT=prod

# JWT
JWT_SECRET_KEY=<strong-random-secret-key-generate-with-openssl>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# API
API_URL=https://api.waf-guard.example.com
WAF_URL=https://waf.example.com
```

**Generate secure secret key:**
```bash
openssl rand -hex 32
```

## Database Configuration

### Three PostgreSQL Databases:

#### 1. **cwaf** - Analyzer Data
- Symbol tables
- Macro definitions
- Constant recovery data

#### 2. **files** - Configuration Storage
- Uploaded configuration files
- File metadata
- Analysis task tracking

#### 3. **chatbot** - Conversation Data
- User accounts
- Conversation threads
- Messages
- LangGraph checkpoints

### Neo4j Graph Database:
- Configuration structure (VirtualHosts, Directories, etc.)
- Directive relationships (CONTAINS, USES, DEPENDS_ON)
- ModSecurity rule graph
- APOC plugins for advanced operations
- Batch operations (5000 items per batch for performance)

## Migration Strategy

### Phase 1: Setup Foundation (Day 1-2)
1. ✅ Create new folder structure
2. ✅ Move `common/config.py` and settings
3. ✅ Create `common/database/connections/` with connection management
4. ✅ Update docker-compose and Dockerfile

### Phase 2: Centralize Data Access (Day 3-5)
1. ✅ Create `common/database/access/` classes
2. ✅ Move queries from current codebase
3. ✅ Test each access class
4. ✅ Remove duplicate DB code from services

### Phase 3: Refactor Services (Day 6-8)
1. ✅ Create `services/analyzer/` and `services/chatbot/`
2. ✅ Move business logic to service layer
3. ✅ Update services to use data access layer
4. ✅ Move service-specific models to `services/*/models/`

### Phase 4: Unify API (Day 9-10)
1. ✅ Create `api/main.py` with unified FastAPI app
2. ✅ Consolidate all routers in `api/routers/`
3. ✅ Create `api/schemas/` for DTOs
4. ✅ Set up `api/dependencies.py` for DI

### Phase 5: Centralize Auth (Day 11-12)
1. ✅ Move auth to `common/auth/`
2. ✅ Update all protected endpoints
3. ✅ Remove duplicate auth code
4. ✅ Test authentication flow

### Phase 6: Testing & Cleanup (Day 13-14)
1. ✅ Write unit tests for services
2. ✅ Write integration tests
3. ✅ Update documentation
4. ✅ Remove old code

## Benefits of This Architecture

| Benefit | Explanation |
|---------|-------------|
| **No Code Duplication** | Database queries in one place (`common/database/access/`) |
| **Easy Testing** | Mock data access layer, no real DB needed for unit tests |
| **Clear Separation** | Each layer has single responsibility (API → Services → Data) |
| **Maintainable** | Easy to find and modify code - clear structure |
| **Scalable** | Can extract services to separate containers later if needed |
| **Type Safe** | Pydantic models throughout, catch errors at development time |
| **Modular** | Clear boundaries between components |
| **Framework Independent** | Services are plain Python, could use different framework |
| **Testable** | Dependency injection makes mocking easy |
| **Secure** | Centralized authentication, no password leaks in responses |

## Best Practices

### DO ✅

- ✅ Use dependency injection for all services
- ✅ Keep routers thin - delegate to services
- ✅ Put ALL database queries in `common/database/access/`
- ✅ Use Pydantic for all models and validation
- ✅ Type hint everything (`mypy` should pass)
- ✅ Use connection pooling for databases
- ✅ Separate domain models from API schemas
- ✅ Write tests that mock the data access layer
- ✅ Use environment variables for all configuration
- ✅ Log errors properly

### DON'T ❌

- ❌ Write SQL/Cypher queries in services
- ❌ Write business logic in routers
- ❌ Import from higher layers (services importing from api)
- ❌ Mix HTTP concerns with business logic
- ❌ Duplicate data access code across services
- ❌ Create circular dependencies
- ❌ Expose sensitive data in API responses (passwords, etc.)
- ❌ Create new database connections in services
- ❌ Use global variables for state
- ❌ Commit secrets to git

## Future Considerations

### If You Need to Split Services Later

The modular structure makes extraction easy:

```bash
# Extract analyzer to separate microservice:
1. Copy services/analyzer/ to new project
2. Copy relevant common/database/access/ classes
3. Create REST client for inter-service communication
4. Update dependency injection
5. Deploy analyzer separately
```

### Adding New Features

**New entity** (e.g., `Rule`):
1. Add to `common/models/domain.py`
2. Create `common/database/access/rules.py`
3. Add business logic in relevant service
4. Create API schemas in `api/schemas/`
5. Add router in `api/routers/rules.py`

**New service** (e.g., `reporter`):
1. Create `services/reporter/`
2. Implement `services/reporter/service.py`
3. Reuse existing data access classes from `common/database/access/`
4. Add router in `api/routers/reporter.py`
5. Register in `api/dependencies.py`

### Performance Optimization

- Use connection pooling (already implemented)
- Batch Neo4j operations (5000 items per batch)
- Cache frequently accessed data (add Redis if needed)
- Use async database drivers if needed
- Add database indexes
- Profile slow queries

### Monitoring & Observability

Consider adding:
- Structured logging (Python `logging` module)
- Metrics (Prometheus)
- Tracing (OpenTelemetry)
- Health checks for each database
- Performance monitoring

## Quick Reference

### Starting the Backend
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Project Structure Commands
```bash
# See folder structure
tree src -I '__pycache__|*.pyc'

# Count lines of code
find src -name '*.py' | xargs wc -l

# Find all TODOs
grep -r "TODO" src/
```

### Common Development Tasks

**Add new endpoint:**
1. Create route function in `api/routers/{resource}.py`
2. Define request/response schemas in `api/schemas/`
3. Implement business logic in relevant service
4. Add data access methods if needed

**Add new database query:**
1. Add method to relevant class in `common/database/access/`
2. Use from services
3. Never write queries outside data access layer

**Add authentication to endpoint:**
```python
from common.auth.dependencies import get_current_user

@router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    # User is authenticated here
    ...
```

---

**Architecture Version**: 1.0
**Last Updated**: 2025-11-13
**Maintainer**: WAF-GUARD Team

**Questions or suggestions?** Open an issue or update this document.
