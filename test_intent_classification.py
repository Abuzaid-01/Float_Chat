#!/usr/bin/env python3
"""
Test Intent Classification System
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from rag_engine.intent_classifier import intent_classifier

# Load environment variables
load_dotenv()


def test_intent_classification():
    """Test various query types"""
    
    test_queries = [
        # Developer/Creator queries
        ("who built you?", "developer_info"),
        ("whi built this app?", "developer_info"),  # Typo handling
        ("who is the creator?", "developer_info"),
        ("who developed floatchat?", "developer_info"),
        
        # Greetings
        ("hello", "greeting"),
        ("hi there", "greeting"),
        ("good morning", "greeting"),
        
        # Help queries
        ("help me", "help"),
        ("what can you do?", "help"),
        ("how do i use this?", "help"),
        
        # Thanks
        ("thank you", "thanks"),
        ("thanks a lot", "thanks"),
        
        # About FloatChat
        ("what is floatchat?", "about_floatchat"),
        ("tell me about this app", "about_floatchat"),
        
        # Data queries
        ("show me temperature in arabian sea", "data_query"),
        ("what is the average salinity?", "data_query"),
        ("compare regions", "data_query"),
    ]
    
    print("🧪 Testing Intent Classification System")
    print("="*70)
    
    correct = 0
    total = len(test_queries)
    
    for query, expected_intent in test_queries:
        result = intent_classifier.classify_intent(query)
        
        is_correct = result['intent'] == expected_intent
        correct += is_correct
        
        status = "✅" if is_correct else "❌"
        print(f"\n{status} Query: '{query}'")
        print(f"   Expected: {expected_intent}")
        print(f"   Got: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"   Requires data query: {result['requires_data_query']}")
        
        if result['direct_response'] and len(result['direct_response']) > 100:
            print(f"   Response preview: {result['direct_response'][:100]}...")
        elif result['direct_response']:
            print(f"   Response: {result['direct_response']}")
    
    print("\n" + "="*70)
    print(f"📊 Results: {correct}/{total} correct ({correct/total*100:.1f}%)")
    
    if correct == total:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️  {total - correct} tests failed")
    
    return correct == total


if __name__ == "__main__":
    success = test_intent_classification()
    sys.exit(0 if success else 1)
