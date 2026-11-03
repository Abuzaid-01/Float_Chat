"""
Tests for the rule-based question parser and SQL builder (no database, no LLM).

Each test pins a behaviour that was once wrong in production: a constraint in
the question that the generated SQL silently ignored, or a word matched as a
substring of another word.
"""

from datetime import datetime

import pytest

from rag_engine.query_parser import build_query, parse_question, resolve_with_history

DATASET_END = datetime(2025, 10, 19, 1, 15, 33)


def sql_for(question, history=None):
    spec = resolve_with_history(question, history or [], DATASET_END)
    built = build_query(spec) if spec else None
    return built.sql if built else None


class TestConstraintsAreHonoured:
    def test_specific_date_becomes_a_one_day_window(self):
        sql = sql_for("Show temperature in Arabian Sea on October 7 2025")
        assert "timestamp >= '2025-10-07 00:00:00'" in sql
        assert "timestamp < '2025-10-08 00:00:00'" in sql

    def test_date_without_year_uses_the_dataset_year(self):
        sql = sql_for("salinity in the Bay of Bengal on 12 october")
        assert "timestamp >= '2025-10-12 00:00:00'" in sql

    def test_relative_window_is_measured_from_the_newest_data(self):
        sql = sql_for("Show temperature in the Southern Indian Ocean last 7 days")
        assert "timestamp >= '2025-10-13 00:00:00'" in sql
        assert "CURRENT_DATE" not in sql

    def test_latitude_range(self):
        sql = sql_for("Show salinity in the Bay of Bengal between 10 and 15 degrees north")
        assert "latitude >= 10.0" in sql and "latitude <= 15.0" in sql

    def test_southern_latitudes_are_negative(self):
        sql = sql_for("temperature between 10 and 20 degrees south")
        assert "latitude >= -20.0" in sql and "latitude <= -10.0" in sql

    def test_cycle_number(self):
        sql = sql_for("Show data for float 2903956 cycle 113")
        assert "float_id = '2903956'" in sql and "cycle_number = 113" in sql

    def test_depth_below_and_above(self):
        assert "pressure >= 500.0" in sql_for("salinity below 500 m in the Arabian Sea")
        assert "pressure <= 200.0" in sql_for("temperature above 200 m in the Arabian Sea")

    def test_threshold_without_depth_unit_is_a_value_filter(self):
        sql = sql_for("temperature above 28 in the Arabian Sea")
        assert "temperature > 28.0" in sql
        assert "pressure" not in sql.split("WHERE")[1].split("ORDER BY")[0]

    def test_depth_window_around_a_level(self):
        sql = sql_for("temperature at 500 m in the Arabian Sea")
        assert "pressure >= 450.0" in sql and "pressure <= 550.0" in sql

    def test_surface_means_top_ten_dbar(self):
        assert "pressure <= 10.0" in sql_for("Show surface temperature in the Bay of Bengal")

    def test_southern_ocean_is_a_region(self):
        assert "'Southern Indian Ocean'" in sql_for("Show temperature in the Southern Ocean")


class TestWholeWordMatching:
    @pytest.mark.parametrize("question", [
        "What does the temperature look like in the Arabian Sea?",
        "How do temperatures in the Arabian Sea change with depth?",
        "Graph temperature for the Arabian Sea",
    ])
    def test_no_phantom_bgc_filters(self, question):
        sql = sql_for(question)
        assert "dissolved_oxygen" not in sql
        assert "ph IS NOT NULL" not in sql

    def test_real_bgc_request_still_filters(self):
        sql = sql_for("Find dissolved oxygen data")
        assert "dissolved_oxygen IS NOT NULL" in sql
        assert "FROM argo_profiles" in sql


class TestAnswerShape:
    def test_how_many_measurements_counts_instead_of_listing(self):
        sql = sql_for("How many temperature measurements are in the Bay of Bengal?")
        assert "COUNT(*) AS measurement_count" in sql
        assert "LIMIT 1000" not in sql

    def test_how_many_floats(self):
        sql = sql_for("How many floats are there?")
        assert "COUNT(DISTINCT float_id) AS float_count" in sql

    def test_superlative_orders_by_the_value(self):
        sql = sql_for("What is the warmest temperature recorded in the Equatorial Indian Ocean?")
        assert "ORDER BY temperature DESC" in sql
        assert "'Equatorial Indian Ocean'" in sql

    def test_by_region_groups(self):
        sql = sql_for("Average salinity by region")
        assert "GROUP BY ocean_region" in sql and "AVG(salinity)" in sql

    def test_which_region_ranks_regions(self):
        sql = sql_for("Which region is the saltiest?")
        assert "GROUP BY ocean_region" in sql and "ORDER BY average_salinity DESC" in sql

    def test_change_with_depth_bins_by_depth(self):
        sql = sql_for("How do temperatures in the Arabian Sea change with depth?")
        assert "AS depth_bin" in sql and "GROUP BY depth_bin" in sql

    def test_latest_n_profiles_limits_profiles_not_rows(self):
        sql = sql_for("Show the latest 5 profiles in the Arabian Sea")
        assert "ORDER BY MAX(timestamp) DESC LIMIT 5" in sql

    def test_comparison_keeps_both_regions(self):
        sql = sql_for("Compare temperature in Arabian Sea and Bay of Bengal")
        assert "ocean_region IN ('Arabian Sea', 'Bay of Bengal')" in sql
        assert "GROUP BY ocean_region" in sql

    def test_most_cycles_ranks_floats(self):
        sql = sql_for("Which float has the most cycles?")
        assert "ORDER BY cycle_count DESC" in sql and "_qc" not in sql

    def test_trajectory(self):
        sql = sql_for("Where has float 2903956 been?")
        assert "GROUP BY float_id, cycle_number" in sql

    def test_thermocline_selects_one_profile(self):
        spec = parse_question("Calculate thermocline depth for float 2903956", DATASET_END)
        assert spec.intent == "profile_analysis" and spec.analysis == "thermocline"
        assert "LIMIT 1)" in build_query(spec).sql


class TestQualityControl:
    def test_values_are_restricted_to_good_qc(self):
        assert "temp_qc IN (1, 2)" in sql_for("What is the average temperature in the Arabian Sea?")
        assert "sal_qc IN (1, 2)" in sql_for("Average salinity by region")

    def test_counts_are_not_quality_filtered(self):
        assert "_qc" not in sql_for("How many floats are there?")

    def test_raw_data_on_request(self):
        assert "_qc" not in sql_for("Show raw temperature in the Arabian Sea")

    def test_description_states_the_quality_rule(self):
        spec = parse_question("average temperature in the Arabian Sea", DATASET_END)
        assert "QC 1–2" in build_query(spec).description
        spec = parse_question("How many floats are there?", DATASET_END)
        assert "all quality flags" in build_query(spec).description


class TestDefersToTheLlm:
    @pytest.mark.parametrize("question", [
        "What is the median salinity in the Arabian Sea?",
        "tell me what is weird about the bay of bengal",
        "average temperature at 20:50 on October 7 2025",
        "Show me all the data",
        "temperature in the Arabian Sea excluding float 2903956",
        "correlation between temperature and salinity",
    ])
    def test_out_of_grammar_questions_are_not_answered_by_rules(self, question):
        assert sql_for(question) is None

    def test_unexplained_number_defers(self):
        # "42" is not a depth, date, coordinate or threshold the rules recognise.
        assert sql_for("temperature in the Arabian Sea for 42 somethings") is None


class TestFollowUps:
    HISTORY = ["What is the average temperature in the Arabian Sea?"]

    def test_follow_up_keeps_region_and_intent(self):
        sql = sql_for("what about salinity there?", self.HISTORY)
        assert "'Arabian Sea'" in sql and "AVG(salinity)" in sql

    def test_follow_up_can_change_the_region(self):
        sql = sql_for("and in the Bay of Bengal?", self.HISTORY)
        assert "'Bay of Bengal'" in sql and "'Arabian Sea'" not in sql and "AVG(temperature)" in sql

    def test_complete_question_does_not_inherit(self):
        sql = sql_for("How many floats are there?", ["Show temperature in Arabian Sea"])
        assert "Arabian Sea" not in sql

    def test_are_there_is_not_a_reference_to_a_place(self):
        spec = parse_question("How many floats are there?", DATASET_END)
        assert spec.follow_up is False

    def test_follow_up_keeps_depth_and_date(self):
        history = ["average temperature in the Arabian Sea below 500 m on October 7 2025"]
        sql = sql_for("what about salinity?", history)
        assert "pressure >= 500.0" in sql and "2025-10-07" in sql and "AVG(salinity)" in sql


class TestSqlSafety:
    @pytest.mark.parametrize("question", [
        "Show temperature in Arabian Sea'; DROP TABLE argo_profiles; --",
        "float 2903956' OR '1'='1",
        "temperature in the Arabian Sea on 2025-10-07'; DELETE FROM argo_profiles",
    ])
    def test_user_text_never_reaches_the_sql(self, question):
        sql = sql_for(question)
        if sql is not None:
            assert "DROP" not in sql.upper() and "DELETE" not in sql.upper()
            assert "'1'='1" not in sql
            assert sql.count(";") == 1
