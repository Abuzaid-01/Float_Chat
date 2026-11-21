"""Exercise the production API, parser, SQL executor and profile analysis together."""

from datetime import datetime, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from api import deps
from api.main import app
from database.db_setup import DatabaseSetup


def test_standard_neon_url_uses_installed_postgresql_driver(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://reader@db.example.invalid/archive?sslmode=require&channel_binding=require",
    )
    db = DatabaseSetup()
    try:
        assert db.engine.dialect.driver == "psycopg2"
        assert db.engine.url.query == {"sslmode": "require", "channel_binding": "require"}
    finally:
        db.engine.dispose()


@pytest.fixture
def api(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'archive.sqlite'}")
    with engine.begin() as connection:
        connection.exec_driver_sql("""
            CREATE TABLE argo_profiles (
                float_id TEXT, cycle_number INTEGER, latitude REAL, longitude REAL, timestamp TEXT,
                pressure REAL, temperature REAL, salinity REAL, temp_qc INTEGER, sal_qc INTEGER,
                ocean_region TEXT
            )
        """)
        rows = []
        for number, region in (("2903956", "Arabian Sea"), ("2903957", "Bay of Bengal")):
            for cycle in (112, 113):
                date = datetime(2025, 10, 17) + timedelta(days=cycle - 112)
                for level in range(36):
                    temp = 27 - min(max(level - 3, 0), 8) - max(level - 12, 0) * 0.1
                    rows.append((number, cycle, 12.0, 70.0, str(date), level * 10.0, temp, 35.0, 1, 1, region))
        connection.exec_driver_sql("INSERT INTO argo_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

    monkeypatch.setattr(deps, "_instances", {})
    monkeypatch.setattr(deps, "get_db", lambda: SimpleNamespace(engine=engine))
    try:
        yield TestClient(app)
    finally:
        engine.dispose()


def chat(api, question, history=None):
    result = api.post("/api/v1/chat", json={"message": question, "conversation_history": history or []})
    assert result.status_code == 200
    return result.json()


def test_real_chat_and_query_distinguish_archive_counts(api):
    result = chat(api, "How many floats are there?")
    assert result["success"] and result["route"] == "rules"
    assert result["data"] == [{"float_count": 2, "profile_count": 4, "measurement_count": 144}]
    assert "**2** floats" in result["response"]

    query = api.post("/api/v1/query", json={"query": "How many profiles?", "use_cache": False}).json()
    assert query["data"][0]["profile_count"] == 4
    assert query["cached"] is False


def test_pressure_and_date_filters_are_independent(api):
    for pressure, expected in [(100, 20), (200, 40)]:
        result = chat(api, f"How many measurements are in the Arabian Sea at pressures below {pressure} dbar?")
        assert result["data"][0]["measurement_count"] == expected
        assert f"pressure < {pressure}.0" in result["sql"]
    empty = chat(api, "Show temperature in Arabian Sea on January 15 1900")
    assert empty["success"] and empty["result_count"] == 0
    assert empty["summary"]["total_matching"] == 0


def test_followup_changes_parameter_and_retains_the_archive_scope(api):
    history = [{"role": "user", "content": "Show average temperature in the Arabian Sea on October 17 2025"}]
    result = chat(api, "What about salinity?", history)
    assert result["success"]
    assert "AVG(salinity)" in result["sql"] and "'Arabian Sea'" in result["sql"]
    assert "2025-10-17" in result["sql"]
    assert result["data"][0]["measurement_count"] == 36


def test_analysis_selects_the_same_cast_in_chat_and_rest(api):
    result = chat(api, "Calculate thermocline depth for float 2903956")
    assert result["success"] and result["analysis"]["success"]
    assert result["analysis"]["profile"]["cycle_number"] == 113
    assert result["analysis"]["thermocline_depth_dbar"] > 0
    assert len(result["data"]) == 36
    reply = api.post("/api/v1/analytics/thermocline", params={"query": "Show float 2903956"})
    assert reply.status_code == 200
    assert reply.json()["thermocline"] == result["analysis"]


def test_free_form_question_uses_exact_plan_cache_but_always_reads_rows(api, monkeypatch):
    processor = deps.get_query_processor()
    generator = processor._get_sql_generator()
    source = {"float_id": "2903956", "summary_text": "An Arabian Sea profile from the local test archive."}
    monkeypatch.setattr(processor, "warm_retrieval", lambda: (
        None,
        SimpleNamespace(generate_embedding=lambda query: []),
        SimpleNamespace(search=lambda *args, **kwargs: [(1, source)]),
        SimpleNamespace(get_similar_examples=lambda *args, **kwargs: []),
    ))
    prompts = []

    def complete(**kwargs):
        prompts.append(kwargs["messages"][0]["content"])
        sql = "SELECT AVG(temperature) AS archive_mean FROM argo_profiles WHERE ocean_region = 'Arabian Sea';"
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=sql))])

    monkeypatch.setattr(generator.client.chat.completions, "create", complete)
    question = "How unusual are temperatures in the Arabian Sea?"
    before = chat(api, question)
    assert before["route"] == "llm" and not before["cached"]
    assert before["retrieval"][0]["summary"] == source["summary_text"] in prompts[0]

    with processor.db_setup.engine.begin() as connection:
        connection.exec_driver_sql("UPDATE argo_profiles SET temperature = temperature + 1")
    after = chat(api, question)
    assert after["cached"] and len(prompts) == 1
    assert after["data"][0]["archive_mean"] == pytest.approx(before["data"][0]["archive_mean"] + 1)
    fresh = api.post("/api/v1/query", json={"query": question, "use_cache": False}).json()
    assert fresh["success"] and not fresh["cached"] and len(prompts) == 2
