#!/usr/bin/env python3
"""
Fix float_id trailing spaces in Neon database
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database.db_setup import DatabaseSetup
from sqlalchemy import text

def fix_float_ids():
    """Remove trailing spaces from float_id column"""
    
    print("="*70)
    print("🔧 FIXING FLOAT_ID TRAILING SPACES")
    print("="*70)
    
    db_setup = DatabaseSetup()
    session = db_setup.get_session()
    
    try:
        # Check current state
        print("\n📊 Checking current float_ids...")
        result = session.execute(text("""
            SELECT float_id, COUNT(*) as count
            FROM argo_profiles
            WHERE float_id IS NOT NULL
            GROUP BY float_id
            ORDER BY float_id
            LIMIT 5
        """))
        
        print("\n🔍 Sample float_ids (before fix):")
        for row in result:
            print(f"   '{row[0]}' → {row[1]:,} records")
        
        # Fix trailing spaces
        print("\n🔧 Removing trailing spaces...")
        session.execute(text("""
            UPDATE argo_profiles
            SET float_id = TRIM(float_id)
            WHERE float_id IS NOT NULL
        """))
        session.commit()
        print("   ✅ Float IDs trimmed!")
        
        # Verify fix
        print("\n✅ Checking fixed float_ids...")
        result = session.execute(text("""
            SELECT float_id, COUNT(*) as count
            FROM argo_profiles
            WHERE float_id IS NOT NULL
            GROUP BY float_id
            ORDER BY float_id
            LIMIT 10
        """))
        
        print("\n🎯 Sample float_ids (after fix):")
        for i, row in enumerate(result, 1):
            print(f"   {i}. '{row[0]}' → {row[1]:,} records")
        
        print("\n" + "="*70)
        print("✅ FIX COMPLETE!")
        print("="*70)
        print("\n💡 Now try these queries in FloatChat:")
        print("   'Show me data for float 1901740'")
        print("   'Analyze float 1901740 profile statistics'")
        print("   'List all available float IDs'")
        print("="*70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    fix_float_ids()
