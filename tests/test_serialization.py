"""Tests for the JSON-safety helpers."""

from datetime import datetime
from decimal import Decimal

import numpy as np
import pandas as pd

from rag_engine.serialization import dataframe_to_records, to_jsonable


def test_numpy_and_pandas_scalars_become_builtins():
    value = to_jsonable({
        "flag": np.bool_(True), "count": np.int64(3), "mean": np.float64(1.5), "missing": np.float64("nan"),
        "amount": Decimal("2.25"), "when": pd.Timestamp("2025-10-01 12:00"), "range": (np.float64(1.0), 2),
        "never": pd.NaT, "day": datetime(2025, 10, 1),
    })
    assert value == {
        "flag": True, "count": 3, "mean": 1.5, "missing": None, "amount": 2.25,
        "when": "2025-10-01T12:00:00", "range": [1.0, 2], "never": None, "day": "2025-10-01T00:00:00",
    }
    assert type(value["flag"]) is bool and type(value["count"]) is int


def test_byte_string_wrappers_are_removed():
    assert to_jsonable("b'6904092 '") == "6904092"
    assert to_jsonable(b"6904092 ") == "6904092"


def test_dataframe_records_are_limited_and_rounded():
    frame = pd.DataFrame({"temperature": [1.234567, 2.0, 3.0], "float_id": ["1", "2", "3"]})
    assert dataframe_to_records(frame, limit=2) == [
        {"temperature": 1.2346, "float_id": "1"}, {"temperature": 2.0, "float_id": "2"},
    ]
    assert dataframe_to_records(pd.DataFrame()) == []
