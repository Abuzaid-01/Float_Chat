"""
LangSmith Test Dataset for FloatChat
Creates reusable test cases for RAG pipeline evaluation
"""

from langsmith import Client
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize LangSmith client
client = Client()

def create_test_dataset():
    """Create test dataset with essential FloatChat queries"""
    
    print("🚀 Creating LangSmith test dataset for FloatChat...")
    
    # Create dataset
    dataset = client.create_dataset(
        dataset_name="FloatChat-Core-Queries",
        description="Essential queries for testing FloatChat RAG pipeline"
    )
    
    print(f"✅ Created dataset: {dataset.name} (ID: {dataset.id})")
    
    # Test cases
    test_cases = [
        # Basic queries
        {
            "inputs": {"query": "Show me all float IDs"},
            "outputs": {
                "expected_sql_keywords": ["SELECT", "DISTINCT", "float_id", "argo_profiles"],
                "expected_response_mentions": ["float"]
            },
            "metadata": {"category": "basic", "difficulty": "easy"}
        },
        {
            "inputs": {"query": "What is the average temperature in Arabian Sea?"},
            "outputs": {
                "expected_sql_keywords": ["AVG", "temperature", "latitude", "longitude"],
                "expected_response_mentions": ["arabian sea", "°C", "temperature"],
                "region": "Arabian Sea"
            },
            "metadata": {"category": "aggregation", "difficulty": "medium"}
        },
        {
            "inputs": {"query": "Average salinity in Bay of Bengal"},
            "outputs": {
                "expected_sql_keywords": ["AVG", "salinity"],
                "expected_response_mentions": ["bay of bengal", "PSU", "salinity"],
                "region": "Bay of Bengal"
            },
            "metadata": {"category": "aggregation", "difficulty": "medium"}
        },
        
        # MCP tool queries
        {
            "inputs": {"query": "Calculate thermocline depth in Bay of Bengal"},
            "outputs": {
                "expected_tools": ["calculate_thermocline"],
                "expected_response_mentions": ["thermocline", "depth", "meters"],
                "should_have_depth_value": True
            },
            "metadata": {"category": "mcp_tools", "difficulty": "hard"}
        },
        {
            "inputs": {"query": "Identify water masses in Arabian Sea"},
            "outputs": {
                "expected_tools": ["identify_water_masses"],
                "expected_response_mentions": ["water mass", "temperature", "salinity"],
                "should_have_classifications": True
            },
            "metadata": {"category": "mcp_tools", "difficulty": "hard"}
        },
        {
            "inputs": {"query": "Compare Arabian Sea vs Bay of Bengal temperature"},
            "outputs": {
                "expected_tools": ["compare_regions"],
                "expected_response_mentions": ["arabian sea", "bay of bengal", "comparison", "°C"],
                "should_compare_both_regions": True
            },
            "metadata": {"category": "mcp_tools", "difficulty": "hard"}
        },
        
        # Spatial queries
        {
            "inputs": {"query": "Find floats near 15°N, 65°E"},
            "outputs": {
                "expected_tools": ["search_by_coordinates"],
                "expected_response_mentions": ["latitude", "longitude", "float"],
                "should_have_coordinates": True
            },
            "metadata": {"category": "spatial", "difficulty": "medium"}
        },
        
        # Temporal queries
        {
            "inputs": {"query": "Show recent data from October 2025"},
            "outputs": {
                "expected_sql_keywords": ["timestamp", "2025-10"],
                "expected_response_mentions": ["october", "2025"],
                "temporal_filter": True
            },
            "metadata": {"category": "temporal", "difficulty": "medium"}
        },
        
        # Profile analysis
        {
            "inputs": {"query": "Analyze float 2902696 statistics"},
            "outputs": {
                "expected_tools": ["analyze_profile"],
                "expected_response_mentions": ["2902696", "statistics"],
                "specific_float": "2902696"
            },
            "metadata": {"category": "profile_analysis", "difficulty": "medium"}
        },
        
        # Database structure
        {
            "inputs": {"query": "What is the database schema?"},
            "outputs": {
                "expected_tools": ["get_database_schema"],
                "expected_response_mentions": ["table", "column", "argo_profiles"],
                "should_show_structure": True
            },
            "metadata": {"category": "metadata", "difficulty": "easy"}
        }
    ]
    
    # Add examples to dataset
    print(f"\n📝 Adding {len(test_cases)} test cases...")
    for i, test_case in enumerate(test_cases, 1):
        client.create_example(
            dataset_id=dataset.id,
            inputs=test_case["inputs"],
            outputs=test_case["outputs"],
            metadata=test_case.get("metadata", {})
        )
        print(f"  ✅ Test case {i}: {test_case['inputs']['query']}")
    
    print(f"\n🎉 Successfully created {len(test_cases)} test cases!")
    print(f"📊 View dataset at: https://smith.langchain.com/")
    print(f"📁 Dataset ID: {dataset.id}")
    
    return dataset

if __name__ == "__main__":
    try:
        dataset = create_test_dataset()
        print("\n✅ Done! You can now run evaluations against this dataset.")
        print("\n💡 Next steps:")
        print("   1. Run a query in your Streamlit app to test tracing")
        print("   2. Check https://smith.langchain.com/ to see the trace")
        print("   3. Run 'python tests/run_langsmith_eval.py' to evaluate all test cases")
    except Exception as e:
        print(f"\n❌ Error creating dataset: {e}")
        print("\n🔍 Troubleshooting:")
        print("   - Check that LANGCHAIN_API_KEY is set correctly in .env")
        print("   - Verify your LangSmith account is active")
        print("   - Make sure you have internet connection")
