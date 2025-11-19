# WAF-GUARD Frontend

A modern, professional Next.js application for managing and analyzing Web Application Firewall (WAF) configurations.

## Features

### 🔐 Authentication
- Secure JWT-based authentication
- User registration and login
- Protected routes with automatic redirection

### ⚙️ Configuration Management
- Upload WAF configurations (ZIP/TAR)
- Select active configuration
- Analyze configurations with progress tracking
- View and edit configuration files with Monaco Editor
- File tree navigation

### 💬 AI Chatbot
- Interactive chat interface with LangGraph integration
- Thread management (create, rename, delete)
- Message history
- Real-time streaming responses
- Context-aware conversations about WAF configurations

### 📊 Graph Database Queries
- Interactive Cypher query editor
- Graph visualization with vis-network
- Table view for query results
- Example queries for quick start

### 🔍 Directives Search
- Search by Rule ID
- Search by Tag
- Search by Node ID
- Find remover directives
- Detailed results with all properties

### 💾 Database Management
- Export Neo4j and PostgreSQL databases
- Import from previous exports
- System status monitoring
- Safe backup and restore operations

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Radix UI primitives
- **Code Editor**: Monaco Editor
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **HTTP Client**: Axios
- **Notifications**: React Hot Toast
- **Graph Visualization**: vis-network

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Running backend services:
  - Chatbot API (default: http://localhost:8000)
  - Web App API (default: http://localhost:8001)

### Installation

1. Navigate to the waf-react directory:
```bash
cd waf-react
```

2. Install dependencies:
```bash
npm install
```

3. Create environment file:
```bash
cp .env.example .env.local
```

4. Update the environment variables in `.env.local` if your backend APIs are running on different ports.

### Development

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
waf-react/
├── app/                          # Next.js App Router pages
│   ├── (dashboard)/             # Protected dashboard routes
│   │   ├── chatbot/            # Chatbot interface
│   │   ├── configs/            # Configuration management
│   │   ├── cypher/             # Cypher query interface
│   │   ├── database/           # Database management
│   │   ├── dashboard/          # Main dashboard
│   │   ├── directives/         # Directives search
│   │   └── layout.tsx          # Dashboard layout with sidebar
│   ├── login/                  # Login page
│   ├── register/               # Registration page
│   ├── layout.tsx              # Root layout
│   └── page.tsx                # Home page (redirects to dashboard)
├── components/
│   ├── auth/                   # Authentication components
│   ├── editor/                 # Monaco code editor
│   ├── layout/                 # Layout components (sidebar)
│   ├── providers/              # React Query provider
│   └── ui/                     # Reusable UI components
├── lib/
│   ├── api.ts                  # Axios instances and interceptors
│   └── utils.ts                # Utility functions
├── stores/
│   ├── auth.ts                 # Authentication state (Zustand)
│   └── config.ts               # Configuration state (Zustand)
└── types/
    └── index.ts                # TypeScript type definitions
```

## License

Part of the WAF-GUARD project.
