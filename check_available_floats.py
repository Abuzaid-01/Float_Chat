#!/usr/bin/env python3
"""
Quick script to check available float IDs in database
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database.db_setup import DatabaseSetup
from database.models import ArgoProfile
from sqlalchemy import func, distinct
import pandas as pd

def check_available_floats():
    """Check which float IDs are available in database"""
    
    print("="*70)
    print("🔍 CHECKING AVAILABLE FLOAT IDs IN DATABASE")
    print("="*70)
    
    db_setup = DatabaseSetup()
    session = db_setup.get_session()
    
    try:
        # === 1. TOTAL COUNTS ===
        print("\n📊 OVERALL STATISTICS:")
        total_records = session.query(ArgoProfile).count()
        print(f"   Total measurements: {total_records:,}")
        
        unique_floats = session.query(func.count(distinct(ArgoProfile.float_id))).scalar()
        print(f"   Unique float IDs: {unique_floats}")
        
        # === 2. LIST ALL FLOAT IDs ===
        print("\n🌊 AVAILABLE FLOAT IDs:")
        print("-" * 70)
        
        float_stats = session.query(
            ArgoProfile.float_id,
            func.count(ArgoProfile.id).label('measurement_count'),
            func.count(distinct(ArgoProfile.cycle_number)).label('profile_count'),
            func.min(ArgoProfile.timestamp).label('first_date'),
            func.max(ArgoProfile.timestamp).label('last_date'),
            func.avg(ArgoProfile.latitude).label('avg_lat'),
            func.avg(ArgoProfile.longitude).label('avg_lon')
        ).filter(
            ArgoProfile.float_id.isnot(None)
        ).group_by(
            ArgoProfile.float_id
        ).order_by(
            ArgoProfile.float_id
        ).all()
        
        if not float_stats:
            print("   ❌ No float IDs found in database!")
            return
        
        # Display in table format
        print(f"\n{'Float ID':<15} {'Measurements':<15} {'Profiles':<12} {'Date Range':<25} {'Avg Location':<20}")
        print("-" * 90)
        
        for stat in float_stats:
            float_id = stat.float_id or "NULL"
            measurements = f"{stat.measurement_count:,}"
            profiles = stat.profile_count
            date_range = f"{stat.first_date.strftime('%Y-%m-%d')} to {stat.last_date.strftime('%Y-%m-%d')}"
            location = f"{stat.avg_lat:.2f}°N, {stat.avg_lon:.2f}°E"
            
            print(f"{float_id:<15} {measurements:<15} {profiles:<12} {date_range:<25} {location:<20}")
        
        # === 3. SAMPLE QUERIES ===
        print("\n" + "="*70)
        print("💡 SAMPLE QUERIES YOU CAN USE:")
        print("="*70)
        
        # Get first float ID with data
        sample_float = float_stats[0].float_id if float_stats else None
        
        if sample_float:
            print(f"\n1. Analyze specific float:")
            print(f"   → Analyze float {sample_float} profile statistics")
            print(f"   → Show me all data from float {sample_float}")
            print(f"   → Plot temperature profile for float {sample_float}")
        
        print(f"\n2. List all floats:")
        print(f"   → Show me all available float IDs")
        print(f"   → List all floats with their statistics")
        
        print(f"\n3. Regional queries:")
        print(f"   → Show me floats in Arabian Sea")
        print(f"   → Which floats are in Bay of Bengal?")
        
        print(f"\n4. General queries:")
        print(f"   → Show me temperature profiles")
        print(f"   → Compare salinity between floats")
        print(f"   → Show the latest measurements")
        
        # === 4. CHECK FOR NULL FLOAT IDs ===
        null_count = session.query(ArgoProfile).filter(
            ArgoProfile.float_id.is_(None)
        ).count()
        
        if null_count > 0:
            print(f"\n⚠️  WARNING: {null_count:,} records have NULL float_id")
            print("   These records cannot be queried by float ID")
        
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()

if __name__ == "__main__":
    check_available_floats()
