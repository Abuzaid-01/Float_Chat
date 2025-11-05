


# import os
# import re
# from typing import Dict, Optional, List
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_core.prompts import PromptTemplate
# from dotenv import load_dotenv

# load_dotenv()

# class AdvancedSQLGenerator:
#     """
#     Advanced SQL generator with schema-aware query generation
#     """
    
#     DATABASE_SCHEMA = """
#     Table: argo_profiles
    
#     Core Columns:
#     - id (INTEGER, Primary Key)
#     - float_id (VARCHAR) - Unique float identifier
#     - cycle_number (INTEGER) - Measurement cycle (1, 2, 3...)
#     - latitude (FLOAT) - Latitude (-90 to 90)
#     - longitude (FLOAT) - Longitude (-180 to 180)
#     - timestamp (TIMESTAMP) - Measurement datetime
#     - pressure (FLOAT) - Water pressure in dbar (1 dbar ≈ 1 meter depth)
#     - temperature (FLOAT) - Temperature in Celsius
#     - salinity (FLOAT) - Salinity in PSU (Practical Salinity Units)
    
#     BGC Parameters (may be NULL):
#     - dissolved_oxygen (FLOAT) - DO in μmol/kg
#     - chlorophyll (FLOAT) - Chlorophyll-a in mg/m³
#     - ph (FLOAT) - pH value (seawater pH scale)
    
#     Metadata:
#     - data_mode (VARCHAR) - R/D/A (Realtime/Delayed/Adjusted)
#     - platform_type (VARCHAR) - ARGO or BGC
#     - temp_qc (INTEGER) - Temperature QC flag (1=good, 2=probably good, 3=questionable, 4=bad)
#     - sal_qc (INTEGER) - Salinity QC flag (same scale)
#     - created_at (TIMESTAMP) - Record creation time
    
#     IMPORTANT: Only use columns listed above. Do NOT use nitrate, bbp700, or other unlisted columns.
    
#     Indexes:
#     - idx_lat_lon (latitude, longitude) - Geographic queries
#     - idx_timestamp (timestamp) - Time-based queries
#     - idx_float_id (float_id) - Float identification
#     - idx_spatial_temporal (latitude, longitude, timestamp) - Combined
    
#     Ocean Regions (Auto-detected):
#     - Arabian Sea: lat 5-30°N, lon 40-80°E
#     - Bay of Bengal: lat 5-25°N, lon 80-100°E
#     - Equatorial Indian Ocean: lat -10 to 5°N, lon 40-100°E
#     - Southern Indian Ocean: lat -50 to -10°N, lon 20-120°E
#     - Red Sea: lat 12-30°N, lon 32-44°E
    
#     Best Practices:
#     1. Always use LIMIT (max 10000)
#     2. Quality filter: WHERE temp_qc IN (1,2) AND sal_qc IN (1,2)
#     3. For depth: use pressure column (1 dbar ≈ 1 meter)
#     4. Date format: 'YYYY-MM-DD'
#     5. Avoid N+1 queries - use aggregations
#     6. Use proper indexes for performance
#     """
    
#     SQL_GENERATION_PROMPT = """You are an expert PostgreSQL query generator for oceanographic ARGO float data.

# Database Schema:
# {schema}

# User Query: {user_query}

# Context from similar profiles:
# {context}

# CRITICAL SQL RULES:
# 1. ALWAYS use PostgreSQL syntax (NOT MySQL)
# 2. ALWAYS include LIMIT (default 1000, max 10000)
# 3. ONLY use columns from the schema above - DO NOT use nitrate, bbp700, or other unlisted columns
# 4. Proper NULL handling: col IS NOT NULL
# 5. Date format: 'YYYY-MM-DD'
# 6. Case-insensitive searches: ILIKE instead of LIKE
# 7. Quality control filtering: WHERE temp_qc IN (1,2,3) AND sal_qc IN (1,2,3) for good data (1=good, 2=probably good, 3=probably bad but usable)
# 8. Geographic queries: lat BETWEEN X AND Y, lon BETWEEN X AND Y
# 9. Aggregations: Always GROUP BY related columns
# 10. Aliases: Use meaningful aliases
# 11. Comments: Add -- comments for complex logic
# 12. **FLOAT_ID FORMAT**: Float IDs are stored as "b'XXXXXX '" (with b' prefix, closing ', and trailing space)
#     Example: float_id = 'b''6904092 ''' (note the double quotes for escaping)
#     For float 6904092, use: WHERE float_id = 'b''6904092 '''

# Common Query Patterns:

# Geographic Search:
# SELECT * FROM argo_profiles 
# WHERE latitude BETWEEN 10 AND 20 
#   AND longitude BETWEEN 60 AND 80
#   AND temp_qc IN (1,2)
# ORDER BY timestamp DESC
# LIMIT 1000;

# Recent Data (Last N Days):
# SELECT * FROM argo_profiles 
# WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
#   AND temp_qc IN (1,2)
# ORDER BY timestamp DESC
# LIMIT 1000;

# Regional Statistics:
# SELECT 
#     AVG(temperature) as avg_temp,
#     MIN(temperature) as min_temp,
#     MAX(temperature) as max_temp,
#     AVG(salinity) as avg_salinity,
#     COUNT(*) as measurements
# FROM argo_profiles
# WHERE ocean_region = 'Arabian Sea'
#   AND timestamp >= CURRENT_DATE - INTERVAL '1 month'
#   AND temp_qc IN (1,2);

# Profile Analysis:
# SELECT * FROM argo_profiles
# WHERE float_id = '2902696'
#   AND cycle_number = 100
# ORDER BY pressure ASC;

# BGC Analysis:
# SELECT latitude, longitude, timestamp, 
#        dissolved_oxygen, chlorophyll, ph
# FROM argo_profiles
# WHERE dissolved_oxygen IS NOT NULL
#   AND chlorophyll IS NOT NULL
#   AND ocean_region = 'Arabian Sea'
# LIMIT 1000;

# Temporal Trend:
# SELECT DATE_TRUNC('day', timestamp) as date,
#        AVG(temperature) as avg_temp,
#        COUNT(*) as measurements
# FROM argo_profiles
# WHERE ocean_region = 'Bay of Bengal'
#   AND temp_qc IN (1,2)
# GROUP BY DATE_TRUNC('day', timestamp)
# ORDER BY date DESC
# LIMIT 30;

# Regional Comparison:
# SELECT ocean_region,
#        AVG(temperature) as avg_temp,
#        AVG(salinity) as avg_sal,
#        COUNT(*) as measurements
# FROM argo_profiles
# WHERE temp_qc IN (1,2)
#   AND timestamp >= CURRENT_DATE - INTERVAL '1 month'
# GROUP BY ocean_region
# ORDER BY measurements DESC;

# Float Trajectory:
# SELECT latitude, longitude, timestamp, 
#        temperature, salinity, cycle_number
# FROM argo_profiles
# WHERE float_id = '2902696'
# ORDER BY timestamp ASC
# LIMIT 5000;

# IMPORTANT: 
# - Return ONLY the SQL query
# - Use proper formatting and indentation
# - Include helpful comments for complex queries
# - Validate all column names against schema
# - Ensure WHERE clauses are complete

# Generate the optimized PostgreSQL query:"""
    
#     def __init__(self):
#         self.llm = ChatGoogleGenerativeAI(
#             model=os.getenv('GOOGLE_MODEL', 'gemini-2.5-flash'),
#             temperature=0.0,  # Deterministic for SQL
#             google_api_key=os.getenv('GOOGLE_API_KEY')
#         )
        
#         self.prompt_template = PromptTemplate(
#             input_variables=["user_query", "context", "schema"],
#             template=self.SQL_GENERATION_PROMPT
#         )
        
#         self.common_patterns = self._init_patterns()
    
#     def _init_patterns(self) -> Dict:
#         """Initialize common query patterns"""
#         return {
#             'all_data': "SELECT * FROM argo_profiles ORDER BY timestamp DESC LIMIT 1000;",
#             'recent_month': "SELECT * FROM argo_profiles WHERE timestamp >= CURRENT_DATE - INTERVAL '1 month' ORDER BY timestamp DESC LIMIT 1000;",
#             'region_stats': "SELECT ocean_region, COUNT(*) as count, AVG(temperature) as avg_temp FROM argo_profiles GROUP BY ocean_region ORDER BY count DESC;",
#             'float_profile': "SELECT * FROM argo_profiles WHERE float_id = {float_id} ORDER BY timestamp DESC LIMIT 1000;",
#             'depth_analysis': "SELECT pressure, AVG(temperature) as avg_temp, AVG(salinity) as avg_sal FROM argo_profiles WHERE temp_qc IN (1,2) GROUP BY pressure ORDER BY pressure;",
#         }
    
#     def generate_sql(self, user_query: str, context: str = "") -> Optional[str]:
#         """
#         Generate SQL query with schema awareness
#         """
#         try:
#             # Check for quick patterns
#             quick_sql = self._check_quick_patterns(user_query)
#             if quick_sql:
#                 return quick_sql
            
#             # Generate using LLM with full schema
#             formatted_prompt = self.prompt_template.format(
#                 user_query=user_query,
#                 context=context,
#                 schema=self.DATABASE_SCHEMA
#             )
            
#             response = self.llm.invoke(formatted_prompt)
#             sql_query = self._clean_sql(response.content)
            
#             print(f"🔍 DEBUG - Generated SQL: {sql_query}")
            
#             # Validate
#             if not self.validate_sql(sql_query):
#                 print(f"⚠️ SQL validation failed for: {sql_query}")
#                 return None
            
#             # Optimize
#             sql_query = self._optimize_query(sql_query)
            
#             print(f"✅ Generated SQL: {sql_query[:80]}...")
#             return sql_query
            
#         except Exception as e:
#             print(f"❌ SQL generation error: {e}")
#             return None
    
#     def _check_quick_patterns(self, query: str) -> Optional[str]:
#         """Check for common quick patterns"""
#         query_lower = query.lower()
        
#         if any(w in query_lower for w in ['show all', 'get all', 'everything', 'all data']):
#             return self.common_patterns['all_data']
        
#         if 'recent' in query_lower or 'last month' in query_lower:
#             return self.common_patterns['recent_month']
        
#         if 'region' in query_lower and 'stat' in query_lower:
#             return self.common_patterns['region_stats']
        
#         return None
    
#     def _clean_sql(self, sql: str) -> str:
#         """Clean SQL from markdown and extra whitespace"""
#         sql = re.sub(r'```sql\s*', '', sql, flags=re.IGNORECASE)
#         sql = re.sub(r'```\s*', '', sql)
#         sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
#         sql = ' '.join(sql.split())
#         sql = sql.strip()
        
#         if not sql.endswith(';'):
#             sql += ';'
        
#         return sql
    
#     def _optimize_query(self, sql: str) -> str:
#         """Optimize SQL query"""
#         # Add LIMIT if missing
#         if 'LIMIT' not in sql.upper():
#             sql = sql.rstrip(';') + ' LIMIT 1000;'
        
#         # Ensure reasonable LIMIT
#         limit_match = re.search(r'LIMIT\s+(\d+)', sql, re.IGNORECASE)
#         if limit_match:
#             limit_val = int(limit_match.group(1))
#             if limit_val > 10000:
#                 sql = re.sub(r'LIMIT\s+\d+', 'LIMIT 10000', sql, flags=re.IGNORECASE)
        
#         return sql
    
#     def validate_sql(self, sql: str) -> bool:
#         """Comprehensive SQL validation"""
#         if not sql or len(sql) < 10:
#             print(f"❌ Validation failed: SQL too short or empty")
#             return False
        
#         sql_upper = sql.upper()
        
#         # Check dangerous operations
#         dangerous = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'TRUNCATE', 'ALTER',
#                     'CREATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE']
        
#         for keyword in dangerous:
#             if keyword in sql_upper:
#                 print(f"❌ Validation failed: Dangerous keyword '{keyword}' found")
#                 return False
        
#         # Must be SELECT
#         if not sql_upper.strip().startswith('SELECT'):
#             print(f"❌ Validation failed: Query must start with SELECT, got: {sql[:50]}")
#             return False
        
#         # Check valid table
#         if 'ARGO_PROFILES' not in sql_upper:
#             print(f"❌ Validation failed: Table 'argo_profiles' not found in query")
#             return False
        
#         # No multiple statements
#         if sql.count(';') > 1:
#             print(f"❌ Validation failed: Multiple statements detected")
#             return False
        
#         return True
    
#     def explain_query(self, sql: str) -> str:
#         """Generate human-readable explanation"""
#         try:
#             prompt = f"""Explain this SQL query in 2-3 sentences for oceanographers:\n\n{sql}\n\nFocus on what data it retrieves and why."""
#             response = self.llm.invoke(prompt)
#             return response.content
#         except:
#             return "Query explanation unavailable"







"""
Production-Grade SQL Generator for ARGO Data
Handles complex oceanographic queries with spatial, temporal, and parameter filters
"""

import os
import re
from typing import Dict, Optional, List, Tuple
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class EnhancedSQLGenerator:
    """
    Advanced SQL generator with:
    - Oceanographic domain knowledge
    - Spatial query optimization
    - Temporal reasoning
    - Parameter validation
    - Query complexity assessment
    """
    
    # Complete database schema with all columns
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
    
    BGC PARAMETERS (Bio-Geo-Chemical - May not be available in Core ARGO floats):
    ├─ dissolved_oxygen (FLOAT) - DO in μmol/kg [Check availability before filtering]
    ├─ chlorophyll (FLOAT) - Chlorophyll-a in mg/m³ [Check availability before filtering]
    ├─ ph (FLOAT) - pH on seawater scale [Check availability before filtering]
    
    NOTE: If user queries BGC parameters but they are not available, still generate SQL for available Core parameters (temp, salinity, pressure)
    
    QUALITY CONTROL:
    ├─ temp_qc (INTEGER) - Temperature QC flag
    ├─ sal_qc (INTEGER) - Salinity QC flag
    │   └─ QC VALUES: 1=good, 2=probably good, 3=questionable, 4=bad, 9=missing
    
    METADATA:
    ├─ data_mode (CHAR) - R=Realtime, D=Delayed, A=Adjusted
    ├─ platform_type (VARCHAR) - ARGO, BGC-ARGO, etc.
    ├─ created_at (TIMESTAMP) - Record creation time
    
    SPATIAL INDEXES:
    ├─ idx_lat_lon (latitude, longitude) - Geographic queries
    ├─ idx_timestamp (timestamp) - Temporal queries
    ├─ idx_float_id (float_id) - Float-specific queries
    ├─ idx_spatial_temporal (latitude, longitude, timestamp) - Combined
    
    OCEAN REGIONS (Auto-classified):
    Region Name                 | Lat Range    | Lon Range
    ─────────────────────────────────────────────────────────
    Arabian Sea                | 5°N to 30°N  | 40°E to 80°E
    Bay of Bengal              | 5°N to 25°N  | 80°E to 100°E
    Equatorial Indian Ocean    | 10°S to 5°N  | 40°E to 100°E
    Southern Indian Ocean      | 50°S to 10°S | 20°E to 120°E
    Red Sea                    | 12°N to 30°N | 32°E to 44°E
    Andaman Sea                | 5°N to 20°N  | 92°E to 100°E
    """
    
    # Enhanced query patterns with oceanographic context
    QUERY_PATTERNS = {
        'geographic': {
            'keywords': ['region', 'area', 'location', 'near', 'between', 'arabian', 'bengal', 'ocean', 'sea'],
            'requires': ['latitude', 'longitude']
        },
        'nearest': {
        'keywords': ['nearest', 'closest', 'near', 'within', 'around', 'proximity', 'distance'],
        'requires': ['spatial_query']
    },
        'temporal': {
            'keywords': ['recent', 'last', 'month', 'year', 'date', 'period', 'time', 'historical', 'trend'],
            'requires': ['timestamp']
        },
        'depth': {
            'keywords': ['deep', 'depth', 'pressure', 'surface', 'bottom', 'vertical', 'profile'],
            'requires': ['pressure']
        },
        'parameter': {
            'keywords': ['temperature', 'salinity', 'oxygen', 'chlorophyll', 'ph', 'bgc'],
            'requires': ['temperature', 'salinity']
        },
        'comparison': {
            'keywords': ['compare', 'difference', 'versus', 'vs', 'between'],
            'requires': ['GROUP BY', 'aggregation']
        },
        'statistics': {
            'keywords': ['average', 'mean', 'max', 'min', 'count', 'sum', 'statistics', 'distribution'],
            'requires': ['aggregation functions']
        },
        'float_specific': {
            'keywords': ['float', 'profile', 'cycle', 'trajectory'],
            'requires': ['float_id']
        }
    }
    
    def __init__(self):
        """Initialize SQL generator with LLM"""
        self.llm = ChatGoogleGenerativeAI(
            model=os.getenv('GOOGLE_MODEL', 'gemini-2.5-flash'),
            temperature=0.0,  # Deterministic for SQL
            google_api_key=os.getenv('GOOGLE_API_KEY'),
            timeout=30,
            max_retries=2
        )
        
        self.prompt_template = self._create_enhanced_prompt()
        
        # Query cache for optimization
        self.query_cache = {}
        
        # Statistics for monitoring
        self.stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'failed_queries': 0,
            'avg_complexity': 0
        }
        
        logger.info("✅ Enhanced SQL Generator initialized")
    
    def _create_enhanced_prompt(self) -> PromptTemplate:
        """Create comprehensive SQL generation prompt"""
        
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

1. FLOAT ID FORMAT (IMPORTANT):
   - Float IDs stored as: "b'XXXXXX '" (with b' prefix and trailing space)
   - Example: For float 6904092, use: WHERE float_id = 'b''6904092 '''
   - ALWAYS escape quotes: 'b''XXXXXX '''

2. QUALITY CONTROL:
   - Default: WHERE temp_qc IN (1,2,3) AND sal_qc IN (1,2,3)
   - For strict quality: WHERE temp_qc IN (1,2)
   - ALWAYS filter by QC unless explicitly asked not to

3. SPATIAL QUERIES:
   - Use: latitude BETWEEN x AND y AND longitude BETWEEN x AND y
   - Arabian Sea: lat 5-30, lon 40-80
   - Bay of Bengal: lat 5-25, lon 80-100
   - Use ST_Distance for radius queries (future enhancement)

4. TEMPORAL QUERIES:
   - Recent data: timestamp >= CURRENT_DATE - INTERVAL 'X days/months'
   - Specific date: timestamp >= 'YYYY-MM-DD' AND timestamp <= 'YYYY-MM-DD'
   - Current month: DATE_TRUNC('month', timestamp) = DATE_TRUNC('month', CURRENT_DATE)

5. DEPTH QUERIES:
   - Surface layer: pressure <= 10
   - Euphotic zone: pressure <= 200
   - Thermocline: pressure BETWEEN 50 AND 200
   - Deep ocean: pressure > 1000

6. AGGREGATIONS:
   - Always use GROUP BY for aggregates
   - Include meaningful statistics: COUNT, AVG, MIN, MAX, STDDEV
   - Use HAVING for filtered aggregates

7. PERFORMANCE:
   - ALWAYS add LIMIT (default 1000, max 10000)
   - Use indexes: lat/lon, timestamp, float_id
   - Avoid SELECT * - specify columns
   - Use EXISTS instead of IN for subqueries

8. NULL HANDLING:
   - Use IS NOT NULL for required parameters
   - Handle missing BGC data gracefully

9. ORDER BY:
   - Temporal: ORDER BY timestamp DESC
   - Depth profiles: ORDER BY pressure ASC
   - Geographic: ORDER BY latitude, longitude

10. OUTPUT FORMAT:
    - Return ONLY ONE valid PostgreSQL SQL statement
    - No markdown code blocks (no ```)
    - No explanations or comments before or after
    - No multiple statements (only ONE query)
    - **NO CTEs (WITH clauses) - use simple SELECT only**
    - **NO subqueries in FROM clause - use simple direct queries**
    - End with single semicolon
    - Use proper indentation

11. QUERY SIMPLIFICATION:
    - For lat/lon ranges: Use WHERE clause directly, not subqueries
    - For sample data + stats: Just SELECT the columns needed
    - Return raw data, let application calculate statistics
    - Avoid complex nested queries

EXAMPLE QUERIES:

-- Recent Arabian Sea data with good QC
SELECT latitude, longitude, timestamp, pressure, temperature, salinity
FROM argo_profiles
WHERE latitude BETWEEN 5 AND 30
  AND longitude BETWEEN 40 AND 80
  AND timestamp >= CURRENT_DATE - INTERVAL '30 days'
  AND temp_qc IN (1,2,3)
  AND sal_qc IN (1,2,3)
ORDER BY timestamp DESC
LIMIT 1000;

-- Temperature statistics by region and month
SELECT 
    CASE 
        WHEN latitude BETWEEN 5 AND 30 AND longitude BETWEEN 40 AND 80 THEN 'Arabian Sea'
        WHEN latitude BETWEEN 5 AND 25 AND longitude BETWEEN 80 AND 100 THEN 'Bay of Bengal'
        ELSE 'Other'
    END as region,
    DATE_TRUNC('month', timestamp) as month,
    COUNT(*) as measurements,
    ROUND(AVG(temperature)::numeric, 2) as avg_temp,
    ROUND(MIN(temperature)::numeric, 2) as min_temp,
    ROUND(MAX(temperature)::numeric, 2) as max_temp,
    ROUND(STDDEV(temperature)::numeric, 2) as std_temp
FROM argo_profiles
WHERE temp_qc IN (1,2,3)
  AND timestamp >= CURRENT_DATE - INTERVAL '6 months'
GROUP BY region, month
ORDER BY month DESC, region
LIMIT 1000;

-- Specific float profile with depth ordering
SELECT cycle_number, pressure, temperature, salinity, 
       dissolved_oxygen, chlorophyll
FROM argo_profiles
WHERE float_id = 'b''6904092 '''
  AND cycle_number = 145
  AND temp_qc IN (1,2,3)
ORDER BY pressure ASC
LIMIT 1000;

-- Deep profiles (>1000m) with BGC parameters
SELECT float_id, latitude, longitude, timestamp, pressure,
       temperature, salinity, dissolved_oxygen, ph
FROM argo_profiles
WHERE pressure > 1000
  AND dissolved_oxygen IS NOT NULL
  AND temp_qc IN (1,2,3)
ORDER BY pressure DESC
LIMIT 1000;

RESPOND WITH ONLY THE SQL QUERY (ONE STATEMENT, NO EXPLANATIONS):"""

        return PromptTemplate(
            input_variables=[
                "schema", "user_query", "context", "query_type",
                "region", "parameters", "time_period"
            ],
            template=template
        )
    def generate_sql(
        self,
        user_query: str,
        context: str = "",
        force_regenerate: bool = False
    ) -> Optional[str]:
        """
        Generate SQL with enhanced analysis and caching
        """
        self.stats['total_queries'] += 1
        
        # Check cache
        cache_key = f"{user_query}:{context}"
        if not force_regenerate and cache_key in self.query_cache:
            self.stats['cache_hits'] += 1
            logger.info("✅ Cache hit for query")
            return self.query_cache[cache_key]
        
        try:
            # Analyze query intent
            analysis = self._analyze_query(user_query)
            
            # ADD THIS: Check for spatial/nearest queries
            if analysis['type'] == 'nearest' or any(kw in user_query.lower() for kw in ['nearest', 'closest', 'within']):
                lat, lon = self._extract_coordinates_from_query(user_query)
                if lat is not None and lon is not None:
                    radius_km = self._extract_radius_from_query(user_query)
                    sql_query = self._generate_spatial_query(lat, lon, radius_km)
                    
                    if self.validate_sql(sql_query):
                        self.query_cache[cache_key] = sql_query
                        logger.info(f"✅ Generated spatial SQL: {sql_query[:80]}...")
                        return sql_query
            
            # ... rest of the method remains EXACTLY THE SAME
            # Format prompt with analysis
            formatted_prompt = self.prompt_template.format(
                schema=self.COMPLETE_SCHEMA,
                user_query=user_query,
                context=context or "No similar profiles found",
                query_type=analysis['type'],
                region=analysis['region'],
                parameters=', '.join(analysis['parameters']),
                time_period=analysis['time_period']
            )
            
            # ... rest remains same
    
    # def generate_sql(
    #     self,
    #     user_query: str,
    #     context: str = "",
    #     force_regenerate: bool = False
    # ) -> Optional[str]:
    #     """
    #     Generate SQL with enhanced analysis and caching
        
    #     Args:
    #         user_query: Natural language question
    #         context: Retrieved context from vector store
    #         force_regenerate: Skip cache and regenerate
            
    #     Returns:
    #         PostgreSQL query string or None if generation fails
    #     """
    #     self.stats['total_queries'] += 1
        
    #     # Check cache
    #     cache_key = f"{user_query}:{context}"
    #     if not force_regenerate and cache_key in self.query_cache:
    #         self.stats['cache_hits'] += 1
    #         logger.info("✅ Cache hit for query")
    #         return self.query_cache[cache_key]
        
    #     try:
    #         # Analyze query intent
    #         analysis = self._analyze_query(user_query)
            
    #         # Format prompt with analysis
    #         formatted_prompt = self.prompt_template.format(
    #             schema=self.COMPLETE_SCHEMA,
    #             user_query=user_query,
    #             context=context or "No similar profiles found",
    #             query_type=analysis['type'],
    #             region=analysis['region'],
    #             parameters=', '.join(analysis['parameters']),
    #             time_period=analysis['time_period']
    #         )
            
            # Generate SQL
            logger.info(f"🔧 Generating SQL for: {user_query[:50]}...")
            response = self.llm.invoke(formatted_prompt)
            sql = self._clean_sql(response.content)
            
            # Validate and optimize
            if not self.validate_sql(sql):
                logger.error("❌ Generated SQL failed validation")
                self.stats['failed_queries'] += 1
                return None
            
            sql = self._optimize_query(sql, analysis)
            
            # Cache result
            self.query_cache[cache_key] = sql
            
            logger.info(f"✅ Generated SQL: {sql[:80]}...")
            return sql
            
        except Exception as e:
            logger.error(f"❌ SQL generation error: {e}")
            self.stats['failed_queries'] += 1
            return None
    
    def _analyze_query(self, query: str) -> Dict:
        """
        Analyze query intent and extract key information
        
        Returns dict with:
        - type: Query type (geographic, temporal, etc.)
        - region: Detected ocean region
        - parameters: Requested parameters
        - time_period: Detected time range
        - complexity: Query complexity score
        """
        query_lower = query.lower()
        
        analysis = {
            'type': 'general',
            'region': 'Not specified',
            'parameters': [],
            'time_period': 'All time',
            'complexity': 1
        }
        
        # Detect query type
        for qtype, info in self.QUERY_PATTERNS.items():
            if any(kw in query_lower for kw in info['keywords']):
                analysis['type'] = qtype
                break
        
        # Detect region
        regions = {
            'arabian sea': ('Arabian Sea', (5, 30), (40, 80)),
            'bay of bengal': ('Bay of Bengal', (5, 25), (80, 100)),
            'bengal': ('Bay of Bengal', (5, 25), (80, 100)),
            'arabian': ('Arabian Sea', (5, 30), (40, 80)),
            'equatorial': ('Equatorial Indian Ocean', (-10, 5), (40, 100)),
            'southern ocean': ('Southern Indian Ocean', (-50, -10), (20, 120)),
            'indian ocean': ('Indian Ocean', (-50, 30), (20, 120)),
        }
        
        for keyword, (name, lat_range, lon_range) in regions.items():
            if keyword in query_lower:
                analysis['region'] = name
                analysis['lat_range'] = lat_range
                analysis['lon_range'] = lon_range
                break
        
        # Detect parameters
        param_keywords = {
            'temperature': ['temperature', 'temp', 'thermal', 'warm', 'cold', 'heat'],
            'salinity': ['salinity', 'salt', 'sal', 'psu'],
            'pressure': ['pressure', 'depth', 'deep', 'shallow', 'surface'],
            'dissolved_oxygen': ['oxygen', 'o2', 'dissolved oxygen', 'do'],
            'chlorophyll': ['chlorophyll', 'chl', 'chla', 'phytoplankton'],
            'ph': ['ph', 'acidity', 'alkalinity']
        }
        
        for param, keywords in param_keywords.items():
            if any(kw in query_lower for kw in keywords):
                analysis['parameters'].append(param)
        
        # Detect time period
        time_keywords = {
            'recent': 'Last 30 days',
            'last month': 'Last 30 days',
            'last year': 'Last 365 days',
            'last week': 'Last 7 days',
            '2025': 'Year 2025',
            '2024': 'Year 2024',
            'october': 'October',
            'november': 'November'
        }
        
        for keyword, period in time_keywords.items():
            if keyword in query_lower:
                analysis['time_period'] = period
                break
        
        # Calculate complexity
        complexity = 1
        if analysis['type'] in ['comparison', 'statistics']:
            complexity += 2
        if len(analysis['parameters']) > 2:
            complexity += 1
        if analysis['region'] != 'Not specified':
            complexity += 1
        
        analysis['complexity'] = complexity
        
        return analysis
    def _extract_coordinates_from_query(self, query: str) -> tuple:
        """Extract latitude and longitude from natural language query"""
        import re
        
        # Pattern 1: "15°N, 75°E" or "15N 75E" or "15.5°N, 75.2°E"
        pattern1 = r'(\d+\.?\d*)[°]?\s*([NS]),?\s*(\d+\.?\d*)[°]?\s*([EW])'
        match = re.search(pattern1, query, re.IGNORECASE)
        if match:
            lat = float(match.group(1))
            lat_dir = match.group(2).upper()
            lon = float(match.group(3))
            lon_dir = match.group(4).upper()
            
            # Apply direction: N=positive, S=negative, E=positive, W=negative
            if lat_dir == 'S':
                lat = -lat
            if lon_dir == 'W':
                lon = -lon
            return lat, lon
        
        # Pattern 2: "latitude 15 longitude 75"
        pattern2 = r'lat(?:itude)?\s+(\d+\.?\d*)\s+lon(?:gitude)?\s+(\d+\.?\d*)'
        match = re.search(pattern2, query, re.IGNORECASE)
        if match:
            return float(match.group(1)), float(match.group(2))
        
        # Pattern 3: Common locations (you can expand this)
        locations = {
            'mumbai': (19.0760, 72.8777),
            'chennai': (13.0827, 80.2707),
            'kochi': (9.9312, 76.2673),
            'port blair': (11.6234, 92.7265),
        }
        
        for location, coords in locations.items():
            if location in query.lower():
                return coords
        
        return None, None
    
    def _extract_radius_from_query(self, query: str) -> float:
        """Extract search radius from query"""
        import re
        
        # Pattern: "within 50km" or "50 km" or "100 kilometers"
        pattern = r'(\d+\.?\d*)\s*(?:km|kilometers?|miles?)'
        match = re.search(pattern, query, re.IGNORECASE)
        
        if match:
            radius = float(match.group(1))
            if 'mile' in query.lower():
                radius = radius * 1.60934  # Convert miles to km
            return radius
        
        # Default radius - increased to 1000km for Indian Ocean coverage
        # (Indian Ocean floats are sparse, typical spacing is 300-500km)
        return 1000.0  # 1000km default for better coverage
    










    
    
    
    
    
    def _clean_sql(self, sql: str) -> str:
        """Clean SQL from markdown and formatting"""
        # Remove markdown code blocks
        sql = re.sub(r'```sql\s*', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'```\s*', '', sql)
        
        # Remove any explanatory text before SQL
        lines = sql.split('\n')
        sql_lines = []
        in_sql = False
        
        for line in lines:
            line_upper = line.strip().upper()
            if line_upper.startswith('SELECT') or line_upper.startswith('WITH'):
                in_sql = True
            if in_sql:
                sql_lines.append(line)
        
        if sql_lines:
            sql = '\n'.join(sql_lines)
        
        # If there's a WITH clause (CTE), extract only the final SELECT
        # For this application, we want simple queries only
        if 'WITH' in sql.upper() or ' AS (' in sql.upper():
            # Try to extract just the main SELECT after the CTE
            # Better: reject CTEs and ask for simple query
            select_matches = list(re.finditer(r'\bSELECT\b', sql, re.IGNORECASE))
            if len(select_matches) > 1:
                # Multiple SELECTs found, take the last one (main query)
                last_select_pos = select_matches[-1].start()
                sql = sql[last_select_pos:]
        
        # Remove comments
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        
        # If multiple statements (separated by ;), keep only first
        statements = [s.strip() for s in sql.split(';') if s.strip() and 'SELECT' in s.upper()]
        if statements:
            sql = statements[0]
        
        # Normalize whitespace
        sql = ' '.join(sql.split())
        
        # Ensure ends with semicolon
        sql = sql.strip()
        if not sql.endswith(';'):
            sql += ';'
        
        return sql
    
    def _optimize_query(self, sql: str, analysis: Dict) -> str:
        """Optimize SQL query based on analysis"""
        
        # Add LIMIT if missing
        if 'LIMIT' not in sql.upper():
            sql = sql.rstrip(';') + ' LIMIT 5000;'  # Increased from 1000 to 5000
        
        # Ensure LIMIT is reasonable
        limit_match = re.search(r'LIMIT\s+(\d+)', sql, re.IGNORECASE)
        if limit_match:
            limit_val = int(limit_match.group(1))
            if limit_val > 10000:
                sql = re.sub(r'LIMIT\s+\d+', 'LIMIT 10000', sql, flags=re.IGNORECASE)
        
        # Add index hints for complex queries
        if analysis['complexity'] > 3:
            # This is PostgreSQL-specific optimization
            pass  # Could add query hints here
        
        return sql
    def _generate_spatial_query(
        self, 
        lat: float, 
        lon: float, 
        radius_km: float = 50.0
    ) -> str:
        """
        Generate spatial query using Haversine formula
        (Works without PostGIS extension)
        """
        
        # Haversine formula for distance calculation
        sql = f"""
SELECT 
    float_id,
    latitude,
    longitude,
    timestamp,
    temperature,
    salinity,
    pressure,
    ROUND(
        (6371 * acos(
            cos(radians({lat})) * cos(radians(latitude)) * 
            cos(radians(longitude) - radians({lon})) + 
            sin(radians({lat})) * sin(radians(latitude))
        ))::numeric, 2
    ) AS distance_km
FROM argo_profiles
WHERE temp_qc IN (1, 2, 3)
  AND sal_qc IN (1, 2, 3)
  AND (
    6371 * acos(
        cos(radians({lat})) * cos(radians(latitude)) * 
        cos(radians(longitude) - radians({lon})) + 
        sin(radians({lat})) * sin(radians(latitude))
    )
  ) <= {radius_km}
ORDER BY distance_km ASC
LIMIT 1000;
"""
        return sql
    
    def validate_sql(self, sql: str) -> bool:
        """
        Comprehensive SQL validation
        
        Checks:
        - SQL injection attempts
        - Dangerous operations
        - Table existence
        - Basic syntax
        """
        if not sql or len(sql) < 10:
            logger.error("SQL too short or empty")
            return False
        
        sql_upper = sql.upper()
        
        # Check dangerous operations
        dangerous = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'TRUNCATE',
            'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'EXEC',
            'EXECUTE', 'DECLARE', 'CURSOR'
        ]
        
        for keyword in dangerous:
            if keyword in sql_upper:
                logger.error(f"Dangerous keyword detected: {keyword}")
                return False
        
        # Must be SELECT
        if not sql_upper.strip().startswith('SELECT'):
            logger.error("Query must be SELECT")
            return False
        
        # Must reference argo_profiles
        if 'ARGO_PROFILES' not in sql_upper:
            logger.error("Must query argo_profiles table")
            return False
        
        # No multiple statements
        if sql.count(';') > 1:
            logger.error("Multiple statements detected")
            return False
        
        # Check for SQL injection patterns
        injection_patterns = [
            r"';",  # SQL injection terminator
            r"--",  # Comment injection
            r"/\*",  # Block comment
            r"xp_",  # SQL Server extended procedures
            r"sp_",  # SQL Server stored procedures
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, sql):
                logger.warning(f"Potential injection pattern: {pattern}")
                # Don't fail completely, just warn
        
        return True
    
    def explain_query(self, sql: str) -> str:
        """Generate human-readable explanation of SQL query"""
        try:
            prompt = f"""Explain this SQL query in 2-3 sentences for oceanographers:

{sql}

Focus on:
1. What ocean data it retrieves
2. Any filters or conditions applied
3. How results are organized

Keep it concise and scientific."""
            
            response = self.llm.invoke(prompt)
            return response.content
        except:
            return "Query explanation unavailable."
    
    def get_query_complexity(self, sql: str) -> Tuple[int, str]:
        """
        Assess query complexity
        
        Returns:
            (complexity_score, description)
            Scores: 1=Simple, 2=Moderate, 3=Complex, 4=Very Complex
        """
        sql_upper = sql.upper()
        score = 1
        factors = []
        
        if 'JOIN' in sql_upper:
            score += 2
            factors.append("table joins")
        
        if 'GROUP BY' in sql_upper:
            score += 1
            factors.append("aggregation")
        
        if 'HAVING' in sql_upper:
            score += 1
            factors.append("filtered aggregation")
        
        if 'CASE' in sql_upper:
            score += 1
            factors.append("conditional logic")
        
        if sql_upper.count('SELECT') > 1:
            score += 1
            factors.append("subqueries")
        
        descriptions = {
            1: "Simple",
            2: "Moderate",
            3: "Complex",
            4: "Very Complex"
        }
        
        desc = descriptions.get(min(score, 4), "Complex")
        if factors:
            desc += f" (includes: {', '.join(factors)})"
        
        return score, desc
    
    def get_statistics(self) -> Dict:
        """Get generator statistics"""
        cache_hit_rate = (
            self.stats['cache_hits'] / max(self.stats['total_queries'], 1) * 100
        )
        
        return {
            **self.stats,
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'success_rate': f"{((self.stats['total_queries'] - self.stats['failed_queries']) / max(self.stats['total_queries'], 1) * 100):.1f}%"
        }


# Singleton instance for the app
sql_generator = EnhancedSQLGenerator()