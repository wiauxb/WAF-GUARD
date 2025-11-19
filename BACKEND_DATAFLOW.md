# WAF-GUARD Backend Data Flow & API Reference

This document provides a complete reference for the new backend architecture, showing how data flows through the system, what models exist, what APIs are exposed, and how everything connects together.

## Table of Contents

1. [Folder Structure Overview](#1-folder-structure-overview)
2. [Models Organization](#2-models-organization)
3. [Data Access Layer APIs](#3-data-access-layer-apis)
4. [Service Layer APIs](#4-service-layer-apis)
5. [API Endpoints Reference](#5-api-endpoints-reference)
6. [Complete Data Flows](#6-complete-data-flows)
7. [Import Reference](#7-import-reference)

---

## 1. Folder Structure Overview

```
backend/src/
├── common/                          # Shared infrastructure (used by all services)
│   ├── config.py                    # Centralized settings (Pydantic)
│   ├── auth/                        # Authentication infrastructure
│   ├── database/                    # All database code
│   │   ├── connections/             # Connection pools & drivers
│   │   └── access/                  # Data access layer (all queries)
│   ├── models/                      # Shared domain models
│   └── utils/                       # Shared utilities
│
├── api/                             # HTTP/REST interface
│   ├── main.py                      # FastAPI application
│   ├── dependencies.py              # Dependency injection
│   ├── schemas/                     # Request/response DTOs
│   └── routers/                     # HTTP endpoints (9 routers)
│
└── services/                        # Business logic
    ├── analyzer/                    # Config analysis service
    │   ├── service.py               # Main service class
    │   ├── models/                  # Analyzer-specific models
    │   └── parsers/                 # Parsing implementations
    └── chatbot/                     # AI chatbot service
        ├── service.py               # Main service class
        ├── models/                  # Chatbot-specific models
        └── graph/                   # LangGraph implementation
```

---

## 2. Models Organization (EXHAUSTIVE)

This section lists EVERY model, class, and data structure in the backend.

### Model Categories

1. **Domain Models** - Business entities shared across services
2. **API Schemas** - HTTP request/response contracts
3. **Service Models** - Internal service-specific models
4. **Database Schemas** - PostgreSQL tables and Neo4j nodes

---

### 2.1 Domain Models (`common/models/domain.py`)

**Purpose:** Core business entities that represent your domain. Shared across all services.

**When to use:** Model represents a fundamental business concept that multiple services need to understand.

#### User Models

```python
class User(BaseModel):
    """
    User account for authentication and chat.
    Database: PostgreSQL (chatbot.users)
    """
    id: int                      # users_id from DB
    username: str                # Unique username
    hashed_password: str         # Bcrypt hashed password
```

#### Configuration Models

```python
class Config(BaseModel):
    """
    WAF configuration uploaded by user.
    Database: PostgreSQL (files.configs)
    """
    id: int                      # Config ID
    nickname: str                # User-friendly name
    parsed: bool = False         # Analysis completion status
    created_at: datetime         # Upload timestamp

class File(BaseModel):
    """
    Config file stored in database.
    Database: PostgreSQL (files.files)
    """
    id: int
    config_id: int               # FK to configs
    path: str                    # File path in config
    content: bytes               # File content

class Dump(BaseModel):
    """
    Apache config dump (httpd -D DUMP_CONFIG output).
    Database: PostgreSQL (files.dumps)
    """
    config_id: int               # FK to configs
    dump: str                    # Full dump text

class AnalysisTask(BaseModel):
    """
    Background analysis task.
    Database: PostgreSQL (files.analysis_tasks)
    """
    task_id: str                 # UUID
    config_id: int               # FK to configs
    status: str                  # "pending", "processing", "completed", "failed"
    progress: int                # 0-100
```

#### Directive Models

```python
class Directive(BaseModel):
    """
    Apache/ModSecurity directive from Neo4j.
    Database: Neo4j (various labels: secrule, definestr, etc.)
    """
    node_id: int                 # Unique node ID
    type: str                    # Directive type (lowercase)
    args: str                    # Directive arguments
    Location: str                # Location path (e.g., "/api")
    VirtualHost: str             # Virtual host (e.g., "*:443")
    IfLevel: int                 # If condition nesting level
    conditions: List[str]        # Condition stack
    Context: str                 # File path and line number

    # Optional fields (parsed from args)
    id: Optional[int]            # Rule ID
    tags: Optional[List[str]]    # Rule tags
    phase: Optional[int]         # Execution phase (1-5)
    msg: Optional[str]           # Rule message

    # Variables and constants
    constants: List[str]         # Constants used
    variables: List[str]         # Variables used
```

#### Chat Models

```python
class Thread(BaseModel):
    """
    Chatbot conversation thread.
    Database: PostgreSQL (chatbot.users_threads)
    """
    id: str                      # UUID (thread_id)
    user_id: int                 # FK to users
    title: str = "New Chat"      # Thread title
    created_at: datetime         # Creation timestamp
    updated_at: datetime         # Last message timestamp

class Message(BaseModel):
    """
    Chat message in a thread.
    Database: PostgreSQL (LangGraph checkpoints)
    """
    role: str                    # "user" or "assistant"
    content: str                 # Message text
    created_at: datetime         # Timestamp
```

#### Symbol Table Models

```python
class Symbol(BaseModel):
    """
    Symbol table entry (file context for directive).
    Database: PostgreSQL (cwaf.symboltable)
    """
    id: int                      # Symbol ID
    file_path: str               # File where directive was found
    line_number: int             # Line number in file
    node_id: Optional[int]       # Neo4j node ID

class MacroDef(BaseModel):
    """
    Macro definition.
    Database: PostgreSQL (cwaf.macrodef)
    """
    name: str                    # Macro name (PK)
    rule_id: int                 # FK to symboltable

class MacroCall(BaseModel):
    """
    Macro usage tracking.
    Database: PostgreSQL (cwaf.macrocall)
    """
    id: int                      # Call ID
    node_id: int                 # Directive that uses macro
    macro_name: str              # FK to macrodef
    rule_id: int                 # FK to symboltable
```

---

### 2.2 API Schemas (`api/schemas/`)

**Purpose:** HTTP request/response contracts. Different from domain models for validation, security, and API versioning.

**When to use:** Defining what data crosses the HTTP boundary.

#### Authentication Schemas

```python
# api/schemas/requests.py

class UserRegisterRequest(BaseModel):
    """User registration request"""
    username: constr(min_length=3, max_length=50)
    password: constr(min_length=8)        # Plain text (will be hashed)

class UserLoginRequest(BaseModel):
    """User login request (OAuth2 form)"""
    username: str
    password: str

# api/schemas/responses.py

class TokenResponse(BaseModel):
    """JWT authentication token"""
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    """User response - NO PASSWORD!"""
    id: int
    username: str

    @classmethod
    def from_domain(cls, user: User):
        return cls(id=user.id, username=user.username)
```

#### Config Schemas

```python
# api/schemas/requests.py

class ConfigUploadRequest(BaseModel):
    """Config upload - file via UploadFile, nickname via Form"""
    pass  # Handled by FastAPI multipart

# api/schemas/responses.py

class ConfigResponse(BaseModel):
    """Config response"""
    id: int
    nickname: str
    parsed: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, config: Config):
        return cls(
            id=config.id,
            nickname=config.nickname,
            parsed=config.parsed,
            created_at=config.created_at
        )

class ConfigUploadResponse(BaseModel):
    """Response after config upload"""
    config_id: int

class AnalysisTaskResponse(BaseModel):
    """Analysis task created"""
    task_id: str
    status: str
    progress_endpoint: str       # URL to poll progress

class AnalysisStatusResponse(BaseModel):
    """Analysis completion status"""
    parsed: bool

class TaskProgressResponse(BaseModel):
    """Analysis task progress"""
    task_id: str
    status: str                  # "pending", "processing", "completed", "failed"
    progress: int                # 0-100
```

#### Cypher Query Schemas

```python
# api/schemas/requests.py

class CypherQueryRequest(BaseModel):
    """Execute Cypher query"""
    query: str
    parameters: Optional[Dict] = {}

# api/schemas/responses.py

class CypherGraphResponse(BaseModel):
    """Cypher result as graph visualization"""
    html: str                    # Pyvis HTML

class CypherJsonResponse(BaseModel):
    """Cypher result as JSON"""
    df: List[Dict[str, Any]]     # Pandas DataFrame as dict
```

#### Directive Query Schemas

```python
# api/schemas/requests.py

class DirectiveIdQuery(BaseModel):
    """Query by directive ID"""
    id: str

class DirectiveTagQuery(BaseModel):
    """Query by directive tag"""
    tag: str

class HttpRequestQuery(BaseModel):
    """Simulate HTTP request"""
    location: str                # e.g., "/api/users"
    host: str                    # e.g., "example.com"

class ConstantQuery(BaseModel):
    """Query constant/variable"""
    var_name: str
    var_value: Optional[str] = None

class FileContextQuery(BaseModel):
    """Query by file location"""
    file_path: str
    line_num: int

# api/schemas/responses.py

class DirectivesResponse(BaseModel):
    """Generic directive query result"""
    results: List[Dict[str, Any]]

class NodeMetadataResponse(BaseModel):
    """Node file context metadata"""
    metadata: List[tuple]        # [(macro_name, file_path, line_number), ...]

class VariableSearchResponse(BaseModel):
    """Variable search results"""
    records: List[Dict[str, Any]]
```

#### Storage Schemas

```python
# api/schemas/requests.py

class FileUpdateRequest(BaseModel):
    """Update config file"""
    path: str
    content: str

# api/schemas/responses.py

class ConfigTreeResponse(BaseModel):
    """File tree node"""
    filename: str
    is_folder: bool
    file_content: Optional[str] = None
```

#### Chat Schemas

```python
# api/schemas/requests.py

class ChatMessageRequest(BaseModel):
    """Send chat message"""
    messages: list[dict]         # Message history
    config: dict                 # {thread_id: "..."}

class ThreadRenameRequest(BaseModel):
    """Rename thread"""
    new_title: str

# api/schemas/responses.py

class ThreadResponse(BaseModel):
    """Thread response"""
    id: str
    title: str
    updated_at: str              # ISO format

    @classmethod
    def from_domain(cls, thread: Thread):
        return cls(
            id=thread.id,
            title=thread.title,
            updated_at=thread.updated_at.isoformat()
        )

class ChatResponse(BaseModel):
    """Chat message response"""
    messages: List[Dict]         # LangChain message format
```

---

### 2.3 Service-Specific Models

#### 2.3.1 Analyzer Models (`services/analyzer/models/`)

**Purpose:** Internal models for parsing and analysis. Not exposed outside analyzer service.

##### Context Models

```python
# services/analyzer/models/context.py

class Context:
    """
    Base class for directive context (where it was found).
    Used during parsing to track file locations.
    """
    line_num: int               # Line number in source

    def clone(self) -> Context:
        """Deep copy"""

    def pretty(self) -> str:
        """Pretty string representation"""

class FileContext(Context):
    """Direct file context"""
    file_path: str              # Path to config file
    line_num: int               # Line number

    def to_real_path(self) -> str:
        """Convert to absolute filesystem path"""

    def find_line(self) -> str:
        """Get actual line content from file"""

class MacroContext(Context):
    """Macro context (directive inside macro)"""
    macro_name: str             # Macro name
    definition: FileContext     # Where macro is defined
    use: Context                # Where macro is called
    line_num: int               # Offset within macro

    def get_signature(self) -> str:
        """Returns 'macro_name#line_num'"""

    def find_line(self) -> str:
        """Get line content accounting for macro offset"""
```

##### Directive Class Hierarchy

```python
# services/analyzer/models/directives.py

class Directive:
    """
    Base directive class. All Apache/ModSecurity directives inherit from this.
    Represents a parsed directive ready to be added to databases.
    """
    # Location/scope
    Location: str               # Location path
    VirtualHost: str            # Virtual host
    IfLevel: int                # If nesting level
    conditions: list            # Condition stack

    # Identity
    Context: Context            # FileContext or MacroContext
    node_id: int                # Unique node ID
    type: str                   # Directive type (lowercase)

    # Content
    args: str                   # Full argument string
    constants: list             # Constant references
    variables: list             # Variable references
    num_of_variables: int       # Variable count

    # Optional (parsed from args)
    id: Optional[int]           # Rule ID
    tags: Optional[set]         # Tags
    phase: Optional[int]        # Phase (1-5)
    msg: Optional[str]          # Message

    def add_constant(self, constant: str | list | set):
        """Add constant reference"""

    def add_variable(self, variable: str | list | set):
        """Add variable reference"""

    def processs_args(self, args: str):
        """Parse id, tags, phase, msg from arguments"""

    def properties(self) -> dict:
        """All properties as dict"""

    def node_properties(self) -> dict:
        """Neo4j node properties"""

class SecRule(Directive):
    """
    ModSecurity SecRule directive.
    Most complex directive with variables, operators, and actions.
    """
    # Variables (VARIABLES section of rule)
    num_of_vars: int            # Number of variable definitions
    secrule_vars: list          # Flattened [collection, var, collection, var, ...]

    # Operator
    secrule_op: str             # Operator (e.g., "@rx", "@contains")

    # Actions
    secrule_actions: Optional[list]  # List of action strings

    # SetEnv actions
    setenv_vars: list           # Flattened [key, value, key, value, ...]
    setenv_num_vars: int
    setenv_vars_no_value: list  # Keys without values
    setenv_unset: list          # Vars to unset

    # SetVar actions
    setvar_vars: list           # Flattened [collection, key, value, ...]
    setvar_num_vars: int
    setvar_vars_no_value: list  # Flattened [collection, key, ...]
    setvar_num_vars_no_value: int
    setvar_unset: list          # Flattened [collection, key, ...]
    setvar_num_unset: int

class SecRuleRemoveById(Directive):
    """
    SecRuleRemoveById directive - removes rules by ID.
    """
    ids_to_remove: list[int]    # Individual IDs
    ranges_to_remove: list[int] # Flattened [start, end, start, end, ...]
    num_of_ranges: int          # Number of ranges

class SecRuleRemoveByTag(Directive):
    """
    SecRuleRemoveByTag directive - removes rules by tag.
    """
    tags_to_remove: list[str]   # Tags to remove

class DefineStr(Directive):
    """
    Define directive (Apache variable definition).
    """
    cst_name: str               # Constant name
    cst_value: Optional[str]    # Constant value
```

##### Factory Models

```python
# services/analyzer/models/directive_factory.py

class DirectiveFactory:
    """
    Factory for creating appropriate Directive subclass.
    Determines directive type and instantiates correct class.
    """
    @classmethod
    def create(
        cls,
        location: str,
        virtual_host: str,
        if_level: int,
        context: Context,
        node_id: int,
        type: str,
        conditions: list,
        args: str
    ) -> Directive:
        """
        Create appropriate directive instance based on type.
        Returns: Directive, SecRule, SecRuleRemoveById, etc.
        """

# services/analyzer/models/query_factory.py

class QueryFactory:
    """
    Factory for generating Neo4j Cypher queries.
    Each directive type has specific query pattern.
    """
    @classmethod
    def base_module(cls) -> str:
        """Base Cypher for all directives"""

    @classmethod
    def generic_module(cls) -> str:
        """Cypher for generic directives"""

    @classmethod
    def secrule_module(cls) -> str:
        """Cypher for SecRule (most complex)"""

    @classmethod
    def definestr_module(cls) -> str:
        """Cypher for DefineStr"""

    @classmethod
    def removebyid_module(cls) -> str:
        """Cypher for SecRuleRemoveById"""

    @classmethod
    def removebytag_module(cls) -> str:
        """Cypher for SecRuleRemoveByTag"""

    @classmethod
    def create_indexes(cls) -> str:
        """Cypher to create indexes"""
```

##### Utility Models

```python
# services/analyzer/models/macro.py

class Macro:
    """
    Utility class for macro operations.
    """
    @classmethod
    def parse_macro_def(cls, path: str, line: int) -> tuple:
        """
        Parse macro definition.
        Returns: (macro_name, args)
        """

    @classmethod
    def find_line_inside_macro(
        cls,
        path: str,
        line_num: int,
        offset: int = 0
    ) -> str:
        """Get line content from macro file"""

# services/analyzer/models/timer.py

class Timer:
    """
    Context manager for timing operations.
    """
    name: str
    start_time: float
    end: float
    elapsed: float

    def __enter__(self):
        """Start timing"""

    def __exit__(self, *args):
        """Stop timing and print"""
```

#### 2.3.2 Chatbot Models (`services/chatbot/models/`)

```python
# services/chatbot/models/graph_state.py

class GraphState(AgentState):
    """
    LangGraph state for chat conversation.
    TypedDict that defines state schema for LangGraph.
    """
    messages: Annotated[List[AnyMessage], add_messages]
    # add_messages is LangGraph's built-in reducer for message lists
```

---

### 2.4 Database Schemas

#### PostgreSQL Tables

##### Chatbot Database (`chatbot`)

```sql
-- User accounts
CREATE TABLE users (
    users_id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    username text NOT NULL UNIQUE,
    password text NOT NULL  -- bcrypt hashed
);

-- Chat threads
CREATE TABLE users_threads (
    thread_id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id text NOT NULL REFERENCES users(users_id),
    title text NOT NULL DEFAULT 'New Thread',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- LangGraph checkpoint tables (auto-created)
CREATE TABLE checkpoints (
    thread_id text NOT NULL REFERENCES users_threads(thread_id),
    checkpoint_ns text NOT NULL DEFAULT '',
    checkpoint_id text NOT NULL,
    parent_checkpoint_id text,
    type text,
    checkpoint jsonb NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE TABLE checkpoint_writes (
    thread_id text NOT NULL REFERENCES users_threads(thread_id),
    checkpoint_ns text NOT NULL DEFAULT '',
    checkpoint_id text NOT NULL,
    task_id text NOT NULL,
    idx integer NOT NULL,
    channel text,
    type text,
    blob bytea NOT NULL,
    task_path text DEFAULT '',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

CREATE TABLE checkpoint_blobs (
    thread_id text NOT NULL REFERENCES users_threads(thread_id),
    checkpoint_ns text NOT NULL DEFAULT '',
    channel text NOT NULL,
    version text NOT NULL,
    type text,
    blob bytea,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);
```

##### CWAF Database (`cwaf`)

```sql
-- Symbol table (file context for directives)
CREATE TABLE symboltable (
    id serial PRIMARY KEY,
    file_path text NOT NULL,
    line_number integer NOT NULL,
    node_id integer  -- Neo4j node_id
);

-- Macro definitions
CREATE TABLE macrodef (
    name text PRIMARY KEY,
    ruleid integer REFERENCES symboltable(id)
);

-- Macro usage tracking
CREATE TABLE macrocall (
    id serial PRIMARY KEY,
    nodeid integer NOT NULL,  -- Directive using the macro
    macro_name text REFERENCES macrodef(name),
    ruleid integer REFERENCES symboltable(id)  -- Where macro was called from
);
```

##### Files Database (`files`)

```sql
-- Configurations
CREATE TABLE configs (
    id serial PRIMARY KEY UNIQUE,
    nickname text NOT NULL UNIQUE,
    parsed boolean NOT NULL DEFAULT false,
    loaded_at date NOT NULL DEFAULT CURRENT_DATE
);

-- Config files
CREATE TABLE files (
    id serial PRIMARY KEY,
    config_id integer NOT NULL REFERENCES configs(id) ON DELETE CASCADE,
    path text NOT NULL,
    content bytea
);

-- Apache dumps (httpd -D DUMP_CONFIG)
CREATE TABLE dumps (
    config_id integer NOT NULL REFERENCES configs(id) ON DELETE CASCADE,
    dump text NOT NULL
);

-- Selected config (UI state)
CREATE TABLE selected_config (
    id serial PRIMARY KEY,
    config_id integer REFERENCES configs(id) ON DELETE SET NULL
);

-- Analysis tasks
CREATE TABLE analysis_tasks (
    id text NOT NULL UNIQUE,
    config_id integer NOT NULL REFERENCES configs(id) ON DELETE CASCADE,
    status text NOT NULL,
    progress integer NOT NULL
);
```

#### Neo4j Graph Schema

##### Node Labels

- **Directive nodes:** Dynamic labels based on type (`secrule`, `definestr`, `servername`, etc.)
- **Location:** `:Location` - Location paths (e.g., "/api")
- **VirtualHost:** `:VirtualHost` - Virtual hosts (e.g., "*:443")
- **Predicate:** `:Predicate` - If conditions
- **Constant:** `:Constant` - Defined constants/variables
- **Collection:** `:Collection` - ModSecurity collections (ENV, TX, REQUEST_HEADERS)
- **Variable:** `:Variable` - Variables within collections
- **Tag:** `:Tag` - Rule tags
- **Id:** `:Id` - Rule IDs
- **Phase:** `:Phase` - Execution phases (1-5)
- **Regex:** `:Regex` - Regular expressions (for SecRuleRemoveByTag)

##### Common Node Properties

All directive nodes have:
- `node_id`: int (unique)
- `type`: str
- `args`: str
- `Location`: str
- `VirtualHost`: str
- `IfLevel`: int
- `conditions`: list
- `Context`: str
- `constants`: list
- `variables`: list

SecRule-specific properties:
- `id`: int
- `tags`: list
- `phase`: int
- `msg`: str

##### Relationships

- `[:AtLocation]` - Directive → Location
- `[:InVirtualHost]` - Directive → VirtualHost
- `[:Has]` - Directive → Predicate/Tag/Id
- `[:Uses]` - Directive → Constant/Variable/Collection
- `[:Sets]` - SecRule → Variable (setvar action)
- `[:Unsets]` - SecRule → Variable (setvar:!var)
- `[:Define]` - DefineStr → Constant
- `[:DoesRemove]` - SecRuleRemoveById/ByTag → Id/Regex
- `[:Match]` - Regex → Tag
- `[:InPhase]` - Directive → Phase
- `[:IsVariableOf]` - Variable → Collection

##### Indexes

- Fulltext index `cstIndex` on `:Constant`, `:Variable`, `:Collection` nodes for `name` property

---

### Summary Table

| Category | Count | Location |
|----------|-------|----------|
| **Domain Models** | 11 | `common/models/domain.py` |
| **API Request Schemas** | 12 | `api/schemas/requests.py` |
| **API Response Schemas** | 15 | `api/schemas/responses.py` |
| **Analyzer Service Models** | 10 | `services/analyzer/models/` |
| **Chatbot Service Models** | 1 | `services/chatbot/models/` |
| **PostgreSQL Tables** | 14 | 3 databases |
| **Neo4j Node Types** | 12 | Graph database |
| **Neo4j Relationships** | 11 | Graph database |

**Total:** 86 data structures across all layers

---

## 3. Data Access Layer APIs

All database queries live here. Services and routers call these methods instead of writing SQL/Cypher directly.

### 3.1 ConfigAccess (`common/database/access/configs.py`)

**Purpose:** Manage configurations, files, dumps, and analysis tasks.

**Databases:** PostgreSQL (files), Neo4j (for graph cleanup)

#### Config CRUD

```python
def get_all() -> List[Config]:
    """
    Get all configurations ordered by creation date.

    Query: SELECT id, nickname, parsed, created_at FROM configs ORDER BY created_at DESC
    """

def get_by_id(config_id: int) -> Optional[Config]:
    """
    Get a single config by ID.

    Query: SELECT * FROM configs WHERE id = %s
    """

def create(nickname: str) -> int:
    """
    Create new config entry.

    Query: INSERT INTO configs (nickname) VALUES (%s) RETURNING id
    Returns: config_id
    """

def delete(config_id: int) -> bool:
    """
    Delete config and associated data.

    Query: DELETE FROM configs WHERE id = %s
    Returns: True if deleted, False if not found
    """

def update_parsed_status(config_id: int, parsed: bool) -> None:
    """
    Mark config as parsed or unparsed.

    Query: UPDATE configs SET parsed = %s WHERE id = %s
    """
```

#### Selected Config Management

```python
def get_selected_config() -> Optional[int]:
    """
    Get the currently selected config ID.

    Query: SELECT config_id FROM selected_config LIMIT 1
    Returns: config_id or None
    """

def set_selected_config(config_id: int) -> None:
    """
    Set the currently selected config (for UI state).

    Query: UPDATE/INSERT into selected_config
    """
```

#### File Management

```python
def save_file(config_id: int, path: str, content: bytes) -> None:
    """
    Store a config file in database.

    Query: INSERT INTO files (config_id, path, content) VALUES (%s, %s, %s)
    """

def get_file(config_id: int, filepath: str) -> Optional[bytes]:
    """
    Retrieve file content.

    Query: SELECT content FROM files WHERE path = %s AND config_id = %s
    """

def get_files_by_config(config_id: int) -> List[tuple]:
    """
    Get all files for a config.

    Query: SELECT path, content FROM files WHERE config_id = %s
    Returns: List of (path, content) tuples
    """

def update_file(config_id: int, path: str, content: bytes) -> None:
    """
    Update existing file content.

    Query: UPDATE files SET content = %s WHERE config_id = %s AND path = %s
    """
```

#### Dump Management

```python
def save_dump(config_id: int, dump: str) -> None:
    """
    Store Apache config dump (output of 'httpd -D DUMP_CONFIG').

    Query: INSERT INTO dumps (config_id, dump) VALUES (%s, %s)
    """

def get_dump(config_id: int) -> Optional[str]:
    """
    Retrieve config dump.

    Query: SELECT dump FROM dumps WHERE config_id = %s
    """
```

#### Analysis Task Management

```python
def create_analysis_task(config_id: int, task_id: str) -> None:
    """
    Create analysis task for background processing.

    Query: INSERT INTO analysis_tasks (id, config_id, status, progress)
           VALUES (%s, %s, 'pending', 0)
    """

def update_task_status(task_id: str, status: str) -> None:
    """
    Update task status.

    Query: UPDATE analysis_tasks SET status = %s WHERE task_id = %s
    """

def get_task_progress(task_id: str) -> Optional[tuple]:
    """
    Get task progress.

    Query: SELECT status, progress FROM analysis_tasks WHERE task_id = %s
    Returns: (status, progress) tuple
    """
```

### 3.2 DirectiveAccess (`common/database/access/directives.py`)

**Purpose:** Query directive graph in Neo4j.

**Database:** Neo4j

#### Directive Queries by ID/Tag

```python
def get_directives_removed_by_id(id: str) -> List[Dict[str, Any]]:
    """
    Find directives that are removed by a specific rule ID.

    Cypher: MATCH (n:secruleremovebyid)-[:DoesRemove]->(i:Id {value: $id}) RETURN n
    Used by: Frontend to show what was removed
    """

def get_directives_removed_by_tag(tag: str) -> List[Dict[str, Any]]:
    """
    Find directives that are removed by a specific tag.

    Cypher: MATCH (n:secruleremovebytag)-[*..2]->(t:Tag {value: $tag}) RETURN n
    """

def get_directives_by_id(id: str) -> List[Dict[str, Any]]:
    """
    Get directives with a specific ID.

    Cypher: MATCH (n)-[:Has]->(i:Id {value: $id}) RETURN n
    """

def get_directives_by_tag(tag: str) -> List[Dict[str, Any]]:
    """
    Get directives with a specific tag.

    Cypher: MATCH (n)-[:Has]->(t:Tag {value: $tag}) RETURN n
    """

def get_directive_by_node_id(node_id: int) -> List[Dict[str, Any]]:
    """
    Get directive by Neo4j node ID.

    Cypher: MATCH (n {node_id: $nodeid}) RETURN n
    """

def get_remover_directives(node_id: int) -> List[Dict[str, Any]]:
    """
    Get directives that removed a specific directive (by ID or tag).

    Cypher: MATCH (n)-[:DoesRemove]->(crt)-[*..2]-(a {node_id: $nodeid})
            WHERE n.node_id > a.node_id
            RETURN LABELS(crt) as type, crt, n

    Returns: List with criterion_type, criterion_value, directive
    """
```

#### HTTP Request Simulation

```python
def filter_by_location_and_host(location: str, host: str) -> List[Dict[str, Any]]:
    """
    Filter rules that apply to a specific HTTP request.

    Cypher: MATCH (vh:VirtualHost WHERE vh.value =~ '{host}')
                  <-[:InVirtualHost]-(n)-[:AtLocation]->
                  (l:Location WHERE l.value =~ '{location}')
            RETURN n ORDER BY n.phase, n.IfLevel, n.Location, n.VirtualHost, n.node_id

    WARNING: Currently vulnerable to injection - needs parameterization!
    Used by: HTTP request analyzer tool
    """
```

#### Variable/Constant Search

```python
def search_variable(var_name: str) -> List[Dict[str, Any]]:
    """
    Search for constants/variables by name using fulltext index.

    Cypher: CALL db.index.fulltext.queryNodes('cstIndex', $name_query)
            YIELD node RETURN node

    Used by: Constant lookup in chatbot and frontend
    """

def get_set_node(var_name: str, var_value: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get nodes that set/define a constant.

    Cypher: MATCH (c {name: $name})<-[:Sets|Define]-(n) RETURN n
    """

def get_use_node(var_name: str, var_value: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get nodes that use a constant.

    Cypher: MATCH (c {name: $name})<-[:Uses]-(n) RETURN n
    """
```

#### Generic Cypher Execution

```python
def execute_cypher(query: str, parameters: dict = None) -> Any:
    """
    Execute arbitrary Cypher query.

    Used by: Custom query endpoint, graph visualization
    """

def execute_cypher_to_json(query: str) -> List[Dict[str, Any]]:
    """
    Execute Cypher and return results as JSON/DataFrame.

    Used by: Frontend data tables
    """
```

### 3.3 UserAccess (`common/database/access/users.py`)

**Purpose:** User authentication and management.

**Database:** PostgreSQL (chatbot)

```python
def create(username: str, hashed_password: str) -> int:
    """
    Register new user.

    Query: INSERT INTO users (username, password) VALUES (%s, %s) RETURNING users_id
    Returns: user_id
    """

def get_by_username(username: str) -> Optional[User]:
    """
    Get user by username for login.

    Query: SELECT users_id, username, password FROM users WHERE username = %s
    Returns: User domain model or None
    """

def get_by_id(user_id: int) -> Optional[User]:
    """
    Get user by ID.

    Query: SELECT users_id, username, password FROM users WHERE users_id = %s
    """
```

### 3.4 ThreadAccess (`common/database/access/threads.py`)

**Purpose:** Chat thread management.

**Database:** PostgreSQL (chatbot)

```python
def get_by_user(user_id: int) -> List[Thread]:
    """
    Get all threads for a user, ordered by most recent.

    Query: SELECT thread_id, title, updated_at
           FROM users_threads
           WHERE user_id = %s
           ORDER BY updated_at DESC
    """

def create(user_id: int) -> str:
    """
    Create new thread.

    Query: INSERT INTO users_threads (user_id) VALUES (%s) RETURNING thread_id
    Returns: thread_id (UUID)
    """

def delete(thread_id: str) -> None:
    """
    Delete thread.

    Query: DELETE FROM users_threads WHERE thread_id = %s
    """

def get_by_id(thread_id: str) -> Optional[Thread]:
    """
    Get thread by ID.

    Query: SELECT thread_id, user_id, title, updated_at
           FROM users_threads
           WHERE thread_id = %s
    """

def rename(thread_id: str, new_title: str) -> None:
    """
    Rename thread.

    Query: UPDATE users_threads SET title = %s WHERE thread_id = %s
    """

def update_timestamp(thread_id: str) -> None:
    """
    Mark thread as recently used (bump updated_at).

    Query: UPDATE users_threads SET updated_at = now() WHERE thread_id = %s
    """

def get_messages(thread_id: str) -> List[BaseMessage]:
    """
    Get conversation history from LangGraph checkpoint.

    Uses: PostgresSaver.get() to retrieve checkpoint
    Returns: List of LangChain messages
    """
```

### 3.5 AnalyzerAccess (`common/database/access/analyzer.py`)

**Purpose:** Analyzer metadata (symbol tables, macro tracking).

**Databases:** PostgreSQL (cwaf), Neo4j

#### Table Management

```python
def init_tables() -> None:
    """
    Create analyzer metadata tables.

    Tables created:
    - symboltable: Maps directives to file locations
    - macrodef: Macro definitions
    - macrocall: Macro call tracking
    """

def clear_schema() -> None:
    """
    Drop and recreate entire PostgreSQL schema.

    WARNING: Destructive! Terminates all connections.
    Used during analysis to start fresh.
    """

def clear_graph(batch_size: int = 5000) -> int:
    """
    Clear all nodes from Neo4j in batches.

    Cypher: MATCH (n) WITH n LIMIT {batch_size} DETACH DELETE n
    Returns: Total nodes deleted
    """
```

#### Symbol Table Operations

```python
def add_symbol(file_path: str, line_number: int, node_id: Optional[int] = None) -> int:
    """
    Add entry to symbol table (file context for a directive).

    Query: INSERT INTO symboltable (file_path, line_number, node_id)
           VALUES (%s, %s, %s) RETURNING id
    Returns: symbol_id
    """

def add_macro_def(name: str, rule_id: int) -> str:
    """
    Record macro definition.

    Query: INSERT INTO macrodef (name, ruleid) VALUES (%s, %s)
    """

def add_macro_call(node_id: int, macro_name: str, rule_id: int) -> int:
    """
    Record macro usage.

    Query: INSERT INTO macrocall (nodeid, macro_name, ruleid)
           VALUES (%s, %s, %s) RETURNING id
    """

def get_macro_def(name: str) -> Optional[int]:
    """
    Look up macro definition.

    Query: SELECT ruleid FROM macrodef WHERE name = %s
    """
```

#### Metadata Queries

```python
def get_metadata_by_node_id(node_id: int) -> List[tuple]:
    """
    Get file context for a directive (where it was defined).

    Query: SELECT macro_name, file_path, line_number
           FROM symboltable JOIN macrocall
           WHERE nodeid = %s

    Returns: List of (macro_name, file_path, line_number)
    Used by: Frontend to show "defined in file X:Y"
    """

def get_node_ids_by_file_context(file_path: str, line_num: int) -> List[int]:
    """
    Reverse lookup: Get directive node IDs from file location.

    Query: SELECT nodeid FROM symboltable/macrocall
           WHERE file_path = %s AND line_number = %s

    Returns: List of node_ids
    Used by: Code editor integration
    """
```

---

## 4. Service Layer APIs

Business logic orchestration. Services coordinate between data access and implement domain rules.

### 4.1 AnalyzerService (`services/analyzer/service.py`)

**Purpose:** Parse Apache/ModSecurity configs and populate databases.

**Dependencies:** ConfigAccess, AnalyzerAccess

```python
class AnalyzerService:
    def __init__(self, config_access: ConfigAccess, analyzer_access: AnalyzerAccess):
        self.config_access = config_access
        self.analyzer_access = analyzer_access
        self.apache_parser = ApacheParser()
        self.modsec_parser = ModSecParser()
```

#### Public Methods

```python
def analyze_config(config_id: int) -> int:
    """
    Main analysis entry point. Parse config and populate databases.

    Steps:
    1. Retrieve config files and dump from database
    2. Write files to /tmp/{config_id}/
    3. Parse dump to extract directives
    4. Clear databases (Neo4j + PostgreSQL cwaf)
    5. Process each directive:
       - Add to symbol table
       - Track macro definitions/calls
       - Create Neo4j nodes and relationships
    6. Create indexes
    7. Mark config as parsed

    Parameters:
        config_id: Config ID from files database

    Returns:
        Number of directives processed

    Raises:
        ValueError: If config not found

    Used by:
        - api/routers/analyzer.py POST /analyze/{config_id}

    Time: ~10-60 seconds depending on config size
    """

def reset_databases() -> None:
    """
    Clear Neo4j and PostgreSQL cwaf database.

    WARNING: Destructive operation!

    Used internally during analysis to start fresh.
    """
```

### 4.2 ChatbotService (`services/chatbot/service.py`)

**Purpose:** AI-powered chatbot using LangGraph.

**Dependencies:** ConfigAccess, ThreadAccess, DirectiveAccess

```python
class ChatbotService:
    def __init__(
        self,
        config_access: ConfigAccess,
        thread_access: ThreadAccess,
        directive_access: DirectiveAccess
    ):
        self.config_access = config_access
        self.thread_access = thread_access
        self.directive_access = directive_access
        self.graph = UIGraph()
```

#### Public Methods

```python
def chat(thread_id: str, messages: list, user_id: int) -> dict:
    """
    Process chat message and generate AI response.

    Steps:
    1. Verify thread belongs to user (authorization)
    2. Invoke LangGraph with message history
    3. LangGraph may call tools:
       - filter_rule (query directives by location/host)
       - get_constant_info (search variables)
       - get_file (retrieve config files)
    4. Update thread timestamp
    5. Return AI response

    Parameters:
        thread_id: LangGraph thread ID (UUID)
        messages: List of message dicts from frontend
        user_id: User ID for authorization

    Returns:
        AI response dict with message content

    Raises:
        ValueError: If thread not found or access denied

    Used by:
        - api/routers/chatbot.py POST /chat/ui_graph

    Note: Messages are persisted automatically by LangGraph's PostgresSaver
    """
```

---

## 5. API Endpoints Reference

All HTTP endpoints organized by router file.

### 5.1 Authentication (`api/routers/auth.py`)

**Purpose:** User registration and login.

```python
POST /auth/register
    Request: UserRegisterRequest {username, password}
    Response: UserResponse {id, username}

    Description: Register new user account
    Service: UserAccess.create()
    Auth: None (public)

POST /auth/login
    Request: Form {username, password}
    Response: TokenResponse {access_token, token_type}

    Description: Login and get JWT token
    Service: UserAccess.get_by_username(), verify_password(), create_access_token()
    Auth: None (public)
```

### 5.2 Configs (`api/routers/configs.py`)

**Purpose:** Config CRUD and analysis management.

```python
GET /configs
    Response: List[ConfigResponse]

    Description: Get all configurations
    Service: ConfigAccess.get_all()
    Auth: Required

GET /configs/selected
    Response: int (config_id)

    Description: Get currently selected config
    Service: ConfigAccess.get_selected_config()
    Auth: Required

POST /configs/select/{config_id}
    Response: {"success": true}

    Description: Set selected config
    Service: ConfigAccess.set_selected_config()
    Auth: Required

DELETE /configs/{config_id}
    Response: {"success": true}

    Description: Delete config and all associated data
    Service: ConfigAccess.delete()
    Auth: Required

POST /configs/analyze/{config_id}
    Response: AnalysisTaskResponse {task_id, status, progress_endpoint}

    Description: Start background analysis task
    Service: ConfigAccess.create_analysis_task(), AnalyzerService.analyze_config()
    Auth: Required
    Note: Analysis runs asynchronously

GET /configs/analyze/{config_id}
    Response: AnalysisStatusResponse {parsed: bool}

    Description: Get analysis completion status
    Service: ConfigAccess.get_by_id()
    Auth: Required
```

### 5.3 Analyzer (`api/routers/analyzer.py`)

**Purpose:** Direct analyzer service invocation.

```python
POST /analyze/{config_id}
    Response: {"directive_count": int, "status": "completed"}

    Description: Synchronously analyze config (may take 10-60 seconds)
    Service: AnalyzerService.analyze_config()
    Auth: Required
    Note: Blocks until complete
```

### 5.4 Chatbot (`api/routers/chatbot.py`)

**Purpose:** AI chat and thread management.

```python
POST /chat/ui_graph
    Request: ChatMessageRequest {messages: [...], config: {thread_id: "..."}}
    Response: {"messages": [...]}

    Description: Send chat message and get AI response
    Service: ChatbotService.chat()
    Auth: Required

GET /chat/threads
    Response: List[ThreadResponse] {id, title, updated_at}

    Description: Get all user's threads
    Service: ThreadAccess.get_by_user()
    Auth: Required

POST /chat/threads
    Response: {"thread_id": str}

    Description: Create new thread
    Service: ThreadAccess.create()
    Auth: Required

GET /chat/threads/{thread_id}
    Response: List[Message]

    Description: Get thread message history
    Service: ThreadAccess.get_messages()
    Auth: Required

DELETE /chat/threads/{thread_id}
    Response: {"success": true}

    Description: Delete thread
    Service: ThreadAccess.delete()
    Auth: Required

PUT /chat/threads/{thread_id}
    Request: ThreadRenameRequest {new_title}
    Response: {"success": true}

    Description: Rename thread
    Service: ThreadAccess.rename()
    Auth: Required
```

### 5.5 Cypher (`api/routers/cypher.py`)

**Purpose:** Execute custom Cypher queries.

```python
POST /cypher/run
    Request: CypherQueryRequest {query, parameters}
    Response: CypherGraphResponse {html: "<graph visualization>"}

    Description: Execute Cypher and return graph visualization
    Service: DirectiveAccess.execute_cypher()
    Auth: Required
    Note: Uses pyvis for visualization

POST /cypher/to_json
    Request: CypherQueryRequest {query}
    Response: CypherJsonResponse {df: [...]}

    Description: Execute Cypher and return JSON results
    Service: DirectiveAccess.execute_cypher_to_json()
    Auth: Required
```

### 5.6 Directives (`api/routers/directives.py`)

**Purpose:** Query directives from Neo4j graph.

```python
GET /directives/remove_by/id?id={id}
    Response: DirectivesResponse {results: [...]}

    Description: Get directives removed by rule ID
    Service: DirectiveAccess.get_directives_removed_by_id()
    Auth: Required

GET /directives/remove_by/tag?tag={tag}
    Response: DirectivesResponse {results: [...]}

    Description: Get directives removed by tag
    Service: DirectiveAccess.get_directives_removed_by_tag()
    Auth: Required

GET /directives/id?id={id}
    Response: DirectivesResponse {results: [...]}

    Description: Get directives with specific ID
    Service: DirectiveAccess.get_directives_by_id()
    Auth: Required

GET /directives/tag?tag={tag}
    Response: DirectivesResponse {results: [...]}

    Description: Get directives with specific tag
    Service: DirectiveAccess.get_directives_by_tag()
    Auth: Required

GET /directives/removed/{nodeid}
    Response: List[{criterion_type, criterion_value, directive}]

    Description: Get directives that removed a specific directive
    Service: DirectiveAccess.get_remover_directives()
    Auth: Required

GET /directives/id/{nodeid}
    Response: DirectivesResponse {results: [...]}

    Description: Get directive by node ID
    Service: DirectiveAccess.get_directive_by_node_id()
    Auth: Required
```

### 5.7 Nodes (`api/routers/nodes.py`)

**Purpose:** Node metadata and constant lookup.

```python
POST /nodes/parse_http_request
    Request: HttpRequestQuery {location, host}
    Response: DirectivesResponse {results: [...]}

    Description: Simulate HTTP request to find applicable rules
    Service: DirectiveAccess.filter_by_location_and_host()
    Auth: Required
    WARNING: Currently vulnerable to injection!

GET /nodes/get_metadata/{node_id}
    Response: NodeMetadataResponse {metadata: [(macro, file, line), ...]}

    Description: Get file context for a directive
    Service: AnalyzerAccess.get_metadata_by_node_id()
    Auth: Required

GET /nodes/search_var/{var_name}
    Response: VariableSearchResponse {records: [...]}

    Description: Fulltext search for constants/variables
    Service: DirectiveAccess.search_variable()
    Auth: Required

POST /nodes/get_setnode
    Request: ConstantQuery {var_name, var_value?}
    Response: List[Directive]

    Description: Find where constant is set/defined
    Service: DirectiveAccess.get_set_node()
    Auth: Required

POST /nodes/use_node
    Request: ConstantQuery {var_name, var_value?}
    Response: List[Directive]

    Description: Find where constant is used
    Service: DirectiveAccess.get_use_node()
    Auth: Required

POST /nodes/get_node_ids
    Request: FileContextQuery {file_path, line_num}
    Response: List[int]

    Description: Get directive node IDs from file location
    Service: AnalyzerAccess.get_node_ids_by_file_context()
    Auth: Required
```

### 5.8 Storage (`api/routers/storage.py`)

**Purpose:** File upload/download and dump management.

```python
POST /storage/store_config
    Request: Multipart form {file: UploadFile, nickname: str}
    Response: ConfigUploadResponse {config_id}

    Description: Upload config ZIP file
    Steps:
    1. Create config entry
    2. Extract ZIP
    3. Save all files to database
    4. Fetch dump from WAF service
    5. Save dump
    Service: ConfigAccess.create/save_file/save_dump()
    Auth: Required

POST /storage/config_tree/{config_id}
    Response: List[ConfigTreeResponse]

    Description: Get file tree for config
    Service: ConfigAccess.get_files_by_config()
    Auth: Required

POST /storage/update_config/{config_id}
    Request: FileUpdateRequest {path, content}
    Response: {"success": true}

    Description: Update config file
    Service: ConfigAccess.update_file()
    Auth: Required

POST /storage/get_dump
    Request: {waf_url}
    Response: {"dump": str}

    Description: Fetch dump from WAF service
    Service: External HTTP call
    Auth: Required

POST /storage/store_dump
    Request: {config_id, dump}
    Response: {"success": true}

    Description: Store config dump
    Service: ConfigAccess.save_dump()
    Auth: Required

GET /storage/analysis_progress/{task_id}
    Response: TaskProgressResponse {task_id, status, progress}

    Description: Get analysis task progress
    Service: ConfigAccess.get_task_progress()
    Auth: Required
```

### 5.9 Database (`api/routers/database.py`)

**Purpose:** Database export/import (backup/restore).

```python
POST /database/export/{config_name}
    Response: FileResponse (ZIP file)

    Description: Export Neo4j + PostgreSQL to ZIP
    Service: AnalyzerAccess (for DB queries), filesystem operations
    Auth: Required

POST /database/import/{config_name}
    Request: Multipart form {file: UploadFile}
    Response: {"success": true}

    Description: Import from ZIP backup
    Service: AnalyzerAccess, filesystem operations
    Auth: Required
```

---

## 6. Complete Data Flows

### 6.1 Config Upload and Storage

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User uploads config.zip via frontend                         │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. POST /storage/store_config                                   │
│    Router: api/routers/storage.py                               │
│    Auth: get_current_user() → User                              │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. ConfigAccess.create(nickname)                                │
│    Database: PostgreSQL (files)                                 │
│    Query: INSERT INTO configs (nickname) VALUES (...) RETURNING id│
│    Returns: config_id                                           │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. extract_config(file, config_id, nickname)                   │
│    Utility: common/utils/file_utils.py                         │
│    Action: Unzip to /tmp/{config_id}/                          │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. For each file: ConfigAccess.save_file(config_id, path, content)│
│    Database: PostgreSQL (files)                                 │
│    Query: INSERT INTO files (config_id, path, content) VALUES (...)│
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. HTTP GET {waf_url}/dump                                      │
│    External service call to WAF container                       │
│    Returns: Apache config dump (httpd -D DUMP_CONFIG output)   │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. ConfigAccess.save_dump(config_id, dump)                     │
│    Database: PostgreSQL (files)                                 │
│    Query: INSERT INTO dumps (config_id, dump) VALUES (...)     │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. Return {config_id} to frontend                               │
└─────────────────────────────────────────────────────────────────┘
```

**Time:** ~2-5 seconds
**Databases Modified:** PostgreSQL (files) - configs, files, dumps tables

### 6.2 Config Analysis (Parsing)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User clicks "Analyze" button for config                     │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. POST /configs/analyze/{config_id}                           │
│    Router: api/routers/configs.py                               │
│    Auth: Required                                               │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Generate task_id, create analysis task                      │
│    ConfigAccess.create_analysis_task(config_id, task_id)       │
│    Database: PostgreSQL (files)                                 │
│    Query: INSERT INTO analysis_tasks (id, config_id, status, progress)│
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Start async: POST /analyze/{config_id} (to analyzer service)│
│    Router: api/routers/analyzer.py                              │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. AnalyzerService.analyze_config(config_id)                   │
│    Service: services/analyzer/service.py                        │
│                                                                  │
│    5a. Get files and dump from database                        │
│        ConfigAccess.get_files_by_config(config_id)             │
│        ConfigAccess.get_dump(config_id)                        │
│                                                                  │
│    5b. Write files to /tmp/{config_id}/                        │
│                                                                  │
│    5c. Parse dump file                                          │
│        parse_compiled_config(dump_path) → List[Directive]      │
│        Parser: services/analyzer/parsers/config_parser.py      │
│                                                                  │
│    5d. Clear databases                                          │
│        AnalyzerAccess.clear_schema() (PostgreSQL cwaf)         │
│        AnalyzerAccess.clear_graph() (Neo4j)                    │
│                                                                  │
│    5e. Process each directive (batched for Neo4j)              │
│        For each directive:                                      │
│          - AnalyzerAccess.add_symbol() (file context)          │
│          - AnalyzerAccess.add_macro_def/call() (if macro)      │
│          - Create Neo4j nodes and relationships (batched)      │
│                                                                  │
│    5f. Create indexes                                           │
│        AnalyzerAccess.create_indexes() (Neo4j)                 │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. ConfigAccess.update_parsed_status(config_id, True)          │
│    Database: PostgreSQL (files)                                 │
│    Query: UPDATE configs SET parsed = TRUE WHERE id = ...      │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. ConfigAccess.update_task_status(task_id, "completed")       │
│    Database: PostgreSQL (files)                                 │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. Frontend polls GET /storage/analysis_progress/{task_id}     │
│    Receives: {status: "completed", progress: 100}              │
└─────────────────────────────────────────────────────────────────┘
```

**Time:** ~10-60 seconds (depending on config size)
**Databases Modified:** PostgreSQL (cwaf), Neo4j

### 6.3 Directive Querying

```
┌─────────────────────────────────────────────────────────────────┐
│ User searches for directive by tag "attack-sqli"                │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ GET /directives/tag?tag=attack-sqli                             │
│ Router: api/routers/directives.py                               │
│ Auth: Required                                                   │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ DirectiveAccess.get_directives_by_tag("attack-sqli")           │
│ Database: Neo4j                                                  │
│ Cypher: MATCH (n)-[:Has]->(t:Tag {value: $tag}) RETURN n       │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ Return List[Directive] as JSON                                  │
│ Response: {results: [{node_id, type, args, ...}, ...]}        │
└─────────────────────────────────────────────────────────────────┘
```

**Time:** <1 second
**Databases Queried:** Neo4j

### 6.4 Chat Interaction

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User sends message "Show me SQL injection rules"            │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. POST /chat/ui_graph                                          │
│    Router: api/routers/chatbot.py                               │
│    Request: {messages: [...], config: {thread_id: "..."}}     │
│    Auth: get_current_user() → User                              │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. ChatbotService.chat(thread_id, messages, user_id)          │
│    Service: services/chatbot/service.py                         │
│                                                                  │
│    3a. Verify ownership                                         │
│        ThreadAccess.get_by_id(thread_id)                       │
│        Check: thread.user_id == user_id                        │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. UIGraph.invoke(messages, configuration)                     │
│    LangGraph: services/chatbot/graph/ui_graph.py               │
│                                                                  │
│    4a. Load conversation history                               │
│        PostgresSaver.get(thread_id) → checkpoint               │
│                                                                  │
│    4b. LLM decides to use tool: filter_rule                    │
│        DirectiveAccess.filter_by_location_and_host(...)        │
│        Cypher query to Neo4j                                    │
│                                                                  │
│    4c. LLM generates response based on tool result             │
│                                                                  │
│    4d. Auto-save to checkpoint                                 │
│        PostgresSaver.put() → saves messages                    │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. ThreadAccess.update_timestamp(thread_id)                    │
│    Database: PostgreSQL (chatbot)                               │
│    Query: UPDATE users_threads SET updated_at = now() WHERE ...│
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. Return AI response to frontend                              │
│    Response: {messages: [{role: "assistant", content: "..."}]}│
└─────────────────────────────────────────────────────────────────┘
```

**Time:** ~2-10 seconds (depends on LLM)
**Databases Queried:** PostgreSQL (chatbot), Neo4j (via tools)

### 6.5 User Authentication

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User submits login form                                     │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. POST /auth/login                                             │
│    Router: api/routers/auth.py                                  │
│    Request: Form {username, password}                          │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. UserAccess.get_by_username(username)                        │
│    Database: PostgreSQL (chatbot)                               │
│    Query: SELECT users_id, username, password FROM users ...   │
│    Returns: User (with hashed_password)                        │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. verify_password(plain_password, hashed_password)            │
│    Auth: common/auth/password.py                                │
│    Uses: bcrypt.checkpw()                                       │
│    Returns: True/False                                          │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. create_access_token({"sub": username})                      │
│    Auth: common/auth/jwt.py                                     │
│    Creates: JWT with 30min expiration                          │
│    Returns: token string                                        │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. Return {access_token, token_type: "bearer"}                 │
│    Frontend stores token in localStorage                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 7. Subsequent requests include: Authorization: Bearer <token>  │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. get_current_user(token)                                      │
│    Dependency: common/auth/dependencies.py                      │
│                                                                  │
│    8a. jwt.decode(token) → {"sub": username}                   │
│    8b. UserAccess.get_by_username(username) → User             │
│    8c. Inject User into endpoint parameter                     │
└─────────────────────────────────────────────────────────────────┘
```

**Time:** <1 second
**Databases Queried:** PostgreSQL (chatbot)

### 6.6 Thread Management

```
┌─────────────────────────────────────────────────────────────────┐
│ User clicks "New Chat"                                          │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ POST /chat/threads                                              │
│ Router: api/routers/chatbot.py                                  │
│ Auth: get_current_user() → User                                 │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ ThreadAccess.create(user.id)                                   │
│ Database: PostgreSQL (chatbot)                                  │
│ Query: INSERT INTO users_threads (user_id) VALUES (...) RETURNING thread_id│
│ Returns: thread_id (UUID)                                       │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ Return {thread_id} to frontend                                  │
│ Frontend navigates to chat view with thread_id                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ User loads chat history                                         │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ GET /chat/threads/{thread_id}                                   │
│ Router: api/routers/chatbot.py                                  │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ ThreadAccess.get_messages(thread_id)                           │
│ Uses: PostgresSaver.get(thread_id) → checkpoint                │
│ Returns: List[BaseMessage] (from LangGraph checkpoint)         │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ Convert messages to dict format                                 │
│ Return [{role: "user", content: "..."}, ...]                   │
└─────────────────────────────────────────────────────────────────┘
```

**Time:** <1 second
**Databases Queried:** PostgreSQL (chatbot)

---

## 7. Import Reference

### How to Import and Use Each Layer

#### Configuration

```python
# Anywhere in the codebase
from common.config import settings

neo4j_url = settings.neo4j_url
is_production = settings.environment == "prod"
```

#### Authentication

```python
# In API routers
from fastapi import Depends
from common.auth.dependencies import get_current_user
from common.models.domain import User

@router.get("/protected")
async def protected_endpoint(
    current_user: User = Depends(get_current_user)
):
    # User is authenticated here
    print(f"User {current_user.username} accessed endpoint")
```

#### Database Connections

```python
# In data access classes
from common.database.connections.neo4j import get_neo4j_driver
from common.database.connections.postgres import get_postgres_pool

driver = get_neo4j_driver()
pool = get_postgres_pool('files')  # or 'cwaf', 'chatbot'
```

#### Data Access

```python
# In services or routers (via dependency injection)
from api.dependencies import get_config_access
from common.database.access.configs import ConfigAccess

# In service
class AnalyzerService:
    def __init__(self, config_access: ConfigAccess):
        self.config_access = config_access

    def analyze(self, config_id):
        config = self.config_access.get_by_id(config_id)

# In router
@router.get("/configs")
async def get_configs(
    config_access: ConfigAccess = Depends(get_config_access)
):
    return config_access.get_all()
```

#### Services

```python
# In routers (via dependency injection)
from api.dependencies import get_analyzer_service
from services.analyzer.service import AnalyzerService

@router.post("/analyze/{config_id}")
async def analyze(
    config_id: int,
    analyzer: AnalyzerService = Depends(get_analyzer_service)
):
    result = analyzer.analyze_config(config_id)
    return {"status": "completed", "directives": result}
```

#### Models

```python
# Domain models (anywhere)
from common.models.domain import User, Config, Directive

user = User(id=1, username="admin", hashed_password="...")
config = Config(id=1, nickname="prod", parsed=True, created_at=datetime.now())

# API schemas (in routers)
from api.schemas.requests import ConfigUploadRequest
from api.schemas.responses import ConfigResponse

@router.post("/configs", response_model=ConfigResponse)
async def create_config(request: ConfigUploadRequest):
    ...
    return ConfigResponse.from_domain(config)

# Service models (in services only)
from services.analyzer.models.context import ParseContext

context = ParseContext(
    current_file="/etc/httpd/httpd.conf",
    line_number=42,
    scope_stack=["VirtualHost", "Directory"],
    variables={}
)
```

---

## Summary

This document provides a complete reference for understanding the WAF-GUARD backend architecture:

- **Models** are organized into 3 types: domain (shared), API schemas (HTTP contracts), and service-specific (internal)
- **Data Access Layer** centralizes all database queries in `common/database/access/`
- **Services** contain business logic and orchestrate data access
- **API Routers** are thin HTTP layers that delegate to services
- **Data flows** show how requests move through the system end-to-end

Use this document as a reference while implementing the new architecture or when onboarding new developers.

**Next Steps:**
1. Review BACKEND_ARCHITECTURE.md for implementation details
2. Start migration following the phase-by-phase plan
3. Test each layer independently before integration
4. Update this document as the codebase evolves

---

**Document Version:** 1.0
**Last Updated:** 2025-11-13
**Maintainer:** WAF-GUARD Team
