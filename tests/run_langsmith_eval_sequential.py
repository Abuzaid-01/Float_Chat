"""
Sequential LangSmith Evaluation - Runs queries one at a time
Fixes the parallel execution / tensor loading errors
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langsmith import Client
from rag_engine.query_processor import QueryProcessor
import os
from dotenv import load_dotenv
import time
from datetime import datetime

load_dotenv()

client = Client()

def evaluate_single_query(query: str, query_num: int, total: int):
    """
    Evaluate a single query and return results
    
    Args:
        query: The query string to test
        query_num: Current query number (for progress display)
        total: Total number of queries
    
    Returns:
        Dictionary with results
    """
    print(f"\n{'='*60}")
    print(f"📝 Query {query_num}/{total}: {query}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Initialize query processor (fresh for each query)
        query_processor = QueryProcessor()
        
        # Process query
        result = query_processor.process_query(query)
        
        execution_time = time.time() - start_time
        
        # Extract results
        success = result.get("success", False)
        response = result.get("response", "")
        sql = result.get("generated_sql", "")
        error = result.get("error", None)
        
        # Display results
        if success:
            print(f"✅ SUCCESS in {execution_time:.2f}s")
            print(f"\n📊 Generated SQL:")
            print(f"   {sql[:100]}..." if len(sql) > 100 else f"   {sql}")
            print(f"\n💬 Response Preview:")
            print(f"   {response[:150]}..." if len(response) > 150 else f"   {response}")
        else:
            print(f"❌ FAILED in {execution_time:.2f}s")
            print(f"   Error: {error}")
        
        return {
            "query": query,
            "success": success,
            "execution_time": execution_time,
            "response": response,
            "sql": sql,
            "error": error,
            "has_sql": bool(sql),
            "response_length": len(response)
        }
        
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"❌ EXCEPTION in {execution_time:.2f}s")
        print(f"   Error: {str(e)}")
        
        return {
            "query": query,
            "success": False,
            "execution_time": execution_time,
            "response": "",
            "sql": "",
            "error": str(e),
            "has_sql": False,
            "response_length": 0
        }

def evaluate_quality(results: list):
    """
    Analyze results and provide quality scores
    
    Args:
        results: List of query results
        
    Returns:
        Dictionary with quality metrics
    """
    total_queries = len(results)
    successful = sum(1 for r in results if r["success"])
    failed = total_queries - successful
    
    # Calculate metrics
    success_rate = (successful / total_queries * 100) if total_queries > 0 else 0
    
    # Average execution time (only for successful queries)
    successful_times = [r["execution_time"] for r in results if r["success"]]
    avg_time = sum(successful_times) / len(successful_times) if successful_times else 0
    
    # SQL generation rate
    queries_with_sql = sum(1 for r in results if r["has_sql"])
    sql_rate = (queries_with_sql / total_queries * 100) if total_queries > 0 else 0
    
    # Response completeness
    queries_with_response = sum(1 for r in results if r["response_length"] > 50)
    response_rate = (queries_with_response / total_queries * 100) if total_queries > 0 else 0
    
    # Performance classification
    if avg_time < 3.0:
        performance_grade = "Excellent"
        performance_score = 100
    elif avg_time < 5.0:
        performance_grade = "Good"
        performance_score = 85
    elif avg_time < 10.0:
        performance_grade = "Acceptable"
        performance_score = 70
    else:
        performance_grade = "Slow"
        performance_score = 50
    
    return {
        "total_queries": total_queries,
        "successful": successful,
        "failed": failed,
        "success_rate": success_rate,
        "avg_execution_time": avg_time,
        "sql_generation_rate": sql_rate,
        "response_completeness": response_rate,
        "performance_grade": performance_grade,
        "performance_score": performance_score
    }

def main():
    print("=" * 60)
    print("🚀 FLOATCHAT SEQUENTIAL EVALUATION")
    print("=" * 60)
    print("\n📊 This will run queries ONE AT A TIME to avoid parallel execution errors")
    print("⏱️  Expected time: 30-60 seconds for 10 queries\n")
    
    # Test queries
    test_queries = [
        "Show me all float IDs",
        "What is the average temperature in Arabian Sea?",
        "Average salinity in Bay of Bengal",
        "Calculate thermocline depth in Bay of Bengal",
        "Identify water masses in Arabian Sea",
        "Compare Arabian Sea vs Bay of Bengal temperature",
        "Find floats near 15°N, 65°E",
        "Show recent data from October 2025",
        "Analyze float 2902696 statistics",
        "What is the database schema?"
    ]
    
    print(f"🔧 Running {len(test_queries)} test queries sequentially...\n")
    
    # Run each query
    results = []
    total_start = time.time()
    
    for i, query in enumerate(test_queries, 1):
        result = evaluate_single_query(query, i, len(test_queries))
        results.append(result)
        
        # Small pause between queries to avoid overwhelming the system
        if i < len(test_queries):
            time.sleep(0.5)
    
    total_time = time.time() - total_start
    
    # Calculate quality metrics
    print(f"\n{'='*60}")
    print("📊 EVALUATION COMPLETE!")
    print(f"{'='*60}")
    
    metrics = evaluate_quality(results)
    
    # Display summary
    print(f"\n⏱️  Total Evaluation Time: {total_time:.2f} seconds")
    print(f"\n📈 RESULTS SUMMARY:")
    print(f"{'='*60}")
    print(f"Total Queries:           {metrics['total_queries']}")
    print(f"✅ Successful:           {metrics['successful']}")
    print(f"❌ Failed:               {metrics['failed']}")
    print(f"\n📊 QUALITY METRICS:")
    print(f"{'='*60}")
    print(f"Execution Success Rate:  {metrics['success_rate']:.1f}% ", end="")
    if metrics['success_rate'] >= 90:
        print("✅ Excellent")
    elif metrics['success_rate'] >= 80:
        print("✅ Good")
    elif metrics['success_rate'] >= 70:
        print("⚠️  Acceptable")
    else:
        print("❌ Needs Improvement")
    
    print(f"SQL Generation Rate:     {metrics['sql_generation_rate']:.1f}% ", end="")
    if metrics['sql_generation_rate'] >= 90:
        print("✅")
    elif metrics['sql_generation_rate'] >= 70:
        print("⚠️")
    else:
        print("❌")
    
    print(f"Response Completeness:   {metrics['response_completeness']:.1f}% ", end="")
    if metrics['response_completeness'] >= 90:
        print("✅")
    elif metrics['response_completeness'] >= 70:
        print("⚠️")
    else:
        print("❌")
    
    print(f"Average Response Time:   {metrics['avg_execution_time']:.2f}s ({metrics['performance_grade']}) ", end="")
    if metrics['performance_score'] >= 85:
        print("✅")
    elif metrics['performance_score'] >= 70:
        print("⚠️")
    else:
        print("❌")
    
    # Overall score
    overall_score = (
        metrics['success_rate'] * 0.4 +
        metrics['sql_generation_rate'] * 0.2 +
        metrics['response_completeness'] * 0.2 +
        metrics['performance_score'] * 0.2
    )
    
    print(f"\n{'='*60}")
    print(f"🎯 OVERALL SCORE: {overall_score:.1f}/100 ", end="")
    if overall_score >= 90:
        print("🏆 EXCELLENT")
    elif overall_score >= 80:
        print("✅ GOOD")
    elif overall_score >= 70:
        print("⚠️  ACCEPTABLE")
    else:
        print("❌ NEEDS IMPROVEMENT")
    print(f"{'='*60}")
    
    # Detailed results
    print(f"\n📋 DETAILED RESULTS:")
    print(f"{'='*60}")
    for i, result in enumerate(results, 1):
        status = "✅" if result["success"] else "❌"
        print(f"{i}. {status} {result['query']}")
        print(f"   Time: {result['execution_time']:.2f}s | Response: {result['response_length']} chars | SQL: {'Yes' if result['has_sql'] else 'No'}")
        if not result["success"]:
            print(f"   Error: {result['error'][:80]}...")
    
    # LangSmith traces
    print(f"\n{'='*60}")
    print("🔍 LANGSMITH TRACES")
    print(f"{'='*60}")
    print("All queries were traced and logged to LangSmith!")
    print("\n📊 View detailed traces at:")
    print("   https://smith.langchain.com/")
    print("   → Projects → FloatChat-Development")
    print(f"\n💡 You should see {len(results)} traces from this evaluation run.")
    
    # Recommendations
    print(f"\n{'='*60}")
    print("💡 RECOMMENDATIONS")
    print(f"{'='*60}")
    
    if metrics['success_rate'] < 100:
        print("⚠️  Some queries failed. Check error messages above.")
        print("   Common issues: Database connection, API limits, missing data")
    
    if metrics['avg_execution_time'] > 5.0:
        print("⚠️  Response time is slow (>5 seconds)")
        print("   Consider: Database indexing, caching, or query optimization")
    
    if metrics['success_rate'] >= 90 and metrics['avg_execution_time'] < 5.0:
        print("✅ Excellent! Your RAG pipeline is working well!")
        print("   → LangSmith monitoring is active")
        print("   → All queries are being traced")
        print("   → Performance is good")
    
    print(f"\n{'='*60}")
    print("✨ Evaluation complete! Check LangSmith for detailed traces.")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Evaluation interrupted by user (Ctrl+C)")
        print("Partial results may be available in LangSmith.")
    except Exception as e:
        print(f"\n\n❌ Evaluation failed with error:")
        print(f"   {str(e)}")
        print("\n🔍 Troubleshooting:")
        print("   - Check database connection")
        print("   - Verify LANGCHAIN_API_KEY in .env")
        print("   - Ensure all dependencies are installed")
