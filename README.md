# 🌊 FloatChat - AI-Powered ARGO Ocean Data Analysis

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31-red.svg)](https://streamlit.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://postgresql.org)
[![FAISS](https://img.shields.io/badge/FAISS-Vector%20Store-green.svg)](https://github.com/facebookresearch/faiss)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
<img width="1482" height="970" alt="image" src="https://github.com/user-attachments/assets/38585832-0972-4f99-8c61-2e47510e69c8" />



---

## 📋 Overview

**FloatChat** is an AI-powered conversational interface for querying, exploring, and visualizing **ARGO ocean float data** using natural language. Built with **Retrieval-Augmented Generation (RAG)** pipelines and **Large Language Models (LLMs)**, it democratizes access to complex oceanographic data for researchers, decision-makers, and ocean enthusiasts.

### 🎯 Key Features

- 🤖 **Natural Language Queries** - Ask questions in plain English
- 🗺️ **Interactive Maps** - Visualize float trajectories and data coverage
- 📊 **Profile Analysis** - Explore temperature, salinity, and BGC parameters
- 🔍 **Semantic Search** - Find relevant profiles using FAISS vector store
- 💾 **1.2M+ Records** - Indian Ocean ARGO data (Oct 2025)
- 🚀 **RAG Pipeline** - Context-aware SQL generation with Google Gemini
- 📈 **Beautiful UI** - Modern Streamlit dashboard with Plotly visualizations

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query (NL)                          │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  RAG Pipeline                                               │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │ Vector Search │→ │ SQL Generator│→ │  PostgreSQL DB  │ │
│  │   (FAISS)     │  │  (Gemini LLM)│  │  1.2M records   │ │
│  └───────────────┘  └──────────────┘  └─────────────────┘ │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  Streamlit Dashboard (Visualizations + Chat)                │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | Streamlit 1.31 |
| **Database** | PostgreSQL 16 |
| **Vector Store** | FAISS |
| **LLM** | Google Gemini 2.5 Flash |
| **Embeddings** | SentenceTransformers (all-MiniLM-L6-v2) |
| **Visualizations** | Plotly, Folium |
| **Data Processing** | NetCDF4, xarray, pandas |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16
- Google Gemini API Key (free)

### 1. Clone Repository

```bash
git clone https://github.com/Abuzaid-01/floatchat.git
cd floatchat
```

### 2. Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your API key
GOOGLE_API_KEY=your_gemini_api_key_here
GOOGLE_MODEL=gemini-2.5-flash
```

See [`GEMINI_SETUP.md`](GEMINI_SETUP.md) for detailed API key setup instructions.

### 4. Setup Database

```bash
# Start PostgreSQL
brew services start postgresql@16  # macOS
# OR
sudo systemctl start postgresql    # Linux

# Create database
createdb floatchat

# Configure connection in .env
DATABASE_URL=postgresql://username:password@localhost:5432/floatchat
```

### 5. Process ARGO Data

```bash
# Place NetCDF files in data/netcdf/
# Then run processing script
python scripts/process_netcdf_files.py

# This will:
# - Extract data from NetCDF files
# - Convert to CSV
# - Load into PostgreSQL
# - Generate profile summaries
# - Build FAISS vector index
```

### 6. Launch Application

```bash
streamlit run streamlit_app/app.py
```

Open browser to `http://localhost:8501` 🎉

---

## 💡 Usage Examples

### Natural Language Queries

```
"Show me temperature profiles in the Arabian Sea"
"Compare salinity between Bay of Bengal and Arabian Sea"
"What's the average temperature at 100m depth in October?"
"Find profiles with dissolved oxygen below 50 μmol/kg"
"Plot temperature vs depth for float 2902696"
```

### Chat Interface

The **Chat** tab allows natural conversation:

```
You: What data do we have for October 2025?
AI: We have 1,268,992 measurements from 19 ARGO floats...

You: Show me the warmest profiles
AI: [Generates SQL, executes query, shows results]
```

### Map Visualization

- View geographic distribution of floats
- Filter by date range, temperature, depth
- Animated trajectory playback
- Density heatmaps

### Profile Analysis

- Temperature-depth profiles
- T-S diagrams
- Multi-parameter comparisons
- BGC parameter visualization

---

## 📊 Dataset

- **Source**: Indian Ocean ARGO Float Data (October 2025)
- **Records**: 1,268,992 measurements
- **Floats**: 19 unique profiling floats
- **Date Range**: October 1-19, 2025
- **Parameters**:
  - Core: Temperature, Salinity, Pressure
  - BGC: Dissolved Oxygen, Chlorophyll, pH
  - Metadata: Float ID, Cycle Number, QC Flags

---

## 🗂️ Project Structure

```
FloatChat/
├── data/                      # Data storage
│   ├── netcdf/               # Raw NetCDF files (87 MB)
│   └── csv/                  # Processed CSV files (88 MB)
├── data_processing/          # NetCDF extraction & loading
│   ├── netcdf_extractor.py
│   └── data_loader.py
├── database/                 # PostgreSQL models & setup
│   ├── models.py
│   └── db_setup.py
├── vector_store/             # FAISS vector database
│   ├── vector_db.py
│   ├── embeddings.py
│   └── summaries/            # Profile summaries (1,306)
├── rag_engine/               # RAG pipeline
│   ├── query_processor.py    # Main RAG orchestrator
│   ├── sql_generator.py      # NL → SQL conversion
│   └── response_generator.py # Response formatting
├── streamlit_app/            # Streamlit UI
│   ├── app.py               # Main application
│   └── components/          # UI components
├── visualization/            # Plotting utilities
│   ├── map_plots.py
│   └── profile_plots.py
├── mcp_server/              # Model Context Protocol
│   └── mcp_server.py        # 8 MCP tools
├── scripts/                 # Automation scripts
│   ├── process_netcdf_files.py
│   └── generate_summaries.py
└── requirements.txt         # Python dependencies
```

---

## 🔧 Configuration

### Environment Variables

```bash
# LLM Configuration
GOOGLE_API_KEY=your_api_key
GOOGLE_MODEL=gemini-2.5-flash

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/floatchat

# Vector Store
VECTOR_STORE_PATH=vector_store/faiss_index
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Database Schema

```sql
CREATE TABLE argo_profiles (
    id SERIAL PRIMARY KEY,
    float_id VARCHAR(50),
    cycle_number INTEGER,
    latitude FLOAT,
    longitude FLOAT,
    timestamp TIMESTAMP,
    pressure FLOAT,
    temperature FLOAT,
    salinity FLOAT,
    dissolved_oxygen FLOAT,
    chlorophyll FLOAT,
    ph FLOAT,
    temp_qc INTEGER,
    sal_qc INTEGER,
    data_mode VARCHAR(1),
    platform_type VARCHAR(50)
);

-- Indexes for performance
CREATE INDEX idx_lat_lon ON argo_profiles(latitude, longitude);
CREATE INDEX idx_timestamp ON argo_profiles(timestamp);
CREATE INDEX idx_float_id ON argo_profiles(float_id);
```

---

## 🎨 UI Features

### Modern Design
- Gradient color schemes
- High-contrast text (WCAG AAA compliant)
- Responsive layout
- Interactive charts with Plotly

### 4 Main Tabs

1. **💬 Chat Interface** - Natural language queries
2. **🗺️ Geographic Map** - Spatial visualization
3. **📊 Profile Analysis** - Vertical profiles
4. **📈 Data Explorer** - Tabular view with export

---

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Test database connection
python -c "from database.db_setup import DatabaseSetup; \
           db = DatabaseSetup(); \
           print('✅ DB Connected')"

# Test vector store
python -c "from vector_store.vector_db import FAISSVectorStore; \
           vs = FAISSVectorStore(); \
           vs.load(); \
           print(f'✅ Loaded {vs.get_index_size()} vectors')"
```

---

## 📚 Documentation

- [`SETUP_INSTRUCTIONS.md`](SETUP_INSTRUCTIONS.md) - Detailed setup guide
- [`GEMINI_SETUP.md`](GEMINI_SETUP.md) - Google Gemini API configuration
- [`QUICK_REFERENCE.md`](QUICK_REFERENCE.md) - Common commands & tips
- [`UI_IMPROVEMENTS.md`](UI_IMPROVEMENTS.md) - UI enhancement details

---

## 🤝 Contributing

Contributions welcome! Please follow these steps:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📝 TODO / Future Enhancements

- [ ] Implement full MCP protocol integration
- [ ] Add NetCDF export functionality
- [ ] Expand BGC parameter visualizations
- [ ] Add geospatial nearest-neighbor queries
- [ ] Build FastAPI REST endpoints
- [ ] Add advanced thermocline/MLD analytics
- [ ] Support for satellite data integration
- [ ] Multi-user authentication
- [ ] Query caching for performance
- [ ] Mobile-responsive design

---

## 🏆 Smart India Hackathon 2025

**Problem Statement ID**: 25040  
**Title**: FloatChat - AI-Powered Conversational Interface for ARGO Ocean Data  
**Organization**: Ministry of Earth Sciences (MoES)  
**Department**: INCOIS (Indian National Centre for Ocean Information Services)

### Problem Statement Requirements

✅ NetCDF ingestion and SQL conversion  
✅ Vector database (FAISS) for metadata retrieval  
✅ RAG pipeline with LLM (Google Gemini)  
✅ Interactive Streamlit dashboard  
✅ Natural language chat interface  
✅ Geospatial visualizations (Plotly)  
✅ Support for BGC parameters  
⚠️ Model Context Protocol (MCP) - In progress  
⚠️ NetCDF export - To be implemented  

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Team

**Team Lead**: Abuzaid  
**GitHub**: [@Abuzaid-01](https://github.com/Abuzaid-01)  
**Project**: [FloatChat Repository](https://github.com/Abuzaid-01/floatchat)

---

## 🙏 Acknowledgments

- **INCOIS** for problem statement and domain expertise
- **ARGO Program** for global ocean data
- **Google** for Gemini LLM API
- **Streamlit** for amazing framework
- **PostgreSQL & FAISS** communities

---

## 📧 Contact

For questions, issues, or collaboration:
- GitHub Issues: [FloatChat Issues](https://github.com/Abuzaid-01/floatchat/issues)
- Email: [Contact via GitHub]

---

<div align="center">

**Made with 🌊 for Smart India Hackathon 2025**

[![Star this repo](https://img.shields.io/github/stars/Abuzaid-01/floatchat?style=social)](https://github.com/Abuzaid-01/floatchat)
[![Fork this repo](https://img.shields.io/github/forks/Abuzaid-01/floatchat?style=social)](https://github.com/Abuzaid-01/floatchat/fork)

</div>
