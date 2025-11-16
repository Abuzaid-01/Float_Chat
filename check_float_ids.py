#!/usr/bin/env python3
"""
Quick script to check what float IDs are actually in the Neon database
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database.db_setup import DatabaseSetup
from database.models import ArgoProfile
from sqlalchemy import func, distinct
import pandas as pd

def check_floats():
    """Check which float IDs exist in Neon database"""
    
    print("="*70)
    print("🔍 CHECKING FLOAT IDs IN NEON DATABASE")
    print("="*70)
    
    db_setup = DatabaseSetup()
    session = db_setup.get_session()
    
    try:
        # Total records
        total = session.query(ArgoProfile).count()
        print(f"\n📊 Total measurements: {total:,}")
        
        # Check for NULL float_ids
        null_count = session.query(ArgoProfile).filter(
            ArgoProfile.float_id.is_(None)
        ).count()
        print(f"⚠️  NULL float_ids: {null_count:,} ({null_count/total*100:.1f}%)")
        
        # Count non-null float_ids
        non_null = total - null_count
        print(f"✅ Non-NULL float_ids: {non_null:,} ({non_null/total*100:.1f}%)")
        
        # Get unique float IDs
        unique_floats = session.query(ArgoProfile.float_id).filter(
            ArgoProfile.float_id.isnot(None)
        ).distinct().all()
        
        print(f"\n🌊 Unique float IDs: {len(unique_floats)}")
        
        # Show first 20 float IDs
        print("\n📋 First 20 Float IDs:")
        for i, (float_id,) in enumerate(unique_floats[:20], 1):
            # Count records for this float
            count = session.query(ArgoProfile).filter(
                ArgoProfile.float_id == float_id
            ).count()
            print(f"   {i}. Float {float_id}: {count:,} measurements")
        
        # Get 10 random float IDs for testing
        print("\n🎲 10 Random Float IDs for Testing:")
        print("="*70)
        random_floats = session.query(ArgoProfile.float_id).filter(
            ArgoProfile.float_id.isnot(None)
        ).distinct().limit(10).all()
        
        for i, (float_id,) in enumerate(random_floats, 1):
            count = session.query(ArgoProfile).filter(
                ArgoProfile.float_id == float_id
            ).count()
            print(f"   {i}. {float_id} ({count:,} records)")
        
        print("\n" + "="*70)
        print("💡 Try these queries in FloatChat:")
        print("="*70)
        if random_floats:
            first_float = random_floats[0][0]
            print(f'   "Show me data for float {first_float}"')
            print(f'   "Analyze float {first_float} profile statistics"')
            print(f'   "Plot temperature profile for float {first_float}"')
        print(f'   "Show me all available float IDs"')
        print(f'   "List floats in Arabian Sea"')
        print("="*70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    check_floats()
