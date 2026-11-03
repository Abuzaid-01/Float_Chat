"""
Data routes: direct queries, float and region lookups, analytics, export.

All database access here uses bound parameters or the validated query
pipeline — no user text is ever formatted into SQL.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from api import deps
from api.schemas import BatchQueryRequest, QueryRequest
from rag_engine.serialization import dataframe_to_records, to_jsonable

router = APIRouter(prefix="/api/v1", tags=["FloatChat API"])

# The dataset is an archive that only changes on re-import, so the summary
# endpoints are cached briefly instead of scanning 1.2M rows per page load.
_summary_cache = deps.TTLCache(ttl_seconds=300)

FLOAT_ID_PATTERN = re.compile(r"^\d{4,10}$")
EXPORT_FORMATS = ("csv", "json", "parquet")


def _run_query(query: str, use_cache: bool = True) -> Dict:
    """Run a natural-language query through the pipeline, without an LLM-written answer."""
    result = deps.get_query_processor().process_query(query, generate_answer=False, use_cache=use_cache)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "The query could not be processed"))
    return result


def _newest_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Profile analysis needs one cast: keep the newest (float, cycle) in the result."""
    if df.empty or not {"float_id", "cycle_number"}.issubset(df.columns):
        return df
    if "timestamp" in df.columns:
        newest = df.sort_values("timestamp", ascending=False).iloc[0]
    else:
        newest = df.iloc[0]
    return df[(df["float_id"] == newest["float_id"]) & (df["cycle_number"] == newest["cycle_number"])]


# Regular API Routes

@router.post("/query")
def query_data(request: QueryRequest):
    """Run a natural-language query and return the rows (no generated answer)."""
    try:
        result = _run_query(request.query, use_cache=request.use_cache)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    df = result["results"]
    return {
        "success": True,
        "data": dataframe_to_records(df, request.limit),
        "record_count": len(df),
        "sql": result.get("sql"),
        "route": result.get("route"),
        "interpretation": result.get("interpretation"),
        "summary": result.get("summary"),
        "execution_time": result.get("execution_time", 0),
        "cached": bool(result.get("cached")),
    }


@router.post("/batch-query")
def batch_query(request: BatchQueryRequest):
    """Execute several queries, one after another or on parallel worker threads."""
    processor = deps.get_query_processor()

    def run(query: str) -> Dict:
        try:
            return processor.process_query(query, generate_answer=False)
        except Exception as error:
            return {"success": False, "error": str(error)}

    if request.parallel:
        with ThreadPoolExecutor(max_workers=min(4, len(request.queries))) as pool:
            results = list(pool.map(run, request.queries))
    else:
        results = [run(query) for query in request.queries]

    return {
        "success": True,
        "queries_executed": len(request.queries),
        "results": [
            {
                "query": query,
                "success": result["success"],
                "record_count": len(result["results"]) if result["success"] else 0,
                "sql": result.get("sql"),
                "interpretation": result.get("interpretation"),
                "error": result.get("error") if not result["success"] else None,
            }
            for query, result in zip(request.queries, results)
        ],
    }


@router.get("/floats/{float_id}")
def get_float_info(float_id: str):
    """Get information about a specific float"""
    if not FLOAT_ID_PATTERN.match(float_id):
        raise HTTPException(status_code=400, detail="Float IDs are 4 to 10 digits")

    query = text("""
        SELECT
            float_id,
            COUNT(*) AS total_measurements,
            COUNT(DISTINCT cycle_number) AS total_cycles,
            MIN(timestamp) AS first_measurement,
            MAX(timestamp) AS last_measurement,
            AVG(latitude) AS avg_latitude,
            AVG(longitude) AS avg_longitude,
            MIN(temperature) FILTER (WHERE temp_qc IN (1, 2)) AS min_temp,
            MAX(temperature) FILTER (WHERE temp_qc IN (1, 2)) AS max_temp,
            AVG(temperature) FILTER (WHERE temp_qc IN (1, 2)) AS avg_temp,
            MIN(salinity) FILTER (WHERE sal_qc IN (1, 2)) AS min_sal,
            MAX(salinity) FILTER (WHERE sal_qc IN (1, 2)) AS max_sal,
            AVG(salinity) FILTER (WHERE sal_qc IN (1, 2)) AS avg_sal,
            MAX(pressure) AS max_pressure,
            MAX(ocean_region) AS ocean_region
        FROM argo_profiles
        WHERE float_id = :float_id
        GROUP BY float_id
    """)

    try:
        with deps.get_db().engine.connect() as connection:
            row = connection.execute(query, {"float_id": float_id}).fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if row is None:
        raise HTTPException(status_code=404, detail="Float not found")

    number = lambda value: None if value is None else float(value)  # noqa: E731
    return {
        "float_id": row.float_id,
        "total_measurements": row.total_measurements,
        "total_cycles": row.total_cycles,
        "first_measurement": row.first_measurement.isoformat() if row.first_measurement else None,
        "last_measurement": row.last_measurement.isoformat() if row.last_measurement else None,
        "avg_location": {"lat": number(row.avg_latitude), "lon": number(row.avg_longitude)},
        "temperature": {"min": number(row.min_temp), "max": number(row.max_temp), "mean": number(row.avg_temp)},
        "salinity": {"min": number(row.min_sal), "max": number(row.max_sal), "mean": number(row.avg_sal)},
        "max_pressure": number(row.max_pressure),
        "ocean_region": row.ocean_region,
    }


@router.get("/regions")
def get_regions():
    """Get available ocean regions"""
    cached = _summary_cache.get("regions")
    if cached:
        return cached

    query = text("""
        SELECT ocean_region, COUNT(*) AS measurements, COUNT(DISTINCT float_id) AS floats
        FROM argo_profiles
        WHERE ocean_region IS NOT NULL
        GROUP BY ocean_region
        ORDER BY measurements DESC
    """)
    try:
        with deps.get_db().engine.connect() as connection:
            rows = connection.execute(query).fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return _summary_cache.set("regions", {
        "regions": [{"name": row[0], "measurements": row[1], "floats": row[2]} for row in rows]
    })


@router.post("/analytics/thermocline")
def analyze_thermocline(query: str = Query(..., min_length=1, max_length=1000)):
    """Thermocline and mixed-layer analysis of the newest profile the query returns."""
    try:
        result = _run_query(query)
        profile = _newest_profile(result["results"])
        thermocline = deps.get_analytics().calculate_thermocline_advanced(profile)
        return to_jsonable({
            "success": True,
            "thermocline": thermocline,
            "profile": {
                "float_id": profile["float_id"].iloc[0] if "float_id" in profile.columns and len(profile) else None,
                "cycle_number": profile["cycle_number"].iloc[0] if "cycle_number" in profile.columns and len(profile) else None,
                "measurements": len(profile),
            },
            "record_count": len(result["results"]),
            "sql": result.get("sql"),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analytics/water-masses")
def identify_water_masses(query: str = Query(..., min_length=1, max_length=1000)):
    """Water masses in the newest profile the query returns."""
    try:
        result = _run_query(query)
        profile = _newest_profile(result["results"])
        analytics = deps.get_analytics()
        detail = analytics.identify_water_masses_advanced(profile)
        return to_jsonable({
            "success": True,
            "water_masses": detail.get("water_masses", []) if isinstance(detail, dict) else [],
            "detail": detail,
            "profile": {
                "float_id": profile["float_id"].iloc[0] if "float_id" in profile.columns and len(profile) else None,
                "cycle_number": profile["cycle_number"].iloc[0] if "cycle_number" in profile.columns and len(profile) else None,
                "measurements": len(profile),
            },
            "record_count": len(result["results"]),
            "sql": result.get("sql"),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analytics/trends")
def analyze_trends(region: str, parameter: str, days: int = Query(90, ge=1, le=3650)):
    """Trend of a parameter in a region over the last `days` days of the dataset."""
    try:
        trend = deps.get_analytics().trend_analysis(region, parameter, days)
        return to_jsonable({"success": True, "trend_analysis": trend})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
def database_statistics():
    """Get database statistics"""
    cached = _summary_cache.get("stats")
    if cached:
        return cached

    # One pass over the table.  Averages use good-quality values only (QC 1-2),
    # the same rule the question pipeline applies.
    query = text("""
        SELECT
            COUNT(*) AS total_records,
            COUNT(DISTINCT float_id) AS unique_floats,
            COUNT(DISTINCT (float_id, cycle_number)) FILTER (WHERE float_id IS NOT NULL) AS profiles,
            MIN(timestamp) AS earliest,
            MAX(timestamp) AS latest,
            COUNT(DISTINCT ocean_region) AS regions,
            COUNT(DISTINCT cycle_number) AS cycle_numbers,
            AVG(temperature) FILTER (WHERE temp_qc IN (1, 2)) AS avg_temp,
            AVG(salinity) FILTER (WHERE sal_qc IN (1, 2)) AS avg_sal
        FROM argo_profiles
    """)
    try:
        with deps.get_db().engine.connect() as connection:
            row = connection.execute(query).fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return _summary_cache.set("stats", {
        "total_records": row.total_records,
        "unique_floats": row.unique_floats,
        "profiles": row.profiles,
        "date_range": {
            "earliest": row.earliest.isoformat() if row.earliest else None,
            "latest": row.latest.isoformat() if row.latest else None,
        },
        "regions_covered": row.regions,
        "cycles": row.cycle_numbers,
        "average_temperature": None if row.avg_temp is None else float(row.avg_temp),
        "average_salinity": None if row.avg_sal is None else float(row.avg_sal),
        "generated_at": datetime.now().isoformat(),
    })


@router.post("/export")
def export_data(query: str = Query(..., min_length=1, max_length=1000), format_type: str = "csv"):
    """Export query results in various formats"""
    if format_type not in EXPORT_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported format. Use one of: {', '.join(EXPORT_FORMATS)}")

    try:
        df = _run_query(query)["results"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if format_type == "csv":
        data = df.to_csv(index=False)
    elif format_type == "json":
        data = df.to_json(orient="records", date_format="iso")
    else:
        try:
            data = df.to_parquet(index=False).hex()
        except ImportError:
            raise HTTPException(status_code=501, detail="Parquet export needs the pyarrow package on the server")
    return {"format": format_type, "data": data, "records": len(df)}
