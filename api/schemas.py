"""Request and response models for the FloatChat API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

MAX_MESSAGE_LENGTH = 1000
MAX_HISTORY_TURNS = 40
MAX_BATCH_QUERIES = 10


class ChatTurn(BaseModel):
    role: str = Field(..., max_length=20)
    content: str = Field("", max_length=20000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    conversation_history: List[ChatTurn] = Field(default_factory=list, max_length=MAX_HISTORY_TURNS)


class ChatResponse(BaseModel):
    success: bool
    response: str
    intent: str = "data_query"
    sql: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    # Rows the SQL returned; `data` carries at most the first 500 of them.
    result_count: int = 0
    execution_time: float = 0.0
    # How the SQL was produced: "rules" or "llm".
    route: Optional[str] = None
    # One line saying how the question was understood (rule-built queries).
    interpretation: Optional[str] = None
    # Totals over everything the filters matched, when the rows are a LIMITed sample.
    summary: Optional[Dict[str, Any]] = None
    # Thermocline / water-mass results, when the question asked for them.
    analysis: Optional[Dict[str, Any]] = None
    cached: bool = False
    error: Optional[str] = None


class QueryRequest(BaseModel):
    """Query request model"""
    query: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    limit: int = Field(1000, ge=1, le=10000)
    use_cache: bool = True


class BatchQueryRequest(BaseModel):
    """Batch query request"""
    queries: List[str] = Field(..., min_length=1, max_length=MAX_BATCH_QUERIES)
    parallel: bool = False


class SavedQuery(BaseModel):
    """Saved query model"""
    name: str
    description: str
    query: str
    tags: List[str] = []


class ExportRequest(BaseModel):
    """Export request model"""
    format: str = "csv"  # csv, json, parquet
    include_analysis: bool = False
