"""
Tests for the SQL generation layer (no LLM / network calls).

Covers the security-critical and pure-logic parts:
- validate_sql must REJECT injection payloads (it previously only warned)
- validate_sql must ACCEPT well-formed read-only SELECTs
- spatial query generation produces parameterized-by-float queries
- query intent analysis (region/parameter/time detection)
- LIMIT enforcement
"""

import pytest

from rag_engine.sql_generator import EnhancedSQLGenerator


@pytest.fixture(scope="module")
def generator():
    # Groq client is constructed with the placeholder key from conftest;
    # no network call happens at construction time.
    return EnhancedSQLGenerator()


GOOD_QUERY = (
    "SELECT latitude, longitude, timestamp, pressure, temperature, salinity "
    "FROM argo_profiles "
    "WHERE latitude BETWEEN 5 AND 30 AND longitude BETWEEN 40 AND 80 "
    "AND temp_qc IN (1,2,3) "
    "ORDER BY timestamp DESC "
    "LIMIT 1000;"
)


class TestValidateSqlRejectsInjection:
    @pytest.mark.parametrize("payload", [
        "SELECT * FROM argo_profiles; DROP TABLE argo_profiles;",
        "SELECT * FROM argo_profiles; DELETE FROM argo_profiles;",
        "SELECT * FROM argo_profiles -- comment",
        "SELECT * FROM argo_profiles WHERE float_id = 'x'; SELECT pg_sleep(10);",
        "SELECT * FROM argo_profiles UNION SELECT username, password FROM users",
        "SELECT * INTO outfile FROM argo_profiles",
        "SELECT * FROM argo_profiles WHERE 1=1 /* block comment */",
    ])
    def test_rejects_injection(self, generator, payload):
        assert generator.validate_sql(payload) is False

    def test_rejects_non_select(self, generator):
        assert generator.validate_sql("DELETE FROM argo_profiles;") is False
        assert generator.validate_sql("UPDATE argo_profiles SET temperature = 0;") is False
        assert generator.validate_sql("DROP TABLE argo_profiles;") is False

    def test_rejects_wrong_table(self, generator):
        assert generator.validate_sql("SELECT * FROM users;") is False

    def test_rejects_empty(self, generator):
        assert generator.validate_sql("") is False
        assert generator.validate_sql("SELECT 1") is False  # too short / no table


class TestValidateSqlAccepts:
    def test_accepts_standard_query(self, generator):
        assert generator.validate_sql(GOOD_QUERY) is True

    def test_accepts_aggregation_query(self, generator):
        sql = (
            "SELECT DATE_TRUNC('month', timestamp) AS month, "
            "AVG(temperature) AS avg_temp, COUNT(*) AS measurements "
            "FROM argo_profiles "
            "WHERE temp_qc IN (1,2,3) "
            "GROUP BY month ORDER BY month LIMIT 500;"
        )
        assert generator.validate_sql(sql) is True

    def test_accepts_region_query(self, generator):
        sql = (
            "SELECT latitude, longitude, temperature FROM argo_profiles "
            "WHERE ocean_region = 'Arabian Sea' LIMIT 1000;"
        )
        assert generator.validate_sql(sql) is True


class TestSpatialQuery:
    def test_generates_valid_sql_with_coordinates(self, generator):
        sql = generator._generate_spatial_query(15.5, 75.0, 100.0)
        assert generator.validate_sql(sql) is True
        assert "radians(15.5)" in sql
        assert "radians(75.0)" in sql
        assert "<= 100.0" in sql
        assert sql.strip().startswith("SELECT")

    def test_generated_sql_is_single_statement(self, generator):
        sql = generator._generate_spatial_query(0.0, 50.0, 500.0)
        assert sql.count(";") == 1


class TestAnalyzeQuery:
    def test_detects_region(self, generator):
        analysis = generator._analyze_query("Show temperature in Arabian Sea")
        assert analysis["region"] == "Arabian Sea"
        assert analysis["lat_range"] == (5, 30)

    def test_detects_parameters(self, generator):
        analysis = generator._analyze_query("average salinity and temperature")
        assert set(analysis["parameters"]) == {"salinity", "temperature"}

    def test_detects_time(self, generator):
        analysis = generator._analyze_query("temperature last month")
        assert "30 days" in analysis["time_period"]

    def test_defaults(self, generator):
        analysis = generator._analyze_query("what floats are there")
        # "float" maps to the float_specific pattern — that is correct behavior
        assert analysis["type"] == "float_specific"
        assert analysis["region"] == "Not specified"

    def test_general_query(self, generator):
        analysis = generator._analyze_query("show me all the data")
        assert analysis["type"] == "general"


class TestOptimizeQuery:
    def test_adds_limit_if_missing(self, generator):
        sql = "SELECT latitude, longitude FROM argo_profiles WHERE temp_qc IN (1,2,3);"
        optimized = generator._optimize_query(sql, {"complexity": 1})
        assert "LIMIT" in optimized.upper()

    def test_caps_excessive_limit(self, generator):
        sql = "SELECT * FROM argo_profiles LIMIT 100000;"
        optimized = generator._optimize_query(sql, {"complexity": 1})
        assert "LIMIT 10000" in optimized


class TestCoordinates:
    def test_extract_from_query(self, generator):
        lat, lon = generator._extract_coordinates_from_query(
            "floats near 15N 75E"
        )
        assert (lat, lon) == (15.0, 75.0)

    def test_extract_with_direction(self, generator):
        lat, lon = generator._extract_coordinates_from_query(
            "profiles within 100km of 5.5S 60W"
        )
        assert (lat, lon) == (-5.5, -60.0)

    def test_extract_radius_km(self, generator):
        radius = generator._extract_radius_from_query("within 50km of x")
        assert radius == 50.0