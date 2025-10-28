# 🚀 FloatChat - Streamlit Cloud Deployment Guide

**Last Updated:** October 28, 2025  
**Repository:** https://github.com/Abuzaid-01/Float_Chat  
**Latest Commit:** fc451e7

---

## ✅ **Pre-Deployment Checklist**

### 1. **Files Required**
- ✅ `requirements.txt` - All Python dependencies
- ✅ `streamlit_app/app.py` - Main application entry point
- ✅ `.streamlit/config.toml` - Streamlit configuration (optional)
- ✅ Database credentials in Streamlit Secrets

### 2. **GitHub Repository Status**
```bash
✅ All changes committed
✅ Pushed to main branch
✅ Commit hash: fc451e7
✅ Repository: Abuzaid-01/Float_Chat
```

### 3. **Recent Improvements (Just Pushed)**
- ✅ Fixed spatial coordinate parsing (15°N, 75°E now works correctly)
- ✅ Enhanced database schema tool with data availability
- ✅ Removed misleading BGC example queries
- ✅ Increased default search radius to 1000km
- ✅ Added clear BGC data limitations documentation

---

## 📦 **Step 1: Verify Requirements.txt**

Your `requirements.txt` should include all necessary packages. Key dependencies:

```
streamlit
pandas
numpy
sqlalchemy
psycopg2-binary
python-dotenv
langchain
langchain-google-genai
sentence-transformers
faiss-cpu
plotly
folium
streamlit-folium
openpyxl
netCDF4
google-generativeai
```

**Check if requirements.txt exists:**
```bash
ls -la /Users/abuzaid/Desktop/final/netcdf/FloatChat/requirements.txt
```

---

## 🔐 **Step 2: Prepare Database Connection**

### PostgreSQL Database Options:

#### Option A: **Neon.tech** (Recommended - Free Tier Available)
1. Go to https://neon.tech
2. Create free account
3. Create new project
4. Get connection string:
   ```
   postgresql://username:password@ep-xxx.region.aws.neon.tech/floatchat?sslmode=require
   ```

#### Option B: **Supabase** (Free Tier)
1. Go to https://supabase.com
2. Create project
3. Get PostgreSQL connection from Settings > Database

#### Option C: **ElephantSQL** (Free Tier)
1. Go to https://www.elephantsql.com
2. Create "Tiny Turtle" free instance
3. Copy connection string

### Migrate Your Local Database:

**1. Export your local database:**
```bash
pg_dump -h localhost -U postgres -d argo_db -F c -b -v -f /tmp/argo_backup.dump
```

**2. Import to cloud database:**
```bash
pg_restore -h <cloud-host> -U <cloud-user> -d <cloud-db> -v /tmp/argo_backup.dump
```

Or use pgAdmin for GUI-based transfer.

---

## 🌐 **Step 3: Deploy to Streamlit Cloud**

### A. **Go to Streamlit Cloud**
1. Visit https://share.streamlit.io
2. Sign in with GitHub account

### B. **Create New App**
1. Click "New app"
2. Select repository: `Abuzaid-01/Float_Chat`
3. Select branch: `main`
4. Main file path: `streamlit_app/app.py`
5. App URL: Choose your custom URL (e.g., `floatchat-argo`)

### C. **Configure Secrets**
In Streamlit Cloud dashboard, go to **Advanced settings** > **Secrets**

Add this TOML configuration:

```toml
# Database Configuration
[database]
host = "your-cloud-db-host.neon.tech"
port = "5432"
database = "floatchat"
user = "your-username"
password = "your-password"

# Google API for LLM
GOOGLE_API_KEY = "your-google-api-key"
GOOGLE_MODEL = "gemini-2.5-flash"

# Optional: MCP Configuration
[mcp]
enabled = true
```

### D. **Environment Variables**
If using `.env` style, convert to TOML:

```toml
DB_HOST = "your-host"
DB_PORT = "5432"
DB_NAME = "floatchat"
DB_USER = "your-user"
DB_PASSWORD = "your-password"
GOOGLE_API_KEY = "your-api-key"
```

---

## 🔧 **Step 4: Update Code for Streamlit Cloud**

### A. **Database Connection**
Update `database/db_setup.py` to read from Streamlit secrets:

```python
import streamlit as st

class DatabaseSetup:
    def __init__(self):
        # Try Streamlit secrets first (for cloud deployment)
        try:
            self.config = {
                'host': st.secrets["database"]["host"],
                'port': st.secrets["database"]["port"],
                'database': st.secrets["database"]["database"],
                'user': st.secrets["database"]["user"],
                'password': st.secrets["database"]["password"]
            }
        except:
            # Fallback to .env for local development
            from dotenv import load_dotenv
            load_dotenv()
            self.config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'argo_db'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', '')
            }
```

### B. **API Keys**
Update files that use Google API:

```python
# In rag_engine/sql_generator.py and response_generator.py
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    api_key = os.getenv('GOOGLE_API_KEY')

self.llm = ChatGoogleGenerativeAI(
    model=os.getenv('GOOGLE_MODEL', 'gemini-2.5-flash'),
    google_api_key=api_key
)
```

---

## 📊 **Step 5: Verify Data Files**

### Check if vector store is in repo:
```bash
ls -la /Users/abuzaid/Desktop/final/netcdf/FloatChat/vector_store/
```

**If `faiss_index` files are too large (>100MB):**

1. Add to `.gitignore`:
```
vector_store/faiss_index/
vector_store/*.index
vector_store/*.pkl
```

2. Regenerate on first run in Streamlit Cloud:
```python
# In vector_store/vector_db.py
if not os.path.exists('vector_store/faiss_index'):
    print("⚠️ Vector store not found, rebuilding...")
    self._build_from_database()
```

---

## 🧪 **Step 6: Test Deployment**

### A. **Monitor Build Logs**
Watch Streamlit Cloud build logs for:
- ✅ All dependencies installed
- ✅ Database connection successful
- ✅ Vector store loaded
- ✅ App started successfully

### B. **Test Queries**
Once deployed, test these queries:
1. "What is the database structure?"
2. "Show me data from Arabian Sea"
3. "Find nearest floats to 15°N, 75°E"
4. "Calculate thermocline for Bay of Bengal"

### C. **Check Performance**
- Query response time
- Map visualization loading
- Data export functionality

---

## 🐛 **Common Issues & Solutions**

### Issue 1: "ModuleNotFoundError"
**Solution:** Add missing package to `requirements.txt` and redeploy

### Issue 2: "Database connection failed"
**Solution:** 
- Check secrets configuration
- Verify cloud database is running
- Test connection string locally first

### Issue 3: "Vector store file not found"
**Solution:** 
- Either commit vector store to repo (if <100MB)
- Or rebuild on first run (add regeneration logic)

### Issue 4: "Memory limit exceeded"
**Solution:**
- Streamlit Cloud free tier: 1GB RAM
- Optimize vector store size
- Add pagination for large queries
- Consider upgrading to paid tier

### Issue 5: "Timeout on large queries"
**Solution:**
- Add LIMIT to SQL queries (already implemented: 1000 default)
- Use pagination for results display
- Add progress indicators

---

## 📈 **Step 7: Post-Deployment Optimization**

### A. **Add Caching**
Already implemented in your code:
```python
@st.cache_data
def load_vector_store():
    return vector_store.load()

@st.cache_resource
def get_database_connection():
    return DatabaseSetup()
```

### B. **Monitor Usage**
- Check Streamlit Cloud analytics
- Monitor query patterns
- Track error rates

### C. **Performance Tuning**
- Optimize SQL queries
- Reduce vector store size if needed
- Implement lazy loading for visualizations

---

## 🎯 **Quick Deployment Commands**

```bash
# 1. Ensure all changes are committed
cd /Users/abuzaid/Desktop/final/netcdf/FloatChat
git status

# 2. Push to GitHub (already done!)
git push origin main

# 3. Check requirements.txt
cat requirements.txt

# 4. Export local database (if needed)
pg_dump -h localhost -U postgres -d argo_db -F c -f argo_backup.dump

# 5. Deploy on Streamlit Cloud via web interface
# https://share.streamlit.io
```

---

## 📋 **Deployment Checklist**

- [ ] GitHub repository updated (✅ Done - commit fc451e7)
- [ ] requirements.txt complete and tested
- [ ] Database migrated to cloud PostgreSQL
- [ ] Secrets configured in Streamlit Cloud
- [ ] Vector store accessible (committed or regenerates)
- [ ] Google API key configured
- [ ] Test queries work
- [ ] Map visualizations load
- [ ] Export functionality works
- [ ] Performance acceptable
- [ ] Error handling verified

---

## 🔗 **Useful Links**

- **Streamlit Cloud:** https://share.streamlit.io
- **Streamlit Docs:** https://docs.streamlit.io
- **Neon (Database):** https://neon.tech
- **Supabase:** https://supabase.com
- **GitHub Repo:** https://github.com/Abuzaid-01/Float_Chat

---

## 🆘 **Support**

If you encounter issues:

1. **Check Streamlit Cloud logs** - Most errors are visible here
2. **Test locally first** - Run `streamlit run streamlit_app/app.py`
3. **Verify secrets** - Ensure all required keys are configured
4. **Review commit** - Latest changes in commit fc451e7

---

## ✅ **Ready to Deploy!**

Your app is ready for Streamlit Cloud deployment:
- ✅ All code improvements pushed
- ✅ Spatial queries working
- ✅ BGC data clarity implemented
- ✅ Example queries accurate
- ✅ Documentation complete

**Next Step:** Go to https://share.streamlit.io and follow **Step 3** above! 🚀
