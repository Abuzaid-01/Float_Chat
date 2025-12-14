#!/usr/bin/env python3
"""
Quick test for the improved intent classification
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from rag_engine.intent_classifier import intent_classifier

load_dotenv()

# Test the specific problematic queries
test_queries = [
    "tell me about dataset from which date to which date you have data?",
    "what is the date range of your dataset?",
    "from which date to which date do you have data?",
    "when was this data collected?",
    "what time period does the data cover?",
    "hello",  # Should still be greeting
    "who built you?",  # Should still be developer_info
]

print("🧪 Testing Fixed Intent Classification")
print("="*70)

for query in test_queries:
    result = intent_classifier.classify_intent(query)
    
    print(f"\nQuery: '{query}'")
    print(f"  Intent: {result['intent']}")
    print(f"  Confidence: {result['confidence']:.2f}")
    print(f"  Requires data query: {result['requires_data_query']}")
    
    if result['intent'] == 'data_query':
        print(f"  ✅ Will route to MCP pipeline")
    else:
        print(f"  📝 Direct response (first 80 chars): {result['direct_response'][:80]}...")

print("\n" + "="*70)
