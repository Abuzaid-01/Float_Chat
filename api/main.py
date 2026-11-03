"""
FastAPI Server for FloatChat Backend.
Provides:
    - /api/v1/chat           — Full conversational RAG pipeline
    - /api/v1/suggestions    — Query suggestions
    - /api/v1/pipeline-stats — RAG component statistics
    - /api/v1/health         — Server healthcheck
    - plus the data routes in api/routes.py

Endpoints are plain `def` functions on purpose: FastAPI runs those on a worker
thread pool, so a slow question (LLM + database) no longer blocks health
checks or other users.
"""

import sys
import os
from pathlib import Path

# Ensure project root is on the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from contextlib import asynccontextmanager
from datetime import datetime
from typing import List
import time
import logging
import traceback

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from api import deps
from api.middleware import RateLimitMiddleware
from api.routes import router as existing_router
from api.schemas import ChatRequest, ChatResponse
from rag_engine.serialization import dataframe_to_records

logger = logging.getLogger(__name__)

# Rows sent to the client per answer.  The SQL may return more (see result_count).
MAX_ROWS_IN_RESPONSE = 500


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start loading the embedding model and index now, without delaying startup.
    deps.warm_up()
    yield


app = FastAPI(
    title="FloatChat API",
    description="AI-powered conversational interface for ARGO ocean data",
    version="2.1.0",
    lifespan=lifespan,
)


def _cors_origins() -> List[str]:
    """Comma-separated CORS_ORIGINS, or any origin when unset (the API uses no cookies)."""
    configured = os.getenv("CORS_ORIGINS", "").strip()
    return [origin.strip() for origin in configured.split(",") if origin.strip()] or ["*"]


app.add_middleware(RateLimitMiddleware)
# Added last so it wraps everything, including rate-limit rejections.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(existing_router)


def get_query_processor():
    return deps.get_query_processor()


def get_intent_classifier():
    return deps.get_intent_classifier()


def _fallback_answer(result: dict) -> str:
    """Plain answer for when the LLM could not write one; the data is still returned."""
    count = result.get("result_count", 0)
    total = (result.get("summary") or {}).get("total_matching")
    if count == 0:
        return "No data matched this question. Try a different region, float, depth range or date."
    if total and total > count:
        return f"{total:,} measurements match; the newest {count:,} are shown in the table below."
    return f"Found {count:,} record{'s' if count != 1 else ''} matching your question. They are shown in the table below."


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Full chat pipeline:
    1. Classify intent (greeting/help/data_query)
    2. If data_query → run the RAG pipeline, with the conversation as context
    3. Return the answer together with the rows, the SQL and how it was understood
    """
    start_time = time.time()
    user_message = request.message.strip()
    history = [{"role": turn.role, "content": turn.content} for turn in request.conversation_history]

    if not user_message:
        return ChatResponse(success=False, response="Please type a question.", error="Empty message")

    try:
        # Step 1: Classify intent
        intent_result = get_intent_classifier().classify_intent(user_message, history)
        intent = intent_result.get("intent", "data_query")
        requires_data = intent_result.get("requires_data_query", True)

        # Step 2: Conversational response
        if not requires_data and intent_result.get("direct_response"):
            return ChatResponse(
                success=True,
                response=intent_result["direct_response"],
                intent=intent,
                execution_time=time.time() - start_time,
            )

        # Step 3: RAG pipeline (retrieval → SQL → database → grounded answer).
        # The pipeline writes the answer itself; it is not generated again here.
        result = get_query_processor().process_query(user_message, history=history)

        if not result["success"]:
            return ChatResponse(
                success=False,
                response=f"I couldn't process that query. {result.get('error', 'Please try rephrasing your question.')}",
                intent="data_query",
                sql=result.get("sql"),
                error=result.get("error"),
                execution_time=time.time() - start_time,
            )

        results_df = result["results"]
        return ChatResponse(
            success=True,
            response=result.get("response") or _fallback_answer(result),
            intent="data_query",
            sql=result.get("sql", ""),
            data=dataframe_to_records(results_df, MAX_ROWS_IN_RESPONSE) or None,
            result_count=len(results_df),
            execution_time=time.time() - start_time,
            route=result.get("route"),
            interpretation=result.get("interpretation"),
            summary=result.get("summary"),
            analysis=result.get("analysis"),
            cached=bool(result.get("cached")),
        )

    except Exception as e:
        logger.error(f"Chat endpoint error: {traceback.format_exc()}")
        return ChatResponse(
            success=False,
            response="Sorry, something went wrong while answering that. Please try again.",
            error=f"{type(e).__name__}: {str(e)[:300]}",
            execution_time=time.time() - start_time,
        )


@app.get("/api/v1/pipeline-stats")
def pipeline_stats():
    """Return component statistics."""
    try:
        processor = get_query_processor()
        return {"success": True, "stats": processor.get_pipeline_stats()}
    except Exception as e:
        return {"success": False, "error": str(e)}


_suggestion_cache = deps.TTLCache(ttl_seconds=3600)


def _example_float_id() -> str:
    """A float that really exists in the data, so the example questions always work."""
    cached = _suggestion_cache.get("float")
    if cached:
        return cached
    try:
        with deps.get_db().engine.connect() as connection:
            row = connection.execute(text(
                "SELECT float_id FROM argo_profiles "
                "WHERE float_id IS NOT NULL AND ocean_region = 'Arabian Sea' "
                "GROUP BY float_id ORDER BY COUNT(*) DESC LIMIT 1"
            )).fetchone()
            if row is None:
                row = connection.execute(text(
                    "SELECT float_id FROM argo_profiles WHERE float_id IS NOT NULL LIMIT 1"
                )).fetchone()
        if row:
            return _suggestion_cache.set("float", str(row[0]))
    except Exception as error:
        logger.warning(f"Could not pick an example float: {error}")
    return ""


@app.get("/api/v1/suggestions")
def get_suggestions():
    """Return suggested queries.  Each one is answerable from the current data."""
    suggestions = [
        {"text": "Show temperature in Arabian Sea", "category": "geographic"},
        {"text": "Compare Arabian Sea and Bay of Bengal", "category": "comparison"},
        {"text": "How many floats are there?", "category": "statistics"},
        {"text": "How does temperature change with depth in the Bay of Bengal?", "category": "depth"},
    ]
    float_id = _example_float_id()
    if float_id:
        suggestions += [
            {"text": f"Show temperature profile for float {float_id}", "category": "float"},
            {"text": f"Calculate thermocline depth for float {float_id}", "category": "analysis"},
        ]
    else:
        suggestions += [
            {"text": "Which region is the warmest?", "category": "comparison"},
            {"text": "What is the date range of the dataset?", "category": "statistics"},
        ]
    return {"suggestions": suggestions}


@app.get("/api/v1/health")
def health_check(deep: bool = False):
    """
    Health check.  Cheap by default; `?deep=true` also checks the database.
    """
    body = {
        "status": "healthy",
        "service": "FloatChat Backend API v2.1",
        "timestamp": datetime.now().isoformat(),
        "components": deps.loaded_components(),
    }
    if deep:
        try:
            with deps.get_db().engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            body["database"] = "reachable"
        except Exception as error:
            body["status"] = "degraded"
            body["database"] = f"unreachable: {str(error)[:200]}"
    return body
