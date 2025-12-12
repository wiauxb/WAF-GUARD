# Documentation of Backend
## Services


### AuthService
``` python
def register_user(username: str, password: str) -> UserInfo
    # Create a new user account with hashed password
def login(username: str, password: str) -> TokenResponse
    # Authenticate user and generate JWT access token
def verify_token(token: str) -> UserInfo
    # Verify JWT token and return user information
def get_user_by_id(user_id: int) -> UserInfo
    # Retrieve user by ID
def set_user_active_configuration(user_id: int, configuration_id: int) -> bool
    # Set which configuration the user is currently viewing
def update_user_password(user_id: int, old_password: str, new_password: str) -> bool
    # Change user password after verifying old password
```

#### Request Schemas
```python

```

#### Response Schemas
```python
class UserInfo(BaseModel):
    id: int
    username: str
    is_admin: bool
    active_configuration_id: Optional[int]
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class UserWithActiveConfigResponse(BaseModel):
    user: UserInfo
    active_config: Optional[ConfigurationResponse]

```

### ConfigManagerService
```python
def upload_configuration(user_id: int, zip_file: UploadFile, request: ConfigurationUploadRequest) -> ConfigurationResponse
    # Upload configuration zip, generate dump via WAF, store files, create DB record
    # Process:
    # 1. Store and extract zip file
    # 2. Call WAFService.generate_dump() → receives gzip-compressed dump (bytes)
    # 3. ConfigFileStorage.store_dump() → streams decompression to disk (1MB chunks)
    # 4. Create DB record with metadata
    # Performance: Handles large dumps (>1MB) efficiently with minimal memory overhead
def get_all_configurations(order_by: str = "created_at", order_desc: bool = True) -> List[ConfigurationResponse]
    # List all configurations
def get_configuration_by_id(configuration_id: int) -> ConfigurationResponse
    # Get configuration metadata by ID
def get_configuration_by_name(name: str) -> ConfigurationResponse
    # Get configuration metadata by name
def update_configuration_metadata(configuration_id: int, updates: ConfigurationUpdateRequest) -> ConfigurationResponse
    # Update configuration name and/or description
def delete_configuration(configuration_id: int) -> bool
    # Delete configuration and all associated files and data
def get_dump_path(configuration_id: int) -> str
    # Get filesystem path to configuration dump file (internal use by ParserService)
def get_configuration_tree(configuration_id: int, path: str = "/") -> ConfigTreeResponse
    # Get file tree structure (if path is directory) or file content (if path is file)
def update_file_content(configuration_id: int, file_path: str, content: str) -> bool
    # Update configuration file content (sets parsing_status to not_parsed)
```

#### Request Schemas
```python
class ConfigurationUploadRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    waf_url: str = Field(pattern=r'^https?://')

class ConfigurationUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    
    @root_validator
    def at_least_one_field(cls, values):
        if not any(values.values()):
            raise ValueError('Must provide at least one field')
        return values

class ConfigurationListFilters(BaseModel):
    parsing_status: Optional[Literal["not_parsed", "parsing", "parsed", "error"]] = None
    created_by_user_id: Optional[int] = None
    order_by: Literal["created_at", "name", "parsed_at"] = "created_at"
    order_desc: bool = True

```

#### Response Schemas
```python
class ConfigurationResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    file_path: str
    file_hash: Optional[str]
    file_size: Optional[int]
    parsing_status: str
    parsing_error: Optional[str]
    created_by_user_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    parsed_at: Optional[datetime]

class ConfigTreeResponse(BaseModel):
    is_file: bool
    path: str
    # If directory:
    children: Optional[List[Dict[str, Any]]]  # [{name, type, size}, ...]
    # If file:
    content: Optional[str]

```
### WAFService
```python
def generate_dump(config_zip_path: str, waf_url: str, timeout: int = 120) -> bytes
    # Send configuration zip to WAF container's /get_dump endpoint
    # Returns gzip-compressed Apache dump (binary)
    # Compression typically achieves 70-90% size reduction
```

**Implementation Details:**
- Sends configuration zip to WAF container via HTTP POST
- WAF container returns gzip-compressed dump instead of JSON (performance optimization)
- Returns compressed binary content (not decompressed)
- ConfigFileStorage handles decompression during disk write (streaming in 1MB chunks)
- Network transfer size reduced by 70-90% compared to plain text

**Data Flow:**
```
ConfigZip → WAFService → Gzip Binary → ConfigFileStorage → Decompressed Text File
```

#### Request Schemas
```python
# No request schemas - uses filesystem path
```

#### Response Schemas
```python
# Returns: bytes (gzip-compressed Apache config dump)
```
### ParserService
```python
def parse_configuration(configuration_id: int, options: Optional[ParseConfigurationRequest] = None) -> ParseResponse
def get_parsing_status(configuration_id: int) -> ParseStatusResponse
def reparse_configuration(configuration_id: int) -> ParseResponse
```

#### Request Schemas
```python
class ParseConfigurationRequest(BaseModel):
    force_reparse: bool = False

```

#### Response Schemas
```python
class ParseResponse(BaseModel):
    configuration_id: int
    parsing_status: str
    total_symbols: Optional[int]
    total_macros: Optional[int]
    total_macro_calls: Optional[int]
    parsing_error: Optional[str]
    parsed_at: Optional[datetime]

class ParseStatusResponse(BaseModel):
    configuration_id: int
    parsing_status: str
    parsed_at: Optional[datetime]
    parsing_error: Optional[str]

```

### ChatbotService

**Overview**: AI-powered chatbot for WAF configuration assistance using LangGraph and OpenAI.

**Architecture**:
- **LangGraph**: Manages conversational AI with ReAct agent pattern
- **PostgresSaver**: Automatic conversation persistence (checkpointing)
- **Tools**: 5 specialized tools for WAF configuration analysis
- **Streaming**: Real-time response generation via Server-Sent Events (SSE)

```python
def create_conversation(user_id: int, request: ConversationCreateRequest) -> ConversationResponse
    # Create a new conversation thread with optional configuration context
    # Generates unique thread_id for LangGraph persistence

def get_user_conversations(user_id: int, filters: Optional[ConversationListFilters] = None) -> List[ConversationResponse]
    # List user's conversations with optional filtering and pagination

def send_message(thread_id: str, message_request: SendMessageRequest, user_id: int) -> ChatResponse
    # Send message and get chatbot response (uses LangGraph + selected graph)
    # Process:
    # 1. Validate user ownership
    # 2. Get graph from registry (default: "ui_graph_v1")
    # 3. Invoke graph with checkpointer (automatic persistence)
    # 4. Extract assistant response
    # 5. Extract tool usage information (name, arguments, results)
    # 6. Update conversation timestamp
    # Returns complete response message with tools_used list

async def send_message_stream(thread_id: str, message_request: SendMessageRequest, user_id: int) -> AsyncGenerator[str]
    # Stream message response in real-time (yields content chunks)
    # Uses LangGraph astream() with "messages" mode for token-level streaming
    # Ideal for real-time frontend updates via Server-Sent Events (SSE)

def get_conversation_history(thread_id: str, user_id: int, limit: Optional[int] = None) -> ConversationHistoryResponse
    # Get full message history for a conversation from LangGraph checkpointer
    # Messages are persisted automatically by LangGraph PostgresSaver

def delete_conversation(thread_id: str, user_id: int) -> bool
    # Delete conversation metadata AND LangGraph checkpoints
    # Full cleanup of both metadata and conversation history

def rename_conversation(thread_id: str, new_title: str, user_id: int) -> ConversationResponse
    # Rename a conversation
```

#### LangGraph Implementation

**Directory Structure:**
```
services/chatbot/
├── graphs/              # LangGraph implementations
│   ├── registry.py      # Graph factory (get_graph, register_graph)
│   ├── states.py        # State schemas (MessagesState, WAFAnalysisState)
│   └── simple_graphs.py # build_ui_graph_v1() - ReAct agent
├── tools/               # LangChain tool definitions
│   ├── registry.py      # Tool categories (get_tools_for_categories)
│   └── waf/             # WAF analysis tools (5 tools)
│       ├── filter_rule.py
│       ├── get_constant_info.py
│       ├── get_directives.py
│       ├── macro_trace.py
│       └── removed_by.py
├── prompts/             # System prompts per graph
│   └── agent_prompts.py
└── utils/               # Error handling utilities
    └── error_handling.py
```

**Available Graphs:**
- `ui_graph_v1`: Simple ReAct agent with 5 WAF tools (default)
  - Uses `create_agent()` from LangChain (current non-deprecated API)
  - Uses `prompt` parameter for system prompt injection
  - Automatic tool calling and response generation
  - Checkpointer handles conversation persistence
  - Extracts and returns tool usage information (name, arguments, results)

**Available Tools** (Category: "waf"):
1. `filter_rule(location, host)` - Filter rules by location and host patterns
2. `get_constant_info(constant_name)` - Search for constants/variables
3. `get_directives_with_constant(constant_name)` - Find directives using a constant
4. `get_macro_call_trace(node_id)` - Get macro call stack trace
5. `removed_by(node_id)` - Find which directives removed a node

**Note**: Tools currently return **dummy data** as backend analysis services are still in development. Real integration pending.

**Tool Call Extraction**:
- The service automatically extracts tool calls from the LangGraph response
- Matches AIMessage tool_calls with ToolMessage results
- Returns complete tool usage information (name, arguments, results) in ChatResponse.tools_used

**Configuration** (from settings):
- `OPENAI_MODEL`: Model for chatbot (default: "gpt-4o-mini")
- `CHATBOT_TEMPERATURE`: Response temperature (default: 0.7)
- `OPENAI_API_KEY`: Required for OpenAI API access

#### Request Schemas
```python
class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    configuration_id: Optional[int] = Field(None, gt=0)

class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    configuration_id: Optional[int] = Field(None, gt=0)
    graph_name: Optional[str] = Field(default="ui_graph_v1")  # LangGraph to use
    stream: bool = Field(default=False)  # Enable streaming response

class ConversationListFilters(BaseModel):
    configuration_id: Optional[int] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
```

#### Response Schemas
```python
class ConversationResponse(BaseModel):
    id: int
    user_id: int
    configuration_id: Optional[int]
    thread_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    configuration_name: Optional[str]  # Joined from configurations

class ToolCallInfo(BaseModel):
    name: str  # Name of the tool that was called
    arguments: Dict[str, Any]  # Arguments passed to the tool
    result: Any  # Result returned by the tool

class ChatResponse(BaseModel):
    message: str
    thread_id: str
    configuration_id: Optional[int]
    created_at: datetime
    tools_used: List[ToolCallInfo]  # List of tools used to generate the response

class MessageResponse(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime

class ConversationHistoryResponse(BaseModel):
    conversation: ConversationResponse
    messages: List[MessageResponse]
    total_messages: int
```

#### API Endpoints

**Standard (Non-Streaming):**
```
POST   /api/v1/chatbot/conversations/{thread_id}/messages
```

**Streaming (SSE):**
```
POST   /api/v1/chatbot/conversations/{thread_id}/messages/stream
```
Returns: `text/event-stream` with real-time response chunks

**Frontend Integration Example:**
```javascript
// Streaming response
const eventSource = new EventSource(
  `/api/v1/chatbot/conversations/${threadId}/messages/stream`,
  { headers: { Authorization: `Bearer ${token}` } }
);
eventSource.onmessage = (event) => {
  console.log(event.data); // Response chunk
};
```

#### Future Enhancements
- **Tool Backend Integration**: Connect tools to real AnalysisService/ParserService
- **Workflow Graphs**: Routing patterns for complex queries
- **Multi-Agent Orchestration**: Supervisor with specialized agents (LangGraph subgraphs)
- **Deep Agents**: Planning, file system integration, subagent spawning
- **RAG Integration**: Vector store with ModSecurity documentation

### AnalysisService
```python
```

#### Request Schemas
```python
```

#### Response Schemas
```python
```

### LogAnalysisService
```python
def classify_logs(user_id: int, file: UploadFile, configuration_id: Optional[int] = None) -> LogClassificationResponse
    # Process and classify log file
    # Process:
    # 1. Validate file (.san, .txt, audit.log, max 500MB)
    # 2. Create session with UUID
    # 3. Parse ModSecurity audit logs
    # 4. Normalize and format logs
    # 5. Send to ML service for classification
    # 6. Store results in JSON file (backend/src/storage/logs/{session_id}.json)
    # 7. Return summary with categories and counts
    
def get_filtered_logs(session_id: str, filters: LogFilter, include_logs: bool = False) -> FilteredLogsResponse
    # Apply pandas filters to logs (time, columns, exact/contains/greater_than/less_than)
    # Recalculates categories based on filtered data
    # Returns statistics with log indices
    
def get_log_by_transaction(session_id: str, transaction_id: str) -> Optional[LogDetailResponse]
    # Get detailed log entry by transaction ID
    
def get_category_details(session_id: str, category: str, limit: int = 100, offset: int = 0) -> CategoryDetailsResponse
    # Get detailed logs for a specific category with pagination
    
def get_user_sessions(user_id: int, limit: int = 50, offset: int = 0) -> List[LogAnalysisSessionResponse]
    # List all analysis sessions for a user
    
def delete_session(session_id: str, user_id: int) -> bool
    # Delete a session JSON file (with authorization check)
```

#### Request Schemas
```python
class LogFilter(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    columns: List[Dict[str, Any]] = []  # [{"name": "status_code", "value": 403, "type": "exact"}]
    # Filter types: 'exact', 'contains', 'greater_than', 'less_than'

class CategoryRequest(BaseModel):
    category: str
    log_indices: List[int]
    limit: Optional[int] = 100
    offset: Optional[int] = 0

class UserSessionRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
```

#### Response Schemas
```python
class LogClassificationResponse(BaseModel):
    session_id: str  # UUID
    total_logs: int
    categories: List[LogCategoryResponse]
    columns: List[str]

class LogCategoryResponse(BaseModel):
    category: str
    count: int
    percentage: Optional[float]
    log_indices: Optional[List[int]]  # Indices in DataFrame

class FilteredLogsResponse(BaseModel):
    session_id: str
    total_logs: int  # Before filtering
    filtered_logs: int  # After filtering
    categories: List[LogCategoryResponse]  # Recalculated for filtered data
    columns: List[str]
    applied_filters: Dict[str, Any]
    logs: Optional[List[Dict[str, Any]]]  # Full logs if include_logs=True

class LogEntryResponse(BaseModel):
    id: int = 0  # No DB ID (JSON storage)
    transaction_id: str
    timestamp: Optional[datetime]
    remote_address: Optional[str]
    remote_port: Optional[int]
    http_method: Optional[str]
    request_url: Optional[str]
    user_agent: Optional[str]
    response_status_code: Optional[int]
    response_status: Optional[str]
    payload: Optional[str]
    messages: Optional[List[str]]
    message_tags: Optional[List[str]]
    predicted_category: Optional[str]
    prediction_probabilities: Optional[Dict[str, float]]
    formatted_log: Optional[str]

class LogAnalysisSessionResponse(BaseModel):
    id: int = 0
    session_id: str  # UUID
    user_id: int
    configuration_id: Optional[int]
    filename: str
    file_size: Optional[int]
    status: str  # "processing", "completed", "failed"
    total_logs: Optional[int]
    error_message: Optional[str]
    created_at: str  # ISO format
    completed_at: Optional[str]
    categories: Optional[Dict[str, int]]  # Not included in list view

class LogDetailResponse(BaseModel):
    session_id: str
    transaction_id: str
    log: Dict[str, Any]  # Raw parsed log data

class CategoryDetailsResponse(BaseModel):
    session_id: str
    category: str
    total_count: int
    logs: List[LogEntryResponse]
```

**Storage Details:**
- Sessions stored as JSON files in `backend/src/storage/logs/{session_id}.json`
- Each file contains: metadata, all logs, categories, and DataFrame (for filtering)
- No database tables - pure file-based storage
- Pandas DataFrame serialized as dict for filtering support

**JSON Structure:**
```json
{
  "session_id": "uuid",
  "user_id": 1,
  "filename": "audit.log",
  "status": "completed",
  "total_logs": 1500,
  "categories": {"SQL Injection": 450, "XSS": 300},
  "logs": [{...}],
  "dataframe": [{...}]  // Serialized for pandas filtering
}
```

## API

**Base URL**: `/api/v1`


---

## Auth Routes (`/auth`)

| Method | Endpoint | Auth | Request | Response | Description |
|--------|----------|------|---------|----------|-------------|
| POST | `/register` | 🔓 | `RegisterRequest` | `UserInfo` | Register new user |
| POST | `/login` | 🔓 | `LoginRequest` | `TokenResponse` | Login and get token |
| GET | `/me` | ✅ | - | `UserInfo` | Get current user |
| PUT | `/me/password` | ✅ | `PasswordChangeRequest` | `SuccessResponse` | Change password |
| PUT | `/me/active-config` | ✅ | `SetActiveConfigRequest` | `SuccessResponse` | Set active config |

### Request Schemas

```python
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=255, pattern=r'^[a-zA-Z0-9_-]+$')
    password: str = Field(min_length=4, max_length=255)
    password_confirm: str = Field(min_length=4, max_length=255)

    @validator('password_confirm')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=4, max_length=255)

class PasswordChangeRequest(BaseModel):
    old_password: str = Field(min_length=4, max_length=255)
    new_password: str = Field(min_length=4, max_length=255)
    new_password_confirm: str = Field(min_length=4, max_length=255)
    
    @validator('new_password_confirm')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

class SetActiveConfigRequest(BaseModel):
    configuration_id: int = Field(gt=0)
```

### Response Schemas

```python
class UserInfo(BaseModel):
    id: int
    username: str
    is_admin: bool
    active_configuration_id: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
```

---

## Configuration Routes (`/configurations`)

| Method | Endpoint | Auth | Request | Response | Description |
|--------|----------|------|---------|----------|-------------|
| POST | `/` | ✅ | File Upload (see below) | `ConfigurationResponse` | Upload config zip |
| GET | `/` | ✅ | Query: order_by, order_desc | `List[ConfigurationResponse]` | List all configs |
| GET | `/{id}` | ✅ | - | `ConfigurationResponse` | Get config by ID |
| GET | `/by-name/{name}` | ✅ | - | `ConfigurationResponse` | Get config by name |
| PATCH | `/{id}` | ✅ | `ConfigurationUpdateRequest` | `ConfigurationResponse` | Update metadata |
| DELETE | `/{id}` | ✅ | - | `SuccessResponse` | Delete config |
| GET | `/{id}/tree` | ✅ | Query: path | `ConfigTreeResponse` | Get file tree or content |
| PUT | `/{id}/files/{path:path}` | ✅ | `FileUpdateRequest` | `SuccessResponse` | Update file content |

### Request Schemas

```python
# POST / - File Upload (multipart/form-data)
# Special case: File upload with form fields
# Implementation:
@router.post("/")
async def upload_configuration(
    file: UploadFile = File(..., description="Configuration zip file"),
    name: str = Form(..., min_length=1, max_length=255),
    description: Optional[str] = Form(None, max_length=2000),
    current_user: UserInfo = Depends(get_current_user)
):
    # file is the zip, name and description are form fields
    request = ConfigurationUploadRequest(name=name, description=description)
    ...

class ConfigurationUploadRequest(BaseModel):
    """Used internally after extracting form data"""
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)

class ConfigurationUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    
    @root_validator
    def at_least_one_field(cls, values):
        if not any(values.values()):
            raise ValueError('Must provide at least one field')
        return values

class FileUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=1_000_000)
```

### Response Schemas

```python
class ConfigurationResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    file_path: str
    file_hash: Optional[str]
    file_size: Optional[int]
    parsing_status: str  # "not_parsed", "parsing", "parsed", "error"
    parsing_error: Optional[str]
    created_by_user_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    parsed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class ConfigTreeResponse(BaseModel):
    is_file: bool
    path: str
    # If directory:
    children: Optional[List[Dict[str, Any]]] = None  # [{"name": "file.conf", "type": "file", "size": 1024}, ...]
    # If file:
    content: Optional[str] = None
```

---

## Parser Routes (`/parser`)

| Method | Endpoint | Auth | Request | Response | Description |
|--------|----------|------|---------|----------|-------------|
| POST | `/parse/{id}` | ✅ | `ParseRequest` | `ParseResponse` | Parse configuration |
| GET | `/status/{id}` | ✅ | - | `ParseStatusResponse` | Get parsing status |
| POST | `/reparse/{id}` | ✅ | - | `ParseResponse` | Force reparse |

### Request Schemas

```python
class ParseRequest(BaseModel):
    force_reparse: bool = Field(default=False)
```

### Response Schemas

```python
class ParseResponse(BaseModel):
    configuration_id: int
    parsing_status: str  # "parsing", "parsed", "error"
    total_symbols: Optional[int]
    total_macros: Optional[int]
    total_macro_calls: Optional[int]
    parsing_error: Optional[str]
    parsed_at: Optional[datetime]

class ParseStatusResponse(BaseModel):
    configuration_id: int
    parsing_status: str  # "not_parsed", "parsing", "parsed", "error"
    parsed_at: Optional[datetime]
    parsing_error: Optional[str]
```

---

## Common Schemas

```python
class SuccessResponse(BaseModel):
    success: bool = True
    message: str

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    field_errors: Optional[Dict[str, List[str]]] = None
```

---

## Logs Routes (`/logs`)

| Method | Endpoint | Auth | Request | Response | Description |
|--------|----------|------|---------|----------|-------------|
| POST | `/classify` | ✅ | File Upload + Query | `LogClassificationResponse` | Upload and classify logs |
| GET | `/sessions` | ✅ | `UserSessionRequest` | `List[LogAnalysisSessionResponse]` | List user's sessions |
| GET | `/sessions/{session_id}/log/{transaction_id}` | ✅ | - | `LogDetailResponse` | Get specific log detail |
| POST | `/sessions/{session_id}/filter` | ✅ | `LogFilter` | `FilteredLogsResponse` | Filter logs with pandas |
| POST | `/sessions/{session_id}/categories` | ✅ | `CategoryRequest` | `CategoryDetailsResponse` | Get logs by category |
| DELETE | `/sessions/{session_id}` | ✅ | - | `SuccessResponse` | Delete session |

### Request Schemas

```python
# POST /classify - File Upload (multipart/form-data)
@router.post("/classify")
async def classify_log_file(
    file: UploadFile = File(..., description="Log file (.san, .txt, or audit.log)"),
    configuration_id: Optional[int] = Query(None, description="Optional configuration context")
):
    # file: .san, .txt, or audit.log (max 500MB)
    # configuration_id: Optional link to configuration

class LogFilter(BaseModel):
    """Filters for querying log entries"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    columns: List[Dict[str, Any]] = []
    # Column filter format: {"name": "column_name", "value": filter_value, "type": "exact|contains|greater_than|less_than"}

class CategoryRequest(BaseModel):
    """Request for category details"""
    category: str
    log_indices: List[int]
    limit: Optional[int] = 100
    offset: Optional[int] = 0

class UserSessionRequest(BaseModel):
    """Pagination for session list"""
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
```

### Response Schemas

```python
class LogClassificationResponse(BaseModel):
    """Response after log classification"""
    session_id: str  # UUID for the analysis session
    total_logs: int
    categories: List[LogCategoryResponse]
    columns: List[str]  # Available columns in the dataset

class LogCategoryResponse(BaseModel):
    """Category statistics"""
    category: str
    count: int
    percentage: Optional[float] = None
    log_indices: Optional[List[int]] = None  # DataFrame indices for filtered results

class FilteredLogsResponse(BaseModel):
    """Response for filtered log queries"""
    session_id: str
    total_logs: int  # Total before filtering
    filtered_logs: int  # Total after filtering
    categories: List[LogCategoryResponse]  # Recalculated for filtered data
    columns: List[str]
    applied_filters: Dict[str, Any]
    logs: Optional[List[Dict[str, Any]]] = None  # Full logs if include_logs=True

class LogEntryResponse(BaseModel):
    """Individual log entry details"""
    id: int = 0  # Always 0 (no DB storage)
    transaction_id: str
    timestamp: Optional[datetime]
    remote_address: Optional[str]
    remote_port: Optional[int]
    http_method: Optional[str]
    request_url: Optional[str]
    user_agent: Optional[str]
    response_status_code: Optional[int]
    response_status: Optional[str]
    payload: Optional[str]
    messages: Optional[List[str]]
    message_tags: Optional[List[str]]
    predicted_category: Optional[str]
    prediction_probabilities: Optional[Dict[str, float]]
    formatted_log: Optional[str]

class LogAnalysisSessionResponse(BaseModel):
    """Log analysis session metadata"""
    id: int = 0  # Always 0 (no DB storage)
    session_id: str  # UUID
    user_id: int
    configuration_id: Optional[int]
    filename: str
    file_size: Optional[int]
    status: str  # "processing", "completed", "failed"
    total_logs: Optional[int]
    error_message: Optional[str]
    created_at: str  # ISO datetime string
    completed_at: Optional[str]
    categories: Optional[Dict[str, int]] = None  # Only included in detail view

class LogDetailResponse(BaseModel):
    """Single log detail with raw data"""
    session_id: str
    transaction_id: str
    log: Dict[str, Any]  # Complete raw parsed log structure

class CategoryDetailsResponse(BaseModel):
    """Detailed logs for a specific category"""
    session_id: str
    category: str
    total_count: int
    logs: List[LogEntryResponse]
```

### Storage Implementation

**File-Based Storage (JSON):**
- Location: `backend/src/storage/logs/{session_id}.json`
- No database tables required
- Each session = one JSON file
- Includes complete DataFrame for pandas filtering

**Session File Structure:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "configuration_id": null,
  "filename": "audit.log",
  "file_size": 1024000,
  "file_hash": "sha256...",
  "status": "completed",
  "total_logs": 1500,
  "error_message": null,
  "created_at": "2024-12-10T10:30:00",
  "completed_at": "2024-12-10T10:35:00",
  "categories": {
    "SQL Injection": 450,
    "XSS": 300,
    "Normal": 750
  },
  "logs": [
    {
      "transaction_id": "xyz123",
      "timestamp": "2024-12-10T10:30:00Z",
      "remote_address": "192.168.1.1",
      "http_method": "POST",
      "request_url": "/login",
      "response_status_code": 403,
      "predicted_category": "SQL Injection",
      "prediction_probabilities": {
        "SQL Injection": 0.95,
        "XSS": 0.03
      },
      "formatted_log": "...",
      "raw_data": {...}
    }
  ],
  "dataframe": [...]  // Serialized pandas DataFrame for filtering
}
```

### Filtering Examples

**Time-based filtering:**
```json
POST /api/v1/logs/sessions/{session_id}/filter
{
  "start_time": "2024-12-01T00:00:00Z",
  "end_time": "2024-12-31T23:59:59Z"
}
```

**Column-based filtering:**
```json
POST /api/v1/logs/sessions/{session_id}/filter
{
  "columns": [
    {"name": "response_status_code", "value": 403, "type": "exact"},
    {"name": "request_url", "value": "/admin", "type": "contains"},
    {"name": "remote_port", "value": 1024, "type": "greater_than"}
  ]
}
```

**Combined filtering with full logs:**
```json
POST /api/v1/logs/sessions/{session_id}/filter?include_logs=true
{
  "start_time": "2024-12-10T00:00:00Z",
  "columns": [
    {"name": "predicted_category", "value": "SQL Injection", "type": "exact"}
  ]
}
```

---



### FastAPI Implementation

```python
from fastapi import File, Form, UploadFile

@router.post("/configurations")
async def upload_configuration(
    file: UploadFile = File(...),  # ← The ZIP file
    name: str = Form(...),          # ← Text field
    description: Optional[str] = Form(None),  # ← Optional text field
    current_user: UserInfo = Depends(get_current_user)
):
    # file.filename = "config.zip"
    # file.content_type = "application/zip"
    # await file.read() = binary zip content
    
    # name = "My Config"
    # description = "Test description"
    
    request = ConfigurationUploadRequest(name=name, description=description)
    return config_manager.upload_configuration(current_user.id, file, request)
```


## Status Codes

- `200` OK (success)
- `201` Created (new resource)
- `400` Bad Request (validation error)
- `401` Unauthorized (auth failed)
- `404` Not Found (resource missing)
- `409` Conflict (duplicate name/username)
- `500` Internal Server Error

---

**Total Routes:** 25 endpoints across 4 route groups








# WAF-Guard Database Schema Documentation

## Overview
This schema supports multi-configuration WAF management with proper relational integrity. All users can access all configurations (internal tool). Each user can have one active configuration they're currently viewing.

---

## Schema Design Principles

1. **Shared configurations**: All users access all configurations
2. **User-specific state**: Each user has one active configuration
3. **Configuration isolation**: Each config maintains independent parsing data
4. **No data loss**: Configurations are never dumped when switching
5. **Simple parsing status**: Not parsed, parsing, or parsed
6. **Filesystem storage**: Configuration files stored on disk, not in DB

---

## Core Tables

### **users**
User accounts and authentication.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | User identifier |
| `username` | VARCHAR(255) | UNIQUE, NOT NULL | Unique username |
| `hashed_password` | VARCHAR(255) | NOT NULL | Bcrypt hashed password |
| `active_configuration_id` | INTEGER | FK → configurations(id) ON DELETE SET NULL | Currently active config for this user |
| `is_admin` | BOOLEAN | DEFAULT FALSE | Admin privileges flag |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Account creation timestamp |

**Indexes:**
- Primary key on `id`
- Unique index on `username`
- Index on `active_configuration_id`

**Notes:**
- `active_configuration_id` is nullable (user might not have selected any config yet)
- If configuration is deleted, this field automatically becomes NULL
- All users can access all configurations; this just tracks their current view

---

## Configuration Management

### **configurations**
Master table for WAF configurations. Configurations are shared across all users.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Configuration identifier |
| `name` | VARCHAR(255) | UNIQUE, NOT NULL | Configuration name (must be unique) |
| `description` | TEXT | | Optional configuration description |
| `file_path` | VARCHAR(500) | NOT NULL | Path to configuration zip in storage |
| `file_hash` | VARCHAR(64) | | SHA256 hash for integrity checking |
| `file_size` | INTEGER | | Total size in bytes |
| `parsing_status` | VARCHAR(50) | DEFAULT 'not_parsed' | Status: not_parsed, parsing, parsed, error |
| `parsing_error` | TEXT | | Error message if parsing failed |
| `created_by_user_id` | INTEGER | FK → users(id) ON DELETE SET NULL | User who uploaded the config |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Upload timestamp |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Last update timestamp |
| `parsed_at` | TIMESTAMP | | When parsing completed successfully |

**Indexes:**
- Primary key on `id`
- Unique index on `name`
- Index on `parsing_status`
- Index on `created_by_user_id`

**Notes:**
- All users can see and use all configurations
- `parsing_status` tracks the current state of configuration parsing
- `parsing_error` stores detailed error information if parsing fails
- `created_by_user_id` tracks who uploaded (nullable for audit trail)

**Parsing Status Flow:**
```
not_parsed → parsing → parsed ✓
not_parsed → parsing → error → parsing (retry)
```

---

## Parsing & Analysis Tables

### **symbol_table**
Abstract syntax tree (AST) nodes from parsed configurations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Symbol identifier |
| `configuration_id` | INTEGER | FK → configurations(id) ON DELETE CASCADE, NOT NULL | Source configuration |
| `node_id` | VARCHAR(255) | NOT NULL | AST node identifier |
| `file_path` | VARCHAR(500) | NOT NULL | File path where symbol was found |
| `line_number` | INTEGER | NOT NULL | Line number in source file |

**Indexes:**
- Primary key on `id`
- Index on `configuration_id`
- Index on `node_id`
- Index on `(configuration_id, file_path)` - for file-based queries

**Notes:**
- Each configuration has its own isolated symbol table entries
- When switching configurations, query by `configuration_id` - no dumping needed
- Cascade delete ensures parsing data is cleaned up when configuration is deleted

---

### **macro_definitions**
ModSecurity macro definitions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Macro definition identifier |
| `configuration_id` | INTEGER | FK → configurations(id) ON DELETE CASCADE, NOT NULL | Source configuration |
| `name` | VARCHAR(255) | NOT NULL | Macro name |
| `symbol_id` | INTEGER | FK → symbol_table(id) ON DELETE CASCADE, NOT NULL | AST node reference |

**Indexes:**
- Primary key on `id`
- Unique index on `(configuration_id, name)` - unique macro names per config
- Index on `symbol_id`
- Index on `configuration_id`

**Notes:**
- Each configuration can have macros with the same names (isolated by `configuration_id`)
- `symbol_id` links to the AST node where the macro is defined
- Cascade delete ensures macros are removed with their configuration

---

### **macro_calls**
References to macro usage within configurations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Call identifier |
| `configuration_id` | INTEGER | FK → configurations(id) ON DELETE CASCADE, NOT NULL | Source configuration |
| `node_id` | VARCHAR(255) | NOT NULL | Call site node identifier |
| `macro_definition_id` | INTEGER | FK → macro_definitions(id) ON DELETE CASCADE, NOT NULL | Macro being called |
| `symbol_id` | INTEGER | FK → symbol_table(id) ON DELETE CASCADE, NOT NULL | AST node of the call site |

**Indexes:**
- Primary key on `id`
- Index on `configuration_id`
- Index on `macro_definition_id`
- Index on `symbol_id`

**Notes:**
- Links macro calls to their definitions via `macro_definition_id`
- Each call site is tracked in both the AST (`symbol_id`) and as a node identifier
- Cascade delete ensures call references are removed with their configuration

---

## Chatbot Integration

### **conversations**
Chatbot conversation threads (metadata only - LangGraph manages actual messages).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Conversation identifier |
| `user_id` | INTEGER | FK → users(id) ON DELETE CASCADE, NOT NULL | Conversation owner |
| `configuration_id` | INTEGER | FK → configurations(id) ON DELETE SET NULL | Linked configuration (optional) |
| `thread_id` | VARCHAR(255) | UNIQUE, NOT NULL | LangGraph thread identifier |
| `title` | VARCHAR(255) | | Conversation title |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Last message timestamp |

**Indexes:**
- Primary key on `id`
- Unique index on `thread_id`
- Index on `user_id`
- Index on `configuration_id`
- Index on `(user_id, configuration_id)` - for finding user's config-specific chats

**Notes:**
- This table only stores conversation metadata
- Actual messages are stored by LangGraph in its own checkpoint tables
- `thread_id` is the LangGraph identifier used to retrieve message history
- `configuration_id` provides context - chatbot can reference the linked configuration
- If configuration is deleted, `configuration_id` becomes NULL but conversation persists

---

## Relationships Diagram

```
users ──(FK: active_configuration_id)──→ configurations
  │                                            │
  │                                            ├─(M) symbol_table
  │                                            ├─(M) macro_definitions ──(M) macro_calls
  │                                            │
  └──(M) conversations ────────────────────────┘
                        (FK: configuration_id, optional)
```

**Key Relationships:**
- One user has one active configuration (nullable)
- One configuration has many symbols, macros, and calls
- One macro definition has many macro calls
- One user has many conversations
- One conversation optionally links to one configuration

---

## Database Constraints & Business Rules

### Primary Constraints

1. **User active configuration:**
   - Each user can have at most ONE active configuration
   - Field is nullable (user might not have selected any config yet)
   - Automatically set to NULL if configuration is deleted

2. **Configuration names:**
   - Must be unique across all configurations
   - Enforced by unique constraint on `configurations.name`

3. **Macro names per configuration:**
   - Macro names must be unique within a configuration
   - Different configurations can have macros with the same name
   - Enforced by unique constraint on `(configuration_id, name)`

4. **LangGraph thread IDs:**
   - Must be globally unique across all conversations
   - Enforced by unique constraint on `conversations.thread_id`

### Cascade Delete Rules

**When a user is deleted:**
- ✅ Their conversations are deleted
- ✅ Their selection in other users is unaffected
- ⚠️ Configurations they created remain (created_by_user_id set to NULL)

**When a configuration is deleted:**
- ✅ All symbol_table entries are deleted
- ✅ All macro_definitions are deleted
- ✅ All macro_calls are deleted
- ✅ User active selections are set to NULL
- ✅ Conversation links are set to NULL (conversations persist)

**When a symbol is deleted:**
- ✅ Associated macro_definitions are deleted (if linked)
- ✅ Associated macro_calls are deleted (if linked)

**When a macro_definition is deleted:**
- ✅ All macro_calls referencing it are deleted

---














## Performance Optimization

### Recommended Indexes

All indexes from the table definitions above, plus:

```sql
-- Composite indexes for common query patterns
CREATE INDEX idx_symboltable_config_node ON symbol_table(configuration_id, node_id);
CREATE INDEX idx_macrocall_config_macro ON macro_calls(configuration_id, macro_definition_id);

-- Partial indexes for active records
CREATE INDEX idx_configurations_parsed 
    ON configurations(id) 
    WHERE parsing_status = 'parsed';

CREATE INDEX idx_users_active 
    ON users(active_configuration_id) 
    WHERE active_configuration_id IS NOT NULL;
```

### Query Optimization Tips

1. **Always filter by configuration_id first** - it's the primary partition key
2. **Use JOIN instead of subqueries** when fetching related data
3. **Add LIMIT clauses** for large result sets
4. **Use prepared statements** to cache query plans
5. **Consider materialized views** for complex aggregations if needed























<!-- 
functions
- upload files
- get files_from_db
- get_dump_from_db 

- send_chat_stream? maybe in config?


### Old services
#### Chatbot
- send_chat(chat,config)->[messages]
- get_threads(config)->[threads]
- create_thread(name) -> True (or id)
- get_thread_messages(thread_id) -> [messages]
- delete_thread(thread_id)
- rename_thread(name)



#### parser
- run_analyzer(id)



## old DB
### Tables
- users
    -user_id, username, hashed_password
- threads
    - thread_id, user_id(FK users(user_id)),title, created_at, updated_at
- analysis_tasks
    - config_id(fk configs(is)), status, progress, id
- configs
    - id, nickname, parsed, loaded_at
- dumps
    - config_id(FK configs(id)), dump
- files
    - id, config_id(FK configs(id)),path, content
- selected_config
    - id, config_id(FK configs(id))
- macro_call
    - id, node_id, macro_name(fk macrodef(name)),ruleid(FK symboltable(id))
- macro_def
    - name, ruleid(FK symboltable(id))
- symboltable
    - id, file_path, line_number, node_id


## Old api

- get_all_configs               get /configs
- get_selected_config           get /configs/selected
- select config                 post /configs/select/{id}
- delete_config                 delete /configs/{id}
- parse_config                  post /configs/analyze/{id}
    - (launch a task with tracking id)       
- get_analyzed_config ?         get /configs/analyze/{id}
    - (maybe return just True)
- run_cypher                    post /cypher/run
    - html free query
- run_cypher_to_json            post /cypher/to_json
    - df(full but free query)
- get_remove_by_id              get /directives/remove_by/id
    - df(full)
- get_remove_by_tag             get /directives/remove_by/tag
    - df(full)
- get_directives_by_id          get /directives/id
    - df(full)
- get_directives_by_tag         get /directives/tag
    - df(full)
- get_remover_directives        get /directives/removed/{id}
    - df('criterion_type', 'criterion_value', 'directive')
- get_directives_by_nodeid      get /directives/id/{id}
    - df(full)
- parse_http_request            post /nodes/parse_http_request
    - string cypher query(host,loc)
- get_metadata                  get /nodes/get_metadata/{id}
    - macro_name,file_path, line_number
- search_var                    get /nodes/search_var/{name}
    -? probably list of matching var with some label
- get_setnode                   post /nodes/get_setnode
    - recursive nodes that set variable
- use_node                      post /nodes/use_node
    - recursive nodes that use variable
- get_node_ids                  post /nodes/get_node_ids
    - prbly directive at line and path
- store_config                  post /storage/store_config
    - need zip and name, store in db+dump
- config_tree                   post /storage//config_tree/{id}
    - display config tree, if file, return content
- update_config                 post /storage/update_config/{id}
    - update path and file content
- get_dump                      post /storage/get_dump
    - send conf to waf, return dump
- store_dump                    post /storage/store_dump
    - store dump in db
- get_analysis_progress         get /storage/analysis_progress/{id}
    - task_id, status, progress
- export_database               post /database/export/{name}
    - export neo4j and postgres in file
- import_database               post /database/import/{name}
    - import previously exported


-->