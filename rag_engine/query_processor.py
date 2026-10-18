"""
Main Production RAG Pipeline Processor for FloatChat.
Features:
- Domain-aware query expansion
- Sub-second Semantic Caching
- Deterministic Template routing (LLM bypass)
- Hybrid Retrieval (FAISS vector embeddings + BM25 keyword matching + RRF)
- Few-shot Example Injection with Dynamic Promotion
- Query Planning for complex comparative/multi-condition requests
- Self-Correction Retry Loop (relax QC, widen bounds on 0 results)
"""

from typing import Dict, List, Tuple, Optional
import pandas as pd
import time
import re
import logging
from sqlalchemy import text

from database.db_setup import DatabaseSetup
from vector_store.vector_db import FAISSVectorStore
from vector_store.embeddings import EmbeddingGenerator
from rag_engine.sql_generator import EnhancedSQLGenerator
from rag_engine.domain_utils import expand_query
from rag_engine.semantic_cache import SemanticCache
from rag_engine.example_store import ExampleStore
from rag_engine.query_planner import QueryPlanner
from rag_engine.query_router import QueryRouter
from rag_engine.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)


class QueryProcessor:
    """
    Production-grade RAG pipeline processor.
    """

    def __init__(self):
        self.db_setup = DatabaseSetup()
        self.vector_store = FAISSVectorStore()
        self.vector_store.load()
        self.embedding_generator = EmbeddingGenerator()
        self.sql_generator = EnhancedSQLGenerator()

        # Hybrid retriever: FAISS (semantic) + BM25 (keyword) + RRF
        self.hybrid_retriever = HybridRetriever(self.vector_store)

        # Semantic cache
        self.semantic_cache = SemanticCache(
            similarity_threshold=0.95,
            max_entries=200,
            ttl_seconds=1800,
        )

        # Example store
        self.example_store = ExampleStore()
        self.example_store.initialize()

        # Query planner & router
        self.query_planner = QueryPlanner()
        self.query_router = QueryRouter()

        logger.info("✅ Enhanced QueryProcessor initialized (production mode)")

    def process_query(self, user_query: str, top_k: int = 3) -> Dict:
        """
        Complete RAG pipeline execution.
        """
        start_time = time.time()

        print(f"\n{'='*60}")
        print(f"🔍 Processing Query: {user_query}")
        print(f"{'='*60}")

        # Step 0: Domain expansion
        print("\n📚 Step 0: Expanding query with domain knowledge...")
        expanded_query = expand_query(user_query)

        # Step 1: Semantic cache check
        print("\n💾 Step 1: Checking semantic cache...")
        query_embedding = self.embedding_generator.generate_embedding(expanded_query)
        cached = self.semantic_cache.check(query_embedding)
        if cached:
            execution_time = time.time() - start_time
            print(f"⚡ Cache HIT! Returning cached result in {execution_time:.2f}s")
            results_df, error = self._execute_sql(cached["sql"])
            if not error:
                return {
                    "success": True,
                    "query": user_query,
                    "sql": cached["sql"],
                    "results": results_df,
                    "result_count": len(results_df),
                    "similar_profiles": [],
                    "execution_time": execution_time,
                    "cache_hit": True,
                    "route": "cache",
                }

        # Step 2: Route query
        print("\n🚦 Step 2: Routing query...")
        route = self.query_router.classify(user_query)
        print(f"   Route: {route['route']} — {route['reason']}")

        # Template route: instant 0ms SQL execution
        if route["route"] == "template":
            return self._handle_template_route(user_query, route, query_embedding, start_time)

        # RAG routes (simple_rag or complex_rag)
        return self._handle_rag_route(
            user_query,
            expanded_query,
            route,
            query_embedding,
            top_k,
            start_time,
        )

    def _handle_template_route(
        self,
        user_query: str,
        route: Dict,
        query_embedding,
        start_time: float,
    ) -> Dict:
        sql_query = route["template_sql"]
        print(f"🚀 Template SQL: {sql_query}")

        results_df, error = self._execute_sql(sql_query)
        execution_time = time.time() - start_time

        if error:
            return {
                "success": False,
                "error": error,
                "query": user_query,
                "sql": sql_query,
            }

        self.semantic_cache.store(user_query, query_embedding, sql_query, len(results_df))

        return {
            "success": True,
            "query": user_query,
            "sql": sql_query,
            "results": results_df,
            "result_count": len(results_df),
            "similar_profiles": [],
            "execution_time": execution_time,
            "route": "template",
        }

    def _handle_rag_route(
        self,
        user_query: str,
        expanded_query: str,
        route: Dict,
        query_embedding,
        top_k: int,
        start_time: float,
    ) -> Dict:
        is_complex = route["route"] == "complex_rag"

        # Step 3: Planning
        query_plan = None
        if is_complex:
            print("\n🧠 Step 3: Planning complex query...")
            query_plan = self.query_planner.plan(user_query)

        # Step 4: Hybrid search (FAISS + BM25 + RRF)
        print("\n🔍 Step 4: Hybrid search (semantic + keyword)...")
        similar_profiles = self.hybrid_retriever.search(
            query_text=expanded_query,
            query_embedding=query_embedding,
            k=top_k,
        )
        context = self._format_context(similar_profiles)
        print(f"   Found {len(similar_profiles)} profiles (hybrid FAISS+BM25)")

        # Step 5: Few-shot examples
        print("\n📋 Step 5: Retrieving few-shot examples...")
        examples = self.example_store.get_similar_examples(expanded_query, k=3)

        # Step 6: Generate SQL
        print("\n🔧 Step 6: Generating SQL query...")
        sql_query = self.sql_generator.generate_sql(
            user_query,
            context,
            few_shot_examples=examples if examples else None,
            query_plan=query_plan,
        )

        if not sql_query or not self.sql_generator.validate_sql(sql_query):
            return {
                "success": False,
                "error": "Could not generate valid SQL query",
                "query": user_query,
            }

        # Step 7: Execute SQL
        print("\n💾 Step 7: Executing database query...")
        results_df, error = self._execute_sql(sql_query)

        if error:
            return {
                "success": False,
                "error": error,
                "query": user_query,
                "sql": sql_query,
            }

        # Step 8: Self-correction retry if 0 results
        if len(results_df) == 0:
            print("\n🔄 Step 8: Zero results — attempting self-correction...")
            results_df, sql_query, error = self._retry_with_relaxed(
                user_query, sql_query, context, examples, query_plan
            )
            if error:
                return {
                    "success": False,
                    "error": error,
                    "query": user_query,
                    "sql": sql_query,
                }

        execution_time = time.time() - start_time
        result_count = len(results_df)

        # Cache & self-improve
        self.semantic_cache.store(user_query, query_embedding, sql_query, result_count)
        if result_count > 0:
            self.example_store.promote_from_logs(user_query, sql_query, result_count)

        print(f"\n✅ Query completed in {execution_time:.2f}s")
        print(f"📈 Retrieved {result_count} records")

        return {
            "success": True,
            "query": user_query,
            "sql": sql_query,
            "results": results_df,
            "result_count": result_count,
            "similar_profiles": similar_profiles,
            "execution_time": execution_time,
            "route": route["route"],
        }

    def _retry_with_relaxed(
        self,
        user_query: str,
        original_sql: str,
        context: str,
        examples: List[Dict],
        query_plan: Optional[Dict],
    ) -> Tuple[pd.DataFrame, str, Optional[str]]:
        """Self-correction: retry SQL with relaxed QC and widened bounds."""
        instructions = (
            "RELAXATION: Previous query returned 0 results. "
            "Remove strict QC filters or use temp_qc IN (1,2,3,4). "
            "Also widen spatial bounds by 5 degrees."
        )
        relaxed_context = f"{context}\n\n{instructions}\n\nPrevious SQL that returned 0 results:\n{original_sql}"
        relaxed_sql = self.sql_generator.generate_sql(
            user_query,
            relaxed_context,
            force_regenerate=True,
            few_shot_examples=examples,
            query_plan=query_plan,
        )
        if relaxed_sql and self.sql_generator.validate_sql(relaxed_sql):
            results_df, error = self._execute_sql(relaxed_sql)
            if not error and len(results_df) > 0:
                print(f"   ✅ Self-correction succeeded: {len(results_df)} records")
                return results_df, relaxed_sql, None

        return pd.DataFrame(), original_sql, None

    def _format_context(self, similar_profiles: List[Tuple[float, dict]]) -> str:
        parts = []
        for i, (score, metadata) in enumerate(similar_profiles, 1):
            parts.append(f"{i}. {metadata.get('summary_text', 'No summary available')}")
        return "\n".join(parts)

    def _execute_sql(self, sql_query: str) -> Tuple[pd.DataFrame, Optional[str]]:
        session = self.db_setup.get_session()
        try:
            result = session.execute(text(sql_query))
            rows = result.fetchall()
            if len(rows) == 0:
                return pd.DataFrame(), None
            columns = result.keys()
            df = pd.DataFrame(rows, columns=columns)
            return df, None
        except Exception as e:
            error_msg = f"SQL execution error: {str(e)}"
            print(f"❌ {error_msg}")
            return pd.DataFrame(), error_msg
        finally:
            session.close()

    def get_statistics(self, df: pd.DataFrame) -> Dict:
        if df.empty:
            return {}
        stats = {"record_count": len(df), "columns": list(df.columns)}
        numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns
        for col in numeric_cols:
            stats[col] = {
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
            }
        return stats

    def get_pipeline_stats(self) -> Dict:
        return {
            "cache": self.semantic_cache.get_stats(),
            "example_store": self.example_store.get_stats(),
            "sql_generator": self.sql_generator.get_statistics(),
            "router_templates": self.query_router.get_template_count(),
            "hybrid_retriever": self.hybrid_retriever.get_stats(),
        }
