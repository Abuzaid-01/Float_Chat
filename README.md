# 🌊 FloatChat — AI-Powered ARGO Ocean Data Intelligence

[![Netlify Status](https://api.netlify.com/api/v1/badges/53d62349-d478-4fcc-a8c1-5c8c26caeb39/deploy-status)](https://app.netlify.com/projects/peppy-pastelito-f38703/deploys)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-brightgreen.svg)](https://neon.tech/)

> **Conversational AI interface for querying 1.27 million ARGO oceanographic float records using natural language — no SQL required.**

**🔗 Live App (Next.js):** [peppy-pastelito-f38703.netlify.app](https://peppy-pastelito-f38703.netlify.app)  
**🔗 Live App (Streamlit):** [floatchat-chat.streamlit.app](https://floatchat-chat.streamlit.app/)  
**📂 GitHub:** [github.com/Abuzaid-01/Float_Chat](https://github.com/Abuzaid-01/Float_Chat)

---

## 📋 Table of Contents

1. [What is FloatChat?](#-what-is-floatchat)
2. [Dataset Statistics](#-dataset-statistics)
3. [System Architecture](#-system-architecture)
4. [RAG Pipeline](#-rag-pipeline-8-steps)
5. [Key Technical Innovations](#-key-technical-innovations)
6. [MCP Tool System](#-mcp-tool-system)
7. [Advanced Analytics](#-advanced-analytics)
8. [Database Schema](#-database-schema)
9. [Dual Frontend](#-dual-frontend)
10. [Project Structure](#-project-structure)
11. [Tech Stack](#-tech-stack)
12. [Local Development Setup](#-local-development-setup)
13. [Environment Variables](#-environment-variables)
14. [Deployment](#-deployment)
15. [Example Queries](#-example-queries)

---

## 🎯 What is FloatChat?

**ARGO floats** are autonomous underwater robots deployed globally to measure ocean temperature, salinity, and pressure at depths up to 2,000 m. They surface every 10 days to transmit data — forming one of the world's most important oceanographic datasets.

**FloatChat** makes this data accessible to anyone:

- Ask questions in plain English: *"What is the average temperature in the Arabian Sea in October?"*
- Get back structured tables, natural-language summaries, and interactive charts
- Drill into profiles: thermocline depth, mixed layer depth, water mass identification
- Compare regions, track temporal trends, and run semantic similarity searches across profiles

The backend combines a **Hybrid RAG pipeline** (FAISS + BM25 + RRF reranking), **dynamic SQL generation** (Groq Llama 3.3 70B), **semantic caching**, a **self-correction loop**, and a **9-tool MCP server** — making it production-ready, not just a demo.

---

## 📊 Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Measurements** | 1,268,992 |
| **Unique ARGO Floats** | 714 |
| **Vertical Profiles** | 1,306 |
| **Date Range** | 2004 – 2025 |
| **Geographic Coverage** | Indian Ocean |
| **Core Parameters** | Temperature, Salinity, Pressure |
| **BGC Parameters** | Dissolved O₂, Nitrate, pH, Chlorophyll-a, BBP, Irradiance |
| **Vector Embeddings** | 1,306 (384-dim, all-MiniLM-L6-v2) |

### Indian Ocean Regions

| Region | Coverage |
|--------|----------|
| Arabian Sea | 45–78°E, 5–25°N |
| Bay of Bengal | 80–100°E, 5–22°N |
| Red Sea | 32–43°E, 12–28°N |
| Andaman Sea | 92–100°E, 5–15°N |
| Equatorial Indian Ocean | 45–95°E, 10°S–5°N |
| Southern Indian Ocean | 20–115°E, 60–30°S |

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Frontends
        NX["Next.js 16\n(Netlify)"]
        ST["Streamlit\n(Streamlit Cloud)"]
    end

    subgraph FastAPI_Backend["FastAPI Backend (api/main.py)"]
        CRW["_rewrite_with_context()\nConversation Rewriter"]
        IC["Intent Classifier\n8 intent categories"]
        QR["Query Router\nTemplate / Simple / Complex"]
    end

    subgraph RAG_Engine["RAG Engine"]
        QP["Query Processor\n8-step pipeline"]
        SC["Semantic Cache\ncosine ≥ 0.95, 30-min TTL"]
        HR["Hybrid Retriever\nFAISS + BM25 + RRF"]
        SG["SQL Generator\nDynamic Schema Pruning"]
        RG["Response Generator"]
    end

    subgraph MCP_Layer["MCP Server (9 tools)"]
        MCP["argo_mcp_server.py"]
    end

    subgraph Data_Layer["Data Layer"]
        DB[("Neon PostgreSQL\n1.27M records")]
        VS["FAISS Vector Store\n1,306 embeddings"]
    end

    subgraph AI_Models["AI Models"]
        GROQ["Groq Llama 3.3 70B\nSQL + Response + Intent"]
        EMB["all-MiniLM-L6-v2\n384-dim embeddings"]
    end

    NX --> FastAPI_Backend
    ST --> FastAPI_Backend
    CRW --> IC --> QR --> QP
    QP --> SC
    QP --> HR --> VS
    QP --> SG --> GROQ
    QP --> DB
    QP --> RG --> GROQ
    QP --> MCP
    EMB --> VS
```

---

## 🔄 RAG Pipeline (8 Steps)

Every data query passes through this pipeline in `rag_engine/query_processor.py`:

| Step | Name | What Happens |
|------|------|--------------|
| **1** | **Semantic Cache Check** | Cosine similarity (≥ 0.95) against recent queries. Cache hit → return instantly, skip all steps below |
| **2** | **Query Parsing** | `QueryParser` extracts dates, regions, float IDs, parameters, quality flags. Detects SCOPE_BROADENING follow-ups |
| **3** | **Context Rewriting** | `_rewrite_with_context()` in FastAPI resolves pronouns and references using prior conversation turns |
| **4** | **Hybrid Retrieval** | FAISS (dense, `k=10`) + BM25 (sparse, `k=10`) → RRF reranking (`k=60`) → top-5 profile summaries as context |
| **5** | **Dynamic Schema Pruning** | Only relevant columns passed to LLM (~57% token reduction vs full schema) |
| **6** | **SQL Generation** | Groq Llama 3.3 70B generates SQL with retrieved context; syntax validated before execution |
| **7** | **Self-Correction Loop** | If 0 results returned: auto-relax QC filters + widen bounding box by 5° and retry |
| **8** | **Response Generation** | Results formatted into natural-language response with Groq Llama 3.3 70B |

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant SC as Semantic Cache
    participant HR as Hybrid Retriever
    participant SG as SQL Generator
    participant DB as Neon PostgreSQL
    participant RG as Response Generator

    U->>API: Natural language query
    API->>API: _rewrite_with_context()
    API->>SC: Check cache (cosine ≥ 0.95)
    SC-->>API: Cache HIT → instant return
    Note over API,RG: Cache MISS → full pipeline
    API->>HR: FAISS(k=10) + BM25(k=10) → RRF → top-5
    HR-->>API: Profile context
    API->>SG: Query + context + pruned schema
    SG->>DB: Validated SQL
    DB-->>SG: Results DataFrame
    Note over SG,DB: 0 results? Self-correct: relax QC + widen 5°
    SG->>RG: Results + context
    RG-->>U: Natural language response (~2–5 s)
```

---

## ✨ Key Technical Innovations

### 1. Hybrid RAG with RRF Reranking
- **Dense retrieval**: FAISS `IndexFlatL2` (384-dim embeddings from `all-MiniLM-L6-v2`)
- **Sparse retrieval**: BM25 over profile summary text
- **Fusion**: Reciprocal Rank Fusion (`k=60`) merges both ranked lists for best of both worlds

### 2. Dynamic Schema Pruning (~57% Token Reduction)
The SQL generator in `rag_engine/sql_generator.py` inspects the parsed query and passes only the columns likely needed to the LLM — not the full schema. This cuts input tokens dramatically and reduces hallucination risk.

### 3. Semantic Caching
`rag_engine/semantic_cache.py` caches query–response pairs. On each new query it computes cosine similarity against cached entries:
- **Threshold**: ≥ 0.95
- **TTL**: 30 minutes
- **Max entries**: 200
- **Effect**: Sub-second responses for semantically identical follow-ups

### 4. Self-Correction Loop
When the DB returns 0 rows, the pipeline automatically:
1. Removes strict QC flag filters (`qc_flag = 1`)
2. Widens geographic bounding boxes by ±5°
3. Re-runs the SQL
This prevents frustrating "no data found" dead ends.

### 5. Scope-Broadening Detection
`rag_engine/query_parser.py` uses regex patterns to detect when a follow-up broadens scope (e.g., *"for October 12"* → *"for each day"*). When detected, the prior date/region filter is discarded rather than kept as context — fixing a critical conversation memory bug.

### 6. Conversation Context Rewriting
`api/main.py` runs `_rewrite_with_context()` before every query. It prepends the last N conversation turns and asks the LLM to rewrite the user's message as a fully self-contained question. This allows multi-turn conversations like:
> "Show data for float 2902746" → "Now compare it with the Arabian Sea" ✅

### 7. Query Routing
`rag_engine/query_router.py` classifies each query into one of three routes:
- **Template** — exact pattern match (schema lookups, count queries) → no LLM call
- **Simple RAG** — single-table queries → single SQL + response
- **Complex RAG** — multi-step, comparative, or analytical → full 8-step pipeline + MCP tools

### 8. MCP Protocol (9 Specialized Tools)
The Model Context Protocol server exposes oceanographic tools as structured APIs, enabling the LLM to call them with typed arguments and get structured JSON back.

---

## 🛠️ MCP Tool System

`mcp_server/argo_mcp_server.py` registers 9 tools:

| # | Tool | Purpose | Key Inputs |
|---|------|---------|------------|
| 1 | `query_argo_data` | General NL→SQL data queries | `query`, `limit` |
| 2 | `get_database_schema` | Return full schema + row counts | — |
| 3 | `search_similar_profiles` | FAISS semantic search | `query_text`, `top_k` |
| 4 | `analyze_float_profile` | Stats for one float/cycle | `float_id`, `cycle` |
| 5 | `calculate_thermocline` | Find thermocline depth & gradient | `float_id`, `cycle` |
| 6 | `identify_water_masses` | T-S diagram classification | `min_depth`, `max_depth` |
| 7 | `compare_regions` | Side-by-side regional comparison | `region1`, `region2`, `parameter` |
| 8 | `analyze_temporal_trends` | Time series of any parameter | `parameter`, `date_range` |
| 9 | `calculate_mixed_layer_depth` | MLD via density/temperature criteria | `float_id`, `cycle`, `criteria` |

---

## 🌡️ Advanced Analytics

`advanced_analytics/profile_analytics.py` provides physics-based computations:

### Thermocline Detection
- Computes temperature gradient (°C / dbar) at every depth level
- Identifies the depth where `|dT/dP|` exceeds threshold
- Returns thermocline depth + gradient strength

### Mixed Layer Depth (MLD)
- **Temperature criterion**: depth where T drops 0.2°C below surface
- **Density criterion**: depth where Δσθ > 0.03 kg/m³ from surface
- Returns MLD value in dbar

### Water Mass Identification (8 Types)
Classifies water parcels in T-S space:

| Code | Name | Typical Location |
|------|------|-----------------|
| IOSW | Indian Ocean Surface Water | Surface, tropical |
| ASHSW | Arabian Sea High-Salinity Water | Arabian Sea surface |
| BBLSW | Bay of Bengal Low-Salinity Water | BoB surface |
| IOCW | Indian Ocean Central Water | 200–800 m |
| ITW | Indian Thermocline Water | Thermocline layer |
| AAIW | Antarctic Intermediate Water | 800–1200 m |
| IDW | Indian Deep Water | 1500–3500 m |
| AABW | Antarctic Bottom Water | > 3500 m |

### Brunt-Väisälä Frequency (N²)
Computes ocean stability: $N^2 = -\frac{g}{\rho_0} \frac{\partial \rho}{\partial z}$, indicating stratification strength at each depth.

---

## 💾 Database Schema

**Primary table**: `argo_profiles` (1,268,992 rows)

| Column | Type | Description |
|--------|------|-------------|
| `float_id` | VARCHAR | ARGO float WMO identifier |
| `cycle_number` | INTEGER | Profile cycle (surfacing number) |
| `observation_date` | TIMESTAMP | UTC observation time |
| `latitude` | FLOAT | Decimal degrees N |
| `longitude` | FLOAT | Decimal degrees E |
| `pressure` | FLOAT | Depth in dbar |
| `temperature` | FLOAT | In-situ temperature (°C) |
| `salinity` | FLOAT | Practical salinity units (PSU) |
| `temperature_qc` | INTEGER | Quality flag (1=good, 4=bad) |
| `salinity_qc` | INTEGER | Quality flag |
| `region` | VARCHAR | One of 6 Indian Ocean regions |
| `dissolved_oxygen` | FLOAT | BGC parameter (µmol/kg) |
| `nitrate` | FLOAT | BGC parameter (µmol/kg) |
| `ph` | FLOAT | BGC parameter |
| `chlorophyll_a` | FLOAT | BGC parameter (mg/m³) |

**Supporting tables**: `profile_summaries` (1,306 rows, used for vector embeddings), `query_logs`, `saved_queries`, `workflow_recipes`

---

## 🖥️ Dual Frontend

FloatChat ships with **two independent frontends** that share the same FastAPI backend.

### Frontend 1 — Next.js 16 (Production)
- **Location**: `nexus-saa-s-ai-platform/`
- **Deployed on**: Netlify → [peppy-pastelito-f38703.netlify.app](https://peppy-pastelito-f38703.netlify.app)
- **Stack**: Next.js 16, React 19, TypeScript, Tailwind CSS, Radix UI
- **Design**: Dark-mode terminal/SaaS aesthetic
- **Features**: Chat interface, data tables with CSV export, response time display, conversation history
- **Build**: `pnpm run build` → `.next/` (static + edge functions)

### Frontend 2 — Streamlit (Scientific Dashboard)
- **Location**: `streamlit_app/`
- **Deployed on**: Streamlit Cloud → [floatchat-chat.streamlit.app](https://floatchat-chat.streamlit.app/)
- **Stack**: Streamlit 1.31+, Plotly, Leaflet
- **Design**: 5-tab scientific dashboard
- **Tabs**:
  1. **Chat** — conversational query interface
  2. **Dashboard** — aggregate metrics & KPI cards
  3. **Maps** — interactive Leaflet float location maps
  4. **Analysis** — depth profiles, T-S diagrams, time series
  5. **Export** — download filtered data as CSV

Both frontends are fully independent — either can be used standalone.

---

## 📁 Project Structure

```
FloatChat/
├── api/
│   └── main.py                  # FastAPI app, _rewrite_with_context(), /chat endpoint
├── rag_engine/
│   ├── query_processor.py       # 8-step RAG pipeline orchestrator
│   ├── query_router.py          # Template / Simple / Complex routing
│   ├── query_parser.py          # NL parsing, scope-broadening detection
│   ├── hybrid_retriever.py      # FAISS + BM25 + RRF (k=60)
│   ├── sql_generator.py         # Groq Llama 3.3 70B NL→SQL, schema pruning
│   ├── response_generator.py    # Natural language response formatting
│   ├── intent_classifier.py     # 8 intent categories
│   └── semantic_cache.py        # Cosine cache, 30-min TTL, max 200 entries
├── vector_store/
│   ├── vector_db.py             # FAISSVectorStore (IndexFlatL2, 384-dim)
│   └── embeddings.py            # all-MiniLM-L6-v2 wrapper
├── mcp_server/
│   └── argo_mcp_server.py       # 9 MCP tool registrations
├── advanced_analytics/
│   └── profile_analytics.py     # Thermocline, MLD, water mass, N²
├── database/
│   └── models.py                # SQLAlchemy ORM models (5 tables)
├── data_processing/
│   ├── netcdf_extractor.py      # NetCDF → PostgreSQL ETL (xarray)
│   └── regions.py               # 6 Indian Ocean bounding boxes
├── streamlit_app/               # Frontend 2: Streamlit scientific dashboard
│   ├── app.py
│   └── components/
├── nexus-saa-s-ai-platform/     # Frontend 1: Next.js 16 SaaS UI (Netlify)
│   ├── app/
│   ├── components/
│   ├── netlify.toml
│   └── package.json
├── netlify.toml                  # Root Netlify config (points to Next.js dir)
├── requirements.txt
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology | Role |
|-------|-----------|------|
| **LLM** | Groq Llama 3.3 70B Versatile | SQL generation, intent classification, response formatting |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` (384-dim) | Profile semantic search |
| **Dense Retrieval** | FAISS `IndexFlatL2` | k-NN similarity search |
| **Sparse Retrieval** | BM25 (rank-bm25) | Keyword-based retrieval |
| **Reranking** | Reciprocal Rank Fusion | Merge dense + sparse results |
| **Backend API** | FastAPI + Uvicorn | REST `/chat`, `/health` endpoints |
| **Database** | PostgreSQL 16 (Neon Cloud) | 1.27M measurement rows |
| **ORM** | SQLAlchemy | Database models + queries |
| **Frontend 1** | Next.js 16, React 19, TypeScript | SaaS chat UI (Netlify) |
| **Frontend 2** | Streamlit 1.31+ | Scientific 5-tab dashboard |
| **Visualization** | Plotly Express, Leaflet | Charts and maps (Streamlit) |
| **Styling** | Tailwind CSS, Radix UI | Next.js frontend |
| **Package Manager** | pnpm | Next.js build |
| **NetCDF Parsing** | xarray | Raw ARGO file ingestion |
| **Scientific** | NumPy, SciPy, Pandas | Analytics computations |

---

## ⚙️ Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 20+ and pnpm
- A Neon PostgreSQL database (or local PostgreSQL)
- A Groq API key (free at [console.groq.com](https://console.groq.com))

### 1. Clone & Python setup

```bash
git clone https://github.com/Abuzaid-01/Float_Chat.git
cd Float_Chat

python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment variables

Create a `.env` file in the project root (see [Environment Variables](#-environment-variables) below).

### 3. Build the vector store

```bash
python -m vector_store.vector_db
```

### 4. Start the FastAPI backend

```bash
uvicorn api.main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`  
Swagger docs at `http://localhost:8000/docs`

### 5a. Run the Streamlit frontend

```bash
streamlit run streamlit_app/app.py
```

### 5b. Run the Next.js frontend

```bash
cd nexus-saa-s-ai-platform
pnpm install
pnpm run dev
```

Next.js app available at `http://localhost:3000`

---

## 🔐 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | Neon PostgreSQL connection string |
| `GROQ_API_KEY` | ✅ | Groq API key for Llama 3.3 70B |
| `NEXT_PUBLIC_API_URL` | ✅ (Next.js) | FastAPI backend URL (e.g. `https://your-backend.onrender.com`) |

**Example `.env`:**
```env
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
GROQ_API_KEY=gsk_xxxxxxxxxxxx
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
```

> ⚠️ Never commit `.env` to Git. It is already listed in `.gitignore`.

---

## 🚀 Deployment

### FastAPI Backend → Render

1. Connect your GitHub repo on [render.com](https://render.com)
2. **Build command**: `pip install -r requirements.txt`
3. **Start command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables: `DATABASE_URL`, `GROQ_API_KEY`

### Next.js Frontend → Netlify

Netlify is configured via `netlify.toml` at the repo root:

```toml
[build]
  base    = "nexus-saa-s-ai-platform"
  command = "pnpm run build"
  publish = ".next"
```

1. Connect repo on [netlify.com](https://netlify.com)
2. Add environment variable: `NEXT_PUBLIC_API_URL` → your Render backend URL
3. Every push to `main` triggers an automatic deploy

### Streamlit Dashboard → Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Point to `streamlit_app/app.py`
3. Add secrets: `DATABASE_URL`, `GROQ_API_KEY`

---

## 💬 Example Queries

| Type | Example Query |
|------|--------------|
| **Temperature** | "What is the average temperature in the Arabian Sea in October 2025?" |
| **Daily summary** | "Show me data for each day in October 2025" |
| **Float profile** | "Show all measurements for float 2902746" |
| **Regional comparison** | "Compare salinity between Bay of Bengal and Arabian Sea" |
| **Thermocline** | "Calculate the thermocline depth for float 1901740 cycle 45" |
| **Water masses** | "Identify water masses between 200 m and 800 m depth" |
| **Trends** | "Show temperature trend over October 2025" |
| **Semantic search** | "Find profiles similar to warm salty Arabian Sea water" |
| **Mixed layer** | "What is the mixed layer depth for float 2902746?" |
| **Schema** | "What data is available in the database?" |

---

## 🔒 Security

- ✅ No hardcoded credentials in source code
- ✅ All secrets via environment variables / `.env`
- ✅ `.gitignore` covers `.env`, `*.pkl`, vector index files
- ✅ Neon DB uses SSL connections (`sslmode=require`)
- ✅ Query audit trail logged in `query_logs` table
- ✅ Netlify environment variables stored encrypted

---

## 📈 Performance

| Stage | Average Time |
|-------|-------------|
| Semantic cache hit | < 50 ms |
| Intent classification | ~200 ms |
| Hybrid retrieval (FAISS + BM25 + RRF) | ~120 ms |
| SQL generation (Groq) | ~800 ms |
| Database query (Neon) | ~600 ms |
| Response generation (Groq) | ~500 ms |
| **Total (cache miss)** | **~2–3 s** |
| **Total (cache hit)** | **< 0.1 s** |

---

**Built with ❤️ by Abuzaid**

---

*Last Updated: November 2026*
