#!/usr/bin/env python3
"""
Quick test of Neon database connection
"""

import psycopg2

# Your Neon connection string
DATABASE_URL = "postgresql://neondb_owner:npg_8yOoZiL1bJpW@ep-falling-block-a8srv2pf-pooler.eastus2.azure.neon.tech/neondb?sslmode=require"

print("🔍 Testing Neon PostgreSQL Connection...")
print("="*60)

try:
    # Connect
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("✅ Connection successful!")
    
    # Test query
    cursor.execute("SELECT COUNT(*) FROM argo_profiles;")
    count = cursor.fetchone()[0]
    print(f"✅ Found {count:,} records in argo_profiles")
    
    # Test sample data
    cursor.execute("SELECT float_id, latitude, longitude, temperature FROM argo_profiles LIMIT 5;")
    rows = cursor.fetchall()
    
    print("\n📊 Sample data:")
    for row in rows:
        print(f"   Float: {row[0]}, Lat: {row[1]:.2f}, Lon: {row[2]:.2f}, Temp: {row[3]}°C")
    
    cursor.close()
    conn.close()
    
    print("\n✅ All tests passed! Database is working correctly.")
    print("="*60)
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\n💡 Troubleshooting:")
    print("   1. Check if Neon database is active (not suspended)")
    print("   2. Verify connection string is correct")
    print("   3. Check if data was migrated successfully")
