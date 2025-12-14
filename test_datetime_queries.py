#!/usr/bin/env python3
"""
Test datetime-specific queries
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from rag_engine.sql_generator import EnhancedSQLGenerator

load_dotenv()

# Create SQL generator
sql_gen = EnhancedSQLGenerator()

print("🧪 Testing DateTime Query Generation")
print("="*80)

# Test queries with specific dates/times
test_queries = [
    "What was the temperature on October 7, 2025 at 20:50?",
    "Show me data from October 7, 2025",
    "What was recorded on 7 October 2025?",
    "Temperature on 2025-10-07 at 20:50",
    "Data from October 2025",
]

for query in test_queries:
    print(f"\n📝 Query: {query}")
    print("-" * 80)
    
    # Analyze query
    analysis = sql_gen._analyze_query(query)
    print(f"Analysis:")
    print(f"  Type: {analysis['type']}")
    print(f"  Time Period: {analysis['time_period']}")
    print(f"  Has Specific DateTime: {analysis.get('has_specific_datetime', False)}")
    print(f"  Parameters: {analysis['parameters']}")
    
    # Generate SQL
    sql = sql_gen.generate_sql(query, context="")
    
    if sql:
        print(f"\n✅ Generated SQL:")
        print(f"{sql}")
    else:
        print(f"\n❌ Failed to generate SQL")

print("\n" + "="*80)
print("Test complete!")
