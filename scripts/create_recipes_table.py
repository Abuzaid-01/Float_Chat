#!/usr/bin/env python3
"""
Create workflow_recipes and query_history tables
Run once to add these tables to your Neon database
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_setup import DatabaseSetup
from database.models import Base, WorkflowRecipe, SavedQuery
from sqlalchemy import inspect

def create_tables():
    """Create workflow_recipes and query_history tables"""
    
    print("="*70)
    print("🔧 Creating New Tables")
    print("="*70)
    
    db_setup = DatabaseSetup()
    engine = db_setup.engine
    inspector = inspect(engine)
    
    # Check existing tables
    existing_tables = inspector.get_table_names()
    print(f"\n📊 Existing tables: {existing_tables}")
    
    # Create only the new tables
    tables_to_create = []
    
    if 'workflow_recipes' not in existing_tables:
        tables_to_create.append('workflow_recipes')
        print(f"\n✅ Will create: workflow_recipes")
    else:
        print(f"\n⚠️  Table 'workflow_recipes' already exists")
    
    if 'saved_queries' not in existing_tables:
        tables_to_create.append('saved_queries')
        print(f"✅ Will create: saved_queries")
    else:
        print(f"⚠️  Table 'saved_queries' already exists")
    
    if tables_to_create:
        print(f"\n🔨 Creating tables: {', '.join(tables_to_create)}")
        
        # Create only the specific tables
        WorkflowRecipe.__table__.create(engine, checkfirst=True)
        SavedQuery.__table__.create(engine, checkfirst=True)
        
        print(f"✅ Tables created successfully!")
    else:
        print(f"\n✅ All tables already exist!")
    
    print("\n" + "="*70)
    print("✅ Database Setup Complete!")
    print("="*70)
    print("\n💡 Next step: Run 'python scripts/seed_recipes.py' to add sample recipes")
    print("="*70)

if __name__ == "__main__":
    create_tables()
