# mcp_server/mcp_server.py
"""
Free MCP Server Implementation for FloatChat
Provides tools for Claude/LLMs to use FloatChat capabilities
No external paid services needed - all built-in tools
"""

import json
import sys
from typing import Any
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_engine.query_processor import QueryProcessor
# from rag_engine.sql_generator import AdvancedSQLGenerator 
from rag_engine.sql_generator import EnhancedSQLGenerator
from database.db_setup import DatabaseSetup
from database.models import ArgoProfile
from data_processing.regions import ALLOWED_PARAMETERS
from vector_store.vector_db import FAISSVectorStore
import pandas as pd
from sqlalchemy import text

# Columns we allow in dynamic aggregation (whitelist, NOT user-controlled strings)
BGC_COLUMNS = ["dissolved_oxygen", "chlorophyll", "ph"]

class MCPToolServer:
    """
    Implements MCP (Model Context Protocol) tools.
    These are FREE tools that any Claude-compatible system can use.
    """
    
    def __init__(self):
        self.query_processor = QueryProcessor()
        # self.sql_generator = AdvancedSQLGenerator()
        self.sql_generator = EnhancedSQLGenerator()
        self.db_setup = DatabaseSetup()
        self.vector_store = FAISSVectorStore()
        self.vector_store.load()
    
    def get_available_tools(self) -> list:
        """Return list of available MCP tools"""
        return [
            {
                "name": "query_argo_data",
                "description": "Query ARGO ocean float data using natural language",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query about ARGO data"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return (default: 1000)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "generate_sql",
                "description": "Generate SQL query from natural language",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Question in natural language"
                        },
                        "context": {
                            "type": "string",
                            "description": "Optional context about the query"
                        }
                    },
                    "required": ["question"]
                }
            },
            {
                "name": "search_similar_profiles",
                "description": "Find similar ARGO profiles using semantic search",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query_text": {
                            "type": "string",
                            "description": "Description of what you're looking for"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of similar profiles to return (default: 5)"
                        }
                    },
                    "required": ["query_text"]
                }
            },
            {
                "name": "get_database_schema",
                "description": "Get ARGO database schema and statistics",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "analyze_profile",
                "description": "Detailed analysis of an ARGO profile",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "float_id": {
                            "type": "string",
                            "description": "Float identifier"
                        },
                        "cycle_number": {
                            "type": "integer",
                            "description": "Cycle number (optional)"
                        }
                    },
                    "required": ["float_id"]
                }
            },
            {
                "name": "compare_regions",
                "description": "Compare oceanographic conditions between regions",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "region1": {
                            "type": "string",
                            "description": "First ocean region"
                        },
                        "region2": {
                            "type": "string",
                            "description": "Second ocean region"
                        },
                        "parameter": {
                            "type": "string",
                            "description": "Parameter to compare (temperature, salinity, etc)"
                        }
                    },
                    "required": ["region1", "region2", "parameter"]
                }
            },
            {
                "name": "get_bgc_data",
                "description": "Get BGC (Bio-Geo-Chemical) parameter data",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "parameters": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "BGC parameters: dissolved_oxygen, chlorophyll, ph, nitrate"
                        },
                        "region": {
                            "type": "string",
                            "description": "Ocean region (optional)"
                        }
                    },
                    "required": ["parameters"]
                }
            },
            {
                "name": "temporal_analysis",
                "description": "Analyze temporal trends in ARGO data",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "region": {
                            "type": "string",
                            "description": "Ocean region"
                        },
                        "parameter": {
                            "type": "string",
                            "description": "Parameter to analyze"
                        },
                        "period": {
                            "type": "string",
                            "description": "Time period (last_month, last_quarter, last_year, custom)"
                        }
                    },
                    "required": ["region", "parameter"]
                }
            }
        ]
    
    def execute_tool(self, tool_name: str, **kwargs) -> dict:
        """Execute an MCP tool"""
        try:
            if tool_name == "query_argo_data":
                return self._query_argo_data(kwargs)
            elif tool_name == "generate_sql":
                return self._generate_sql(kwargs)
            elif tool_name == "search_similar_profiles":
                return self._search_similar_profiles(kwargs)
            elif tool_name == "get_database_schema":
                return self._get_database_schema(kwargs)
            elif tool_name == "analyze_profile":
                return self._analyze_profile(kwargs)
            elif tool_name == "compare_regions":
                return self._compare_regions(kwargs)
            elif tool_name == "get_bgc_data":
                return self._get_bgc_data(kwargs)
            elif tool_name == "temporal_analysis":
                return self._temporal_analysis(kwargs)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            return {"error": str(e), "tool": tool_name}
    
    def _query_argo_data(self, params: dict) -> dict:
        """Query ARGO data using RAG pipeline"""
        query = params.get("query")
        limit = params.get("limit", 1000)
        
        result = self.query_processor.process_query(query)
        
        if result['success']:
            df = result['results']
            
            # CRITICAL FIX: Only apply limit if we have MORE records than limit
            # Don't artificially inflate the result count
            actual_records = len(df)
            data_to_return = df.head(limit).to_dict('records') if actual_records > limit else df.to_dict('records')
            
            print(f"🔍 Query returned {actual_records} records, sending {len(data_to_return)} to client")
            
            return {
                "success": True,
                "record_count": len(data_to_return),  # Return actual count, not inflated
                "total_matched": actual_records,  # Total that matched the query
                "data": data_to_return,
                "sql": result['sql'],
                "execution_time": result.get('execution_time', 0)
            }
        else:
            return {"success": False, "error": result.get('error')}
    
    def _generate_sql(self, params: dict) -> dict:
        """Generate SQL from natural language"""
        question = params.get("question")
        context = params.get("context", "")
        
        sql = self.sql_generator.generate_sql(question, context)
        
        return {
            "success": True if sql else False,
            "sql": sql,
            "question": question
        }
    
    def _search_similar_profiles(self, params: dict) -> dict:
        """Search for similar profiles using semantic search"""
        query_text = params.get("query_text")
        top_k = params.get("top_k", 5)
        
        from vector_store.embeddings import EmbeddingGenerator
        generator = EmbeddingGenerator()
        embedding = generator.generate_embedding(query_text)
        
        results = self.vector_store.search(embedding, k=top_k)
        
        return {
            "success": True,
            "query": query_text,
            "similar_profiles": [
                {
                    "similarity_score": float(score),
                    "profile_info": metadata
                }
                for score, metadata in results
            ]
        }
    
    def _get_database_schema(self, params: dict) -> dict:
        """Get database schema and statistics"""
        session = self.db_setup.get_session()

        try:
            # Get table statistics
            record_count = session.query(ArgoProfile).count()
            unique_floats = session.query(ArgoProfile.float_id).distinct().count()
        finally:
            session.close()

        # Get available columns
        columns = {
            "core": ["latitude", "longitude", "timestamp", "pressure", "temperature", "salinity"],
            "bgc": list(BGC_COLUMNS),
            "metadata": ["float_id", "cycle_number", "data_mode", "platform_type", "ocean_region"],
            "qc": ["temp_qc", "sal_qc"]
        }

        return {
            "success": True,
            "total_records": record_count,
            "unique_floats": unique_floats,
            "columns": columns,
            "database": "PostgreSQL - ARGO Profiles"
        }

    def _analyze_profile(self, params: dict) -> dict:
        """Analyze specific profile (parameterized — injection-safe)"""
        float_id = str(params.get("float_id", "")).strip()
        if not float_id:
            return {"success": False, "error": "float_id is required"}

        cycle_number = params.get("cycle_number")
        session = self.db_setup.get_session()

        try:
            # Parameterized LIKE: works for clean IDs and any legacy rows that
            # still carry the byte-string wrapper, without full-table scans
            sql = "SELECT * FROM argo_profiles WHERE float_id LIKE :fid"
            binds = {"fid": f"%{float_id}%"}
            if cycle_number is not None:
                sql += " AND cycle_number = :cycle"
                binds["cycle"] = int(cycle_number)

            df = pd.read_sql(text(sql), session.bind, params=binds)
        except (TypeError, ValueError) as e:
            return {"success": False, "error": f"Invalid cycle_number: {e}"}
        finally:
            session.close()

        if df.empty:
            return {"success": False, "error": "Profile not found"}

        def _safe_float(col: str) -> float:
            if col in df.columns and df[col].notna().any():
                return float(df[col].mean())
            return None

        # Analyze
        analysis = {
            "float_id": float_id,
            "cycle_number": cycle_number or "all",
            "measurements": len(df),
            "location": {
                "lat": _safe_float("latitude"),
                "lon": _safe_float("longitude")
            },
            "date_range": {
                "start": df['timestamp'].min().isoformat() if 'timestamp' in df.columns and df['timestamp'].notna().any() else None,
                "end": df['timestamp'].max().isoformat() if 'timestamp' in df.columns and df['timestamp'].notna().any() else None
            },
            "temperature": {
                "min": float(df['temperature'].min()) if 'temperature' in df.columns and df['temperature'].notna().any() else None,
                "max": float(df['temperature'].max()) if 'temperature' in df.columns and df['temperature'].notna().any() else None,
                "mean": _safe_float("temperature"),
                "std": float(df['temperature'].std()) if 'temperature' in df.columns and df['temperature'].notna().any() else None
            },
            "salinity": {
                "min": float(df['salinity'].min()) if 'salinity' in df.columns and df['salinity'].notna().any() else None,
                "max": float(df['salinity'].max()) if 'salinity' in df.columns and df['salinity'].notna().any() else None,
                "mean": _safe_float("salinity"),
                "std": float(df['salinity'].std()) if 'salinity' in df.columns and df['salinity'].notna().any() else None
            },
            "depth_range": {
                "min": _safe_float("pressure"),
                "max": _safe_float("pressure")
            }
        }

        return {"success": True, "analysis": analysis}

    def _compare_regions(self, params: dict) -> dict:
        """Compare two ocean regions (parameter whitelisted, injection-safe)"""
        region1 = str(params.get("region1", "")).strip()
        region2 = str(params.get("region2", "")).strip()
        parameter = str(params.get("parameter", "temperature")).strip().lower()

        if parameter not in ALLOWED_PARAMETERS:
            return {"success": False, "error": f"Unsupported parameter: {parameter}. Allowed: {sorted(ALLOWED_PARAMETERS)}"}
        if not region1 or not region2:
            return {"success": False, "error": "region1 and region2 are required"}

        session = self.db_setup.get_session()

        def _region_stats(region: str) -> dict:
            """Aggregate stats for one region. Bounded LIKE param — no injection."""
            query = text(f"""
                SELECT AVG({parameter}) AS mean,
                       MIN({parameter}) AS min,
                       MAX({parameter}) AS max,
                       STDDEV({parameter}) AS std,
                       COUNT(*) AS count
                FROM argo_profiles
                WHERE ocean_region ILIKE :region
                  AND {parameter} IS NOT NULL
            """)
            df = pd.read_sql(query, session.bind, params={"region": f"%{region}%"})
            if df.empty or df.iloc[0]["count"] == 0:
                return None
            row = df.iloc[0]
            return {
                "mean": float(row["mean"]) if row["mean"] is not None else None,
                "min": float(row["min"]) if row["min"] is not None else None,
                "max": float(row["max"]) if row["max"] is not None else None,
                "std": float(row["std"]) if row["std"] is not None else None,
                "measurements": int(row["count"])
            }

        try:
            stats1 = _region_stats(region1)
            stats2 = _region_stats(region2)
        finally:
            session.close()

        if stats1 is None or stats2 is None:
            return {
                "success": False,
                "error": "Insufficient data for one or both regions",
                "region1_stats": stats1,
                "region2_stats": stats2
            }

        diff = stats1["mean"] - stats2["mean"] if stats1["mean"] is not None and stats2["mean"] is not None else None
        return {
            "success": True,
            "parameter": parameter,
            "region1": region1,
            "region2": region2,
            "region1_stats": stats1,
            "region2_stats": stats2,
            "difference": abs(diff) if diff is not None else None,
            "higher_region": region1 if (diff or 0) >= 0 else region2
        }

    def _get_bgc_data(self, params: dict) -> dict:
        """Get BGC parameter data (single WHERE clause, whitelisted columns)"""
        requested = [str(p).strip().lower() for p in params.get("parameters", [])]
        parameters = [p for p in requested if p in ALLOWED_PARAMETERS]
        if not parameters:
            parameters = list(BGC_COLUMNS)

        region = str(params.get("region", "")).strip() or None

        cols = ",".join(parameters)
        clauses = [f"{p} IS NOT NULL" for p in parameters]
        binds = {}
        if region:
            clauses.append("ocean_region ILIKE :region")
            binds["region"] = f"%{region}%"

        query = f"SELECT latitude, longitude, timestamp, {cols} FROM argo_profiles WHERE " + " AND ".join(clauses)

        session = self.db_setup.get_session()
        try:
            df = pd.read_sql(text(query), session.bind, params=binds)
        finally:
            session.close()

        return {
            "success": True,
            "bgc_data": df.to_dict("records"),
            "record_count": len(df)
        }

    def _temporal_analysis(self, params: dict) -> dict:
        """Analyze temporal trends (parameter whitelisted, injection-safe)"""
        region = str(params.get("region", "")).strip() or None
        parameter = str(params.get("parameter", "temperature")).strip().lower()
        period = str(params.get("period", "last_month")).strip().lower()

        if parameter not in ALLOWED_PARAMETERS:
            return {"success": False, "error": f"Unsupported parameter: {parameter}. Allowed: {sorted(ALLOWED_PARAMETERS)}"}

        if period == "last_month":
            time_filter = "timestamp >= CURRENT_DATE - INTERVAL '1 month'"
        elif period == "last_quarter":
            time_filter = "timestamp >= CURRENT_DATE - INTERVAL '3 months'"
        elif period == "last_year":
            time_filter = "timestamp >= CURRENT_DATE - INTERVAL '1 year'"
        else:
            time_filter = "timestamp >= CURRENT_DATE - INTERVAL '1 year'"

        binds = {}
        region_clause = ""
        if region:
            region_clause = " AND ocean_region ILIKE :region"
            binds["region"] = f"%{region}%"

        query = f"""
        SELECT DATE_TRUNC('day', timestamp) as date,
               AVG({parameter}) as avg_value,
               COUNT(*) as measurements
        FROM argo_profiles
        WHERE {time_filter}{region_clause}
        GROUP BY DATE_TRUNC('day', timestamp) ORDER BY date
        """

        session = self.db_setup.get_session()
        try:
            df = pd.read_sql(text(query), session.bind, params=binds)
        finally:
            session.close()

        return {
            "success": True,
            "temporal_data": df.to_dict("records"),
            "region": region,
            "parameter": parameter,
            "period": period
        }


# HTTP Server wrapper for MCP (Optional - for web integration)
if __name__ == "__main__":
    server = MCPToolServer()
    
    # Print available tools
    tools = server.get_available_tools()
    print("Available MCP Tools:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")
    
    # Example: Execute a tool
    result = server.execute_tool(
        "get_database_schema"
    )
    print("\nDatabase Schema:", json.dumps(result, indent=2))