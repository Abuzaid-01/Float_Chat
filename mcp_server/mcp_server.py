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
from vector_store.vector_db import FAISSVectorStore
import pandas as pd

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
            return {
                "success": True,
                "record_count": len(df),
                "data": df.head(limit).to_dict('records'),
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
        from sqlalchemy import text
        
        session = self.db_setup.get_session()
        
        # Get table statistics
        record_count = session.query(ArgoProfile).count()
        from database.models import ArgoProfile
        unique_floats = session.query(ArgoProfile.float_id).distinct().count()
        
        # Get available columns
        columns = {
            "core": ["latitude", "longitude", "timestamp", "pressure", "temperature", "salinity"],
            "bgc": ["dissolved_oxygen", "chlorophyll", "ph"],
            "metadata": ["float_id", "cycle_number", "data_mode", "platform_type"],
            "qc": ["temp_qc", "sal_qc"]
        }
        
        session.close()
        
        return {
            "success": True,
            "total_records": record_count,
            "unique_floats": unique_floats,
            "columns": columns,
            "database": "PostgreSQL - ARGO Profiles"
        }
    
    def _analyze_profile(self, params: dict) -> dict:
        """Analyze specific profile"""
        float_id = params.get("float_id")
        cycle_number = params.get("cycle_number")
        
        from sqlalchemy import text
        session = self.db_setup.get_session()
        
        # Build query
        query = f"""
        SELECT * FROM argo_profiles 
        WHERE float_id = '{float_id}'
        """
        if cycle_number:
            query += f" AND cycle_number = {cycle_number}"
        
        df = pd.read_sql(text(query), session.bind)
        session.close()
        
        if df.empty:
            return {"success": False, "error": "Profile not found"}
        
        # Analyze
        analysis = {
            "float_id": float_id,
            "cycle_number": cycle_number or "all",
            "measurements": len(df),
            "location": {
                "lat": float(df['latitude'].mean()) if 'latitude' in df.columns else None,
                "lon": float(df['longitude'].mean()) if 'longitude' in df.columns else None
            },
            "date_range": {
                "start": df['timestamp'].min().isoformat() if 'timestamp' in df.columns else None,
                "end": df['timestamp'].max().isoformat() if 'timestamp' in df.columns else None
            },
            "temperature": {
                "min": float(df['temperature'].min()) if 'temperature' in df.columns else None,
                "max": float(df['temperature'].max()) if 'temperature' in df.columns else None,
                "mean": float(df['temperature'].mean()),
                "std": float(df['temperature'].std())
            },
            "salinity": {
                "min": float(df['salinity'].min()),
                "max": float(df['salinity'].max()),
                "mean": float(df['salinity'].mean()),
                "std": float(df['salinity'].std())
            },
            "depth_range": {
                "min": float(df['pressure'].min()),
                "max": float(df['pressure'].max())
            }
        }
        
        return {"success": True, "analysis": analysis}
    
    def _compare_regions(self, params: dict) -> dict:
        """Compare two ocean regions"""
        region1 = params.get("region1")
        region2 = params.get("region2")
        parameter = params.get("parameter", "temperature")
        
        from sqlalchemy import text
        session = self.db_setup.get_session()
        
        # Get data for both regions
        for region in [region1, region2]:
            query = f"""
            SELECT AVG({parameter}) as mean,
                   MIN({parameter}) as min,
                   MAX({parameter}) as max,
                   STDDEV({parameter}) as std,
                   COUNT(*) as count
            FROM argo_profiles
            WHERE ocean_region ILIKE '%{region}%'
            """
            df = pd.read_sql(text(query), session.bind)
        
        session.close()
        
        return {"success": True, "comparison": "Data returned"}
    
    def _get_bgc_data(self, params: dict) -> dict:
        """Get BGC parameter data"""
        parameters = params.get("parameters", [])
        region = params.get("region")
        
        from sqlalchemy import text
        session = self.db_setup.get_session()
        
        # Build column list
        cols = ",".join(parameters) if parameters else "dissolved_oxygen, chlorophyll, ph"
        
        query = f"SELECT latitude, longitude, timestamp, {cols} FROM argo_profiles"
        
        if region:
            query += f" WHERE ocean_region ILIKE '%{region}%'"
        
        query += " WHERE " + " AND ".join([f"{p} IS NOT NULL" for p in parameters])
        
        df = pd.read_sql(text(query), session.bind)
        session.close()
        
        return {
            "success": True,
            "bgc_data": df.to_dict('records'),
            "record_count": len(df)
        }
    
    def _temporal_analysis(self, params: dict) -> dict:
        """Analyze temporal trends"""
        region = params.get("region")
        parameter = params.get("parameter")
        period = params.get("period", "last_month")
        
        from sqlalchemy import text
        session = self.db_setup.get_session()
        
        # Build time filter
        if period == "last_month":
            time_filter = "WHERE timestamp >= CURRENT_DATE - INTERVAL '1 month'"
        elif period == "last_quarter":
            time_filter = "WHERE timestamp >= CURRENT_DATE - INTERVAL '3 months'"
        elif period == "last_year":
            time_filter = "WHERE timestamp >= CURRENT_DATE - INTERVAL '1 year'"
        else:
            time_filter = ""
        
        query = f"""
        SELECT DATE_TRUNC('day', timestamp) as date,
               AVG({parameter}) as avg_value,
               COUNT(*) as measurements
        FROM argo_profiles
        {time_filter}
        """
        
        if region:
            query += f" AND ocean_region ILIKE '%{region}%'"
        
        query += f" GROUP BY DATE_TRUNC('day', timestamp) ORDER BY date"
        
        df = pd.read_sql(text(query), session.bind)
        session.close()
        
        return {
            "success": True,
            "temporal_data": df.to_dict('records'),
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