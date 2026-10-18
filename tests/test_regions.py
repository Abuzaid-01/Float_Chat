"""
Tests for data_processing.regions: ocean-region classification and
float_id normalization. These are pure functions shared by the data loader,
NetCDF extractor, MCP tools and the SQL generator.
"""

import numpy as np
import pytest

from data_processing.regions import (
    ALLOWED_PARAMETERS,
    KNOWN_REGIONS,
    classify_ocean_region,
    normalize_float_id,
)


class TestClassifyOceanRegion:
    def test_arabian_sea(self):
        assert classify_ocean_region(15.0, 60.0) == "Arabian Sea"

    def test_bay_of_bengal(self):
        assert classify_ocean_region(10.0, 90.0) == "Bay of Bengal"

    def test_equatorial(self):
        assert classify_ocean_region(0.0, 80.0) == "Equatorial Indian Ocean"

    def test_southern(self):
        assert classify_ocean_region(-30.0, 70.0) == "Southern Indian Ocean"

    def test_red_sea(self):
        assert classify_ocean_region(20.0, 38.0) == "Red Sea"

    def test_andaman_sea(self):
        assert classify_ocean_region(10.0, 95.0) == "Andaman Sea"

    def test_outside_indian_ocean_returns_none(self):
        assert classify_ocean_region(45.0, -60.0) is None

    def test_missing_coordinates_returns_none(self):
        assert classify_ocean_region(None, 60.0) is None
        assert classify_ocean_region("bad", 60.0) is None

    def test_boundary_values(self):
        # Exactly on the Arabian Sea bbox corner
        assert classify_ocean_region(5.0, 40.0) == "Arabian Sea"


class TestNormalizeFloatId:
    def test_plain_digits_unchanged(self):
        assert normalize_float_id("6904092") == "6904092"

    def test_numpy_bytes_wrapper(self):
        # str(np.bytes_) produces "b'6904092 '"
        raw = str(np.bytes_("6904092 ".encode()))
        assert raw == "b'6904092 '"
        assert normalize_float_id(raw) == "6904092"

    def test_actual_bytes_object(self):
        assert normalize_float_id(b"6904092 ") == "6904092"

    def test_padding_and_quotes(self):
        assert normalize_float_id(" '1901514' ") == "1901514"

    def test_none_returns_none(self):
        assert normalize_float_id(None) is None

    def test_empty_returns_none(self):
        assert normalize_float_id("") is None
        assert normalize_float_id("   ") is None


class TestConstants:
    def test_allowed_parameters(self):
        assert "temperature" in ALLOWED_PARAMETERS
        assert "salinity" in ALLOWED_PARAMETERS
        assert "pressure" in ALLOWED_PARAMETERS
        assert ALLOWED_PARAMETERS.isdisjoint({"user_id", "password", "1; DROP"})

    def test_known_regions(self):
        assert KNOWN_REGIONS == {
            "Arabian Sea",
            "Bay of Bengal",
            "Equatorial Indian Ocean",
            "Southern Indian Ocean",
            "Red Sea",
            "Andaman Sea",
        }