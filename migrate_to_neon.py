#!/usr/bin/env python3
"""
Migrate data from local PostgreSQL to Neon PostgreSQL
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import os
import pandas as pd
from sqlalchemy import create_engine, text
from database.models import Base, ArgoProfile, ProfileSummary
from tqdm import tqdm

# Connection strings
LOCAL_DB = "postgresql://postgres:floatchat123@localhost:5432/floatchat"
NEON_DB = "postgresql://neondb_owner:npg_8yOoZiL1bJpW@ep-falling-block-a8srv2pf-pooler.eastus2.azure.neon.tech/neondb?sslmode=require"

def test_connections():
    """Test both database connections"""
    print("="*70)
    print("🔍 TESTING DATABASE CONNECTIONS")
    print("="*70)
    
    # Test local
    print("\n1️⃣ Testing LOCAL PostgreSQL...")
    try:
        local_engine = create_engine(LOCAL_DB)
        with local_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            print("   ✅ Local connection successful!")
    except Exception as e:
        print(f"   ❌ Local connection failed: {e}")
        return False
    
    # Test Neon
    print("\n2️⃣ Testing NEON PostgreSQL...")
    try:
        neon_engine = create_engine(NEON_DB)
        with neon_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            print("   ✅ Neon connection successful!")
    except Exception as e:
        print(f"   ❌ Neon connection failed: {e}")
        return False
    
    return True

def create_tables_on_neon():
    """Create tables on Neon database"""
    print("\n" + "="*70)
    print("📦 CREATING TABLES ON NEON")
    print("="*70)
    
    try:
        neon_engine = create_engine(NEON_DB)
        
        # Drop existing tables if any
        print("\n🗑️  Dropping existing tables (if any)...")
        Base.metadata.drop_all(bind=neon_engine)
        print("   ✅ Existing tables dropped")
        
        # Create all tables
        print("\n📊 Creating new tables...")
        Base.metadata.create_all(bind=neon_engine)
        print("   ✅ Tables created: argo_profiles, profile_summaries, query_logs")
        
        return True
    except Exception as e:
        print(f"   ❌ Error creating tables: {e}")
        return False

def migrate_argo_profiles():
    """Migrate argo_profiles table"""
    print("\n" + "="*70)
    print("🌊 MIGRATING ARGO_PROFILES TABLE")
    print("="*70)
    
    try:
        local_engine = create_engine(LOCAL_DB)
        neon_engine = create_engine(NEON_DB)
        
        # Count records in local
        with local_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM argo_profiles"))
            total_records = result.scalar()
        
        print(f"\n📊 Total records to migrate: {total_records:,}")
        
        if total_records == 0:
            print("   ⚠️  No records found in local database!")
            return False
        
        # Migrate in chunks (10,000 at a time for better performance)
        chunk_size = 10000
        print(f"📦 Migrating in chunks of {chunk_size:,} records...")
        
        for offset in tqdm(range(0, total_records, chunk_size), desc="Migrating"):
            # Read chunk from local
            query = f"""
                SELECT id, float_id, cycle_number, latitude, longitude, timestamp,
                       pressure, temperature, salinity, dissolved_oxygen, chlorophyll, ph,
                       temp_qc, sal_qc, data_mode, platform_type, created_at
                FROM argo_profiles
                ORDER BY id
                LIMIT {chunk_size} OFFSET {offset}
            """
            
            df = pd.read_sql(query, local_engine)
            
            # Write chunk to Neon
            df.to_sql('argo_profiles', neon_engine, if_exists='append', index=False, method='multi')
        
        # Verify count
        with neon_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM argo_profiles"))
            migrated_records = result.scalar()
        
        print(f"\n✅ Migration complete!")
        print(f"   Local records: {total_records:,}")
        print(f"   Neon records: {migrated_records:,}")
        
        if migrated_records == total_records:
            print("   ✅ All records migrated successfully!")
            return True
        else:
            print(f"   ⚠️  Warning: Record count mismatch!")
            return False
            
    except Exception as e:
        print(f"\n❌ Error migrating argo_profiles: {e}")
        import traceback
        traceback.print_exc()
        return False

def migrate_profile_summaries():
    """Migrate profile_summaries table"""
    print("\n" + "="*70)
    print("📝 MIGRATING PROFILE_SUMMARIES TABLE")
    print("="*70)
    
    try:
        local_engine = create_engine(LOCAL_DB)
        neon_engine = create_engine(NEON_DB)
        
        # Count records in local
        with local_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM profile_summaries"))
            total_records = result.scalar()
        
        print(f"\n📊 Total summaries to migrate: {total_records:,}")
        
        if total_records == 0:
            print("   ⚠️  No summaries found in local database!")
            return False
        
        # Read all summaries (usually not too many)
        query = """
            SELECT id, float_id, cycle_number, summary_text, latitude, longitude,
                   timestamp, min_depth, max_depth, temp_range, sal_range, created_at
            FROM profile_summaries
        """
        
        df = pd.read_sql(query, local_engine)
        
        # Write to Neon
        df.to_sql('profile_summaries', neon_engine, if_exists='append', index=False, method='multi')
        
        # Verify count
        with neon_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM profile_summaries"))
            migrated_records = result.scalar()
        
        print(f"\n✅ Migration complete!")
        print(f"   Local summaries: {total_records:,}")
        print(f"   Neon summaries: {migrated_records:,}")
        
        if migrated_records == total_records:
            print("   ✅ All summaries migrated successfully!")
            return True
        else:
            print(f"   ⚠️  Warning: Summary count mismatch!")
            return False
            
    except Exception as e:
        print(f"\n❌ Error migrating profile_summaries: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_indexes_on_neon():
    """Create indexes on Neon database for performance"""
    print("\n" + "="*70)
    print("🔧 CREATING INDEXES ON NEON")
    print("="*70)
    
    try:
        neon_engine = create_engine(NEON_DB)
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_lat_lon ON argo_profiles (latitude, longitude)",
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON argo_profiles (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_float_id ON argo_profiles (float_id)",
            "CREATE INDEX IF NOT EXISTS idx_spatial_temporal ON argo_profiles (latitude, longitude, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_summary_location ON profile_summaries (latitude, longitude)"
        ]
        
        with neon_engine.connect() as conn:
            for idx_sql in indexes:
                print(f"   Creating index: {idx_sql.split('IF NOT EXISTS')[1].split('ON')[0].strip()}...")
                conn.execute(text(idx_sql))
                conn.commit()
        
        print("\n✅ All indexes created successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error creating indexes: {e}")
        return False

def verify_migration():
    """Verify the migration was successful"""
    print("\n" + "="*70)
    print("🔍 VERIFYING MIGRATION")
    print("="*70)
    
    try:
        local_engine = create_engine(LOCAL_DB)
        neon_engine = create_engine(NEON_DB)
        
        # Compare counts
        tables = ['argo_profiles', 'profile_summaries']
        
        for table in tables:
            with local_engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                local_count = result.scalar()
            
            with neon_engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                neon_count = result.scalar()
            
            match = "✅" if local_count == neon_count else "❌"
            print(f"\n{match} {table}:")
            print(f"   Local: {local_count:,}")
            print(f"   Neon:  {neon_count:,}")
        
        # Sample data check
        print("\n📊 Sample data from Neon:")
        with neon_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT float_id, latitude, longitude, temperature, salinity
                FROM argo_profiles
                LIMIT 5
            """))
            for row in result:
                print(f"   Float: {row[0]}, Lat: {row[1]:.2f}, Lon: {row[2]:.2f}, Temp: {row[3]:.2f}°C")
        
        print("\n✅ Migration verification complete!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error verifying migration: {e}")
        return False

def update_env_file():
    """Update .env file with Neon connection string"""
    print("\n" + "="*70)
    print("📝 UPDATING .env FILE")
    print("="*70)
    
    env_path = Path(__file__).parent / '.env'
    
    try:
        # Read current .env
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Update DATABASE_URL
        new_lines = []
        for line in lines:
            if line.startswith('DATABASE_URL='):
                new_lines.append(f'DATABASE_URL={NEON_DB}\n')
                print(f"   ✅ Updated DATABASE_URL to Neon")
            else:
                new_lines.append(line)
        
        # Write back
        with open(env_path, 'w') as f:
            f.writelines(new_lines)
        
        print("   ✅ .env file updated successfully!")
        return True
        
    except Exception as e:
        print(f"   ❌ Error updating .env: {e}")
        return False

def main():
    """Main migration process"""
    print("🚀 FLOATCHAT MIGRATION TO NEON POSTGRESQL")
    print("="*70)
    
    # Step 1: Test connections
    if not test_connections():
        print("\n❌ Connection test failed. Aborting migration.")
        return
    
    # Step 2: Create tables on Neon
    if not create_tables_on_neon():
        print("\n❌ Table creation failed. Aborting migration.")
        return
    
    # Step 3: Migrate argo_profiles
    if not migrate_argo_profiles():
        print("\n❌ argo_profiles migration failed. Aborting.")
        return
    
    # Step 4: Migrate profile_summaries
    if not migrate_profile_summaries():
        print("\n❌ profile_summaries migration failed. Aborting.")
        return
    
    # Step 5: Create indexes
    if not create_indexes_on_neon():
        print("\n⚠️  Index creation failed, but data is migrated.")
    
    # Step 6: Verify migration
    verify_migration()
    
    # Step 7: Update .env file
    print("\n" + "="*70)
    print("⚠️  IMPORTANT: Update .env file")
    print("="*70)
    print(f"\nAdd this to your .env file:")
    print(f"DATABASE_URL={NEON_DB}")
    
    response = input("\nUpdate .env file automatically? (y/n): ")
    if response.lower() == 'y':
        update_env_file()
    
    # Final summary
    print("\n" + "="*70)
    print("✅ MIGRATION COMPLETE!")
    print("="*70)
    print("\n📝 Next steps:")
    print("1. ✅ Data migrated to Neon PostgreSQL")
    print("2. 📝 Update .env with Neon DATABASE_URL (if not done)")
    print("3. 🚀 Deploy to Streamlit Cloud with Neon connection")
    print("4. 📦 Upload vector_store files to Streamlit")
    print("\n🌐 Neon Dashboard: https://console.neon.tech/")
    print("="*70)

if __name__ == "__main__":
    main()
