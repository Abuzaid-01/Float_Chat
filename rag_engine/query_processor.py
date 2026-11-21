"""Query the ARGO archive through rules or retrieval-augmented SQL generation."""

from collections import OrderedDict
from datetime import datetime
import logging
from threading import Lock
import time

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database.db_setup import DatabaseSetup
from rag_engine.domain_utils import expand_query
from rag_engine.query_parser import FOLLOW_UP, build_query, resolve_with_history
from rag_engine.query_planner import QueryPlanner
from rag_engine.serialization import to_jsonable

logger = logging.getLogger(__name__)

_SQL_CACHE_SIZE = 128
_ARCHIVE_TTL = 300
_SQL_CACHE_TTL = 900
_MAX_QUERY_ROWS = 10000


class QueryProcessor:
    """Use deterministic SQL where possible and query PostgreSQL for every answer."""

    def __init__(self, db_setup: DatabaseSetup | None = None):
        self.db_setup = db_setup or DatabaseSetup()
        self.query_planner = QueryPlanner()
        self._retrieval_lock = Lock()
        self._range_lock = Lock()
        self._stats_lock = Lock()
        self._dataset_range = None
        self._sql_cache = OrderedDict()
        self._retrieval = None
        self._sql_generator = None
        self._stats = {"total_queries": 0, "rule_built": 0, "llm_built": 0, "failed_queries": 0, "cache_hits": 0}

    def get_dataset_range(self):
        """Cache archive bounds briefly so relative dates share one data clock."""
        with self._range_lock:
            now = time.monotonic()
            if self._dataset_range is not None and self._dataset_range[0] > now:
                return self._dataset_range[1]
            rows, error = self._execute_sql("SELECT MIN(timestamp) AS earliest, MAX(timestamp) AS latest FROM argo_profiles;")
            if error:
                raise RuntimeError(error)
            bounds = tuple(
                datetime.fromisoformat(value) if isinstance(value, str) else value
                for value in (rows.iloc[0]["earliest"], rows.iloc[0]["latest"])
            )
            self._dataset_range = (now + _ARCHIVE_TTL, bounds)
            return bounds

    def warm_retrieval(self):
        """Load the local archive index once. The deterministic path stays independent."""
        with self._retrieval_lock:
            if self._retrieval is None:
                from rag_engine.example_store import ExampleStore
                from rag_engine.hybrid_retriever import HybridRetriever
                from vector_store.embeddings import EmbeddingGenerator
                from vector_store.vector_db import FAISSVectorStore

                store = FAISSVectorStore()
                if not store.load() or store.index.ntotal == 0:
                    raise RuntimeError("The ARGO profile index is missing or empty.")
                embeddings = EmbeddingGenerator()
                examples = ExampleStore(embeddings)
                examples.initialize()
                self._retrieval = (store, embeddings, HybridRetriever(store), examples)
            return self._retrieval

    def _get_sql_generator(self):
        with self._retrieval_lock:
            if self._sql_generator is None:
                from rag_engine.sql_generator import EnhancedSQLGenerator

                self._sql_generator = EnhancedSQLGenerator()
            return self._sql_generator

    def process_query(
        self,
        user_query: str,
        top_k: int = 3,
        *,
        history: list[dict] | None = None,
        generate_answer: bool = True,
        use_cache: bool = True,
        analysis: str | None = None,
    ) -> dict:
        started = time.monotonic()
        question = user_query.strip()

        def failure(message, **fields):
            self._increment("failed_queries")
            return {"success": False, "query": question, "error": message, **fields}

        if not question or len(question) > 1000:
            return failure("Ask an ocean-data question between 1 and 1,000 characters.")
        self._increment("total_queries")
        previous = [
            turn["content"].strip()[:1000]
            for turn in (history or [])[-8:]
            if turn.get("role") == "user" and isinstance(turn.get("content"), str) and turn["content"].strip()
        ][-4:]

        try:
            earliest, latest = self.get_dataset_range()
        except RuntimeError as error:
            return failure(str(error))
        if latest is None:
            return failure("The measurement archive is empty.")

        spec = resolve_with_history(question, previous, latest)
        if analysis:
            if spec is None:
                return failure("Specify the region, float, cycle, or date for the profile analysis.")
            spec.intent = "profile_analysis"
            spec.analysis = analysis
        built = build_query(spec) if spec is not None else None
        route = "rules" if built else "llm"
        similar = []
        cached = False
        summary_sql = built.summary_sql if built else None

        if built is not None:
            statement = built.sql
            interpretation = built.description
            self._increment("rule_built")
        else:
            # Preserve exact date, ID and pressure constraints in an LLM cache key.
            # Prior turns are only relevant to a question that refers to them.
            follow_up = previous if FOLLOW_UP.search(question.lower()) else []
            top_k = max(1, min(int(top_k), 10))
            key = (question, tuple(follow_up), top_k, earliest, latest)
            entry = self._read_cache(key) if use_cache else None
            if entry is None:
                try:
                    generator = self._get_sql_generator()
                    statement, similar = self._build_model_query(
                        generator, question, follow_up, earliest, latest, top_k
                    )
                except (RuntimeError, ImportError, OSError) as error:
                    logger.warning("Free-form query unavailable: %s", type(error).__name__)
                    return failure("Free-form search is unavailable. Try a float ID, named region, or explicit date range.")
                if not statement or not generator.validate_sql(statement):
                    return failure("The model did not produce an executable archive query. Try a more specific question.")
                self._increment("llm_built")
            else:
                statement, similar = entry
                cached = True
                self._increment("cache_hits")
            interpretation = None

        rows, error = self._execute_sql(statement, summary_sql)
        if error:
            return failure(error, sql=statement, route=route)

        # _execute_sql returns the summary as dataframe attributes from the same transaction.
        summary = rows.attrs.get("summary")
        if route == "llm" and use_cache and not cached and not rows.empty:
            self._store_cache(key, (statement, similar))

        profile_analysis = None
        if built is not None and built.kind == "profile_analysis":
            profile_analysis = self._analyze_profile(rows, spec.analysis)

        response = None
        if generate_answer:
            response = self._answer(rows, summary, spec if built else None, profile_analysis)

        return {
            "success": True,
            "query": question,
            "sql": statement,
            "results": rows,
            "result_count": len(rows),
            "route": route,
            "kind": built.kind if built else "model_query",
            "interpretation": interpretation,
            "summary": to_jsonable(summary),
            "analysis": to_jsonable(profile_analysis),
            "similar_profiles": similar,
            "retrieval": self._retrieval_sources(similar),
            "response": response,
            "cached": cached,
            "cache_hit": cached,
            "execution_time": time.monotonic() - started,
        }

    def _build_model_query(self, generator, question, history, earliest, latest, top_k):
        _, embeddings, retriever, examples = self.warm_retrieval()
        search_query = expand_query(" ".join([*history[-1:], question]))
        embedding = embeddings.generate_embedding(search_query)
        similar = retriever.search(search_query, embedding, k=top_k)
        context = [f"Archive coverage: {earliest.isoformat()} through {latest.isoformat()}."]
        if history:
            context.append("Earlier user questions, oldest first:\n" + "\n".join(history))
        context.extend(
            f"Profile summary {index}: {meta.get('summary_text', '')[:1000]}"
            for index, (_, meta) in enumerate(similar, 1)
        )
        sql = generator.generate_sql(
            question,
            "\n".join(context),
            few_shot_examples=examples.get_similar_examples(search_query, k=3),
            query_plan=self.query_planner.plan(question),
        )
        return sql, similar

    @staticmethod
    def _retrieval_sources(similar):
        return [
            {
                "float_id": to_jsonable(meta.get("float_id")),
                "cycle_number": to_jsonable(meta.get("cycle_number")),
                "timestamp": to_jsonable(meta.get("timestamp")),
                "summary": meta.get("summary_text", ""),
                "rank": rank,
            }
            for rank, (_, meta) in enumerate(similar, 1)
        ]

    def _execute_sql(self, statement, summary_statement=None):
        try:
            with self.db_setup.engine.begin() as connection:
                if connection.dialect.name == "postgresql":
                    connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                    connection.exec_driver_sql("SET LOCAL statement_timeout = '12s'")
                    connection.exec_driver_sql("SET LOCAL search_path = pg_catalog, public, pg_temp")
                result = connection.execute(text(statement))
                rows = pd.DataFrame(result.fetchmany(_MAX_QUERY_ROWS), columns=list(result.keys()))
                if summary_statement:
                    summary = connection.execute(text(summary_statement)).mappings().one()
                    rows.attrs["summary"] = dict(summary)
                return rows, None
        except SQLAlchemyError as error:
            logger.warning("Archive query failed: %s", type(error).__name__)
            return pd.DataFrame(), "The archive could not complete this query. Try a narrower question or retry shortly."

    def _analyze_profile(self, rows, kind):
        from advanced_analytics.profile_analytics import AdvancedProfileAnalytics

        if rows.empty:
            return {"type": kind, "success": False, "error": "No profile met the filters with enough usable readings."}
        analytics = AdvancedProfileAnalytics(self.db_setup)
        first = rows.iloc[0]
        profile = {column: first[column] for column in ("float_id", "cycle_number", "timestamp")}
        profile["measurements"] = len(rows)
        if kind == "water_masses":
            result = analytics.identify_water_masses_advanced(rows)
        else:
            result = analytics.calculate_thermocline_advanced(rows)
        return {**result, "type": kind, "profile": profile}

    @staticmethod
    def _answer(rows, summary, spec, analysis):
        if analysis:
            if not analysis["success"]:
                return analysis["error"]
            profile = analysis["profile"]
            subject = f"Float **{profile['float_id']}**, cycle **{profile['cycle_number']}**"
            if analysis["type"] == "water_masses":
                count = analysis["water_masses_detected"]
                return f"{subject}, matched **{count}** reference water-mass signatures using temperature, salinity, and pressure."
            thermocline = analysis["thermocline_depth_dbar"]
            mixed_layer = analysis["mixed_layer_depth_dbar"]
            answer = f"{subject}, has an estimated thermocline at **{thermocline:,.1f} dbar**."
            if mixed_layer is not None:
                answer += f" The estimated mixed-layer depth is **{mixed_layer:,.1f} dbar**."
            return answer
        if rows.empty:
            return "No observations matched those filters."
        if (
            spec and spec.intent == "compare" and 1 < len(rows) <= 4
            and "ocean_region" in rows and spec.group_by in (None, "region")
        ):
            comparison = []
            for row in to_jsonable(rows.to_dict("records")):
                values = []
                for column, unit in (("temperature", "°C"), ("salinity", "PSU"), ("pressure", "dbar")):
                    mean = row.get(f"average_{column}")
                    if mean is not None:
                        values.append(f"{column} **{mean:,.3f} {unit}**")
                if values:
                    comparison.append(f"{row['ocean_region'] or 'Unclassified region'} averaged " + " and ".join(values) + ".")
            if comparison:
                return "\n\n".join(comparison)
        if len(rows) == 1:
            values = to_jsonable(rows.to_dict("records")[0])
            if spec and spec.intent == "count" and not spec.group_by:
                label = spec.count_target
                column = {"floats": "float_count", "profiles": "profile_count", "measurements": "measurement_count"}[label]
                total = values[column]
                return f"**{total:,}** {label} match this question."
            if spec and spec.intent == "date_range":
                if values["earliest"] is None:
                    return "No observations matched those filters."
                return f"The observations run from **{values['earliest']}** to **{values['latest']}** (UTC)."
            if values.get("measurement_count") == 0:
                return "No observations matched those filters."
            fields = [
                f"{name.replace('_', ' ').capitalize()} **{value:,}**" if isinstance(value, int) else
                f"{name.replace('_', ' ').capitalize()} **{value:,.4f}**" if isinstance(value, float) else
                f"{name.replace('_', ' ').capitalize()} **{value}**"
                for name, value in values.items()
                if value is not None and name not in {"latitude", "longitude", "cycle_number", "float_id", "ocean_region"}
            ]
            if fields:
                return " · ".join(fields[:6])
        total = summary.get("total_matching") if summary else None
        if total is not None:
            answer = f"**{total:,}** measurements match the filters."
            if total > len(rows):
                answer += f" The query returned the newest **{len(rows):,}**."
            return answer
        label = "result rows" if len(rows) != 1 else "result row"
        return f"The archive returned **{len(rows):,}** {label}. Explore the values in the result panel."

    def _increment(self, key):
        with self._stats_lock:
            self._stats[key] += 1

    def _read_cache(self, key):
        with self._stats_lock:
            entry = self._sql_cache.pop(key, None)
            if entry and time.monotonic() < entry[0]:
                self._sql_cache[key] = entry
                return entry[1]
            return None

    def _store_cache(self, key, value):
        with self._stats_lock:
            self._sql_cache[key] = (time.monotonic() + _SQL_CACHE_TTL, value)
            self._sql_cache.move_to_end(key)
            if len(self._sql_cache) > _SQL_CACHE_SIZE:
                self._sql_cache.popitem(last=False)

    def get_statistics(self, df):
        if df.empty:
            return {}
        stats = {"record_count": len(df), "columns": list(df.columns)}
        for col in df.select_dtypes(include="number").columns:
            stats[col] = {name: float(getattr(df[col], name)()) for name in ("min", "max", "mean", "median")}
        return stats

    def get_pipeline_stats(self):
        with self._stats_lock:
            stats = dict(self._stats)
            cached = sum(expires > time.monotonic() for expires, _ in self._sql_cache.values())
        completed = max(stats["total_queries"], 1)
        stats["cache_hit_rate"] = f"{stats['cache_hits'] / completed:.1%}"
        stats["success_rate"] = f"{max(0, completed - stats['failed_queries']) / completed:.1%}"
        retrieval = self._retrieval
        return {
            "sql_generator": stats,
            "vector_store_loaded": retrieval is not None,
            "vector_count": retrieval[0].index.ntotal if retrieval else 0,
            "cached_results": cached,
        }
