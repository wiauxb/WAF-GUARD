# WAF-GUARD Frontend - API Integration Complete ✅

## Updates Made

I've successfully integrated all the missing API services into your Next.js frontend. Here's what was added:

### 🔧 New API Integrations

#### 1. **Analyzer API** (Port 8001)
- Added axios instance for analyzer service
- Endpoints: `/process_configs/{id}` 
- Used for configuration analysis (called via FastAPI proxy)

#### 2. **WAF API** (Port 9090)
- Added axios instance for WAF service
- Endpoints: `/get_dump`, `/health`
- Used for Apache config dump generation (called via FastAPI proxy)

### 📁 Files Modified

1. **`lib/api.ts`**
   - Added `analyzerApi` instance
   - Added `wafApi` instance
   - Added request/response interceptors for all services
   - Updated to match docker-compose port mappings

2. **`.env.local` & `.env.example`**
   ```bash
   NEXT_PUBLIC_CHATBOT_API_URL=http://localhost:8005    # Chatbot service
   NEXT_PUBLIC_WEB_APP_API_URL=http://localhost:8000    # FastAPI service
   NEXT_PUBLIC_ANALYZER_API_URL=http://localhost:8001   # Analyzer service
   NEXT_PUBLIC_WAF_API_URL=http://localhost:9090        # WAF service
   ```

### 🆕 New Features Added

#### **Services Status Page** (`/services`)
- Real-time health monitoring for all 4 backend services
- Auto-refresh every 30 seconds
- Visual status indicators (online/offline/checking)
- Service details with URLs and descriptions
- Warning alerts when services are down
- Statistics dashboard (total services, online, offline)

#### **Service Health Utilities** (`lib/service-health.ts`)
- `checkWafHealth()` - Check WAF service status
- `checkAnalyzerHealth()` - Check analyzer service status
- `checkChatbotHealth()` - Check chatbot service status
- `checkWebAppHealth()` - Check FastAPI service status
- `checkAllServices()` - Check all services at once

### 🎯 Service Architecture (from docker-compose)

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                    │
│                   Port 3000 (dev: 8002)                  │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┬──────────────┐
        │                 │                 │              │
        ▼                 ▼                 ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   FastAPI    │  │   Chatbot    │  │   Analyzer   │  │     WAF      │
│   Port 8000  │  │   Port 8005  │  │   Port 8001  │  │  Port 9090   │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │              │
        └─────────────────┴─────────────────┴──────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│    Neo4j     │  │  PostgreSQL  │  │   ChromaDB   │
│  Port 7687   │  │  Port 5432   │  │   (volume)   │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 🔄 API Flow

#### Configuration Upload & Analysis:
1. **Frontend** → uploads ZIP to **FastAPI** `/store_config`
2. **FastAPI** → extracts files to PostgreSQL
3. **FastAPI** → sends ZIP to **WAF** `/get_dump`
4. **WAF** → returns Apache config dump
5. **FastAPI** → stores dump in PostgreSQL
6. **FastAPI** → triggers **Analyzer** `/process_configs/{id}`
7. **Analyzer** → parses config and populates Neo4j + PostgreSQL

#### Chat Flow:
1. **Frontend** → sends message to **Chatbot** `/chat/ui_graph`
2. **Chatbot** → uses LangGraph with Neo4j + PostgreSQL context
3. **Chatbot** → returns AI response
4. **Frontend** → displays in chat UI

### 📊 Complete API Coverage

#### Chatbot API (`localhost:8005`)
- ✅ POST `/chat/login` - User authentication
- ✅ POST `/chat/register` - User registration  
- ✅ POST `/chat/ui_graph` - Send chat message
- ✅ GET `/chat/threads` - Get user's threads
- ✅ POST `/chat/threads` - Create new thread
- ✅ GET `/chat/threads/{id}` - Get thread messages
- ✅ PUT `/chat/threads/{id}` - Rename thread
- ✅ DELETE `/chat/threads/{id}` - Delete thread

#### FastAPI / Web App (`localhost:8000`)
- ✅ GET `/configs` - List configurations
- ✅ GET `/configs/selected` - Get selected config
- ✅ POST `/configs/select/{id}` - Select config
- ✅ DELETE `/configs/{id}` - Delete config
- ✅ POST `/configs/analyze/{id}` - Analyze config
- ✅ POST `/store_config` - Upload config
- ✅ POST `/get_dump` - Get WAF dump
- ✅ POST `/store_dump` - Store dump
- ✅ POST `/cypher/run` - Run Cypher query (graph)
- ✅ POST `/cypher/to_json` - Run Cypher query (table)
- ✅ GET `/directives/id` - Search by ID
- ✅ GET `/directives/tag` - Search by tag
- ✅ GET `/directives/id/{nodeid}` - Get by node ID
- ✅ GET `/directives/removed/{nodeid}` - Get removers
- ✅ POST `/database/export/{name}` - Export database
- ✅ POST `/database/import/{name}` - Import database
- ✅ GET `/get_metadata/{node_id}` - Get node metadata
- ✅ GET `/search_var/{var_name}` - Search variables
- ✅ POST `/get_setnode` - Get set nodes
- ✅ POST `/use_node` - Get use nodes
- ✅ POST `/get_node_ids` - Get node IDs from file

#### Analyzer API (`localhost:8001`)
- ✅ POST `/process_configs/{id}` - Process configuration
- ✅ GET `/` - Service root (health check)

#### WAF API (`localhost:9090`)
- ✅ POST `/get_dump` - Get Apache config dump
- ✅ GET `/health` - Health check
- ✅ GET `/` - Service root

### 🎨 New UI Components

1. **Services Status Page** - Monitor all backend services
2. **Health Check Utilities** - Reusable service health functions
3. **Updated Sidebar** - Added "Services" navigation item

### 🚀 Testing the Integration

1. **Start all Docker services:**
   ```bash
   cd /home/dassi/wafguard/WAF-GUARD
   docker-compose up -d
   ```

2. **Verify services are running:**
   ```bash
   docker ps
   ```
   You should see: fastapi, chatbot, analyzer, waf, neo4j, postgres

3. **Start the Next.js frontend:**
   ```bash
   cd waf-react
   npm run dev
   ```

4. **Open browser:**
   - Frontend: http://localhost:3000 (or 8002 if dev running)
   - Navigate to `/services` to see service status
   - All services should show as "Online"

### 🔍 Environment Variables

Make sure your `.env.local` has:
```bash
NEXT_PUBLIC_CHATBOT_API_URL=http://localhost:8005
NEXT_PUBLIC_WEB_APP_API_URL=http://localhost:8000
NEXT_PUBLIC_ANALYZER_API_URL=http://localhost:8001
NEXT_PUBLIC_WAF_API_URL=http://localhost:9090
```

### ✅ Build Status

```bash
✓ Compiled successfully
✓ TypeScript validation passed
✓ All 13 pages generated
✓ Production build ready
```

### 🎉 Summary

Your Next.js frontend now has **complete integration** with all 4 backend services:
- ✅ FastAPI (main web app API)
- ✅ Chatbot (AI assistant)
- ✅ Analyzer (config parser)
- ✅ WAF (Apache dump generator)

All API routes are properly configured with:
- Correct port mappings from docker-compose
- JWT authentication where needed
- Error handling and retries
- Health monitoring
- Loading states

The application is **production-ready** and fully integrated with your backend infrastructure! 🚀
