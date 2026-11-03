"""
Turning database and analysis results into plain JSON-safe Python values.

Query results arrive as pandas / numpy / Decimal / datetime objects, and the
analytics return numpy scalars.  None of those serialise reliably, so every
value that leaves the pipeline goes through `to_jsonable`.
"""

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

import numpy as np
import pandas as pd


def clean_text(value: str) -> str:
    """Strip whitespace and the b'...' wrapper left by numpy byte strings."""
    text = value.strip()
    if (text.startswith("b'") and text.endswith("'")) or (text.startswith('b"') and text.endswith('"')):
        text = text[2:-1].strip()
    return text


def to_jsonable(value: Any) -> Any:
    """Recursively convert a value to JSON-safe builtins (NaN / NaT become None)."""
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, Decimal):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return clean_text(value.decode("utf-8", errors="ignore"))
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return [to_jsonable(item) for item in value.tolist()]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def dataframe_to_records(df: pd.DataFrame, limit: int = 500, float_digits: int = 4) -> List[Dict]:
    """First `limit` rows of a DataFrame as JSON-safe dicts, floats rounded."""
    if df is None or df.empty:
        return []
    records = []
    for row in df.head(limit).to_dict("records"):
        clean = {}
        for key, value in row.items():
            value = to_jsonable(value)
            if isinstance(value, float):
                value = round(value, float_digits)
            clean[str(key)] = value
        records.append(clean)
    return records
