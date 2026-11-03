"""
API tests.  The pipeline, the intent classifier and the database are replaced
by small fakes, so these run offline and make no LLM or database calls.
"""

from datetime import datetime
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import deps
from api.middleware import RateLimitMiddleware


class FakeProcessor:
    def __init__(self, result=None):
        self.calls = []
        self.result = result

    def process_query(self, query, top_k=3, history=None, generate_answer=True, use_cache=True):
        self.calls.append({"query": query, "history": history, "generate_answer": generate_answer})
        if self.result is not None:
            return self.result
        frame = pd.DataFrame({
            "float_id": ["2903956", "2903956"],
            "timestamp": [pd.Timestamp("2025-10-19 00:53:20")] * 2,
            "pressure": [np.float64(3.7), np.float64(5.8)],
            "temperature": [Decimal("28.809"), np.float64("nan")],
            "good": [np.bool_(True), np.bool_(False)],
        })
        return {
            "success": True, "query": query, "sql": "SELECT 1 FROM argo_profiles;", "results": frame,
            "result_count": len(frame), "response": "PIPELINE ANSWER" if generate_answer else None,
            "execution_time": 0.1, "route": "rules", "kind": "list",
            "interpretation": "Temperature measurements · Arabian Sea",
            "summary": {"total_matching": 89832, "rows_returned": 2}, "analysis": None, "cached": False,
        }

    def get_pipeline_stats(self):
        return {"vector_store_loaded": True}


class FakeClassifier:
    def classify_intent(self, query, history=None):
        if query.lower().startswith("hello"):
            return {"intent": "greeting", "requires_data_query": False, "direct_response": "Hi!"}
        return {"intent": "data_query", "requires_data_query": True, "direct_response": None}


class FakeRow:
    def __init__(self, **values):
        self.__dict__.update(values)


class FakeConnection:
    def __init__(self, log, row):
        self.log, self.row = log, row

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, statement, params=None):
        self.log.append({"sql": str(statement), "params": params})
        row = self.row

        class Result:
            def fetchone(self):
                return row

            def fetchall(self):
                return [] if row is None else [row]

        return Result()


class FakeDb:
    def __init__(self, row=None):
        self.log = []
        self.row = row
        self.engine = self

    def connect(self):
        return FakeConnection(self.log, self.row)


@pytest.fixture
def api(monkeypatch):
    """A TestClient wired to fakes.  Returns (client, processor, db)."""
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "0")
    import api.main as main

    processor, db = FakeProcessor(), FakeDb()
    monkeypatch.setattr(deps, "get_query_processor", lambda: processor)
    monkeypatch.setattr(deps, "get_intent_classifier", lambda: FakeClassifier())
    monkeypatch.setattr(deps, "get_db", lambda: db)
    # The limiter was built when the app was imported; switch it off for these tests.
    node = main.app.middleware_stack
    while node is not None:
        if isinstance(node, RateLimitMiddleware):
            monkeypatch.setattr(node, "limit", 0)
        node = getattr(node, "app", None)
    return TestClient(main.app), processor, db


class TestChat:
    def test_data_question_uses_the_pipeline_answer_once(self, api):
        client, processor, _ = api
        body = client.post("/api/v1/chat", json={"message": "Show temperature in Arabian Sea"}).json()
        assert body["success"] is True
        assert body["response"] == "PIPELINE ANSWER"
        # The answer comes from the single pipeline call; nothing regenerates it.
        assert len(processor.calls) == 1 and processor.calls[0]["generate_answer"] is True
        assert body["route"] == "rules"
        assert body["interpretation"].startswith("Temperature measurements")
        assert body["summary"]["total_matching"] == 89832

    def test_history_reaches_the_pipeline(self, api):
        client, processor, _ = api
        history = [{"role": "user", "content": "average temperature in the Arabian Sea"},
                   {"role": "assistant", "content": "11.6"}]
        client.post("/api/v1/chat", json={"message": "what about salinity there?", "conversation_history": history})
        assert processor.calls[0]["history"] == history

    def test_rows_are_json_safe(self, api):
        client, _, _ = api
        rows = client.post("/api/v1/chat", json={"message": "Show temperature"}).json()["data"]
        assert rows[0] == {"float_id": "2903956", "timestamp": "2025-10-19T00:53:20", "pressure": 3.7,
                           "temperature": 28.809, "good": True}
        assert rows[1]["temperature"] is None  # NaN must not leak into JSON

    def test_greeting_skips_the_pipeline(self, api):
        client, processor, _ = api
        body = client.post("/api/v1/chat", json={"message": "hello"}).json()
        assert body["intent"] == "greeting" and body["response"] == "Hi!"
        assert processor.calls == []

    def test_pipeline_failure_is_reported(self, api):
        client, processor, _ = api
        processor.result = {"success": False, "error": "Could not generate valid SQL query", "query": "x"}
        body = client.post("/api/v1/chat", json={"message": "Show temperature"}).json()
        assert body["success"] is False and "Could not generate" in body["error"]

    def test_missing_llm_answer_falls_back_to_a_plain_one(self, api):
        client, processor, _ = api
        result = processor.process_query("q")
        processor.result = {**result, "response": None}
        body = client.post("/api/v1/chat", json={"message": "Show temperature"}).json()
        assert body["success"] is True
        assert "89,832 measurements match" in body["response"]

    def test_unexpected_error_does_not_leak_a_traceback(self, api, monkeypatch):
        client, processor, _ = api
        monkeypatch.setattr(processor, "process_query", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        response = client.post("/api/v1/chat", json={"message": "Show temperature"})
        assert response.status_code == 200
        assert response.json()["success"] is False and "Traceback" not in response.text

    @pytest.mark.parametrize("payload", [{"message": ""}, {"message": "x" * 1001}, {}])
    def test_invalid_messages_are_rejected(self, api, payload):
        client, _, _ = api
        assert client.post("/api/v1/chat", json=payload).status_code == 422


class TestFloatLookup:
    @pytest.mark.parametrize("float_id", ["2903956' OR '1'='1", "abc", "1; DROP TABLE argo_profiles", "12"])
    def test_malformed_ids_never_reach_the_database(self, api, float_id):
        client, _, db = api
        assert client.get(f"/api/v1/floats/{float_id}").status_code == 400
        assert db.log == []

    def test_unknown_float_is_404(self, api):
        client, _, db = api
        assert client.get("/api/v1/floats/2902696").status_code == 404
        # The id travels as a bound parameter, not inside the SQL text.
        assert db.log[0]["params"] == {"float_id": "2902696"}
        assert "2902696" not in db.log[0]["sql"]

    def test_known_float(self, api):
        client, _, db = api
        db.row = FakeRow(
            float_id="2903956", total_measurements=6579, total_cycles=9,
            first_measurement=datetime(2025, 10, 2), last_measurement=datetime(2025, 10, 19),
            avg_latitude=24.05, avg_longitude=60.66, min_temp=9.0, max_temp=30.2, avg_temp=15.2,
            min_sal=None, max_sal=None, avg_sal=None, max_pressure=1029.1, ocean_region="Arabian Sea",
        )
        body = client.get("/api/v1/floats/2903956").json()
        assert body["total_cycles"] == 9 and body["temperature"]["max"] == 30.2
        assert body["salinity"] == {"min": None, "max": None, "mean": None}


class TestDataRoutes:
    def test_query_returns_rows_without_asking_for_an_answer(self, api):
        client, processor, _ = api
        body = client.post("/api/v1/query", json={"query": "Show temperature", "limit": 1}).json()
        assert body["record_count"] == 2 and len(body["data"]) == 1
        assert processor.calls[0]["generate_answer"] is False

    def test_batch_query_in_parallel(self, api):
        client, processor, _ = api
        response = client.post("/api/v1/batch-query", json={"queries": ["a?", "b?", "c?"], "parallel": True})
        assert response.status_code == 200
        assert [item["query"] for item in response.json()["results"]] == ["a?", "b?", "c?"]
        assert len(processor.calls) == 3

    def test_batch_query_size_is_capped(self, api):
        client, _, _ = api
        assert client.post("/api/v1/batch-query", json={"queries": ["q"] * 11}).status_code == 422

    def test_unsupported_export_format_is_400(self, api):
        client, _, _ = api
        assert client.post("/api/v1/export", params={"query": "q", "format_type": "xml"}).status_code == 400

    def test_csv_export(self, api):
        client, _, _ = api
        body = client.post("/api/v1/export", params={"query": "q", "format_type": "csv"}).json()
        assert body["records"] == 2 and body["data"].startswith("float_id,")

    def test_health_is_cheap_and_reports_components(self, api):
        client, _, db = api
        body = client.get("/api/v1/health").json()
        assert body["status"] == "healthy" and "components" in body
        assert db.log == []  # no database round trip unless ?deep=true


class TestRateLimit:
    def test_limit_then_429_with_retry_after(self):
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, limit_per_minute=2)

        @app.post("/api/v1/chat")
        def chat():
            return {"ok": True}

        @app.get("/api/v1/health")
        def health():
            return {"ok": True}

        client = TestClient(app)
        assert [client.post("/api/v1/chat").status_code for _ in range(3)] == [200, 200, 429]
        assert "Retry-After" in client.post("/api/v1/chat").headers
        # Cheap endpoints are never limited.
        assert client.get("/api/v1/health").status_code == 200
