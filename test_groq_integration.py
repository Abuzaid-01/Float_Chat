#!/usr/bin/env python3
"""
Test script to verify Groq API integration
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

def test_groq_connection():
    """Test basic Groq API connection"""
    print("🔧 Testing Groq API Connection...")
    
    try:
        # Initialize Groq client
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            print("❌ GROQ_API_KEY not found in environment variables")
            return False
        
        client = Groq(api_key=api_key)
        model = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
        
        print(f"📡 Using model: {model}")
        print(f"🔑 API Key: {api_key[:20]}...")
        
        # Test simple completion
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": "Say 'Hello from Groq!' in exactly 5 words."
                }
            ],
            temperature=0.1,
            max_completion_tokens=50,
            top_p=1,
            stream=False,
            stop=None
        )
        
        response = completion.choices[0].message.content
        print(f"✅ Groq Response: {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ Groq API Error: {e}")
        return False

def test_response_generator():
    """Test the ResponseGenerator class"""
    print("\n🤖 Testing ResponseGenerator...")
    
    try:
        from rag_engine.response_generator import ResponseGenerator
        import pandas as pd
        
        # Create test data
        test_data = pd.DataFrame({
            'temperature': [25.5, 26.1, 24.8],
            'salinity': [35.2, 35.4, 35.1],
            'pressure': [10, 20, 30],
            'latitude': [15.5, 16.0, 15.8],
            'longitude': [75.2, 75.5, 75.1]
        })
        
        generator = ResponseGenerator()
        
        response = generator.generate_response(
            question="What is the average temperature?",
            query_results=test_data,
            context="Test oceanographic data"
        )
        
        print(f"✅ Generated Response: {response[:200]}...")
        return True
        
    except Exception as e:
        print(f"❌ ResponseGenerator Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mcp_integration():
    """Test MCP integration with Groq"""
    print("\n🔧 Testing MCP Integration...")
    
    try:
        from mcp_server.mcp_query_processor import mcp_query_processor
        
        # Test simple query
        result = mcp_query_processor.process_query_with_mcp(
            "What tools are available?"
        )
        
        if result['success']:
            print(f"✅ MCP Query Success: {len(result['tools_used'])} tools used")
            print(f"📊 Response: {result['response'][:200]}...")
            return True
        else:
            print(f"❌ MCP Query Failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ MCP Integration Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 FloatChat Groq Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Groq API Connection", test_groq_connection),
        ("Response Generator", test_response_generator),
        ("MCP Integration", test_mcp_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 30)
        
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Groq integration is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)