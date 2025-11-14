#!/usr/bin/env python3
"""
Test Streamlit Secrets Configuration
Run this to verify secrets are loaded correctly
"""

import streamlit as st
from database.db_setup import DatabaseSetup
from database.models import ArgoProfile
from sqlalchemy import text

st.title("🔧 FloatChat - Database Connection Test")

st.write("---")
st.subheader("1️⃣ Testing Streamlit Secrets")

# Check if secrets are available
try:
    if "DATABASE_URL" in st.secrets:
        st.success("✅ DATABASE_URL found in secrets")
        
        # Show partial connection string (hide password)
        db_url = st.secrets["DATABASE_URL"]
        if "@" in db_url:
            parts = db_url.split("@")
            safe_url = parts[0].split(":")[0] + ":****@" + parts[1]
            st.code(safe_url)
        else:
            st.code(db_url[:50] + "...")
    else:
        st.error("❌ DATABASE_URL not found in secrets")
        st.write("Available keys:", list(st.secrets.keys()))
        
    if "GOOGLE_API_KEY" in st.secrets:
        st.success("✅ GOOGLE_API_KEY found in secrets")
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.code(api_key[:10] + "..." + api_key[-10:])
    else:
        st.error("❌ GOOGLE_API_KEY not found in secrets")
        
except Exception as e:
    st.error(f"❌ Error reading secrets: {e}")

st.write("---")
st.subheader("2️⃣ Testing Database Connection")

try:
    # Test database connection
    db_setup = DatabaseSetup()
    st.success("✅ DatabaseSetup initialized")
    
    # Test connection
    if db_setup.test_connection():
        st.success("✅ Database connection successful!")
    else:
        st.error("❌ Database connection failed")
        
    # Get session and query data
    session = db_setup.get_session()
    
    # Count records
    total_records = session.query(ArgoProfile).count()
    st.success(f"✅ Found {total_records:,} records in database")
    
    # Get sample data
    sample = session.query(ArgoProfile).limit(5).all()
    
    st.write("**Sample Data:**")
    for record in sample:
        st.write(f"- Float: {record.float_id}, Lat: {record.latitude:.2f}, Lon: {record.longitude:.2f}, Temp: {record.temperature}°C")
    
    session.close()
    
    st.success("🎉 All tests passed! Database is connected properly.")
    
except Exception as e:
    st.error(f"❌ Error: {e}")
    import traceback
    st.code(traceback.format_exc())

st.write("---")
st.subheader("3️⃣ Testing Vector Store")

try:
    from vector_store.vector_db import FAISSVectorStore
    
    vector_store = FAISSVectorStore()
    loaded = vector_store.load()
    
    if loaded:
        st.success(f"✅ Vector store loaded: {vector_store.index.ntotal} vectors")
    else:
        st.error("❌ Vector store not loaded")
        
except Exception as e:
    st.error(f"❌ Vector store error: {e}")
    import traceback
    st.code(traceback.format_exc())

st.write("---")
st.info("💡 If you see errors, check Streamlit Cloud Settings → Secrets")
