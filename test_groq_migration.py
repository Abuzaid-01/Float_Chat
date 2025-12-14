import sys
import os
import pandas as pd

# Add the current directory to sys.path to ensure imports work
sys.path.append(os.getcwd())

try:
    from rag_engine.response_generator import ResponseGenerator
    from rag_engine.sql_generator import EnhancedSQLGenerator
    print("✅ Successfully imported modules")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

def test_response_generator():
    print("\n--- Testing ResponseGenerator ---")
    try:
        rg = ResponseGenerator()
        
        # Mock data
        df = pd.DataFrame({
            'float_id': ['123', '456'],
            'temperature': [20.5, 21.0],
            'pressure': [10, 20]
        })
        
        response = rg.generate_response(
            question="What is the average temperature?",
            query_results=df,
            context="Test context"
        )
        print("✅ Response received:")
        print(response[:200] + "...")
    except Exception as e:
        print(f"❌ ResponseGenerator failed: {e}")

def test_sql_generator():
    print("\n--- Testing EnhancedSQLGenerator ---")
    try:
        sg = EnhancedSQLGenerator()
        
        sql = sg.generate_sql(
            user_query="Show me recent floats in the Arabian Sea",
            context=""
        )
        print("✅ SQL generated:")
        print(sql)
        
        explanation = sg.explain_query(sql)
        print("✅ Explanation generated:")
        print(explanation[:200] + "...")
        
    except Exception as e:
        print(f"❌ EnhancedSQLGenerator failed: {e}")

if __name__ == "__main__":
    test_response_generator()
    test_sql_generator()
