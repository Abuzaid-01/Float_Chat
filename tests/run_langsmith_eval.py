"""
Run LangSmith evaluation on FloatChat RAG pipeline
Tests all queries in the test dataset and reports results
"""

import sys
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from langsmith import Client
from langsmith.evaluation import evaluate
from rag_engine.query_processor import QueryProcessor
import os
from dotenv import load_dotenv

load_dotenv()

client = Client()

def evaluate_floatchat_query(inputs: dict) -> dict:
    """
    Process a FloatChat query and return results for evaluation
    
    Args:
        inputs: Dictionary with 'query' key
        
    Returns:
        Dictionary with response, sql, success, and execution_time
    """
    try:
        query_processor = QueryProcessor()
        query = inputs["query"]
        
        print(f"  🔄 Processing: {query}")
        
        result = query_processor.process_query(query)
        
        return {
            "response": result.get("response", ""),
            "sql": result.get("generated_sql", ""),
            "success": result.get("success", False),
            "execution_time": result.get("execution_time", 0),
            "error": result.get("error", None)
        }
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {
            "response": "",
            "sql": "",
            "success": False,
            "execution_time": 0,
            "error": str(e)
        }

def check_sql_quality(run, example):
    """Evaluator: Check if generated SQL contains expected keywords"""
    expected_keywords = example.outputs.get("expected_sql_keywords", [])
    generated_sql = run.outputs.get("sql", "").upper()
    
    if not expected_keywords:
        return {"score": 1.0, "key": "sql_quality"}
    
    matches = sum(1 for keyword in expected_keywords if keyword.upper() in generated_sql)
    score = matches / len(expected_keywords)
    
    return {
        "score": score,
        "key": "sql_quality",
        "comment": f"Matched {matches}/{len(expected_keywords)} SQL keywords"
    }

def check_response_completeness(run, example):
    """Evaluator: Check if response mentions expected terms"""
    expected_mentions = example.outputs.get("expected_response_mentions", [])
    response = run.outputs.get("response", "").lower()
    
    if not expected_mentions:
        return {"score": 1.0, "key": "response_completeness"}
    
    matches = sum(1 for term in expected_mentions if term.lower() in response)
    score = matches / len(expected_mentions)
    
    return {
        "score": score,
        "key": "response_completeness",
        "comment": f"Mentioned {matches}/{len(expected_mentions)} expected terms"
    }

def check_execution_success(run, example):
    """Evaluator: Check if query executed successfully"""
    success = run.outputs.get("success", False)
    
    return {
        "score": 1.0 if success else 0.0,
        "key": "execution_success",
        "comment": "Query executed successfully" if success else "Query failed"
    }

def check_performance(run, example):
    """Evaluator: Check if query completed in reasonable time"""
    execution_time = run.outputs.get("execution_time", 999)
    
    # Performance thresholds
    if execution_time < 3.0:
        score = 1.0
        comment = f"Fast ({execution_time:.2f}s)"
    elif execution_time < 5.0:
        score = 0.8
        comment = f"Good ({execution_time:.2f}s)"
    elif execution_time < 10.0:
        score = 0.5
        comment = f"Slow ({execution_time:.2f}s)"
    else:
        score = 0.0
        comment = f"Very slow ({execution_time:.2f}s)"
    
    return {
        "score": score,
        "key": "performance",
        "comment": comment
    }

def main():
    print("=" * 60)
    print("🚀 FLOATCHAT RAG PIPELINE EVALUATION")
    print("=" * 60)
    print("\n📊 Loading test dataset: FloatChat-Core-Queries")
    
    try:
        # Check if dataset exists
        datasets = list(client.list_datasets(dataset_name="FloatChat-Core-Queries"))
        
        if not datasets:
            print("\n❌ Dataset 'FloatChat-Core-Queries' not found!")
            print("💡 Run 'python tests/langsmith_test_dataset.py' first to create it.")
            return
        
        # Count examples by listing them
        dataset = datasets[0]
        examples = list(client.list_examples(dataset_id=dataset.id))
        print(f"✅ Found dataset with {len(examples)} test cases")
        
        print("\n🔧 Starting evaluation...")
        print("   This will run all test queries through your RAG pipeline")
        print("   and evaluate SQL quality, response completeness, and performance.\n")
        
        # Run evaluation
        results = evaluate(
            evaluate_floatchat_query,
            data="FloatChat-Core-Queries",
            evaluators=[
                check_sql_quality,
                check_response_completeness,
                check_execution_success,
                check_performance
            ],
            experiment_prefix="FloatChat-RAG-Eval",
            description="Automated evaluation of FloatChat RAG pipeline quality"
        )
        
        print("\n" + "=" * 60)
        print("✅ EVALUATION COMPLETE!")
        print("=" * 60)
        
        print("\n📊 View detailed results at:")
        print("   https://smith.langchain.com/")
        print("\n💡 Results include:")
        print("   • SQL quality scores")
        print("   • Response completeness")
        print("   • Execution success rate")
        print("   • Performance metrics")
        print("   • Detailed traces for each query")
        
    except Exception as e:
        print(f"\n❌ Error running evaluation: {e}")
        print("\n🔍 Troubleshooting:")
        print("   - Make sure the dataset exists (run langsmith_test_dataset.py)")
        print("   - Check that LANGCHAIN_API_KEY is set in .env")
        print("   - Verify database connection is working")
        print("   - Ensure Streamlit app dependencies are installed")

if __name__ == "__main__":
    main()
