# 🔧 FloatChat Deployment Troubleshooting Guide

## ⚠️ Common Issues & Solutions

---

## Issue 1: Database Not Connected

### **Symptoms:**
- App loads but queries return empty results
- Error: "DATABASE_URL not found"
- Database connection timeout

### **Solution:**

#### **Step 1: Verify Streamlit Cloud Secrets**

Go to your Streamlit app → **Settings** → **Secrets**

Make sure you have **EXACTLY** this format (no extra spaces, quotes, or formatting):

```toml
DATABASE_URL = "postgresql://neondb_owner:npg_8yOoZiL1bJpW@ep-falling-block-a8srv2pf-pooler.eastus2.azure.neon.tech/neondb?sslmode=require"

GOOGLE_API_KEY = "AIzaSyCZkkBonU4QHxmKfTAq0DXtf1RtBgczPBg"

GOOGLE_MODEL = "gemini-2.5-flash"

VECTOR_STORE_PATH = "./data/vector_store"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
```

#### **Step 2: Test Connection**

Run the test script in your Streamlit app:
1. Change main file path temporarily to: `FloatChat/test_secrets.py`
2. Deploy and check the output
3. Should show: ✅ Database connection successful
4. Change back to `FloatChat/streamlit_app/app.py`

#### **Step 3: Check Neon Database Status**

1. Go to: https://console.neon.tech/
2. Select your database: `neondb`
3. Check if it's active (not suspended)
4. Verify connection string is correct

#### **Step 4: Verify Data Exists**

In Neon console, run this SQL:
```sql
SELECT COUNT(*) FROM argo_profiles;
-- Should return: 1,268,992

SELECT COUNT(*) FROM profile_summaries;
-- Should return: 1,306
```

---

## Issue 2: Vector Store Not Found

### **Symptoms:**
- Error: "Vector store not found"
- Error: "index.faiss" file missing
- Semantic search fails

### **Solution:**

#### **Step 1: Verify Files in Repo**

Check these files exist in your GitHub repo:
```
FloatChat/data/vector_store/index.faiss
FloatChat/data/vector_store/metadata.pkl
```

#### **Step 2: Check File Sizes**

`index.faiss` should be ~2-5 MB
`metadata.pkl` should be ~100-500 KB

If files are too small or 0 bytes, rebuild:
```bash
python scripts/populate_vector_db.py
```

#### **Step 3: Update .gitattributes**

Create/update `.gitattributes` in FloatChat folder:
```
*.faiss filter=lfs diff=lfs merge=lfs -text
*.pkl filter=lfs diff=lfs merge=lfs -text
```

Or disable Git LFS by ensuring files are regular commits.

---

## Issue 3: Gemini API Key Invalid

### **Symptoms:**
- SQL generation fails
- Error: "Invalid API key"
- Error: "Rate limit exceeded"

### **Solution:**

#### **Step 1: Verify API Key**

Go to: https://makersuite.google.com/app/apikey

1. Check if key is active
2. Verify permissions
3. Check quota/rate limits

#### **Step 2: Update Secrets**

In Streamlit Cloud Secrets:
```toml
GOOGLE_API_KEY = "your_new_api_key_here"
```

#### **Step 3: Test API Key Locally**

```python
import google.generativeai as genai
genai.configure(api_key="your_key")
model = genai.GenerativeModel('gemini-2.0-flash-exp')
response = model.generate_content("Hello")
print(response.text)  # Should return greeting
```

---

## Issue 4: Module Not Found Errors

### **Symptoms:**
- ImportError: No module named 'X'
- ModuleNotFoundError

### **Solution:**

#### **Step 1: Check requirements.txt**

Verify all dependencies are listed in `FloatChat/requirements.txt`:
```txt
streamlit==1.31.0
google-generativeai==0.8.5
langchain==0.1.9
langchain-google-genai==2.0.10
sqlalchemy==2.0.27
psycopg2-binary==2.9.9
faiss-cpu==1.12.0
sentence-transformers==2.3.1
pandas==2.2.0
numpy==1.26.3
plotly==5.18.0
folium==0.15.1
streamlit-folium==0.17.0
python-dotenv==1.0.0
```

#### **Step 2: Rebuild App**

In Streamlit Cloud:
1. Settings → Reboot app
2. Or make a small change and commit to trigger rebuild

---

## Issue 5: App Crashes on Startup

### **Symptoms:**
- Streamlit app shows error screen
- "An error occurred while running your app"

### **Solution:**

#### **Step 1: Check Logs**

In Streamlit Cloud:
1. Click "Manage app"
2. View logs
3. Look for specific error messages

#### **Step 2: Common Fixes**

**Error: "DATABASE_URL not found"**
→ Add to Secrets (see Issue 1)

**Error: "GOOGLE_API_KEY not found"**
→ Add to Secrets

**Error: "No module named..."**
→ Update requirements.txt

**Error: "vector_store not found"**
→ Check files in repo (see Issue 2)

---

## Issue 6: Slow Performance

### **Symptoms:**
- Queries take > 10 seconds
- App is sluggish

### **Solution:**

#### **Step 1: Check Neon Connection**

Use pooler connection string:
```
@ep-falling-block-a8srv2pf-pooler.eastus2.azure.neon.tech
```
(Notice `-pooler` in the URL)

#### **Step 2: Add Connection Pooling**

In `database/db_setup.py`:
```python
self.engine = create_engine(
    self.database_url, 
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)
```

---

## ✅ Quick Checklist for Deployment

- [ ] GitHub repo has all files pushed
- [ ] `.env` file is in `.gitignore` (not pushed)
- [ ] `requirements.txt` is complete and pushed
- [ ] `data/vector_store/index.faiss` exists in repo
- [ ] `data/vector_store/metadata.pkl` exists in repo
- [ ] Neon database has 1,268,992 records
- [ ] Streamlit Cloud secrets configured correctly
- [ ] GOOGLE_API_KEY is valid
- [ ] DATABASE_URL uses pooler connection
- [ ] Test app loads: `https://your-app.streamlit.app`

---

## 🆘 Still Having Issues?

### **Debug Steps:**

1. **Run test_secrets.py**:
   - Change main file to `FloatChat/test_secrets.py`
   - Deploy and check all green checkmarks

2. **Check each component**:
   - ✅ Database connection
   - ✅ Vector store loaded
   - ✅ API key working
   - ✅ Sample query returns data

3. **View detailed logs**:
   - Streamlit Cloud → Manage app → Logs
   - Look for first error that appears

4. **Test locally first**:
   ```bash
   source venv/bin/activate
   streamlit run streamlit_app/app.py
   ```
   If works locally but not on cloud → secrets issue

---

## 📞 Common Error Messages & Fixes

| Error | Fix |
|-------|-----|
| `DATABASE_URL not found` | Add to Streamlit Secrets |
| `psycopg2.OperationalError` | Check Neon database is active |
| `Invalid API key` | Update GOOGLE_API_KEY in Secrets |
| `Vector store not found` | Push vector_store files to GitHub |
| `Module not found` | Add to requirements.txt |
| `Connection timeout` | Use pooler URL, check Neon status |
| `Rate limit exceeded` | Wait 1 minute, Gemini has limits |

---

## 🎯 Final Verification

Once deployed, test these queries:

1. `Show me all available float IDs`
   - Should return: List of 668 floats

2. `Show temperature in Arabian Sea`
   - Should return: Map and data table

3. `Analyze float 1901740 profile statistics`
   - Should return: Statistics and profile info

If all 3 work → ✅ Deployment successful!

---

## 📧 Contact

If issues persist, check:
- Streamlit Community Forum: https://discuss.streamlit.io/
- GitHub Issues: Your repo issues tab
- Neon Support: https://neon.tech/docs
