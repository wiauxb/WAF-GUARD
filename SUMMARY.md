# WAF Analysis Platform - Architecture Summary

## **Core Principles**
- **Service-oriented architecture** with clear boundaries
- **Filesystem + Database hybrid** for config storage
- **Loose coupling** via schemas and service interfaces
- **Clear ownership**: Each service owns its domain

---

## **Project Structure**

```
project/
├── main.py                          # FastAPI app entry point
├── shared/                          # Shared infrastructure
│   ├── database.py                  # SQLAlchemy (engine, Base, SessionLocal, get_db)
│   ├── config.py                    # Settings (Pydantic Settings)
│   ├── exceptions.py                # Custom exceptions
│   └── utils.py                     # Generic utilities
├── api/                             # HTTP/API layer
│   ├── routes/                      # Route handlers
│   │   ├── auth.py                  # Authentication endpoints
│   │   ├── configs.py               # Config management endpoints
│   │   ├── parser.py                # Parser endpoints
│   │   └── chatbot.py               # Chatbot endpoints
│   ├── dependencies.py              # FastAPI dependencies (get_current_user)
│   └── middleware.py                # Middleware (logging, CORS, rate limiting)
├── services/                        # Business logic layer
│   ├── auth/                        # User authentication
│   │   ├── models.py                # User, Session
│   │   ├── schemas.py               # UserInfo, LoginRequest, TokenResponse
│   │   ├── repository.py            # UserRepository
│   │   └── service.py               # AuthService
│   ├── config_manager/              # Configuration file management
│   │   ├── models.py                # ConfigFile, ConfigVersion, ConfigAnalysis
│   │   ├── schemas.py               # ConfigFileSchema, ConfigContentResponse
│   │   ├── repository.py            # ConfigFileRepository
│   │   ├── service.py               # ConfigManagerService
│   │   └── storage/                 # Storage backends
│   │       └── filesystem.py        # Local filesystem operations
│   ├── parser/                      # WAF config parsing & analysis
│   │   ├── models.py                # ParsedResult, ParsingJob
│   │   ├── schemas.py               # ParseRequest, ParseResponse
│   │   ├── repository.py            # ParsedResultRepository
│   │   ├── service.py               # ParserService
│   │   └── parsers/                 # Parser implementations
│   │       ├── modsecurity.py
│   │       └── apache.py
│   └── chatbot/                     # LLM-powered assistant
│       ├── models.py                # Conversation, Message
│       ├── schemas.py               # ChatRequest, ChatResponse
│       ├── repository.py            # ConversationRepository
│       ├── service.py               # ChatbotService
│       └── llm/                     # LLM integration
│           ├── prompt_builder.py
│           └── llm_client.py
├── storage/                         # File storage (not in git)
│   └── configs/                     # Configuration files
│       ├── modsecurity/
│       │   ├── current/             # Active configs
│       │   └── versions/            # Version history
│       └── apache/
├── tests/                           # Test suite
└── alembic/                         # Database migrations
```

---

## **Layer Responsibilities**

### **API Layer** (`api/`)
- **Purpose**: HTTP interface, request/response handling
- **Contains**: Route handlers, dependencies, middleware
- **Does**: Validates requests, manages auth, calls services
- **Does NOT**: Business logic, database operations

### **Service Layer** (`services/`)
- **Purpose**: Business logic, orchestration between services
- **Contains**: Service classes with public methods
- **Does**: Implements business rules, coordinates operations
- **Does NOT**: HTTP concerns, direct database queries

### **Repository Layer** (`services/*/repository.py`)
- **Purpose**: Data access abstraction
- **Contains**: Database query methods
- **Does**: CRUD operations, complex queries
- **Does NOT**: Business logic, HTTP handling

### **Model Layer** (`services/*/models.py`)
- **Purpose**: Database schema definition
- **Contains**: SQLAlchemy models (tables, relationships)
- **Does**: Define data structure
- **Does NOT**: Business logic, queries

### **Schema Layer** (`services/*/schemas.py`)
- **Purpose**: Data contracts between layers/services
- **Contains**: Pydantic models
- **Does**: Validation, serialization
- **Does NOT**: Database operations, business logic

### **Shared Layer** (`shared/`)
- **Purpose**: Cross-cutting concerns
- **Contains**: Database setup, config, utilities
- **Does**: Infrastructure setup
- **Does NOT**: Business logic

---

## **Service Interactions**

```
┌─────────────┐
│    Auth     │ ← Provides user authentication
└─────────────┘
       ↓ (used by all services)
       
┌─────────────┐
│Config Mgr   │ ← Owns configuration files (filesystem + DB)
└─────────────┘
       ↓ (used by)
       
┌─────────────┐
│   Parser    │ ← Analyzes configs, uses Config Manager for access
└─────────────┘
       ↓ (used by)
       
┌─────────────┐
│  Chatbot    │ ← Uses Config Manager + Parser for context
└─────────────┘
```

**Dependency Flow**: Auth ← Config Manager ← Parser ← Chatbot

---

## **Key Design Patterns**

### **1. Service-to-Service Communication**
```python
# ✅ Services call each other via service layer
class ChatbotService:
    def __init__(self, db: Session):
        self.config_manager = ConfigManagerService(db)
        self.parser_service = ParserService(db)
```

### **2. Repository Pattern**
```python
# Repository handles data access
class ConfigFileRepository:
    def get_by_id(self, config_id: int) -> ConfigFile:
        return self.db.query(ConfigFile).filter(...).first()

# Service uses repository
class ConfigManagerService:
    def __init__(self, db: Session):
        self.config_repo = ConfigFileRepository(db)
```

### **3. Schema-Based Contracts**
```python
# Services expose/consume schemas, not models
def get_config_content(self, config_id: int) -> ConfigContentResponse:
    # Returns schema, not model
    return ConfigContentResponse(...)
```

### **4. Dependency Injection**
```python
# FastAPI injects dependencies into routes
@router.get("/configs/{config_id}")
def get_config(
    config_id: int,
    current_user: UserInfo = Depends(get_current_user),  # Auth dependency
    db: Session = Depends(get_db)  # DB session dependency
):
    service = ConfigManagerService(db)
    return service.get_config(config_id)
```

---

## **Data Flow Example: Parsing a Config**

```
1. User uploads config via API
   POST /configs/upload
   ↓
2. API route validates request
   api/routes/configs.py
   ↓
3. Config Manager saves file
   ConfigManagerService.upload_config()
   → ConfigFileRepository.create()
   → FileSystemStorage.save_file()
   → DB: Insert ConfigFile record
   → Filesystem: Save file to storage/configs/
   ↓
4. User requests parsing
   POST /parser/parse
   ↓
5. Parser Service gets config
   ParserService.parse_config()
   → ConfigManagerService.get_config_content()
   → ConfigFileRepository.get_content()
   → FileSystemStorage.read_file()
   ↓
6. Parser analyzes content
   → Calls appropriate parser (modsecurity.py)
   → Creates ParsedResult
   → Saves to DB via ParsedResultRepository
   ↓
7. Parser updates config status
   → ConfigManagerService.update_status()
   ↓
8. API returns result to user
```

---

## **Database Design**

### **Key Tables**
- **users** (auth): User accounts
- **config_files** (config_manager): Config metadata
- **config_versions** (config_manager): Version history
- **parsed_results** (parser): Analysis results
- **conversations** (chatbot): Chat history
- **messages** (chatbot): Individual messages

### **Relationships**
- User → ConfigFiles (one-to-many)
- ConfigFile → ConfigVersions (one-to-many)
- ConfigFile → ParsedResults (one-to-many)
- User → Conversations (one-to-many)
- Conversation → Messages (one-to-many)

---

## **File Storage Strategy**

### **What goes in Database:**
- Metadata (filename, size, hash, timestamps)
- Status, version numbers
- User ownership
- Analysis summaries

### **What goes in Filesystem:**
- Actual config file content
- Version history files
- Generated reports

### **Why Hybrid:**
- Performance: DB stays lean
- Scalability: Easy to move to S3
- Version control: Git can track files
- Debugging: Direct file access

---

## **Authentication Flow**

```
1. User login → AuthService.login()
2. Generate JWT token
3. Return token to client
4. Client includes token in Authorization header
5. API dependency (get_current_user) validates token
6. AuthService.verify_token() decodes JWT
7. Returns UserInfo to route handler
8. Route uses UserInfo for authorization
```

---

## **Migration Strategy**

### **Phase 1: Foundation**
1. Set up `shared/database.py` and `shared/config.py`
2. Create `main.py` with basic FastAPI app
3. Test database connection

### **Phase 2: Auth Service**
1. Migrate auth models, schemas
2. Create auth repository, service
3. Create auth API routes
4. Test authentication flow

### **Phase 3: Config Manager Service**
1. Create config_manager models, schemas
2. Implement filesystem storage
3. Create repository with file + DB operations
4. Create service with business logic
5. Create API routes
6. Test file upload/retrieval

### **Phase 4: Parser Service**
1. Migrate parser models, schemas
2. Create repository
3. Update service to use ConfigManagerService
4. Migrate parser implementations
5. Create API routes
6. Test parsing flow

### **Phase 5: Chatbot Service**
1. Migrate chatbot models, schemas
2. Create repository
3. Update service to use ConfigManagerService + ParserService
4. Integrate LLM client
5. Create API routes
6. Test conversation flow

---

## **Testing Strategy**

### **Unit Tests**
- Test services independently with mocked repositories
- Test repositories with test database
- Test schemas for validation

### **Integration Tests**
- Test service-to-service interactions
- Test API routes with test database
- Test file operations

### **Test Structure**
```
tests/
├── conftest.py              # Shared fixtures (test DB, mock objects)
├── test_auth/
├── test_config_manager/
├── test_parser/
└── test_chatbot/
```

---

## **Configuration Management**

### **Environment Variables** (`.env`)
```
DATABASE_URL=postgresql://user:pass@localhost/waf_db
SECRET_KEY=your-secret-key
STORAGE_ROOT=./storage
LLM_API_KEY=your-llm-key
```

### **Settings Class** (`shared/config.py`)
```python
class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    STORAGE_ROOT: str
    LLM_API_KEY: Optional[str]
    
    class Config:
        env_file = ".env"
```

---

## **Key Takeaways**

1. **Each service owns its domain**: Auth owns users, Config Manager owns files, Parser owns analysis, Chatbot owns conversations
2. **Services communicate via schemas**: Never import models across services
3. **Repository pattern abstracts data access**: Services don't write SQL
4. **Hybrid storage for configs**: Filesystem for content, DB for metadata
5. **Dependency injection**: FastAPI handles auth and DB sessions
6. **Clear boundaries**: API → Service → Repository → Database/Filesystem

---

## **Next Steps for Implementation**

1. Start with shared infrastructure (database.py, config.py)
2. Build one service at a time (Auth → Config Manager → Parser → Chatbot)
3. Test each service independently before moving to next
4. Keep old containers running during migration for comparison
5. Update each service to use the new architecture progressively