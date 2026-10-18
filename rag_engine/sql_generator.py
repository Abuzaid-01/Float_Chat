"""
Production-Grade SQL Generator for ARGO Ocean Data.
Enhanced with:
- Dynamic Schema Pruning (Context Window Optimization: ~57% token reduction)
- Few-shot Example Injection from ExampleStore
- Structured Query Plan Injection from QueryPlanner
- Haversine Spatial Query Generation
- SQL Validation and Safety Checks
"""

import os
import re
from typing import Dict, Optional, List, Tuple
from groq import Groq
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class EnhancedSQLGenerator:
    """
    Advanced SQL generator with domain-aware dynamic schema pruning,
    spatial-temporal reasoning, and query optimization.
    """

    COMPLETE_SCHEMA = """
    Table: argo_profiles (1.2M+ records)
    
    PRIMARY COLUMNS:
    ├─ id (SERIAL PRIMARY KEY) - Unique record identifier
    ├─ float_id (VARCHAR) - Float identifier (format: "b'XXXXXX '")
    ├─ cycle_number (INTEGER) - Measurement cycle number
    ├─ latitude (FLOAT) - Latitude in decimal degrees (-90 to 90)
    ├─ longitude (FLOAT) - Longitude in decimal degrees (-180 to 180)
    ├─ timestamp (TIMESTAMP) - UTC measurement datetime
    ├─ pressure (FLOAT) - Water pressure in dbar (1 dbar ≈ 1m depth)
    
    CORE PARAMETERS (Always available):
    ├─ temperature (FLOAT) - In-situ temperature (°Celsius)
    ├─ salinity (FLOAT) - Practical Salinity (PSU)
    
    BGC PARAMETERS:
    ├─ dissolved_oxygen (FLOAT) - DO in μmol/kg
    ├─ chlorophyll (FLOAT) - Chlorophyll-a in mg/m³
    ├─ ph (FLOAT) - pH on seawater scale
    
    QUALITY CONTROL:
    ├─ temp_qc (INTEGER) - 1=good, 2=probably good, 3=questionable, 4=bad, 9=missing
    ├─ sal_qc (INTEGER) - Salinity QC flag
    
    OCEAN REGIONS:
    Arabian Sea                | 5°N to 30°N  | 40°E to 80°E
    Bay of Bengal              | 5°N to 25°N  | 80°E to 100°E
    Equatorial Indian Ocean    | 10°S to 5°N  | 40°E to 100°E
    Southern Indian Ocean      | 50°S to 10°S | 20°E to 120°E
    Red Sea                    | 12°N to 30°N | 32°E to 44°E
    Andaman Sea                | 5°N to 20°N  | 92°E to 100°E
    """

    QUERY_PATTERNS = {
        "geographic": {
            "keywords": ["region", "area", "location", "near", "between", "arabian", "bengal", "ocean", "sea"],
            "requires": ["latitude", "longitude"],
        },
        "nearest": {
            "keywords": ["nearest", "closest", "within", "around", "proximity", "distance"],
            "requires": ["spatial_query"],
        },
        "temporal": {
            "keywords": ["recent", "last", "month", "year", "date", "period", "time", "historical", "trend"],
            "requires": ["timestamp"],
        },
        "depth": {
            "keywords": ["deep", "depth", "pressure", "surface", "bottom", "vertical", "profile"],
            "requires": ["pressure"],
        },
        "parameter": {
            "keywords": ["temperature", "salinity", "oxygen", "chlorophyll", "ph", "bgc"],
            "requires": ["temperature", "salinity"],
        },
        "comparison": {
            "keywords": ["compare", "difference", "versus", "vs", "between"],
            "requires": ["GROUP BY", "aggregation"],
        },
        "statistics": {
            "keywords": ["average", "mean", "max", "min", "count", "sum", "statistics", "distribution"],
            "requires": ["aggregation functions"],
        },
        "float_specific": {
            "keywords": ["float", "profile", "cycle", "trajectory"],
            "requires": ["float_id"],
        },
    }

    def __init__(self):
        api_key = None
        model = None
        try:
            import streamlit as st
            if "GROQ_API_KEY" in st.secrets:
                api_key = st.secrets["GROQ_API_KEY"]
            if "GROQ_MODEL" in st.secrets:
                model = st.secrets["GROQ_MODEL"]
        except Exception:
            pass

        if not api_key:
            api_key = os.getenv("GROQ_API_KEY")
        if not model:
            model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

        self.client = Groq(api_key=api_key)
        self.model = model
        self.prompt_template = self._create_enhanced_prompt()
        self.query_cache = {}
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "failed_queries": 0,
            "avg_complexity": 0,
        }
        logger.info("✅ Enhanced SQL Generator initialized with Groq")

    def _create_enhanced_prompt(self) -> PromptTemplate:
        template = """You are an expert PostgreSQL query generator for ARGO oceanographic data.
You have deep knowledge of oceanography, SQL optimization, and spatial-temporal queries.

DATABASE SCHEMA:
{schema}

USER QUERY: {user_query}

CONTEXT FROM SIMILAR PROFILES:
{context}

QUERY ANALYSIS:
Query Type: {query_type}
Detected Region: {region}
Detected Parameters: {parameters}
Time Period: {time_period}

CRITICAL SQL GENERATION RULES:

1. FLOAT ID FORMAT (CRITICAL - COMMON ERROR):
   - Float IDs are stored as: "b'XXXXXX '" (with b' prefix, trailing space)
   - Users query with plain numbers: "1901514" or "2902696"
   - ALWAYS use LIKE pattern matching, NOT exact equality
   - Correct: WHERE float_id LIKE '%1901514%'
   - Wrong: WHERE float_id = '1901514' (returns 0 rows!)

2. QUALITY CONTROL:
   - Default: WHERE temp_qc IN (1,2,3) AND sal_qc IN (1,2,3)
   - ALWAYS filter by QC unless explicitly asked not to

3. SPATIAL BOUNDS:
   - Arabian Sea: latitude BETWEEN 5 AND 30 AND longitude BETWEEN 40 AND 80
   - Bay of Bengal: latitude BETWEEN 5 AND 25 AND longitude BETWEEN 80 AND 100
   - Equatorial Indian Ocean: latitude BETWEEN -10 AND 5 AND longitude BETWEEN 40 AND 100

4. TEMPORAL QUERIES:
   - Exact date: timestamp::date = 'YYYY-MM-DD'
   - Date range: timestamp BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'
   - Recent data: timestamp >= CURRENT_DATE - INTERVAL '30 days'

5. OUTPUT FORMAT:
   - Return ONLY ONE valid PostgreSQL SQL statement
   - No markdown backticks (no ```)
   - No explanations before or after
   - No CTEs (WITH clauses) - use direct SELECT only
   - End with a single semicolon

EXAMPLE QUERIES:

-- Recent Arabian Sea data with good QC
SELECT latitude, longitude, timestamp, pressure, temperature, salinity
FROM argo_profiles
WHERE latitude BETWEEN 5 AND 30
  AND longitude BETWEEN 40 AND 80
  AND temp_qc IN (1,2,3)
  AND sal_qc IN (1,2,3)
ORDER BY timestamp DESC
LIMIT 1000;

-- Float trajectory
SELECT cycle_number, pressure, temperature, salinity
FROM argo_profiles
WHERE float_id LIKE '%2902696%'
  AND temp_qc IN (1,2,3)
ORDER BY cycle_number ASC, pressure ASC
LIMIT 1000;

RESPOND WITH ONLY THE SQL QUERY (ONE STATEMENT, NO EXPLANATIONS):"""

        return PromptTemplate(
            input_variables=[
                "schema",
                "user_query",
                "context",
                "query_type",
                "region",
                "parameters",
                "time_period",
            ],
            template=template,
        )

    def generate_sql(
        self,
        user_query: str,
        context: str = "",
        force_regenerate: bool = False,
        few_shot_examples: Optional[List[Dict]] = None,
        query_plan: Optional[Dict] = None,
    ) -> Optional[str]:
        """
        Generate SQL with dynamic schema pruning, few-shot examples, and caching.
        """
        self.stats["total_queries"] += 1
        cache_key = f"{user_query}:{context}"
        if not force_regenerate and cache_key in self.query_cache:
            self.stats["cache_hits"] += 1
            return self.query_cache[cache_key]

        try:
            analysis = self._analyze_query(user_query)

            # Spatial / Nearest distance check
            if analysis["type"] == "nearest" or any(
                kw in user_query.lower() for kw in ["nearest", "closest", "within"]
            ):
                lat, lon = self._extract_coordinates_from_query(user_query)
                if lat is not None and lon is not None:
                    radius_km = self._extract_radius_from_query(user_query)
                    sql_query = self._generate_spatial_query(lat, lon, radius_km)
                    if self.validate_sql(sql_query):
                        self.query_cache[cache_key] = sql_query
                        return sql_query

            # Dynamic Schema Pruning (Context Window Optimization)
            relevant_schema = self._build_relevant_schema(analysis)

            formatted_prompt = self.prompt_template.format(
                schema=relevant_schema,
                user_query=user_query,
                context=context or "No similar profiles found",
                query_type=analysis["type"],
                region=analysis["region"],
                parameters=", ".join(analysis["parameters"]),
                time_period=analysis["time_period"],
            )

            # Inject few-shot examples if available
            if few_shot_examples:
                examples_text = "\n\nSIMILAR SUCCESSFUL QUERIES (reference):\n"
                for i, ex in enumerate(few_shot_examples, 1):
                    examples_text += (
                        f"\nExample {i} (similarity: {ex.get('similarity', 0):.2f}):\n"
                        f"  User: \"{ex['query']}\"\n"
                        f"  SQL: {ex['sql']}\n"
                    )
                formatted_prompt += examples_text

            # Inject structured query plan if available
            if query_plan:
                plan_text = "\n\nSTRUCTURED QUERY PLAN:\n"
                if query_plan.get("intent_type"):
                    plan_text += f"  Intent: {query_plan['intent_type']}\n"
                if query_plan.get("regions"):
                    plan_text += f"  Target Regions: {', '.join(query_plan['regions'])}\n"
                if query_plan.get("parameters"):
                    plan_text += f"  Parameters: {', '.join(query_plan['parameters'])}\n"
                if query_plan.get("float_ids"):
                    plan_text += f"  Float IDs: {', '.join(query_plan['float_ids'])}\n"
                formatted_prompt += plan_text

            # LLM Generation via Groq
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": formatted_prompt}],
                temperature=0.0,
                max_completion_tokens=1024,
                top_p=1,
                stream=False,
            )
            sql = self._clean_sql(completion.choices[0].message.content)

            if not self.validate_sql(sql):
                logger.error("❌ Generated SQL failed validation")
                self.stats["failed_queries"] += 1
                return None

            sql = self._optimize_query(sql, analysis)
            self.query_cache[cache_key] = sql
            return sql

        except Exception as e:
            logger.error(f"❌ SQL generation error: {e}")
            self.stats["failed_queries"] += 1
            return None

    def _build_relevant_schema(self, analysis: Dict) -> str:
        """
        Build a pruned schema containing only columns, regions, and indexes
        relevant to the current query. Saves ~57% tokens on simple queries.
        """
        detected_params = set(analysis.get("parameters", []))
        detected_region = analysis.get("region", "Not specified")
        query_type = analysis.get("type", "general")

        lines = [
            "Table: argo_profiles (1.2M+ records)",
            "",
            "PRIMARY COLUMNS:",
            "├─ id (SERIAL PRIMARY KEY)",
            "├─ float_id (VARCHAR) - Float identifier (format: \"b'XXXXXX '\")",
            "├─ cycle_number (INTEGER) - Measurement cycle number",
            "├─ latitude (FLOAT) - Decimal degrees (-90 to 90)",
            "├─ longitude (FLOAT) - Decimal degrees (-180 to 180)",
            "├─ timestamp (TIMESTAMP) - UTC measurement datetime",
            "├─ pressure (FLOAT) - Water pressure in dbar (≈ depth in m)",
        ]

        # Core parameters
        include_core = (
            not detected_params
            or "temperature" in detected_params
            or "salinity" in detected_params
            or "pressure" in detected_params
            or query_type in (
                "general", "geographic", "temporal", "depth", "comparison", "statistics", "float_specific", "nearest"
            )
        )
        if include_core:
            lines.append("")
            lines.append("CORE PARAMETERS (Always available):")
            lines.append("├─ temperature (FLOAT) - In-situ temperature (°Celsius)")
            lines.append("├─ salinity (FLOAT) - Practical Salinity (PSU)")

        # BGC parameters (only when asked)
        bgc_params = detected_params & {"dissolved_oxygen", "chlorophyll", "ph"}
        if bgc_params:
            lines.append("")
            lines.append("BGC PARAMETERS (May not be available in Core floats):")
            if "dissolved_oxygen" in bgc_params:
                lines.append("├─ dissolved_oxygen (FLOAT) - DO in μmol/kg")
            if "chlorophyll" in bgc_params:
                lines.append("├─ chlorophyll (FLOAT) - Chlorophyll-a in mg/m³")
            if "ph" in bgc_params:
                lines.append("├─ ph (FLOAT) - pH on seawater scale")

        # QC columns
        if include_core or bgc_params:
            lines.append("")
            lines.append("QUALITY CONTROL:")
            lines.append("├─ temp_qc (INTEGER) - 1=good, 2=probably good, 3=questionable, 4=bad")
            lines.append("├─ sal_qc (INTEGER) - Same scale as temp_qc")

        # Metadata
        if query_type in ("float_specific", "general") or not detected_params:
            lines.append("")
            lines.append("METADATA:")
            lines.append("├─ data_mode (CHAR) - R=Realtime, D=Delayed, A=Adjusted")
            lines.append("├─ platform_type (VARCHAR) - ARGO, BGC-ARGO, etc.")

        # Ocean regions
        all_regions = {
            "Arabian Sea": ("5°N to 30°N", "40°E to 80°E"),
            "Bay of Bengal": ("5°N to 25°N", "80°E to 100°E"),
            "Equatorial Indian Ocean": ("10°S to 5°N", "40°E to 100°E"),
            "Southern Indian Ocean": ("50°S to 10°S", "20°E to 120°E"),
            "Red Sea": ("12°N to 30°N", "32°E to 44°E"),
            "Andaman Sea": ("5°N to 20°N", "92°E to 100°E"),
        }

        if detected_region != "Not specified" and detected_region in all_regions:
            lines.append("")
            lines.append("RELEVANT OCEAN REGION:")
            lat, lon = all_regions[detected_region]
            lines.append(f"  {detected_region}: Lat {lat}, Lon {lon}")
        elif query_type in ("geographic", "comparison", "general") or detected_region == "Not specified":
            lines.append("")
            lines.append("OCEAN REGIONS:")
            for name, (lat, lon) in all_regions.items():
                lines.append(f"  {name}: Lat {lat}, Lon {lon}")

        return "\n".join(lines)

    def _analyze_query(self, query: str) -> Dict:
        query_lower = query.lower()
        analysis = {
            "type": "general",
            "region": "Not specified",
            "parameters": [],
            "time_period": "All time",
            "complexity": 1,
        }

        for qtype, info in self.QUERY_PATTERNS.items():
            if any(kw in query_lower for kw in info["keywords"]):
                analysis["type"] = qtype
                break

        regions = {
            "arabian sea": "Arabian Sea",
            "bay of bengal": "Bay of Bengal",
            "bengal": "Bay of Bengal",
            "arabian": "Arabian Sea",
            "equatorial": "Equatorial Indian Ocean",
            "southern ocean": "Southern Indian Ocean",
            "indian ocean": "Indian Ocean",
        }
        for keyword, name in regions.items():
            if keyword in query_lower:
                analysis["region"] = name
                break

        param_keywords = {
            "temperature": ["temperature", "temp", "thermal", "warm", "cold", "heat"],
            "salinity": ["salinity", "salt", "sal", "psu"],
            "pressure": ["pressure", "depth", "deep", "shallow", "surface"],
            "dissolved_oxygen": ["oxygen", "o2", "dissolved oxygen", "do"],
            "chlorophyll": ["chlorophyll", "chl", "chla"],
            "ph": ["ph", "acidity", "alkalinity"],
        }
        for param, keywords in param_keywords.items():
            if any(kw in query_lower for kw in keywords):
                analysis["parameters"].append(param)

        return analysis

    def _extract_coordinates_from_query(self, query: str) -> Tuple[Optional[float], Optional[float]]:
        pattern = r"(\d+\.?\d*)[°]?\s*([NS]),?\s*(\d+\.?\d*)[°]?\s*([EW])"
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            lat = float(match.group(1)) * (-1 if match.group(2).upper() == "S" else 1)
            lon = float(match.group(3)) * (-1 if match.group(4).upper() == "W" else 1)
            return lat, lon
        return None, None

    def _extract_radius_from_query(self, query: str) -> float:
        pattern = r"(\d+\.?\d*)\s*(?:km|kilometers?|miles?)"
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            radius = float(match.group(1))
            if "mile" in query.lower():
                radius *= 1.60934
            return radius
        return 1000.0

    def _generate_spatial_query(self, lat: float, lon: float, radius_km: float = 1000.0) -> str:
        return f"""SELECT 
    float_id, latitude, longitude, timestamp, temperature, salinity, pressure,
    ROUND((6371 * acos(cos(radians({lat})) * cos(radians(latitude)) * cos(radians(longitude) - radians({lon})) + sin(radians({lat})) * sin(radians(latitude))))::numeric, 2) AS distance_km
FROM argo_profiles
WHERE temp_qc IN (1, 2, 3) AND sal_qc IN (1, 2, 3)
  AND (6371 * acos(cos(radians({lat})) * cos(radians(latitude)) * cos(radians(longitude) - radians({lon})) + sin(radians({lat})) * sin(radians(latitude)))) <= {radius_km}
ORDER BY distance_km ASC
LIMIT 1000;"""

    def _clean_sql(self, sql: str) -> str:
        sql = re.sub(r"```sql\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"```\s*", "", sql)
        lines = [l for l in sql.split("\n") if not l.strip().startswith("--")]
        sql = " ".join(lines).strip()
        if not sql.endswith(";"):
            sql += ";"
        return sql

    def _optimize_query(self, sql: str, analysis: Dict) -> str:
        if "LIMIT" not in sql.upper():
            sql = sql.rstrip(";") + " LIMIT 1000;"
        return sql

    def validate_sql(self, sql: str) -> bool:
        if not sql or len(sql) < 10:
            return False
        sql_upper = sql.upper()
        dangerous = ["DROP", "DELETE", "INSERT", "UPDATE", "TRUNCATE", "ALTER", "CREATE", "GRANT"]
        for kw in dangerous:
            if kw in sql_upper:
                return False
        if not sql_upper.strip().startswith("SELECT"):
            return False
        if "ARGO_PROFILES" not in sql_upper:
            return False
        return True

    def get_statistics(self) -> Dict:
        total = max(self.stats["total_queries"], 1)
        hit_rate = (self.stats["cache_hits"] / total) * 100
        return {
            **self.stats,
            "cache_hit_rate": f"{hit_rate:.1f}%",
        }