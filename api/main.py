"""
FastAPI Server for FloatChat Backend.
Provides:
    - /api/v1/chat       — Full conversational RAG pipeline
    - /api/v1/suggestions — Query suggestions
    - /api/v1/pipeline-stats — RAG component statistics
    - /api/v1/health     — Server healthcheck
"""

import sys
import os
from pathlib import Path

# Ensure project root is on the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import time
import logging
import traceback

from api.routes import router as existing_router
from rag_engine.query_processor import QueryProcessor
from rag_engine.response_generator import ResponseGenerator
from rag_engine.intent_classifier import IntentClassifier

logger = logging.getLogger(__name__)

app = FastAPI(
    title="FloatChat API",
    description="AI-powered conversational interface for ARGO ocean data",
    version="2.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(existing_router)

# Lazy singletons
_query_processor: Optional[QueryProcessor] = None
_response_generator: Optional[ResponseGenerator] = None
_intent_classifier: Optional[IntentClassifier] = None


def get_query_processor() -> QueryProcessor:
    global _query_processor
    if _query_processor is None:
        _query_processor = QueryProcessor()
    return _query_processor


def get_response_generator() -> ResponseGenerator:
    global _response_generator
    if _response_generator is None:
        _response_generator = ResponseGenerator()
    return _response_generator


def get_intent_classifier() -> IntentClassifier:
    global _intent_classifier
    if _intent_classifier is None:
        _intent_classifier = IntentClassifier()
    return _intent_classifier


# Request / Response models
class ChatRequest(BaseModel):
    message: str
    conversation_history: List[Dict[str, str]] = []


class ChatResponse(BaseModel):
    success: bool
    response: str
    intent: str = "data_query"
    sql: Optional[str] = None
    data: Optional[List[Dict]] = None
    result_count: int = 0
    execution_time: float = 0.0
    route: Optional[str] = None
    error: Optional[str] = None


def _rewrite_with_context(
    user_message: str,
    conversation_history: List[Dict[str, str]],
) -> str:
    """Rewrite a vague follow-up into a self-contained query using conversation context.

    This is the production fix for the follow-up problem: when a user asks
    "tell me for oct 12 how many data you have?" and then follows up with
    "how many data for each day", the second question is ambiguous — does
    "each day" mean each day *within Oct 12* (nonsensical) or *across the
    entire dataset*?  In real conversation it clearly means the latter, but
    the SQL pipeline has no memory.  This function rewrites the follow-up
    into a complete, unambiguous query the pipeline can execute correctly.

    Rules:
    - Only triggers when the message is short (< 15 words) AND conversation
      history exists AND the message lacks explicit dates/regions.
    - Uses a fast, low-temperature LLM call with strict instructions.
    - If rewriting fails for any reason, returns the original message.
    """
    if not conversation_history:
        return user_message

    # Quick heuristic: only short, vague messages need rewriting.
    word_count = len(user_message.split())
    if word_count > 15:
        return user_message

    # If the message already contains explicit constraints, skip rewriting.
    import re
    has_explicit_date = bool(re.search(
        r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}\b",
        user_message, re.IGNORECASE,
    ))
    has_explicit_region = bool(re.search(
        r"\b(?:arabian|bengal|andaman|red\s+sea|indian\s+ocean|equatorial|southern)\b",
        user_message, re.IGNORECASE,
    ))
    if has_explicit_date and has_explicit_region:
        return user_message

    # Build a compact conversation summary (last 4 turns).
    recent = conversation_history[-4:]
    turns = []
    for msg in recent:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Truncate long assistant responses to save tokens.
        if role == "assistant" and len(content) > 200:
            content = content[:200] + "…"
        turns.append(f"{role}: {content}")
    convo_text = "\n".join(turns)

    prompt = f"""You rewrite vague follow-up questions into self-contained ARGO oceanographic data queries.

CONVERSATION SO FAR:
{convo_text}

NEW USER MESSAGE: "{user_message}"

RULES:
1. If the new message is already clear and self-contained, return it UNCHANGED.
2. If it is a follow-up that refers to the previous conversation, rewrite it into a SINGLE self-contained query.
3. CRITICAL: If the user says "each day", "all days", "every day", "all data", "for all", "entire dataset", etc. — they want to REMOVE any date/region filter from the previous question, NOT keep it. The rewritten query must NOT include the previous date constraint.
4. Preserve the user's intent exactly. Do not add constraints they didn't ask for.
5. Return ONLY the rewritten query text, nothing else. No explanation, no quotes, no markdown.

REWRITTEN QUERY:"""

    try:
        import os
        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return user_message

        client = Groq(api_key=api_key, timeout=10, max_retries=1)
        resp = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_completion_tokens=150,
        )
        rewritten = resp.choices[0].message.content.strip()

        # Sanity check: don't accept empty or suspiciously long rewrites.
        if not rewritten or len(rewritten) > 500:
            return user_message

        # Strip wrapping quotes if the LLM added them.
        if (rewritten.startswith('"') and rewritten.endswith('"')) or \
           (rewritten.startswith("'") and rewritten.endswith("'")):
            rewritten = rewritten[1:-1].strip()

        logger.info(f"🔄 Query rewritten: '{user_message}' → '{rewritten}'")
        return rewritten

    except Exception as e:
        logger.warning(f"Query rewrite failed (using original): {e}")
        return user_message


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Full chat pipeline:
    1. Classify intent (greeting/help/data_query)
    2. If data_query → rewrite follow-ups into self-contained queries
    3. Run enhanced RAG pipeline
    4. Generate natural language response
    5. Return response + data + SQL
    """
    start_time = time.time()
    user_message = request.message.strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="Empty message")

    try:
        classifier = get_intent_classifier()

        # Step 1: Classify intent
        intent_result = classifier.classify_intent(
            user_message, request.conversation_history
        )
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

        # Step 3: Rewrite vague follow-ups into self-contained queries
        effective_query = _rewrite_with_context(
            user_message, request.conversation_history
        )

        # Step 4: RAG pipeline execution
        processor = get_query_processor()
        result = processor.process_query(effective_query)

        if not result["success"]:
            return ChatResponse(
                success=False,
                response=f"I couldn't process that query. {result.get('error', 'Please try rephrasing your question.')}",
                intent="data_query",
                sql=result.get("sql"),
                error=result.get("error"),
                execution_time=time.time() - start_time,
            )

        # Step 5: AI Response Generation
        response_gen = get_response_generator()
        results_df = result["results"]
        sql_query = result.get("sql", "")

        similar = result.get("similar_profiles", [])
        context = ""
        if similar:
            context_parts = [f"{i}. {m.get('summary_text', '')}" for i, (_, m) in enumerate(similar[:3], 1)]
            context = "\n".join(context_parts)

        try:
            ai_response = response_gen.generate_response(user_message, results_df, context)
        except Exception as resp_err:
            logger.warning(f"Response generation error: {resp_err}")
            ai_response = f"Found {len(results_df)} records matching your query."

        # Step 6: Data Serialization
        data_records = None
        if not results_df.empty:
            df_serializable = results_df.head(500).copy()
            def _clean_field_val(val):
                if isinstance(val, bytes):
                    try:
                        return val.decode("utf-8").strip()
                    except Exception:
                        return str(val).strip()
                if isinstance(val, str):
                    s = val.strip()
                    if (s.startswith("b'") and s.endswith("'")) or (s.startswith('b"') and s.endswith('"')):
                        return s[2:-1].strip()
                    return s
                return val

            for col in df_serializable.columns:
                if df_serializable[col].dtype == "datetime64[ns]":
                    df_serializable[col] = df_serializable[col].astype(str)
                elif df_serializable[col].dtype == "object":
                    df_serializable[col] = df_serializable[col].apply(_clean_field_val)
                elif hasattr(df_serializable[col].dtype, "kind") and df_serializable[col].dtype.kind == "f":
                    df_serializable[col] = df_serializable[col].round(4)

            data_records = df_serializable.to_dict("records")

        return ChatResponse(
            success=True,
            response=ai_response,
            intent="data_query",
            sql=sql_query,
            data=data_records,
            result_count=len(results_df),
            execution_time=time.time() - start_time,
            route=result.get("route"),
        )

    except Exception as e:
        logger.error(f"Chat endpoint error: {traceback.format_exc()}")
        return ChatResponse(
            success=False,
            response=f"Sorry, an error occurred: {str(e)}",
            error=str(e),
            execution_time=time.time() - start_time,
        )


@app.get("/api/v1/pipeline-stats")
async def pipeline_stats():
    """Return component statistics."""
    try:
        processor = get_query_processor()
        return {"success": True, "stats": processor.get_pipeline_stats()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/v1/suggestions")
async def get_suggestions():
    """Return suggested queries."""
    return {
        "suggestions": [
            {"text": "Show temperature in Arabian Sea", "category": "geographic"},
            {"text": "Compare Arabian Sea and Bay of Bengal", "category": "comparison"},
            {"text": "How many floats are there?", "category": "statistics"},
            {"text": "Show profiles deeper than 1000 meters", "category": "depth"},
            {"text": "Show temperature profile for float 2902696", "category": "float"},
            {"text": "Find dissolved oxygen data", "category": "bgc"},
        ]
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "FloatChat Backend API v2.0",
        "components": {
            "query_processor": _query_processor is not None,
            "response_generator": _response_generator is not None,
            "intent_classifier": _intent_classifier is not None,
        },
    }
