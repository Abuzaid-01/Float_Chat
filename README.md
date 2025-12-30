# 🌊 FloatChat - Complete Project Architecture

> **AI-Powered Conversational Interface for ARGO Ocean Data Analysis**  
> Ministry of Earth Sciences | INCOIS

---

## 📋 Table of Contents

1. [System Overview](#-system-overview)
2. [Architecture Diagram](#-architecture-diagram)
3. [Component Breakdown](#-component-breakdown)
4. [Execution Flow](#-execution-flow)
5. [MCP Tool System](#-mcp-tool-system)
6. [Data Flow Pipeline](#-data-flow-pipeline)
7. [Technology Stack](#-technology-stack)

---

## 🎯 System Overview

FloatChat is an intelligent conversational interface that enables users to query, analyze, and visualize **1.27 million ARGO ocean float records** using natural language. It combines **RAG (Retrieval-Augmented Generation)**, **MCP (Model Context Protocol)**, and **Vector Search** to provide accurate, context-aware responses.

### Key Features
- 🤖 Natural language queries (no SQL knowledge needed)
- 🗺️ Interactive map visualizations
- 📊 Real-time data analytics
- 🔍 Semantic profile search (FAISS vector store)
- 💬 Context-aware conversation memory
- 🛠️ 9 specialized MCP tools for data operations

---

## 🏗️ Architecture Diagram

### High-Level System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[Streamlit UI<br/>🖥️ Web Interface]
        TABS[Tab System<br/>📑 Dashboard / Map / Analytics / Chat]
    end
    
    subgraph "Application Layer"
        APP[Main App<br/>app.py<br/>🎯 Entry Point]
        INTENT[Intent Classifier<br/>🧠 Groq Llama 3.3<br/>Route: Data vs Conversational]
        MCP_CHAT[MCP Chat Interface<br/>💬 Query Handler]
    end
    
    subgraph "MCP Tool Layer"
        MCP_PROCESSOR[MCP Query Processor<br/>🔧 Tool Orchestrator]
        MCP_SERVER[ARGO MCP Server<br/>🛠️ 9 Tools Registered]
        
        subgraph "MCP Tools"
            T1[query_argo_data]
            T2[get_database_schema]
            T3[search_similar_profiles]
            T4[compare_regions]
            T5[identify_water_masses]
            T6[calculate_thermocline]
            T7[get_temporal_trends]
            T8[calculate_mld]
            T9[analyze_profile_statistics]
        end
    end
    
    subgraph "RAG Pipeline Layer"
        QP[Query Processor<br/>🔄 Orchestrates Pipeline]
        VS[Vector Store<br/>🔍 FAISS<br/>1,306 Embeddings]
        SQLGEN[SQL Generator<br/>🔧 Groq Llama 3.3<br/>NL → SQL]
        RG[Response Generator<br/>📝 Groq Llama 3.3<br/>Format Results]
    end
    
    subgraph "Data Layer"
        DB[(PostgreSQL<br/>Neon Cloud<br/>💾 1.27M Records)]
        SCHEMA[Database Schema<br/>argo_profiles<br/>profile_summaries]
    end
    
    subgraph "AI Models"
        GROQ[Groq API<br/>Llama 3.3 70B<br/>All LLM Tasks]
        EMBED[Embeddings<br/>all-MiniLM-L6-v2<br/>384 dimensions]
    end
    
    UI --> APP
    APP --> INTENT
    INTENT -->|Data Query| MCP_CHAT
    INTENT -->|Conversational| MCP_CHAT
    MCP_CHAT --> MCP_PROCESSOR
    MCP_PROCESSOR --> MCP_SERVER
    MCP_SERVER --> T1 & T2 & T3 & T4 & T5 & T6 & T7 & T8 & T9
    
    T1 & T3 & T4 & T5 & T6 & T7 & T8 & T9 --> QP
    T2 --> DB
    
    QP --> VS
    QP --> SQLGEN
    QP --> DB
    QP --> RG
    
    SQLGEN --> GROQ
    VS --> EMBED
    RG --> GROQ
    INTENT --> GROQ
    
    DB --> SCHEMA
    APP --> TABS
    TABS --> UI
    
    style UI fill:#667eea,stroke:#333,stroke-width:2px,color:#fff
    style MCP_SERVER fill:#f093fb,stroke:#333,stroke-width:2px,color:#000
    style QP fill:#4facfe,stroke:#333,stroke-width:2px,color:#fff
    style DB fill:#43e97b,stroke:#333,stroke-width:2px,color:#000
    style GROQ fill:#feca57,stroke:#333,stroke-width:2px,color:#000
```

---

## 🧩 Component Breakdown

### 1. Frontend Layer (`streamlit_app/`)

#### Main Application (`app.py`)
- **Purpose**: Entry point for the entire application
- **Responsibilities**:
  - Initialize Streamlit page configuration
  - Load custom CSS for modern UI
  - Render main header and navigation
  - Manage tab system (Dashboard, Map, Analytics, Chat, Data Table)
  - Coordinate component communication via session state

#### Components (`components/`)

```mermaid
graph LR
    A[app.py] --> B[MCP Chat Interface]
    A --> C[Data Dashboard]
    A --> D[Map View]
    A --> E[Analytics Panel]
    A --> F[Profile Viewer]
    
    B --> G[Session State Manager]
    C --> G
    D --> G
    E --> G
    
    style A fill:#667eea,color:#fff
    style B fill:#f093fb,color:#000
    style G fill:#43e97b,color:#000
```

| Component | File | Responsibility |
|-----------|------|----------------|
| **MCP Chat Interface** | `mcp_chat_interface.py` | Query input, conversation memory, response display |
| **Data Dashboard** | `data_dashboard.py` | Metrics cards, query-specific statistics |
| **Map View** | `map_view.py` | Interactive Leaflet map with float locations |
| **Advanced Viz Panel** | `advanced_viz_panel.py` | Plotly charts (profiles, trends, comparisons) |
| **Profile Viewer** | `profile_viewer.py` | Detailed profile analysis |
| **Sidebar** | `sidebar.py` | Filters, settings, about section |

---

### 2. Intent Classification System (`rag_engine/intent_classifier.py`)

#### Purpose
Routes queries to appropriate handlers based on user intent, making responses human-like and context-aware.

```mermaid
flowchart TD
    START[User Query] --> KEYWORD{Keyword Match?}
    
    KEYWORD -->|Yes: greeting| GREETING[Return Greeting]
    KEYWORD -->|Yes: thanks| THANKS[Return Thanks]
    KEYWORD -->|Yes: help| HELP[Show Capabilities]
    KEYWORD -->|Yes: who built| DEV[Developer Info]
    KEYWORD -->|Yes: who are you| IDENTITY[Assistant Identity]
    KEYWORD -->|Yes: about floatchat| ABOUT[About FloatChat]
    
    KEYWORD -->|No Match| LLM[Groq Llama 3.3<br/>LLM Classification]
    
    LLM --> INTENT{Intent?}
    INTENT -->|Conversational| CONV[Generate Response]
    INTENT -->|Data Query| DATA[Route to MCP]
    
    GREETING & THANKS & HELP & DEV & IDENTITY & ABOUT --> RETURN[Return to User]
    CONV --> RETURN
    DATA --> MCP[MCP Query Processor]
    
    style START fill:#667eea,color:#fff
    style LLM fill:#feca57,color:#000
    style DATA fill:#f093fb,color:#000
    style MCP fill:#4facfe,color:#fff
```

#### Supported Intents
1. **greeting** - "hi", "hello", "hey"
2. **thanks** - "thank you", "thanks"
3. **help** - "help me", "what can you do"
4. **developer_info** - "who built you"
5. **assistant_identity** - "who are you"
6. **about_floatchat** - "what is floatchat"
7. **data_query** - All oceanographic queries (default)

---

### 3. MCP Tool System

#### MCP Architecture

```mermaid
graph TB
    subgraph "MCP Protocol Layer"
        PROTOCOL[MCP Protocol<br/>mcp_protocol.py<br/>Tool Registry]
    end
    
    subgraph "MCP Server"
        SERVER[ARGO MCP Server<br/>argo_mcp_server.py]
        TOOLS[Tool Handlers]
    end
    
    subgraph "Query Processing"
        PROCESSOR[MCP Query Processor<br/>mcp_query_processor.py<br/>Tool Selection & Orchestration]
    end
    
    subgraph "Tools Implementation"
        direction LR
        T1[Tool 1<br/>query_argo_data<br/>General queries]
        T2[Tool 2<br/>get_database_schema<br/>Schema info]
        T3[Tool 3<br/>search_similar_profiles<br/>Vector search]
        T4[Tool 4<br/>compare_regions<br/>Regional analysis]
        T5[Tool 5<br/>identify_water_masses<br/>T-S analysis]
        T6[Tool 6<br/>calculate_thermocline<br/>Thermal layers]
        T7[Tool 7<br/>get_temporal_trends<br/>Time series]
        T8[Tool 8<br/>calculate_mld<br/>Mixed layer depth]
        T9[Tool 9<br/>analyze_profile_statistics<br/>Profile stats]
    end
    
    PROCESSOR --> SERVER
    SERVER --> PROTOCOL
    PROTOCOL --> TOOLS
    TOOLS --> T1 & T2 & T3 & T4 & T5 & T6 & T7 & T8 & T9
    
    style PROTOCOL fill:#667eea,color:#fff
    style SERVER fill:#f093fb,color:#000
    style PROCESSOR fill:#4facfe,color:#fff
```

#### MCP Tool Details

| Tool Name | Purpose | Input | Output |
|-----------|---------|-------|--------|
| **query_argo_data** | General data queries | `query` (string), `limit` (int) | DataFrame with results |
| **get_database_schema** | Get DB structure | None | Schema + record counts |
| **search_similar_profiles** | Semantic search | `query_text`, `top_k` | Similar profiles |
| **compare_regions** | Regional comparison | `region1`, `region2`, `parameter` | Comparative stats |
| **identify_water_masses** | T-S diagram analysis | `min_depth`, `max_depth` | Water mass classification |
| **calculate_thermocline** | Find thermocline depth | `float_id`, `cycle` | Thermocline depth + gradient |
| **get_temporal_trends** | Time series analysis | `parameter`, `date_range` | Trend data |
| **calculate_mld** | Mixed layer depth | `float_id`, `cycle`, `criteria` | MLD value |
| **analyze_profile_statistics** | Profile summary | `float_id`, `cycle` | Detailed statistics |

---

### 4. RAG Pipeline

#### Complete RAG Flow

```mermaid
sequenceDiagram
    participant User
    participant MCP as MCP Processor
    participant VS as Vector Store<br/>(FAISS)
    participant SQL as SQL Generator<br/>(Groq Llama 3.3)
    participant DB as PostgreSQL
    participant RG as Response Generator<br/>(Groq Llama 3.3)
    
    User->>MCP: Natural language query
    
    Note over MCP: Step 1: Context Retrieval
    MCP->>VS: Generate query embedding
    VS->>VS: Search similar profiles (k=3)
    VS-->>MCP: Return top 3 profiles + metadata
    
    Note over MCP: Step 2: SQL Generation
    MCP->>SQL: Query + Retrieved context
    SQL->>SQL: Generate SQL with Groq LLM
    SQL->>SQL: Validate SQL syntax
    SQL-->>MCP: Valid SQL query
    
    Note over MCP: Step 3: Execute Query
    MCP->>DB: Execute SQL
    DB-->>MCP: Return results (DataFrame)
    
    Note over MCP: Step 4: Response Generation
    MCP->>RG: Query + Results + Context
    RG->>RG: Format natural language response
    RG-->>MCP: Human-readable response
    
    MCP-->>User: Final response + visualizations
    
    Note over User,RG: Total Pipeline Time: ~2-5 seconds
```

#### Pipeline Components

##### **Query Processor** (`rag_engine/query_processor.py`)
- Orchestrates the entire RAG pipeline
- Coordinates vector search, SQL generation, and execution
- Returns structured results with metadata

##### **Vector Store** (`vector_store/vector_db.py`)
- Technology: FAISS (Facebook AI Similarity Search)
- **1,306 profile embeddings** (384 dimensions)
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Average search time: <100ms

##### **SQL Generator** (`rag_engine/sql_generator.py`)
- Powered by Groq Llama 3.3 70B
- Converts natural language → SQL queries
- Context-aware with retrieved profile summaries
- Validates SQL syntax before execution

##### **Response Generator** (`rag_engine/response_generator.py`)
- Formats query results into natural language
- Maintains conversational tone
- Includes relevant context and explanations

---

## 🔄 Complete Execution Flow

### End-to-End Query Processing

```mermaid
flowchart TD
    START([User enters query]) --> LOAD[Load into Streamlit UI]
    
    LOAD --> SESSION{Check Session State}
    SESSION -->|First message| INIT[Initialize conversation]
    SESSION -->|Existing| APPEND[Append to history]
    
    INIT & APPEND --> INTENT[Intent Classification]
    
    INTENT --> CLASSIFY{Query Type?}
    
    CLASSIFY -->|Conversational| CONV_RESP[Generate conversational response]
    CLASSIFY -->|Data Query| MCP_START[MCP Query Processor]
    
    CONV_RESP --> DISPLAY
    
    MCP_START --> PATTERN{Match Query Pattern?}
    
    PATTERN -->|Schema| T_SCHEMA[Tool: get_database_schema]
    PATTERN -->|Comparison| T_COMPARE[Tool: compare_regions]
    PATTERN -->|Thermocline| T_THERMO[Tool: calculate_thermocline]
    PATTERN -->|Water Mass| T_WATER[Tool: identify_water_masses]
    PATTERN -->|Temporal| T_TEMPORAL[Tool: get_temporal_trends]
    PATTERN -->|MLD| T_MLD[Tool: calculate_mld]
    PATTERN -->|Similar| T_SIMILAR[Tool: search_similar_profiles]
    PATTERN -->|Analysis| T_STATS[Tool: analyze_profile_statistics]
    PATTERN -->|General| T_QUERY[Tool: query_argo_data]
    
    T_SCHEMA --> EXECUTE_TOOL
    T_COMPARE --> EXECUTE_TOOL
    T_THERMO --> EXECUTE_TOOL
    T_WATER --> EXECUTE_TOOL
    T_TEMPORAL --> EXECUTE_TOOL
    T_MLD --> EXECUTE_TOOL
    T_SIMILAR --> EXECUTE_TOOL
    T_STATS --> EXECUTE_TOOL
    T_QUERY --> RAG_PIPELINE
    
    EXECUTE_TOOL[Execute Tool Handler] --> RESULTS[Get Results]
    
    RAG_PIPELINE[RAG Pipeline] --> VECTOR[Vector Search<br/>FAISS]
    VECTOR --> SQL_GEN[SQL Generation<br/>Groq Llama 3.3]
    SQL_GEN --> DB_EXEC[Execute on PostgreSQL]
    DB_EXEC --> RESULTS
    
    RESULTS --> ENHANCE[Response Enhancement<br/>Groq Llama 3.3]
    ENHANCE --> FORMAT[Format Response]
    FORMAT --> VISUALIZE[Generate Visualizations]
    
    VISUALIZE --> UPDATE_STATE[Update Session State]
    UPDATE_STATE --> UPDATE_TABS[Sync All Tabs]
    
    UPDATE_TABS --> DISPLAY[Display in UI]
    
    DISPLAY --> END([User sees response])
    
    style START fill:#667eea,color:#fff
    style INTENT fill:#feca57,color:#000
    style MCP_START fill:#f093fb,color:#000
    style RAG_PIPELINE fill:#4facfe,color:#fff
    style DB_EXEC fill:#43e97b,color:#000
    style END fill:#667eea,color:#fff
```

---

## 📊 Data Flow Pipeline

### Database to Visualization

```mermaid
graph LR
    subgraph "Data Sources"
        ARGO[ARGO Float Data<br/>NetCDF Files]
    end
    
    subgraph "Database"
        DB[(PostgreSQL Neon<br/>1,268,992 records)]
        T1[argo_profiles<br/>Core + BGC params]
        T2[profile_summaries<br/>1,306 summaries]
    end
    
    subgraph "Vector Store"
        VS[FAISS Index<br/>1,306 embeddings]
        META[Metadata PKL<br/>Profile info]
    end
    
    subgraph "Processing"
        QP[Query Processor]
        SQL[SQL Generator]
    end
    
    subgraph "Results"
        DF[Pandas DataFrame]
        VIZ[Plotly Visualizations]
        MAP[Leaflet Maps]
        METRICS[Metric Cards]
    end
    
    ARGO -->|ETL| DB
    DB --> T1 & T2
    T2 -->|Generate Embeddings| VS
    VS --> META
    
    T1 & T2 --> QP
    VS --> QP
    QP --> SQL
    SQL --> DB
    DB --> DF
    
    DF --> VIZ & MAP & METRICS
    
    style DB fill:#43e97b,color:#000
    style VS fill:#4facfe,color:#fff
    style DF fill:#f093fb,color:#000
```

---

## 💾 Database Schema


### Data Statistics

| Metric | Value |
|--------|-------|
| **Total Records** | 1,268,992 |
| **Unique Floats** | 668 |
| **Unique Profiles** | 1,306 |
| **Date Range** | 2004 - 2024 |
| **Geographic Coverage** | Indian Ocean |
| **Core ARGO Parameters** | Temperature, Salinity, Pressure |
| **BGC Parameters** | DO, Nitrate, pH, Chlorophyll, BBP, Irradiance |

---

## 🛠️ Technology Stack

### Frontend
```mermaid
graph LR
    A[Streamlit 1.31+] --> B[Plotly Express]
    A --> C[Leaflet Maps]
    A --> D[Custom CSS/JS]
    
    style A fill:#FF4B4B,color:#fff
```

### Backend & AI
```mermaid
graph TB
    subgraph "AI Models"
        G[Groq<br/>Llama 3.3 70B<br/>All LLM Tasks]
        E[HuggingFace<br/>all-MiniLM-L6-v2<br/>Embeddings]
    end
    
    subgraph "Data Processing"
        PD[Pandas]
        NP[NumPy]
        SP[SciPy]
    end
    
    subgraph "MCP & RAG"
        LC[LangChain]
        LS[LangSmith Tracing]
    end
    
    style G fill:#feca57,color:#000
    style E fill:#4facfe,color:#fff
```

### Database & Storage
```mermaid
graph LR
    A[PostgreSQL 16<br/>Neon Cloud] --> B[SQLAlchemy ORM]
    C[FAISS<br/>Vector Store] --> D[384-dim Embeddings]
    
    style A fill:#43e97b,color:#000
    style C fill:#4facfe,color:#fff
```

### Complete Stack Table

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Frontend** | Streamlit | Web UI framework |
| **Visualization** | Plotly, Leaflet | Charts and maps |
| **Database** | PostgreSQL (Neon) | Data storage |
| **Vector Store** | FAISS | Similarity search |
| **LLM (All Tasks)** | Groq Llama 3.3 70B | Intent, SQL, Responses |
| **Embeddings** | all-MiniLM-L6-v2 | Text embeddings |
| **ORM** | SQLAlchemy | Database operations |
| **Framework** | LangChain | RAG orchestration |
| **Monitoring** | LangSmith | Query tracing |
| **Data Processing** | Pandas, NumPy | Data manipulation |

---

## 🚀 Performance Metrics

### Query Processing Times

```mermaid
gantt
    title Average Query Processing Time Breakdown
    dateFormat YYYY-MM-DD
    axisFormat %L
    
    section RAG Pipeline
    Intent Classification (200ms)    :a1, 2024-01-01, 200ms
    Vector Search (100ms)            :a2, after a1, 100ms
    SQL Generation (800ms)           :a3, after a2, 800ms
    Database Query (600ms)           :a4, after a3, 600ms
    Response Generation (500ms)      :a5, after a4, 500ms
    Visualization (300ms)            :a6, after a5, 300ms
```

| Stage | Average Time | Description |
|-------|--------------|-------------|
| **Intent Classification** | 200ms | Groq API call |
| **Vector Search** | 100ms | FAISS similarity search |
| **SQL Generation** | 800ms | Groq API + validation |
| **Database Query** | 600ms | PostgreSQL execution |
| **Response Generation** | 500ms | Format results with Groq |
| **Visualization** | 300ms | Generate Plotly charts |
| **Total Pipeline** | **~2.5s** | End-to-end query |

---

## 📈 System Capabilities

### What FloatChat Can Do

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'primaryColor':'#667eea','primaryTextColor':'#fff','primaryBorderColor':'#5a67d8','lineColor':'#4facfe','secondaryColor':'#f093fb','tertiaryColor':'#43e97b'}}}%%
mindmap
    root((FloatChat<br/>Capabilities))
        Data Queries
            Temperature profiles
            Salinity measurements
            BGC parameters
            Float locations
            Historical data
        Analysis
            Regional comparisons
            Water mass identification
            Thermocline calculation
            Mixed layer depth
            Temporal trends
            Profile statistics
        Visualizations
            Interactive maps
            Depth profiles
            Time series
            T-S diagrams
            Scatter plots
            Heatmaps
        Smart Features
            Natural language
            Context awareness
            Conversation memory
            Smart suggestions
            Follow-up queries
```

---

## 🎓 Example Queries

### Supported Query Types

| Query Type | Example | MCP Tool Used |
|------------|---------|---------------|
| **General** | "Show me temperature data in Arabian Sea" | `query_argo_data` |
| **Schema** | "What data is available?" | `get_database_schema` |
| **Comparison** | "Compare salinity in Bay of Bengal vs Arabian Sea" | `compare_regions` |
| **Analysis** | "Find the thermocline for float 2902746" | `calculate_thermocline` |
| **Water Mass** | "Identify water masses between 100-500m" | `identify_water_masses` |
| **Trends** | "Show temperature trends over last 5 years" | `get_temporal_trends` |
| **Similarity** | "Find profiles similar to warm tropical water" | `search_similar_profiles` |
| **Statistics** | "Analyze profile statistics for float 1901740" | `analyze_profile_statistics` |

---

## 🔐 Security & Privacy

- ✅ No hardcoded API keys in code
- ✅ Environment variables for sensitive data
- ✅ `.gitignore` configured properly
- ✅ Secrets managed via Streamlit Cloud
- ✅ Database uses SSL connections
- ✅ Query logging for audit trails

---



| Metric | Count |
|--------|-------|
| **Total Lines of Code** | ~15,000 |
| **Python Files** | 45+ |
| **Components** | 12 |
| **MCP Tools** | 9 |
| **Database Tables** | 2 |
| **Vector Embeddings** | 1,306 |
| **Test Files** | 4 |

---

## 🎯 Key Innovations

1. **Hybrid RAG + MCP Architecture**
   - Combines retrieval-augmented generation with Model Context Protocol
   - Tool-based approach for specialized oceanographic operations

2. **Intent-Driven Routing**
   - Smart classification between conversational and data queries
   - Human-like responses for non-data questions

3. **Conversation Memory**
   - Maintains context across multiple turns
   - Understands follow-up queries ("tell me more", "elaborate")

4. **Synchronized Visualization**
   - All tabs update based on query context
   - Query-specific metrics (not entire database)

5. **Semantic Profile Search**
   - FAISS vector store for finding similar oceanographic profiles
   - Enables "find profiles like X" queries

---

## 📖 Documentation

- ✅ **README.md** - Project overview and features
- ✅ **DEPLOYMENT.md** - Complete deployment guide
- ✅ **SETUP_INSTRUCTIONS.md** - Local development setup
- ✅ **INTENT_CLASSIFICATION_GUIDE.md** - Intent system details
- ✅ **PERFORMANCE_OPTIMIZATION_GUIDE.md** - Performance tips
- ✅ **README_PROJECT_ARCHITECTURE.md** - This document

---



---

## 📞 Support

- **Documentation**: All `.md` files in root directory
- **Issues**: Check DEPLOYMENT.md troubleshooting section
- **Monitoring**: LangSmith dashboard for query traces

---

## 🏆 Achievements

- ✅ **1.27M records** migrated and queryable
- ✅ **2-3 second** average query response time
- ✅ **92% reduction** in documentation clutter
- ✅ **100%** test coverage for intent classification
- ✅ **Zero downtime** deployment on Streamlit Cloud

---

**Built with ❤️ by Abuzaid


---

*Last Updated: December 28, 2025*
