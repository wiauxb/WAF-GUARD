# Documentation of Backend

> **Status legend**
> - 🔴 **TODO** — specified here, not implemented yet.
> - 🟡 **TO REVIEW** — implemented, but doc and code disagree, or the code has a known gap. Decide which side is right, then fix it.
> - ✅ **DONE** — implemented and matches this document.

## Migration status

`new_archi` becomes the main project once every feature is extracted from the old
architecture and wired to the React frontend. `CrsVersion` / `experiments/` are a
separate track and are out of scope for this document.

| Service | Status | Blocking gap |
|---------|--------|--------------|
| AuthService | ✅ DONE | — |
| ConfigManagerService | 🟡 TO REVIEW | Doc describes fields and a process order that the code does not have |
| WAFService | ✅ DONE | — |
| **ParserService** | ✅ DONE | Ported from `old/services/analyzer/`, behaviour-identical. Carries 12 known defects — see [PARSER.md](PARSER.md) |
| **AnalysisService** | ✅ DONE | 13 methods / 13 routes, scoped to the active configuration |
| ChatbotService | 🟡 TO REVIEW | Works, but its 5 WAF tools return dummy data and checkpoint deletion is a no-op |
| LogAnalysisService | 🟡 TO REVIEW | Largest doc/code drift; the ML service it calls is not reachable |

**Route totals:** all 46 implemented. See [Route Totals](#route-totals).

**Critical path:** ~~ParserService~~ ✅ → ~~AnalysisService~~ ✅ →
~~re-point the `/directives` page~~ ✅ → swap the chatbot's dummy tools for real calls.

> The `/cypher` page is still wired to the dropped free-Cypher endpoints and 404s on every
> action. It remains in the sidebar; either rebuild it on `/analysis/directives/search` or
> remove the nav entry.

> ⚠️ **Schema migration required on existing databases.** `symbol_table.node_id` must be
> nullable — only the innermost frame of a directive's context chain carries a node_id.
> `create_all()` never alters an existing table, so a database created before this change
> needs:
> ```sql
> ALTER TABLE symbol_table ALTER COLUMN node_id DROP NOT NULL;
> ```
> Fresh databases pick it up automatically from the model.

## Services


### AuthService
> ✅ **DONE** — matches [services/auth/](backend/src/services/auth/).

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

# 🟡 TO REVIEW — UserWithActiveConfigResponse is defined nowhere in the codebase.
# Either implement it (there is no route that would return it today) or delete it.
class UserWithActiveConfigResponse(BaseModel):
    user: UserInfo
    active_config: Optional[ConfigurationResponse]

```

### ConfigManagerService
> 🟡 **TO REVIEW** — implemented in [services/configmanager/](backend/src/services/configmanager/), but four things disagree:
> 1. The documented upload order below is inverted — the code creates the DB row **first**, to get the ID used for the storage directory name ([service.py:63](backend/src/services/configmanager/service.py#L63)).
> 2. `ConfigurationUploadRequest.waf_url` is not a field; the URL comes from `settings.WAF_URL`.
> 3. `ConfigurationListFilters` is defined nowhere in the codebase.
> 4. `ConfigTreeResponse.children` is `List[ConfigTreeNode]`, not `List[Dict]`, and the response carries an undocumented `size`.

```python
async def upload_configuration(user_id: int, zip_file: UploadFile, request: ConfigurationUploadRequest) -> ConfigurationResponse
    # Upload configuration zip, generate dump via WAF, store files, create DB record
    # Actual process (see 🟡 above — the DB record comes first):
    # 1. Reject if the name already exists
    # 2. Create DB record with empty file_path → yields the ID used for config_{id}/
    # 3. ConfigFileStorage.store_zip() → saves original.zip, extracts to extracted/
    # 4. Call WAFService.generate_dump() → receives gzip-compressed dump (bytes)
    # 5. ConfigFileStorage.store_dump() → streams decompression to disk (1MB chunks)
    # 6. Update the DB record with file_path / file_hash / file_size
    # On any failure: delete the files and the DB record, then re-raise
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
    # 🟡 TO REVIEW — no waf_url field. The WAF URL is read from settings.WAF_URL.
    # frontend/waf-react/types/index.ts still carries this phantom field too.

class ConfigurationUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)

    # 🟡 TO REVIEW — code uses the pydantic v2 form, not v1 @root_validator:
    #   @model_validator(mode='after')
    #   def at_least_one_field(self): ...
    @root_validator
    def at_least_one_field(cls, values):
        if not any(values.values()):
            raise ValueError('Must provide at least one field')
        return values

# 🟡 TO REVIEW — ConfigurationListFilters is defined nowhere. The list route takes
# order_by / order_desc as plain query params and supports no other filtering.
# Either implement this schema or delete it.
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

# 🟡 TO REVIEW — actual shape is children: Optional[List[ConfigTreeNode]] and there is
# an extra size: Optional[int] on the response ([schemas.py:70](backend/src/services/configmanager/schemas.py#L70)).
class ConfigTreeResponse(BaseModel):
    is_file: bool
    path: str
    # If directory:
    children: Optional[List[Dict[str, Any]]]  # [{name, type, size}, ...]
    # If file:
    content: Optional[str]

```
### WAFService
> ✅ **DONE** — matches [services/waf/service.py](backend/src/services/waf/service.py).
> `models.py`, `schemas.py` and `repository.py` in that package are intentionally empty:
> the service is a stateless HTTP client.

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

> ✅ **DONE** — implemented in [services/parser/](backend/src/services/parser/), ported
> from `old/services/analyzer/` and verified behaviour-identical: both parsers produce all
> 92,443 directives with zero differences across 15 compared fields on the 129 MB
> reference dump.
>
> 🟡 **TO REVIEW** — the port is *faithful*, so it reproduces 12 known defects from the old
> implementation, two of them serious (80% of directives get no location; 98.5% get a
> truncated context string). None are fixed. See **[PARSER.md](PARSER.md)** for the full
> analysis and the recommended fix tranches.

> 📖 **See [PARSER.md](PARSER.md)** for how the parser works in depth — the dump format,
> the scanner state machine, the macro context chain, the constant-recovery taint
> analysis — and a measured analysis of 12 defects carried over from the old
> implementation, with reproduction commands.

**Overview**: Reads a configuration's Apache dump, parses it into directive objects, and
populates Neo4j (the directive graph) and PostgreSQL (the symbol / macro tables).

**Responsibility boundary**: the parser *only* parses and writes. It exposes **no query
API** — every read of the parsed data belongs to [AnalysisService](#analysisservice).

**Source**: ported from `old/services/analyzer/`, which was a standalone container
invoked over HTTP. Here it becomes an in-process service.

#### Directory Structure

```
services/parser/
├── service.py                # orchestration, background task, status transitions
├── repository.py             # SymbolRepository (Postgres) + GraphRepository (Neo4j batches)
├── schemas.py
├── models.py                 # EXISTS ✅ — Symbol, MacroDefinition, MacroCall
├── core/                     # pure logic, no DB — ports over almost unchanged
│   ├── dump_parser.py            <- old/services/analyzer/analyzer.py
│   ├── context.py                <- old/services/analyzer/helper_classes/context.py
│   ├── macro.py                  <- old/services/analyzer/helper_classes/macro.py
│   ├── directives.py             <- old/services/analyzer/helper_classes/directives.py
│   ├── directive_factory.py      <- old/services/analyzer/helper_classes/directive_factory.py
│   ├── const_recovery.py         <- old/services/analyzer/const_recovery.py
│   ├── rule_parsing.py           <- old/services/analyzer/rule_parsing.py
│   └── constants/
│       ├── modsec.py             <- old/services/analyzer/modsec.py (COLLECTIONS, OPERATORS)
│       └── apache.py             <- old/services/analyzer/apache.py (SPECIAL_VARIABLES)
└── graph/
    └── query_factory.py          <- old/services/analyzer/helper_classes/query_factory.py
```

#### Methods

```python
def parse_configuration(configuration_id: int, options: Optional[ParseRequest] = None) -> ParseResponse
    # Validates the config exists and its dump.conf is present.
    # Refuses if parsing_status is already 'parsing' unless options.force_reparse.
    # Sets parsing_status='parsing', schedules _run_parse as a FastAPI BackgroundTask,
    # and returns 202 immediately — parsing a large config takes minutes.

def get_parsing_status(configuration_id: int) -> ParseStatusResponse
    # Poll target for the frontend. Adds row counts once parsing_status == 'parsed'.

def reparse_configuration(configuration_id: int) -> ParseResponse
    # clear_parsed_data() then parse_configuration(force_reparse=True)

def clear_parsed_data(configuration_id: int) -> bool
    # Deletes this configuration's Neo4j nodes (batched by settings.DELETE_BATCH_SIZE)
    # and its symbol_table rows. macro_definitions / macro_calls follow by FK cascade.
    # Resets parsing_status to 'not_parsed'.

def _run_parse(configuration_id: int) -> None
    # Background worker. Never raises to the caller — failures land in parsing_error.
```

**`_run_parse` pipeline:**

1. `ConfigManagerService.get_dump_path(id)` → `storage/configs/config_{id}/dump.conf`.
   The config root used to resolve macro definitions back to source files is the sibling
   `storage/configs/config_{id}/extracted/` directory.
2. `parse_compiled_config(dump_path, config_root)` → `list[Directive]`.
   Single pass over the dump tracking VirtualHost / Location / `<If>` nesting / macro
   context, assigning each directive an incrementing `node_id`.
3. Per batch: `GraphRepository.add_directives()` (Neo4j, `UNWIND` batch insert) and
   `SymbolRepository.add_directive()` (Postgres symbol / macro rows).
4. Create the fulltext index `cstIndex` (see [Neo4j Graph Schema](#neo4j-graph-schema)).
5. On success: `parsing_status='parsed'`, `parsed_at=now()`.
   On failure: `parsing_status='error'`, `parsing_error=<traceback summary>`.

**Status flow** — the `configurations` columns already exist and are indexed; nothing
writes them yet:

```
not_parsed → parsing → parsed ✓
not_parsed → parsing → error → parsing (retry via /reparse)
```

#### ⚠️ Porting constraints

These are the only real behavioural changes from `old/`. Everything else ports verbatim.

**1. `CONFIG_ROOT` must stop being a global.**
`FileContext.to_real_path()` reads `os.environ["CONFIG_ROOT"]`
([old/.../context.py:30](old/services/analyzer/helper_classes/context.py#L30)) to map a
dump path back to a real file. Two configurations may parse concurrently in the same
process, so this must become a parameter threaded through `parse_compiled_config` down
into `FileContext` / `MacroContext`.

**2. Parsing must stop being destructive.**
`initialize_databases()` runs `DROP SCHEMA public CASCADE` and detach-deletes **every**
Neo4j node before each run ([old/.../main.py:47](old/services/analyzer/main.py#L47)) —
the old analyzer only ever held one configuration. Replace with the scoped
`clear_parsed_data(configuration_id)` above.

**3. Macro names are per-configuration now.**
The old `macrodef.name` was a **global primary key**, so `select_macrodef` deduped by
name alone ([old/.../sql_interface.py:94](old/services/analyzer/helper_classes/sql_interface.py#L94)).
`MacroDefinition` is unique on `(configuration_id, name)`, so that lookup must filter by
configuration too — otherwise config B silently reuses config A's macro rows.

**4. Every Neo4j node carries `configuration_id`.**
See [Neo4j Graph Schema](#neo4j-graph-schema). Value nodes (`:Constant`, `:Tag`, `:Id`,
`:Location`, …) are `MERGE`d, so without it two configurations would share them.

#### Request Schemas
```python
class ParseRequest(BaseModel):
    """Options for a parse run"""
    force_reparse: bool = False
```

#### Response Schemas
```python
class ParseResponse(BaseModel):
    """Returned on accept (202) — the parse has been scheduled, not finished"""
    configuration_id: int
    parsing_status: str            # "parsing" on accept
    parsing_error: Optional[str]   # set only if the request was rejected outright
    parsed_at: Optional[datetime]  # last successful parse, if any

class ParseStatusResponse(BaseModel):
    """Poll target — counts are populated only once parsing_status == 'parsed'"""
    configuration_id: int
    parsing_status: str            # not_parsed | parsing | parsed | error
    parsing_error: Optional[str]
    parsed_at: Optional[datetime]
    total_directives: Optional[int]
    total_symbols: Optional[int]
    total_macros: Optional[int]
    total_macro_calls: Optional[int]
```

> **Note**: the `total_*` counts moved from `ParseResponse` onto `ParseStatusResponse`.
> `POST /parse` returns before any parsing happens, so it has nothing to count.

### ChatbotService

> 🟡 **TO REVIEW** — implemented and working, but three claims below are wrong and one
> feature is stubbed:
> 1. **The 5 WAF tools return hardcoded dummy data** — see the 🔴 under *Available Tools*.
> 2. `delete_conversation` is documented as full cleanup, but `_delete_thread_checkpoints`
>    is a TODO that returns `True` without deleting anything
>    ([repository.py:207](backend/src/services/chatbot/repository.py#L207)). Checkpoints
>    leak on every delete. The route docstring
>    ([chatbot.py:191](backend/src/api/routes/chatbot.py#L191)) asserts the *opposite* of
>    the service docstring — pick one and make both agree.
> 3. `ConversationResponse.configuration_name` is never populated (`# TODO` in
>    `get_user_conversations`); it is always `null`.
> 4. Doc says `create_agent()` from LangChain; the code uses `create_react_agent` from
>    `langgraph.prebuilt` ([simple_graphs.py:72](backend/src/services/chatbot/graphs/simple_graphs.py#L72)).

**Overview**: AI-powered chatbot for WAF configuration assistance using LangGraph and OpenAI.

**Architecture**:
- **LangGraph**: Manages conversational AI with ReAct agent pattern
- **PostgresSaver**: Automatic conversation persistence (checkpointing)
- **Tools**: 5 specialized tools for WAF configuration analysis
- **Streaming**: Real-time response generation via Server-Sent Events (SSE)
- **Unified Message Schema**: Single MessageResponse schema for all messages (immediate and historical)

```python
def create_conversation(user_id: int, request: ConversationCreateRequest) -> ConversationResponse
    # Create a new conversation thread with optional configuration context
    # Generates unique thread_id for LangGraph persistence

def get_user_conversations(user_id: int, filters: Optional[ConversationListFilters] = None) -> List[ConversationResponse]
    # List user's conversations with optional filtering and pagination

def send_message(thread_id: str, message_request: SendMessageRequest, user_id: int) -> MessageResponse
    # Send message and get chatbot response (uses LangGraph + selected graph)
    # Process:
    # 1. Validate user ownership
    # 2. Get graph from registry (default: "ui_graph_v1")
    # 3. Get current state to track existing message count
    # 4. Invoke graph with checkpointer (automatic persistence)
    # 5. Extract ONLY NEW messages from this exchange (not entire history)
    # 6. Parse new messages and extract tool usage (name, arguments, results)
    # 7. Combine tool calls with their resulting response into single message
    # 8. Update conversation timestamp
    # Returns MessageResponse with assistant's reply and associated tools_used

async def send_message_stream(thread_id: str, message_request: SendMessageRequest, user_id: int) -> AsyncGenerator[str]
    # Stream message response in real-time (yields content chunks)
    # Uses LangGraph astream() with "messages" mode for token-level streaming
    # Ideal for real-time frontend updates via Server-Sent Events (SSE)

def get_conversation_history(thread_id: str, user_id: int, limit: Optional[int] = None) -> ConversationHistoryResponse
    # Get full message history for a conversation from LangGraph checkpointer
    # Messages are persisted automatically by LangGraph PostgresSaver
    # Each MessageResponse includes tools_used when applicable
    # Tool calls are automatically associated with their resulting message content

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
├── utils/               # Shared utilities
│   ├── __init__.py      # Exports all utilities
│   ├── error_handling.py # Tool error handling with fallbacks
│   └── message_parser.py # LangChain → MessageResponse conversion
├── repository.py        # Data access layer (conversations, message history)
├── service.py           # Business logic layer
├── schemas.py           # Pydantic schemas (unified MessageResponse)
└── models.py            # Database models
```

**Available Graphs:**
- `ui_graph_v1`: Simple ReAct agent with 5 WAF tools (default)
  - 🟡 Uses `create_react_agent()` from `langgraph.prebuilt` (doc previously said `create_agent()`)
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

> 🔴 **TODO** — all 5 tools return **hardcoded dummy data** with `"status": "dummy_data"`
> ([tools/waf/](backend/src/services/chatbot/tools/waf/)). Each maps 1:1 onto an
> AnalysisService method — see the tool mapping table under
> [Analysis Routes](#analysis-routes-analysis). Swapping them over is the step that makes
> the chatbot actually useful, and it is blocked on ParserService + AnalysisService.

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

class MessageResponse(BaseModel):
    """Universal message representation for both immediate responses and conversation history"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    tools_used: Optional[List[ToolCallInfo]]  # Tools used to generate this message (assistant only)

class ConversationHistoryResponse(BaseModel):
    conversation: ConversationResponse
    messages: List[MessageResponse]  # Each message includes tools_used when applicable
    total_messages: int
```

#### Future Enhancements
- 🔴 **Tool Backend Integration**: replace the 5 dummy tools with calls to
  `AnalysisService.filter_directives_by_request`, `.search_symbols`,
  `.get_directives_using_constant`, `.get_macro_call_trace`, `.get_removers_of_node`.
  Pass the conversation's `configuration_id` through so a chat linked to config A never
  queries config B.
- **Workflow Graphs**: Routing patterns for complex queries
- **Multi-Agent Orchestration**: Supervisor with specialized agents (LangGraph subgraphs)
- **Deep Agents**: Planning, file system integration, subagent spawning
- **RAG Integration**: Vector store with ModSecurity documentation

### AnalysisService

> ✅ **DONE** — implemented in [services/analysis/](backend/src/services/analysis/),
> verified end to end against a real parsed configuration (38 assertions covering all 13
> endpoints, the active-config fallback, pagination, and both identifier spaces).
>
> **Two identifier spaces.** A directive carries both, and they are never conflated:
> `node_id` is assigned by the parser and present on *every* directive; `rule_id` is the
> ModSecurity `id:NNN`, present only where declared, and one-to-many because a chained
> `SecRule` spans several directives sharing one id. Their numeric ranges overlap, so no
> field or parameter is ever named bare `id` — the old API had `/directives/id` and
> `/directives/id/{nodeid}` meaning different things.

**Overview**: Read-only querying of the structure the parser stored. Reads **Neo4j** for
graph questions (which directives match, what removes what, what uses which constant) and
**PostgreSQL** `symbol_table` / `macro_definitions` / `macro_calls` for source mapping
(which file and line a node came from, through which macro calls).

**Source**: ported from `old/api/routers/directives.py` and `old/api/routers/nodes.py`,
plus one method that only ever existed composed inside the old chatbot.

**Out of scope**: free-form Cypher execution (`old/api/routers/cypher.py`) and database
export/import (`old/api/routers/database.py`) are deliberately **not** being ported.

**Configuration scoping**: every method takes `configuration_id` as its first argument.
At the route layer it is an optional query param that falls back to the caller's
`active_configuration_id`, and is a `400` if neither is present.

#### Directory Structure

```
services/analysis/
├── service.py       # business logic, config resolution, result shaping
├── repository.py    # GraphQueryRepository (Neo4j) + SymbolQueryRepository (Postgres)
├── queries.py       # parameterized Cypher templates — no f-strings (see ⚠️ below)
├── schemas.py
└── models.py        # stays empty — reuses services/parser/models.py
```

#### Methods

Each method is annotated with the `old/` endpoint it replaces.

```python
# ==================== Directive lookup ====================
def get_directive_by_node_id(configuration_id: int, node_id: int) -> DirectiveListResponse
    # <- GET /directives/id/{nodeid}
    # MATCH (n {node_id: $nid, configuration_id: $cid}) RETURN n

def get_directives_by_rule_id(configuration_id: int, rule_id: str) -> DirectiveListResponse
    # <- GET /directives/id
    # MATCH (n)-[:Has]->(:Id {value: $rule_id, configuration_id: $cid}) RETURN n

def get_directives_by_tag(configuration_id: int, tag: str) -> DirectiveListResponse
    # <- GET /directives/tag
    # MATCH (n)-[:Has]->(:Tag {value: $tag, configuration_id: $cid}) RETURN n

# ==================== Request simulation ====================
def filter_directives_by_request(configuration_id: int, location: str, host: str) -> DirectiveListResponse
    # <- POST /parse_http_request + POST /cypher/to_json, collapsed into ONE call.
    # The old API built a Cypher string in one endpoint and made the caller POST it back
    # to another; there is no reason to keep that round trip.
    # location/host are treated as regexes (=~).
    # ORDER BY n.phase, n.IfLevel, n.Location, n.VirtualHost, n.node_id
    #   == the order Apache/ModSecurity would actually evaluate them.

# ==================== Removal analysis ====================
def get_removers_of_node(configuration_id: int, node_id: int) -> RemoverListResponse
    # <- GET /directives/removed/{nodeid}
    # "What removed this node, and on what grounds?" Works for both by-id and by-tag
    # removals; returns (criterion_type, criterion_value, directive) triples.
    # Only counts removers with a HIGHER node_id — a directive cannot remove something
    # that is declared after it.

def get_directives_removing_rule_id(configuration_id: int, rule_id: str) -> DirectiveListResponse
    # <- GET /directives/remove_by/id
    # MATCH (n:secruleremovebyid)-[:DoesRemove]->(:Id {value: $rule_id, ...})

def get_directives_removing_tag(configuration_id: int, tag: str) -> DirectiveListResponse
    # <- GET /directives/remove_by/tag
    # MATCH (n:secruleremovebytag)-[*..2]->(:Tag {value: $tag, ...})
    # The 2-hop is the :Regex node in between — RemoveByTag stores a pattern, and the
    # parser pre-computes (:Regex)-[:Match]->(:Tag) at write time.

# ==================== Constant / variable analysis ====================
def search_symbols(configuration_id: int, query: str) -> SymbolSearchResponse
    # <- GET /search_var/{var_name}
    # Fulltext search over the cstIndex (:Constant|:Variable|:Collection on .name).
    # Old impl split the query on whitespace and joined with "~" for fuzzy matching.
    # Returns each match with its labels so the caller can tell a Constant from a Variable.

def get_directives_using_constant(configuration_id: int, name: str, value: Optional[str] = None) -> DirectiveListResponse
    # <- POST /use_node
    # MATCH (c {name: $name, configuration_id: $cid})<-[:Uses]-(n)
    # value=None means "match the node whose value IS NULL", not "any value".

def get_directives_setting_constant(configuration_id: int, name: str, value: Optional[str] = None) -> DirectiveListResponse
    # <- POST /get_setnode
    # MATCH (c {name: $name, configuration_id: $cid})<-[:Sets|Define]-(n)
    # Same value=None semantics as above.

# ==================== Source mapping ====================
def get_node_metadata(configuration_id: int, node_id: int) -> NodeMetadataResponse
    # <- GET /get_metadata/{node_id}
    # PostgreSQL only. The macrocall ⋃ symboltable UNION query, ordered so the
    # innermost frame comes first and the defining file last.
    # Returns the (macro_name, file_path, line_number) chain for the node.

def get_nodes_at_source(configuration_id: int, file_path: str, line_number: int) -> DirectiveListResponse
    # <- POST /get_node_ids
    # "Which directives did this line of config produce?" — the inverse of the above.
    # Resolves node_ids in Postgres, then fetches those nodes from Neo4j.
    # Powers click-through from the config file editor.

def get_macro_call_trace(configuration_id: int, node_id: int) -> MacroTraceResponse
    # <- composed inside the old chatbot, never an endpoint
    #    (old/services/chatbot/Graph/uiGraph.py:153)
    # get_node_metadata(), then read the actual config files through
    # ConfigManagerService to extract each <Macro ...>...</Macro> body and its `Use` site.
    # This is the ONLY analysis method that touches the filesystem.
```

#### ⚠️ Porting constraints

**1. Parameterize every query.**
[old/api/routers/nodes.py:14](old/api/routers/nodes.py#L14) carries an explicit
`# FIXME: This is vulnerable to "SQL" injection` — `host` and `location` are f-stringed
straight into the Cypher string, and `use_node` / `get_use_node`
([nodes.py:78](old/api/routers/nodes.py#L78)) do the same with `var_name` / `var_value`.
All templates in `queries.py` must use bound parameters (`$location`, `$host`, `$name`,
`$cid`). Note `get_setnode` already does this correctly — copy that one.

**2. `get_macro_call_trace` depends on ConfigManagerService.**
It needs the extracted config files, not just the databases. The old implementation
([uiGraph.py:230](old/services/chatbot/Graph/uiGraph.py#L230)) picks the `Use` site whose
line number is **closest** to the one recorded in `symbol_table` — preserve that, since a
macro is often used many times in one file.

**3. Drop the `fillna(-1)` convention.**
Every old handler returned `pd.DataFrame(records).fillna(-1).to_dict(orient="records")`,
which is why the frontend renders `-1` as null
([directives/page.tsx:97](frontend/waf-react/app/(dashboard)/directives/page.tsx#L97)).
The new schemas use real `Optional` fields — the frontend needs a matching follow-up.

#### Request Schemas
```python
class HttpRequestFilter(BaseModel):
    """Filter directives by simulated request target. Both fields are regexes."""
    location: str = Field(default=".*")
    host: str = Field(default=".*")

class ConstantQuery(BaseModel):
    """Look up a constant or variable. value=None matches nodes with no value set."""
    name: str = Field(min_length=1)
    value: Optional[str] = None

class SourceLocationQuery(BaseModel):
    """Reverse lookup from a config file position back to directives"""
    file_path: str = Field(min_length=1)
    line_number: int = Field(gt=0)
```

#### Response Schemas
```python
class DirectiveResponse(BaseModel):
    """A directive node, typed. Replaces the old untyped property bag."""
    node_id: int
    type: str                          # lowercased directive name == the Neo4j label
    args: str
    location: Optional[str]
    virtual_host: Optional[str]
    if_level: int
    conditions: List[str]              # enclosing <If> expressions
    phase: Optional[int]
    rule_id: Optional[int]             # ModSecurity id:NNN, when present
    tags: List[str]
    msg: Optional[str]
    constants: List[str]
    variables: List[str]

# NOTE: there is deliberately no `context` field. The parser's denormalised provenance
# string was truncated on ~98.5% of directives and duplicated symbol_table; it was removed.
# Use GET /analysis/nodes/{node_id}/metadata for a directive's source chain.

class DirectiveListResponse(BaseModel):
    configuration_id: int
    directives: List[DirectiveResponse]
    total_count: int                   # FULL match count, not the page size
    limit: int
    offset: int

class RemoverEntry(BaseModel):
    """One reason a node was removed"""
    criterion_type: str                # "Id" | "Regex"
    criterion_value: Any               # the rule_id (int) or the tag pattern (str)
    directive: DirectiveResponse       # the SecRuleRemoveBy* that did it

class RemoverListResponse(BaseModel):
    configuration_id: int
    node_id: int                       # the victim -- a PARSER node_id
    removers: List[RemoverEntry]
    total_count: int
    limit: int
    offset: int

class SymbolMatch(BaseModel):
    name: str
    value: Optional[str]
    labels: List[str]                  # ["Constant"] | ["Variable"] | ["Collection"]

class SymbolSearchResponse(BaseModel):
    configuration_id: int
    query: str
    matches: List[SymbolMatch]
    total_count: int
    limit: int
    offset: int

class NodeMetadataEntry(BaseModel):
    """One frame of the macro call chain. macro_name is '/' for the defining file."""
    macro_name: str
    file_path: str
    line_number: int

class NodeMetadataResponse(BaseModel):
    configuration_id: int
    node_id: int
    frames: List[NodeMetadataEntry]    # innermost call first, defining file last

class MacroTraceFrame(BaseModel):
    macro_name: str
    file_path: str
    line_number: int
    content: str                       # the <Macro> body, or the `Use` line

class MacroTraceResponse(BaseModel):
    configuration_id: int
    node_id: int
    frames: List[MacroTraceFrame]
    formatted: str                     # pre-rendered text, for the chatbot tool
```

### LogAnalysisService

> 🟡 **TO REVIEW** — implemented in [services/logs/](backend/src/services/logs/), but this
> is the largest doc/code drift in the file **and it cannot currently run**.
>
> **Blocking:** the ML classifier is unreachable. `model_na` is commented out in
> [docker-compose.yaml](docker-compose.yaml), *and* the code targets hostname `model`,
> not `model_na` ([service.py:38](backend/src/services/logs/service.py#L38)). Both need
> fixing before `POST /classify` can succeed.
>
> **Contract drift** (each is flagged inline below):
> - `GET /sessions` in this doc is `POST /sessions` in the code
>   ([api/routes/logs.py:54](backend/src/api/routes/logs.py#L54)).
> - `include_logs` and `FilteredLogsResponse.logs` do not exist.
> - `get_category_details` additionally requires `log_indices`.
> - `LogEntryResponse.id` is `str` and required, not `int = 0`.
> - Stored `categories` is a dict-of-dicts, not `{name: count}`.
> - `CategoryDetailsResponse.logs` is `List[Dict]`, not `List[LogEntryResponse]`.

```python
async def classify_logs(user_id: int, file: UploadFile, configuration_id: Optional[int] = None) -> LogClassificationResponse
    # Process and classify log file
    # Process:
    # 1. Validate file (.san, .txt, audit.log, max 500MB)
    # 2. Create session with UUID
    # 3. Parse ModSecurity audit logs
    # 4. Normalize and format logs
    # 5. Send to ML service for classification
    # 6. Store results in JSON file (backend/src/storage/logs/{session_id}.json)
    # 7. Return summary with categories and counts
    
def get_filtered_logs(session_id: str, filters: LogFilter) -> FilteredLogsResponse
    # 🟡 TO REVIEW — no include_logs parameter exists. The response has no `logs` field,
    # so there is no way to get full log bodies out of this endpoint today.
    # Apply pandas filters to logs (time, columns, exact/contains/greater_than/less_than)
    # Recalculates categories based on filtered data
    # Returns statistics with log indices

def get_log_by_transaction(session_id: str, transaction_id: str) -> Optional[LogDetailResponse]
    # Get detailed log entry by transaction ID

def get_category_details(session_id: str, category: str, log_indices: List[int], limit: int = 100, offset: int = 0) -> CategoryDetailsResponse
    # 🟡 TO REVIEW — log_indices is REQUIRED and undocumented. The caller must first get
    # the indices from classify_logs/get_filtered_logs and hand them back here.
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
    # 🟡 TO REVIEW — this field does not exist on the real schema. Either add it (plus the
    # include_logs param) or drop it from the doc and the frontend types.
    logs: Optional[List[Dict[str, Any]]]  # Full logs if include_logs=True

class LogEntryResponse(BaseModel):
    id: int = 0  # 🟡 TO REVIEW — actual field is `id: str`, required, no default
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

# 🟡 TO REVIEW — real schema: `id: int` (required, service passes 0 explicitly),
# `created_at: datetime` and `completed_at: Optional[datetime]` (not str),
# `categories: Optional[List[LogCategoryResponse]]` (not Dict[str, int]).
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
    logs: List[LogEntryResponse]  # 🟡 TO REVIEW — actually List[Dict[str, Any]]
```

**Storage Details:**
- Sessions stored as JSON files in `backend/src/storage/logs/{session_id}.json`
- Each file contains: metadata, all logs, categories, and DataFrame (for filtering)
- No database tables - pure file-based storage
- Pandas DataFrame serialized as dict for filtering support

**JSON Structure:**

> 🟡 **TO REVIEW** — `categories` is a **dict of dicts**, not `{name: count}`. The shape
> below is what [service.py:125](backend/src/services/logs/service.py#L125) actually
> writes, and `get_category_details` depends on it (`categories[category]["count"]`).

```json
{
  "session_id": "uuid",
  "user_id": 1,
  "filename": "audit.log",
  "status": "completed",
  "total_logs": 1500,
  "categories": {
    "SQL Injection": {
      "category": "SQL Injection",
      "count": 450,
      "log_indices": [0, 3, 7]
    }
  },
  "logs": [{...}],
  "dataframe": [{...}]  // Serialized for pandas filtering
}
```

## API

**Base URL**: `/api/v1`


---

## Auth Routes (`/auth`)
> ✅ **DONE** — 5/5 implemented in [api/routes/auth.py](backend/src/api/routes/auth.py).

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
> 🟡 **TO REVIEW** — 8/8 implemented in [api/routes/configs.py](backend/src/api/routes/configs.py),
> but the collection routes are registered as `POST ""` / `GET ""`, not `POST "/"` — the
> real paths are `/api/v1/configurations` with **no trailing slash**.

| Method | Endpoint | Auth | Request | Response | Description |
|--------|----------|------|---------|----------|-------------|
| POST | `` (no trailing slash) | ✅ | File Upload (see below) | `ConfigurationResponse` | Upload config zip |
| GET | `` (no trailing slash) | ✅ | Query: order_by, order_desc | `List[ConfigurationResponse]` | List all configs |
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

> ✅ **DONE** — 4/4 implemented in [api/routes/parser.py](backend/src/api/routes/parser.py).
> [configs/page.tsx:153](frontend/waf-react/app/(dashboard)/configs/page.tsx#L153)'s
> "Analyze" button now works.
>
> ✅ Status polling is implemented in
> [ConfigGuard](frontend/waf-react/components/analysis/ConfigGuard.tsx), which starts a
> parse and polls `GET /parser/status/{id}` until it leaves `parsing`.
>
> 🔴 **TODO (frontend)** — the *configs* page still fires a parse without polling, so its
> row keeps showing `parsing` until manually refreshed. The polling hook in ConfigGuard
> can be reused there.

| Method | Endpoint | Auth | Request | Response | Description |
|--------|----------|------|---------|----------|-------------|
| POST | `/parse/{id}` | ✅ | `ParseRequest` | `ParseResponse` (202) | Start parsing in background |
| GET | `/status/{id}` | ✅ | - | `ParseStatusResponse` | Poll parsing status |
| POST | `/reparse/{id}` | ✅ | - | `ParseResponse` (202) | Clear parsed data and re-parse |
| DELETE | `/data/{id}` | ✅ | - | `SuccessResponse` | Drop parsed data, back to `not_parsed` |

**Status codes:**
- `202 Accepted` — parse scheduled (`/parse`, `/reparse`). The work happens in a
  BackgroundTask; poll `/status/{id}`.
- `404` — configuration not found.
- `409` — already `parsing` and `force_reparse` was not set.
- `422` — configuration has no dump file (upload never completed).

### Request Schemas

```python
class ParseRequest(BaseModel):
    force_reparse: bool = Field(default=False)
```

### Response Schemas

See the **ParserService → Response Schemas** section above for `ParseResponse` and
`ParseStatusResponse`.

---

## Analysis Routes (`/analysis`)

> ✅ **DONE** — 13/13 implemented in
> [api/routes/analysis.py](backend/src/api/routes/analysis.py), and all 13 are consumed by
> the [directives page](frontend/waf-react/app/(dashboard)/directives/page.tsx) through the
> typed client in [lib/analysis.ts](frontend/waf-react/lib/analysis.ts).

All routes are authenticated and paginated (`limit`, default 100, max 1000; `offset`).
`total_count` always reports the **full** match count, not the page size.

All accept an optional `configuration_id` query parameter; when omitted it falls back to
the caller's `active_configuration_id` (set by the configs page via
`PUT /auth/me/active-config`). Resolution is handled once in
`get_analysis_configuration_id` ([api/dependencies.py](backend/src/api/dependencies.py)),
which also validates that the target is actually queryable:

| Status | When |
|--------|------|
| `400` | No `configuration_id` given and no active configuration set |
| `404` | The configuration does not exist |
| `409` | It exists but `parsing_status != 'parsed'` |
| `409` | It is marked `parsed` but holds no graph nodes — re-parse it |

> The last case guards a real split-brain: PostgreSQL keeps `parsing_status` independently
> of Neo4j, so a lost graph would otherwise surface as empty results for a configuration
> that claims to be ready. See the Neo4j volume note under *Neo4j Graph Schema*.

| Method | Endpoint | Request | Response | Description |
|--------|----------|---------|----------|-------------|
| POST | `/directives/search` | `DirectiveSearchQuery` | `DirectiveListResponse` | **Any combination of criteria, any sort order.** Backs the Directives page |
| POST | `/directives/values/{field}` | `ValueListQuery` | `FacetValuesResponse` | Value list for `tag` \| `host` \| `location` \| `type` \| `phase` \| `msg`, **counted inside the filters already applied** |
| POST | `/locations/match-url` | `UrlMatchRequest` | `UrlMatchResponse` | Which `<Location>`/`<LocationMatch>` blocks cover a URL from a log |
| GET | `/directives/{node_id}` | - | `DirectiveListResponse` | Directive by node ID |
| GET | `/directives/by-rule-id/{rule_id}` | - | `DirectiveListResponse` | Directives carrying a ModSecurity rule ID |
| GET | `/directives/by-tag/{tag}` | - | `DirectiveListResponse` | Directives carrying a tag |
| POST | `/directives/filter` | `HttpRequestFilter` | `DirectiveListResponse` | Directives matching a host/location, in execution order |
| GET | `/directives/{node_id}/removed-by` | - | `RemoverListResponse` | What removed this node, and why |
| GET | `/removals/by-rule-id/{rule_id}` | - | `DirectiveListResponse` | `SecRuleRemoveById` directives targeting a rule ID |
| GET | `/removals/by-tag/{tag}` | - | `DirectiveListResponse` | `SecRuleRemoveByTag` directives matching a tag |
| GET | `/symbols/search` | Query: `q` | `SymbolSearchResponse` | Fulltext search over constants/variables/collections |
| POST | `/symbols/used-by` | `ConstantQuery` | `DirectiveListResponse` | Directives that *use* a constant |
| POST | `/symbols/set-by` | `ConstantQuery` | `DirectiveListResponse` | Directives that *set or define* a constant |
| GET | `/nodes/{node_id}/metadata` | - | `NodeMetadataResponse` | Source file/line chain for a node |
| GET | `/nodes/{node_id}/macro-trace` | - | `MacroTraceResponse` | Full macro call stack with file contents |
| POST | `/nodes/at-source` | `SourceLocationQuery` | `DirectiveListResponse` | Directives produced by a given config line |

### `POST /directives/search` — the combinable filter

The single-purpose lookups above are each expressible here (`by-tag/{t}` is
`{"tags": ["t"]}`), and unlike them they compose. Criteria are AND-ed; **within** one
criterion the meaning follows the underlying property, which is the only part that
surprises people:

| Field | Reading | Why |
|-------|---------|-----|
| `types`, `phases`, `rule_ids`, `hosts`, `locations` | *any of* | A directive has one type, one phase, one id, one host, one location — so a list can only mean "either" |
| `tags` | *all of* | A directive carries a **list** of tags, so a list narrows to those carrying every one |

**`url`** is shorthand for `locations`: paste a URL or path from a log and the server
resolves which location blocks cover it, then **merges them into the `locations` set** —
so a URL and explicit location chips combine as "any of", like every other multi-value
field. (They used to be separate clauses, which AND-ed two sets on the same property and
returned zero whenever a chip was not already in the URL's match set.) Scheme, host,
query and fragment are ignored — `VirtualHost` holds bind specs (`*:80`), not hostnames.
`POST /locations/match-url` returns the same match set with per-block counts, for showing
*which* patterns hit.

> Matching runs in **Python, not Cypher**. Apache's `<LocationMatch>` is an unanchored
> **PCRE** search while Cypher's `=~` is Java-flavoured and fully anchored, and `<Location>`
> is not a regex at all but a path-component prefix (`/wp` covers `/wp/admin`, not
> `/wpfoo`). The `regex` module is pinned in requirements for this: the stdlib `re` rejects
> PCRE's mid-pattern inline flags and fails on 56 of one real configuration's 545 patterns.

Other fields: `node_id`, `args_contains` / `msg_contains` (case-insensitive substring),
`has_rule_id` (separates real ModSecurity rules from the config directives around them),
and `source` (a file+line, resolved through PostgreSQL to node IDs and then joined as an
ordinary clause). An empty body returns the whole configuration.

> **`hosts`/`locations` are exact; `host`/`location` are regex and API-only.** The stored
> values keep the quotes the dump used — `"*:80"`, `".well-known/acme-challenge"` — and
> contain regex metacharacters, so `*:80` is not even a valid pattern (it used to 500; an
> invalid regex now returns 400). And now that the parser tracks `<LocationMatch>`, Location
> values themselves ARE regexes like `(?i)[.]axd($|/)`, which makes regex-matching them
> meaningless as well. The UI therefore sends only the exact forms.
>
> `""` is a real value meaning **outside any VirtualHost/Location block** — the parser
> initialises both to `""` and never to null. So `locations: [""]` filters to exactly those
> directives (20,995 once `<LocationMatch>` is tracked, down from 71,236), and needs no
> sentinel.

### Faceted counts

`POST /directives/values/{field}` counts within the filter set the caller sends, so every
number answers one question: **how many results if I add this value?** A value whose count
would be zero has no row and is not listed — with `phase 2` applied, `type` drops from 196
values to the 2 that still have directives.

The two semantics need opposite treatment, and both are exact in a single aggregation:

| field kind | own chips | why |
|---|---|---|
| OR (`type`, `phase`, `host`, `location`, `msg`) | **excluded** | Adding a value widens. Counting with its own chips applied would collapse the list to what is already picked, and a second value could never be added |
| AND (`tag`) | **kept** | Adding a tag narrows, so each candidate's count within the current results is exactly what picking it gives |

> Consequence worth knowing: for an OR field the counts do **not** sum to the table total,
> because they ignore that field's own chips. That is what makes multi-select work.

The clauses come from `AnalysisService._build_clauses`, the same builder
`/directives/search` uses, so a dropdown can never advertise a number the search would not
reproduce.

**Restricted to directive nodes.** `configuration_id` is not unique to directives — every
value node the parser MERGEs (`Id`, `Tag`, `Constant`, `Variable`, `Collection`, `Location`,
`VirtualHost`, `Phase`, `Regex`, `Predicate`) carries it too, ~4,500 of them on a full
configuration. The base MATCH therefore carries `n.node_id IS NOT NULL`, which every
directive satisfies and no value node does. The single-purpose routes never needed it: each
constrains `n` through a relationship, which already implies a directive.

Every criterion is matched against a node **property** rather than the relationship that
mirrors it — `$tag IN n.tags`, not `(n)-[:Has]->(:Tag)`. That is what lets them all be
conjuncts on one `MATCH`, and it is cheaper for location/host, where the relationship form
expands every directive's edge through a single shared `value:""` node.

`sort_by` (`node_id` | `type` | `rule_id` | `phase` | `host` | `location`) and `sort_dir` order the
**full match set** server-side, so paging stays correct. Two details in
[queries.build_directive_search](backend/src/services/analysis/queries.py):
Cypher cannot parameterise `ORDER BY`, so the column is interpolated from a closed
whitelist and anything else 422s; and directives with no value for the sort column sort
**last in both directions**. Neo4j treats `null` as the largest value, so a `phase DESC`
would otherwise open on a page of blanks — and "blank" is not only null, since `Location`
and `VirtualHost` store absence as `""`, which sorts *first* ascending. Both cases are
covered.

Measured on `Full conf` (92,443 directives, no index on directive nodes): page + count
together run in ~100–170 ms for every sort column.

**Status codes:**
- `400` — no `configuration_id` given and the user has no active configuration.
- `404` — configuration not found, or node ID does not exist in it.
- `409` — configuration exists but `parsing_status != 'parsed'`; nothing to query yet.

### Chatbot Tool Mapping

The 5 WAF tools in [services/chatbot/tools/waf/](backend/src/services/chatbot/tools/waf/)
are the primary consumer. Each maps onto exactly one method — swapping them off dummy data
is a direct substitution.

| Tool | AnalysisService method |
|------|------------------------|
| `filter_rule(location, host)` | `filter_directives_by_request` |
| `get_constant_info(constant_name)` | `search_symbols` |
| `get_directives_with_constant(constant_name)` | `get_directives_using_constant` |
| `get_macro_call_trace(node_id)` | `get_macro_call_trace` |
| `removed_by(node_id)` | `get_removers_of_node` |

### Frontend Consumers

Two pages are currently dead — they still call the **old** API paths and will need
re-pointing once these routes exist:

| Page | Currently calls | Should call |
|------|-----------------|-------------|
| [directives/page.tsx](frontend/waf-react/app/(dashboard)/directives/page.tsx) | `/directives/id`, `/directives/tag`, `/directives/id/{nodeid}`, `/directives/removed/{nodeid}` | **`/analysis/directives/search`** for the whole Directives tab — combinable filters and sorting replace the five one-at-a-time modes; `/analysis/removals/*` for the Removals tab |
| [cypher/page.tsx](frontend/waf-react/app/(dashboard)/cypher/page.tsx) | `/cypher/run`, `/cypher/to_json` | **N/A** — free Cypher is out of scope. Either delete the page or rebuild it on `/analysis/directives/filter`. |

### Request Schemas

See the **AnalysisService → Request Schemas** section above for `HttpRequestFilter`,
`ConstantQuery` and `SourceLocationQuery`.

### Response Schemas

See the **AnalysisService → Response Schemas** section above.

---

## Chatbot Routes (`/chatbot`)
> 🟡 **TO REVIEW** — all 7 routes below are implemented in
> [api/routes/chatbot.py](backend/src/api/routes/chatbot.py). The behavioural gaps are in
> the service, not the routing: see the ChatbotService marker (dummy tools, leaking
> checkpoints, null `configuration_name`).

| Method | Endpoint | Auth | Request | Response | Description |
|--------|----------|------|---------|----------|-------------|
| POST | `/conversations` | ✅ | `ConversationCreateRequest` | `ConversationResponse` | Create new conversation |
| GET | `/conversations` | ✅ | Query: configuration_id, limit, offset | `List[ConversationResponse]` | List user's conversations |
| POST | `/conversations/{thread_id}/messages` | ✅ | `SendMessageRequest` | `MessageResponse` | Send message and get response |
| POST | `/conversations/{thread_id}/messages/stream` | ✅ | `SendMessageRequest` | SSE Stream | Send message with streaming response |
| GET | `/conversations/{thread_id}/history` | ✅ | Query: limit | `ConversationHistoryResponse` | Get conversation history |
| DELETE | `/conversations/{thread_id}` | ✅ | - | `SuccessResponse` | Delete conversation (🟡 metadata only — checkpoints leak) |
| PUT | `/conversations/{thread_id}/title` | ✅ | `ConversationRenameRequest` | `ConversationResponse` | Rename conversation |

### Request Schemas

```python
class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    configuration_id: Optional[int] = Field(None, gt=0)

class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    configuration_id: Optional[int] = Field(None, gt=0)
    graph_name: Optional[str] = Field(default="ui_graph_v1")  # LangGraph to use
    stream: bool = Field(default=False)  # Enable streaming response

class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)

class ConversationListFilters(BaseModel):
    configuration_id: Optional[int] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
```

### Response Schemas

```python
class ConversationResponse(BaseModel):
    id: int
    user_id: int
    configuration_id: Optional[int]
    thread_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    configuration_name: Optional[str]

class ToolCallInfo(BaseModel):
    name: str  # Tool name
    arguments: Dict[str, Any]  # Tool arguments
    result: Any  # Tool result

class MessageResponse(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    tools_used: Optional[List[ToolCallInfo]]  # Tools used for this message

class ConversationHistoryResponse(BaseModel):
    conversation: ConversationResponse
    messages: List[MessageResponse]
    total_messages: int
```

### Streaming Endpoint

The `/conversations/{thread_id}/messages/stream` endpoint returns Server-Sent Events (SSE):

**Response Type**: `text/event-stream`

**Frontend Integration Example**:
```javascript
const eventSource = new EventSource(
  `/api/v1/chatbot/conversations/${threadId}/messages/stream`,
  { headers: { Authorization: `Bearer ${token}` } }
);
eventSource.onmessage = (event) => {
  console.log(event.data); // Response chunk
};
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

> 🟡 **TO REVIEW** — 6/6 implemented in [api/routes/logs.py](backend/src/api/routes/logs.py),
> but `POST /classify` cannot succeed: the ML service it calls is not running (see the
> LogAnalysisService marker). Also note `list_user_sessions` is a **POST** taking a body,
> which the row below gets wrong.

| Method | Endpoint | Auth | Request | Response | Description |
|--------|----------|------|---------|----------|-------------|
| POST | `/classify` | ✅ | File Upload + Query | `LogClassificationResponse` | Upload and classify logs |
| POST | `/sessions` | ✅ | `UserSessionRequest` | `List[LogAnalysisSessionResponse]` | List user's sessions (🟡 doc said GET) |
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
    # 🟡 TO REVIEW — field does not exist in the code. See LogAnalysisService marker.
    logs: Optional[List[Dict[str, Any]]] = None  # Full logs if include_logs=True

class LogEntryResponse(BaseModel):
    """Individual log entry details"""
    id: int = 0  # 🟡 TO REVIEW — actual field is `id: str`, required
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

# 🟡 TO REVIEW — real schema uses `created_at: datetime`, `completed_at: Optional[datetime]`,
# `categories: Optional[List[LogCategoryResponse]]`, and `id: int` is required (the service
# passes 0 explicitly rather than defaulting).
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
    logs: List[LogEntryResponse]  # 🟡 TO REVIEW — actually List[Dict[str, Any]]
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

**Combined filtering:**

> 🟡 **TO REVIEW** — `?include_logs=true` is **not** supported; the endpoint takes no such
> parameter and never returns log bodies. This example only works without it.

```json
POST /api/v1/logs/sessions/{session_id}/filter
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

## Route Totals

| Group | Prefix | Implemented | Specified, not implemented | Status |
|-------|--------|-------------|----------------------------|--------|
| Auth | `/auth` | 5 | 0 | ✅ |
| Configurations | `/configurations` | 8 | 0 | 🟡 |
| Parser | `/parser` | **4** | 0 | ✅ |
| Analysis | `/analysis` | **16** | 0 | ✅ |
| Chatbot | `/chatbot` | 7 | 0 | 🟡 |
| Logs | `/logs` | 6 | 0 | 🟡 |
| **Total under `/api/v1`** | | **46** | **0** | |

Plus 2 unprefixed routes in [main.py](backend/src/main.py): `GET /` and `GET /health`.
Grand total of implemented handlers: **48**.

> The old figure of "32 endpoints" counted 3 Parser routes that were never built and 3
> "Common" entries that are shared schemas, not routes.

Verify with:
```bash
grep -rn "@router\.\(get\|post\|put\|patch\|delete\)" backend/src/api/routes/ | wc -l
```








# WAF-Guard Database Schema Documentation

> ✅ **DONE** — every table below matches
> [the SQLAlchemy models](backend/src/services/), including composite indexes and cascade
> rules. Tables are created by `Base.metadata.create_all()` in
> [shared/database.py](backend/src/shared/database.py) at startup.
>
> 🟡 **TO REVIEW** — there is **no migration tool** (no Alembic). `create_all()` only ever
> *adds* tables; it never alters an existing one. Any future column change will need a
> manual migration or a volume wipe.

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

> ✅ **DONE** — populated by ParserService and read by AnalysisService for source mapping.
>
> ⚠️ `symbol_table.node_id` is **nullable**: a symbol row is written for every frame of a
> directive's context chain, and only the innermost frame carries a node_id (the macro
> definition and use frames have none). On the reference configuration that is 92,443 rows
> with a node_id and 557,836 without. Databases created before this was corrected need
> `ALTER TABLE symbol_table ALTER COLUMN node_id DROP NOT NULL;` — `create_all()` never
> alters an existing table.

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

# Neo4j Graph Schema

> ✅ **DONE** — produced by ParserService, queried by AnalysisService.
> The model below was reverse-engineered from
> [old/.../query_factory.py](old/services/analyzer/helper_classes/query_factory.py),
> **plus** the `configuration_id` scoping described at the end, which the old
> single-config analyzer did not have.

PostgreSQL stores *where directives came from* (file, line, macro chain). Neo4j stores
*what directives mean and how they relate* — this is what AnalysisService queries.

> ⚠️ **The graph needs a persistent volume.** `neo4j_data` was declared in
> [docker-compose.yaml](docker-compose.yaml) but never mounted, so Docker attached a fresh
> **anonymous** volume on every container create (the `neo4j` image declares `VOLUME /data`
> itself). A `compose down` + `up` therefore wiped the whole graph while PostgreSQL — which
> mounts the *named* `postgres_data` — kept its rows, leaving configurations marked
> `parsed` with no graph behind them. Now mounted as `neo4j_data:/data`. Note the old
> commented-out line pointed at `/neo4j/`, which is not where Neo4j stores data.

## Multi-configuration scoping

The old analyzer wiped the entire graph before each run, so it only ever held one
configuration. Value nodes are `MERGE`d by name/value, which means that **without
scoping, two configurations would silently share their `:Constant`, `:Tag`, `:Id`,
`:Location` and `:VirtualHost` nodes.**

Every node — directive and value alike — therefore carries a `configuration_id` property,
and it must be part of **every `MERGE` key** and **every match filter**:

```cypher
// old — collides across configurations
MERGE (co:Constant {name: constant})
MERGE (node)-[:Uses]->(co)

// new — scoped
MERGE (co:Constant {name: constant, configuration_id: $cid})
MERGE (node)-[:Uses]->(co)
```

```cypher
// analysis side — always filter
MATCH (n {configuration_id: $cid})-[:Has]->(:Id {value: $rule_id, configuration_id: $cid})
RETURN n
```

> Rejected alternatives: a `:Config_{id}` label per configuration (unbounded label space),
> and one Neo4j database per configuration (`neo4j:latest` in
> [docker-compose.yaml](docker-compose.yaml) is Community Edition, which permits only one
> user database).

`clear_parsed_data(configuration_id)` deletes with the same filter, batched by
`settings.DELETE_BATCH_SIZE`:

```cypher
MATCH (n {configuration_id: $cid}) WITH n LIMIT $batch
DETACH DELETE n RETURN count(n) AS deleted
```

## Directive nodes

Each directive becomes **one node whose label is the lowercased directive name** —
`secrule`, `definestr`, `secruleremovebyid`, `secruleremovebytag`, `include`,
`sethandler`, and so on. The label is assigned dynamically from `properties.type`.

| Property | Type | Notes |
|----------|------|-------|
| `node_id` | int | Sequential within a configuration; the join key to `symbol_table` |
| `configuration_id` | int | Scoping key |
| `type` | string | Lowercased directive name — same as the label |
| `args` | string | Raw argument text |
| `Location` | string | Enclosing `<Location>`, `""` if none |
| `VirtualHost` | string | Enclosing `<VirtualHost>`, `""` if none |
| `IfLevel` | int | `<If>` nesting depth |
| `conditions` | list[string] | The enclosing `<If>` expressions |
| `constants` | list[string] | Constants referenced, from taint recovery |
| `variables` | list[string] | Flattened `[collection, name, ...]` pairs |
| `id` | int | *optional* — ModSecurity `id:NNN` |
| `tags` | list[string] | *optional* — ModSecurity `tag:` values |
| `phase` | int | *optional* — ModSecurity `phase:N` |
| `msg` | string | *optional* — ModSecurity `msg:` |

`SecRule` nodes carry additional `secrule_*`, `setenv_*` and `setvar_*` properties used
to build the `Sets` / `Unsets` / `Uses` edges.

## Value nodes

All carry `configuration_id` in addition to the properties listed.

| Label | Properties | Created from |
|-------|-----------|--------------|
| `:Location` | `value`, `kind` | `<Location>` (literal path) or `<LocationMatch>` (regex) context; `kind` says which, and is part of the MERGE key |
| `:VirtualHost` | `value` | `<VirtualHost>` context |
| `:Predicate` | `value` | `<If>` condition expressions |
| `:Constant` | `name`, `value` *(optional)* | `Define` / `SetEnv`, and taint recovery |
| `:Collection` | `name` | ModSecurity collections (`TX`, `ARGS`, `ENV`, …) |
| `:Variable` | `name`, `value` *(optional)* | `setvar:` / `setenv:` / SecRule targets |
| `:Id` | `value` | `id:NNN`, and `SecRuleRemoveById` targets (ranges expanded) |
| `:Tag` | `value` | `tag:` values |
| `:Phase` | `value` | `phase:N` |
| `:Regex` | `value` | `SecRuleRemoveByTag` patterns |

## Relationships

| Relationship | From → To | Meaning |
|--------------|-----------|---------|
| `AtLocation` | directive → `:Location` | Directive sits in this `<Location>` / `<LocationMatch>` |
| `InVirtualHost` | directive → `:VirtualHost` | Directive sits in this vhost |
| `Has` | directive → `:Predicate` \| `:Id` \| `:Tag` | Guarded by an `<If>`, or declares an id/tag |
| `InPhase` | directive → `:Phase` | ModSecurity processing phase |
| `Uses` | directive → `:Constant` \| `:Variable` \| `:Collection` | Reads this symbol |
| `Define` | `definestr`/`setenv` → `:Constant` | Defines a constant |
| `Sets` | directive → `:Variable` | `setvar:`/`setenv:` assignment |
| `Unsets` | directive → `:Variable` | `setvar:!x` / `setenv:!x` |
| `IsVariableOf` | `:Variable` → `:Collection` | Variable belongs to a collection |
| `DoesRemove` | `secruleremovebyid` → `:Id` | Removes rules by ID (ranges expanded to individual `:Id` nodes) |
| `DoesRemove` | `secruleremovebytag` → `:Regex` | Removes rules by tag pattern |
| `Match` | `:Regex` → `:Tag` | Pre-computed at write time: which tags this pattern matches |

> The `Regex → Match → Tag` edge is why "which directives remove tag X" is a 2-hop query.
> The parser resolves the regex once at write time rather than at every read.

## Indexes

```cypher
CREATE FULLTEXT INDEX cstIndex IF NOT EXISTS
FOR (n:Constant|Variable|Collection)
ON EACH [n.name]
```

Backs `AnalysisService.search_symbols`. Created at the end of every parse run.

Plus one range index per scoped label, so the `configuration_id` filter on every query
does not force a label scan. Created by `QueryFactory.create_scope_indexes()` at the end
of each parse:

```cypher
CREATE INDEX cfg_constant IF NOT EXISTS FOR (n:Constant) ON (n.configuration_id)
-- ...and the same for Location, VirtualHost, Predicate, Collection,
--    Variable, Id, Tag, Phase, Regex
```

> ⚠️ `cstIndex` is **global** — it carries no `configuration_id`. `search_symbols`
> therefore filters its results by configuration *after* the fulltext lookup, or one
> configuration's symbols would leak into another's search.

## Worked example

`SecRule REQUEST_HEADERS:User-Agent "@rx evil" "id:1234,phase:2,deny,tag:custom/BOT"`
inside `<VirtualHost *:443>` / `<Location /api>` becomes:

```
(:secrule {node_id: 42, configuration_id: 5, phase: 2, id: 1234, ...})
  -[:AtLocation]->     (:Location {value: "/api"})
  -[:InVirtualHost]->  (:VirtualHost {value: "*:443"})
  -[:InPhase]->        (:Phase {value: 2})
  -[:Has]->            (:Id {value: 1234})
  -[:Has]->            (:Tag {value: "custom/BOT"})
  -[:Uses]->           (:Variable {name: "User-Agent"})-[:IsVariableOf]->(:Collection {name: "REQUEST_HEADERS"})
```

A later `SecRuleRemoveById 1234` produces
`(:secruleremovebyid)-[:DoesRemove]->(:Id {value: 1234})`, which is what
`get_removers_of_node(5, 42)` traverses backwards.

---














## Performance Optimization

### Recommended Indexes

> 🟡 **TO REVIEW** — the composite indexes `idx_symboltable_config_node` and
> `idx_macrocall_config_macro` **are** declared in
> [services/parser/models.py](backend/src/services/parser/models.py). The two **partial**
> indexes below are not created anywhere. Add them as raw DDL after `create_all()`, or
> drop them from this doc.

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























---

# Appendix: Legacy API Porting Checklist

The block below is the inventory of the **old** architecture (`old/`), kept as the
authoritative list of what still needs porting. Status of each old endpoint group:

| Old endpoint group | Disposition |
|--------------------|-------------|
| `/configs/*` (list, select, delete, analyze) | ✅ Ported → Configuration Routes + `active_configuration_id`. `analyze` → ✅ Parser Routes |
| `/storage/*` (store_config, config_tree, update_config, get_dump, store_dump) | ✅ Ported → Configuration Routes + WAFService |
| `/storage/analysis_progress/{task_id}` | ⛔ Dropped — replaced by `parsing_status` polling on `GET /parser/status/{id}`; no task table |
| `/directives/*` (id, tag, remove_by/id, remove_by/tag, removed/{id}, id/{id}) | ✅ Ported → Analysis Routes. Note the old `/id` (rule id) vs `/id/{nodeid}` (node id) ambiguity is gone |
| `/nodes/*` (parse_http_request, get_metadata, search_var, get_setnode, use_node, get_node_ids) | ✅ Ported → Analysis Routes. `parse_http_request` + `cypher/to_json` collapsed into `POST /analysis/directives/filter` |
| `/cypher/run`, `/cypher/to_json` | ⛔ **Deliberately dropped.** Free-form Cypher is out of scope. `/cypher/run` also wrote a shared `tmp.html` via pyvis on every request — race-prone. Rebuild the frontend page on `/analysis/directives/filter` or delete it |
| `/database/export/{name}`, `/database/import/{name}` | ⛔ Dropped for now — no equivalent planned. Revisit if backup/restore is needed |
| Chatbot (`send_chat`, threads CRUD) | ✅ Ported → Chatbot Routes, with LangGraph checkpointing replacing the manual message tables |

**Old DB tables → new schema:**

| Old | New |
|-----|-----|
| `users` | `users` (+ `active_configuration_id`, `is_admin`) |
| `threads` | `conversations` (messages now live in LangGraph checkpoint tables) |
| `configs`, `dumps`, `files` | `configurations` + filesystem storage under `storage/configs/config_{id}/` |
| `selected_config` (global singleton) | `users.active_configuration_id` (per user) |
| `symboltable` | `symbol_table` (+ `configuration_id`) |
| `macro_def` (name as global PK) | `macro_definitions` (unique on `configuration_id, name`) |
| `macro_call` | `macro_calls` (+ `configuration_id`) |
| `analysis_tasks` | ⛔ Dropped — status lives on `configurations.parsing_status` |

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