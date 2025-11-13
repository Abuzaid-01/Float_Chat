#!/usr/bin/env python3
"""
Fast migration using CSV files directly
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from sqlalchemy import create_engine, text
from database.models import Base
from tqdm import tqdm

# Neon connection string
NEON_DB = "postgresql://neondb_owner:npg_8yOoZiL1bJpW@ep-purple-bread-a83vjb6i-pooler.eastus2.azure.neon.tech/neondb?sslmode=require"

def upload_from_csv():
    """Upload data from CSV files to Neon"""
    print("🚀 FAST MIGRATION TO NEON FROM CSV FILES")
    print("="*70)
    
    # Test connection
    print("\n1️⃣ Testing Neon connection...")
    try:
        engine = create_engine(NEON_DB)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("   ✅ Connection successful!")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return
    
    # Create tables
    print("\n2️⃣ Creating tables...")
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("   ✅ Tables created!")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Upload argo_profiles from CSV
    print("\n3️⃣ Uploading argo_profiles from CSV...")
    csv_path = "data/processed/argo_profiles.csv"
    
    if not Path(csv_path).exists():
        print(f"   ❌ CSV not found: {csv_path}")
        return
    
    try:
        # Read CSV in chunks
        chunk_size = 50000
        print(f"   📦 Processing in chunks of {chunk_size:,} records...")
        
        for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunk_size)):
            print(f"   Uploading chunk {i+1}...")
            chunk.to_sql('argo_profiles', engine, if_exists='append', index=False, method='multi')
        
        # Count records
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM argo_profiles"))
            count = result.scalar()
        
        print(f"   ✅ Uploaded {count:,} records!")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Create indexes
    print("\n4️⃣ Creating indexes for performance...")
    try:
        with engine.connect() as conn:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_lat_lon ON argo_profiles (latitude, longitude)",
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON argo_profiles (timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_float_id ON argo_profiles (float_id)",
                "CREATE INDEX IF NOT EXISTS idx_spatial_temporal ON argo_profiles (latitude, longitude, timestamp)"
            ]
            for idx in indexes:
                print(f"   Creating {idx.split('idx_')[1].split(' ON')[0]}...")
                conn.execute(text(idx))
                conn.commit()
        print("   ✅ Indexes created!")
    except Exception as e:
        print(f"   ⚠️  Index creation warning: {e}")
    
    # Verify
    print("\n5️⃣ Verification...")
    try:
        with engine.connect() as conn:
            # Count
            result = conn.execute(text("SELECT COUNT(*) FROM argo_profiles"))
            total = result.scalar()
            
            # Sample
            result = conn.execute(text("""
                SELECT float_id, latitude, longitude, temperature
                FROM argo_profiles
                LIMIT 5
            """))
            
            print(f"   Total records: {total:,}")
            print(f"   Sample data:")
            for row in result:
                print(f"     Float {row[0]}: {row[1]:.2f}°N, {row[2]:.2f}°E, {row[3]:.2f}°C")
        
        print("\n✅ Migration successful!")
        
    except Exception as e:
        print(f"   ❌ Verification error: {e}")
    
    print("\n" + "="*70)
    print("📝 NEXT STEPS:")
    print("="*70)
    print("\n1. Update .env file:")
    print(f"   DATABASE_URL={NEON_DB}")
    print("\n2. Create Streamlit secrets.toml file:")
    print("   [Create in Streamlit Cloud Dashboard]")
    print(f'   DATABASE_URL = "{NEON_DB}"')
    print(f'   GOOGLE_API_KEY = "your_api_key"')
    print("\n3. Upload vector_store files to GitHub:")
    print("   - data/vector_store/index.faiss")
    print("   - data/vector_store/metadata.pkl")
    print("\n🎉 Ready for Streamlit Cloud deployment!")
    print("="*70)

if __name__ == "__main__":
    upload_from_csv()
