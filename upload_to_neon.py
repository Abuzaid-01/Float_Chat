#!/usr/bin/env python3
"""
Upload FloatChat data to Neon PostgreSQL
This script will:
1. Create tables in Neon
2. Upload argo_profiles from CSV
3. Generate and upload profile_summaries
4. Create indexes for fast queries
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database.models import Base, ArgoProfile, ProfileSummary

# Database URLs
NEON_URL = os.getenv("NEON_DATABASE_URL")

print("="*80)
print("🌊 FLOATCHAT - NEON DATABASE MIGRATION")
print("="*80)

def create_tables(engine):
    """Create all tables in Neon"""
    print("\n📦 Step 1: Creating tables in Neon...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def upload_argo_profiles(engine, csv_path):
    """Upload argo_profiles from CSV"""
    print(f"\n📊 Step 2: Uploading argo_profiles from CSV...")
    print(f"   CSV path: {csv_path}")
    
    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        return False
    
    try:
        # Read CSV
        print("   Reading CSV file...")
        df = pd.read_csv(csv_path)
        print(f"   ✅ Loaded {len(df):,} records from CSV")
        
        # Clean data
        print("   Cleaning data...")
        # Convert timestamp to datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Replace NaN with None for SQL
        df = df.replace({np.nan: None})
        
        # Upload in batches
        batch_size = 10000
        total_batches = (len(df) + batch_size - 1) // batch_size
        
        print(f"   Uploading in {total_batches} batches of {batch_size:,} records...")
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            batch.to_sql('argo_profiles', engine, if_exists='append', index=False, method='multi')
            current_batch = (i // batch_size) + 1
            print(f"   ✅ Batch {current_batch}/{total_batches} uploaded ({i+len(batch):,}/{len(df):,} records)")
        
        print(f"✅ Successfully uploaded {len(df):,} records to argo_profiles!")
        return True
        
    except Exception as e:
        print(f"❌ Error uploading data: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_profile_summaries(engine):
    """Generate profile summaries"""
    print("\n📝 Step 3: Generating profile summaries...")
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Group by profile
        print("   Querying and grouping profiles...")
        profiles = session.query(
            ArgoProfile.float_id,
            ArgoProfile.cycle_number,
            ArgoProfile.latitude,
            ArgoProfile.longitude,
            ArgoProfile.timestamp,
            func.min(ArgoProfile.pressure).label('min_depth'),
            func.max(ArgoProfile.pressure).label('max_depth'),
            func.min(ArgoProfile.temperature).label('min_temp'),
            func.max(ArgoProfile.temperature).label('max_temp'),
            func.avg(ArgoProfile.temperature).label('avg_temp'),
            func.min(ArgoProfile.salinity).label('min_sal'),
            func.max(ArgoProfile.salinity).label('max_sal'),
            func.avg(ArgoProfile.salinity).label('avg_sal')
        ).group_by(
            ArgoProfile.float_id,
            ArgoProfile.cycle_number,
            ArgoProfile.latitude,
            ArgoProfile.longitude,
            ArgoProfile.timestamp
        ).all()
        
        print(f"   Found {len(profiles)} unique profiles")
        
        # Generate summaries
        print("   Creating summary texts...")
        summaries = []
        for prof in profiles:
            summary_text = create_summary_text(prof)
            
            summary = ProfileSummary(
                float_id=prof.float_id,
                cycle_number=prof.cycle_number,
                latitude=prof.latitude,
                longitude=prof.longitude,
                timestamp=prof.timestamp,
                min_depth=prof.min_depth,
                max_depth=prof.max_depth,
                temp_range=f"{prof.min_temp:.2f}-{prof.max_temp:.2f}°C" if prof.min_temp else None,
                sal_range=f"{prof.min_sal:.2f}-{prof.max_sal:.2f} PSU" if prof.min_sal else None,
                summary_text=summary_text
            )
            summaries.append(summary)
        
        # Bulk insert
        print(f"   Uploading {len(summaries)} summaries...")
        session.bulk_save_objects(summaries)
        session.commit()
        
        print(f"✅ Generated and uploaded {len(summaries)} profile summaries!")
        return True
        
    except Exception as e:
        print(f"❌ Error generating summaries: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False
    finally:
        session.close()

def create_summary_text(profile) -> str:
    """Create natural language summary"""
    try:
        date_str = profile.timestamp.strftime("%B %d, %Y") if profile.timestamp else "Unknown date"
        
        # Determine region
        region = get_region(profile.latitude, profile.longitude)
        
        summary = (
            f"ARGO float {profile.float_id} profile from {date_str} "
            f"at location {profile.latitude:.2f}°N, {profile.longitude:.2f}°E "
            f"in the {region}. "
        )
        
        if profile.min_depth and profile.max_depth:
            summary += f"Measurements from {profile.min_depth:.1f}m to {profile.max_depth:.1f}m depth. "
        
        if profile.min_temp and profile.max_temp and profile.avg_temp:
            summary += (
                f"Temperature range: {profile.min_temp:.2f}°C to {profile.max_temp:.2f}°C "
                f"(average {profile.avg_temp:.2f}°C). "
            )
        
        if profile.min_sal and profile.max_sal and profile.avg_sal:
            summary += (
                f"Salinity range: {profile.min_sal:.2f} to {profile.max_sal:.2f} PSU "
                f"(average {profile.avg_sal:.2f} PSU)."
            )
        
        return summary
    except Exception as e:
        return f"ARGO float {profile.float_id} profile (summary generation error)"

def get_region(lat: float, lon: float) -> str:
    """Determine ocean region based on coordinates"""
    if 5 <= lat <= 30 and 40 <= lon <= 80:
        return "Arabian Sea"
    elif -10 <= lat <= 25 and 80 <= lon <= 100:
        return "Bay of Bengal"
    elif -30 <= lat <= 30 and 30 <= lon <= 120:
        return "Indian Ocean"
    elif -60 <= lat <= -30 and 20 <= lon <= 180:
        return "Southern Ocean"
    else:
        return "Ocean"

def create_indexes(engine):
    """Create indexes for fast queries"""
    print("\n🔧 Step 4: Creating indexes...")
    
    try:
        with engine.connect() as conn:
            # Indexes already defined in models.py, but let's ensure they exist
            print("   Creating spatial index (lat, lon)...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_lat_lon 
                ON argo_profiles (latitude, longitude)
            """))
            
            print("   Creating temporal index (timestamp)...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON argo_profiles (timestamp)
            """))
            
            print("   Creating float_id index...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_float_id 
                ON argo_profiles (float_id)
            """))
            
            print("   Creating composite spatio-temporal index...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_spatial_temporal 
                ON argo_profiles (latitude, longitude, timestamp)
            """))
            
            conn.commit()
        
        print("✅ Indexes created successfully!")
        return True
        
    except Exception as e:
        print(f"⚠️  Warning: Some indexes may already exist: {e}")
        return True  # Not critical if indexes already exist

def verify_data(engine):
    """Verify uploaded data"""
    print("\n✅ Step 5: Verifying data...")
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Count records
        total_records = session.query(ArgoProfile).count()
        print(f"   Total argo_profiles: {total_records:,}")
        
        # Count unique floats
        unique_floats = session.query(func.count(func.distinct(ArgoProfile.float_id))).scalar()
        print(f"   Unique float IDs: {unique_floats}")
        
        # Count summaries
        total_summaries = session.query(ProfileSummary).count()
        print(f"   Total profile_summaries: {total_summaries:,}")
        
        # Sample data
        sample = session.query(ArgoProfile).limit(1).first()
        if sample:
            print(f"\n   Sample record:")
            print(f"   - Float ID: {sample.float_id}")
            print(f"   - Location: {sample.latitude:.2f}°N, {sample.longitude:.2f}°E")
            print(f"   - Temperature: {sample.temperature}°C")
            print(f"   - Salinity: {sample.salinity} PSU")
        
        print("\n✅ Data verification complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying data: {e}")
        return False
    finally:
        session.close()

def main():
    """Main migration function"""
    if not NEON_URL:
        raise SystemExit("Set NEON_DATABASE_URL before running this migration.")
    
    # CSV path
    csv_path = "data/processed/argo_profiles.csv"
    
    try:
        # Connect to Neon
        print("\n🔌 Connecting to Neon PostgreSQL...")
        engine = create_engine(NEON_URL, echo=False)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected to Neon PostgreSQL!")
            print(f"   Version: {version[:50]}...")
        
        # Step 1: Create tables
        if not create_tables(engine):
            print("\n❌ Migration failed at table creation")
            return
        
        # Step 2: Upload data
        if not upload_argo_profiles(engine, csv_path):
            print("\n❌ Migration failed at data upload")
            return
        
        # Step 3: Generate summaries
        if not generate_profile_summaries(engine):
            print("\n⚠️  Warning: Profile summaries generation failed, but data is uploaded")
        
        # Step 4: Create indexes
        create_indexes(engine)
        
        # Step 5: Verify
        verify_data(engine)
        
        print("\n" + "="*80)
        print("🎉 MIGRATION COMPLETE!")
        print("="*80)
        print("""
Next steps:
1. Set DATABASE_URL to your Neon connection string.
2. Add secrets to Streamlit Cloud:
   - DATABASE_URL="your-neon-database-url"
   - GROQ_API_KEY="your-groq-api-key"
   - GROQ_MODEL="openai/gpt-oss-120b"
3. Deploy to Streamlit Cloud
4. Upload vector_store files to GitHub (data/vector_store/)

Your FloatChat is ready for deployment! 🚀
        """)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
