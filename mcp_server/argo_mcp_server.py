"""
ARGO-specific MCP Server Implementation
Provides oceanographic data tools following MCP protocol
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.mcp_protocol import (
    MCPProtocol, MCPToolCall, MCPResource, 
    MCPResourceProvider, MCPPromptTemplate, MCPPromptProvider
)
from rag_engine.query_processor import QueryProcessor
from database.db_setup import DatabaseSetup
from database.models import ArgoProfile
from vector_store.vector_db import FAISSVectorStore
from advanced_analytics.profile_analytics import AdvancedProfileAnalytics
import pandas as pd
from sqlalchemy import text
from typing import Dict, Any, List
import json


class ARGOMCPServer:
    """
    Production MCP Server for ARGO Float Data
    Implements full Model Context Protocol specification
    """
    
    def __init__(self):
        # Initialize MCP components
        self.protocol = MCPProtocol()
        self.resource_provider = MCPResourceProvider()
        self.prompt_provider = MCPPromptProvider()
        
        # Initialize data components
        self.db_setup = DatabaseSetup()
        self.query_processor = QueryProcessor()
        self.vector_store = FAISSVectorStore()
        self.vector_store.load()
        self.analytics = AdvancedProfileAnalytics()
        
        # Register all MCP tools
        self._register_tools()
        
        # Register MCP resources
        self._register_resources()
        
        # Register MCP prompts
        self._register_prompts()
        
        print("✅ ARGO MCP Server initialized with full protocol support")
    
    def _register_tools(self):
        """Register all ARGO tools with MCP protocol"""
        
        # Tool 1: Query ARGO Data
        self.protocol.register_tool(
            name="query_argo_data",
            description="Query ARGO ocean float data using natural language. Returns oceanographic measurements including temperature, salinity, pressure, and BGC parameters.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query about ARGO data (e.g., 'Show temperature in Arabian Sea')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 1000
                    }
                },
                "required": ["query"]
            },
            handler=self._handle_query_argo_data
        )
        
        # Tool 2: Get Database Schema
        self.protocol.register_tool(
            name="get_database_schema",
            description="Get the complete ARGO database schema including table structure, columns, data types, and available parameters.",
            input_schema={
                "type": "object",
                "properties": {}
            },
            handler=self._handle_get_schema
        )
        
        # Tool 3: Search Similar Profiles
        self.protocol.register_tool(
            name="search_similar_profiles",
            description="Find oceanographic profiles similar to a description using semantic search. Useful for discovering relevant historical data.",
            input_schema={
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "Description of what to search for (e.g., 'warm surface water in tropical regions')"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of similar profiles to return",
                        "default": 5
                    }
                },
                "required": ["query_text"]
            },
            handler=self._handle_search_similar
        )
        
        # Tool 4: Analyze Float Profile
        self.protocol.register_tool(
            name="analyze_float_profile",
            description="Perform detailed analysis of a specific ARGO float profile including statistics, depth ranges, and parameter distributions.",
            input_schema={
                "type": "object",
                "properties": {
                    "float_id": {
                        "type": "string",
                        "description": "ARGO float identifier"
                    },
                    "cycle_number": {
                        "type": "integer",
                        "description": "Optional cycle number for specific profile",
                        "default": None
                    }
                },
                "required": ["float_id"]
            },
            handler=self._handle_analyze_profile
        )
        
        # Tool 5: Calculate Thermocline
        self.protocol.register_tool(
            name="calculate_thermocline",
            description="Calculate thermocline characteristics (depth, strength, width) for oceanographic profiles.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query to get profiles for thermocline analysis"
                    }
                },
                "required": ["query"]
            },
            handler=self._handle_calculate_thermocline
        )
        
        # Tool 6: Identify Water Masses
        self.protocol.register_tool(
            name="identify_water_masses",
            description="Identify water masses based on T-S (Temperature-Salinity) characteristics. Returns water mass types and depth ranges.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query to get profiles for water mass analysis"
                    }
                },
                "required": ["query"]
            },
            handler=self._handle_identify_water_masses
        )
        
        # Tool 7: Regional Comparison
        self.protocol.register_tool(
            name="compare_regions",
            description="Compare oceanographic conditions between two ocean regions including temperature, salinity, and other parameters.",
            input_schema={
                "type": "object",
                "properties": {
                    "region1": {
                        "type": "string",
                        "description": "First region name (e.g., 'Arabian Sea')"
                    },
                    "region2": {
                        "type": "string",
                        "description": "Second region name (e.g., 'Bay of Bengal')"
                    },
                    "parameter": {
                        "type": "string",
                        "description": "Parameter to compare (temperature, salinity, etc.)",
                        "default": "temperature"
                    }
                },
                "required": ["region1", "region2"]
            },
            handler=self._handle_compare_regions
        )
        
        # Tool 8: Temporal Trend Analysis
        self.protocol.register_tool(
            name="analyze_temporal_trends",
            description="Analyze temporal trends in oceanographic parameters over time for a specific region.",
            input_schema={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Ocean region name"
                    },
                    "parameter": {
                        "type": "string",
                        "description": "Parameter to analyze (temperature, salinity, etc.)"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to analyze",
                        "default": 90
                    }
                },
                "required": ["region", "parameter"]
            },
            handler=self._handle_temporal_trends
        )
        
        # Tool 9: Get BGC Parameters
        self.protocol.register_tool(
            name="get_bgc_parameters",
            description="Retrieve Bio-Geo-Chemical (BGC) parameters including dissolved oxygen, chlorophyll, pH, and nutrients.",
            input_schema={
                "type": "object",
                "properties": {
                    "parameters": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "BGC parameters to retrieve: dissolved_oxygen, chlorophyll, ph, nitrate"
                    },
                    "region": {
                        "type": "string",
                        "description": "Optional region filter"
                    }
                },
                "required": ["parameters"]
            },
            handler=self._handle_get_bgc
        )
        
        # Tool 10: Calculate Mixed Layer Depth
        self.protocol.register_tool(
            name="calculate_mixed_layer_depth",
            description="Calculate Mixed Layer Depth (MLD) for oceanographic profiles using temperature threshold method.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query to get profiles for MLD calculation"
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Temperature difference threshold (°C)",
                        "default": 0.5
                    }
                },
                "required": ["query"]
            },
            handler=self._handle_calculate_mld
        )
    
    # Tool Handlers
    def _handle_query_argo_data(self, query: str, limit: int = 1000) -> Dict:
        """Handle ARGO data query"""
        import json
        from decimal import Decimal
        import pandas as pd
        import numpy as np
        
        result = self.query_processor.process_query(query)
        
        if result['success']:
            df = result['results'].head(limit)
            
            # Convert DataFrame to dict, handling Decimal and Timestamp types
            data_records = df.to_dict('records')
            
            # Convert non-JSON-serializable types to JSON-compatible types
            def convert_to_json_serializable(obj):
                """Recursively convert objects to JSON-serializable types"""
                if isinstance(obj, list):
                    return [convert_to_json_serializable(item) for item in obj]
                elif isinstance(obj, dict):
                    return {key: convert_to_json_serializable(value) for key, value in obj.items()}
                elif isinstance(obj, Decimal):
                    return float(obj)
                elif isinstance(obj, (pd.Timestamp, pd.DatetimeIndex)):
                    return obj.isoformat()
                elif isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif pd.isna(obj):
                    return None
                else:
                    return obj
            
            data_records = convert_to_json_serializable(data_records)
            
            return {
                "success": True,
                "record_count": len(df),
                "data": data_records,
                "sql": result['sql'],
                "execution_time": result.get('execution_time', 0)
            }
        else:
            return {"success": False, "error": result.get('error')}
    
    def _handle_get_schema(self) -> Dict:
        """Handle schema request"""
        session = self.db_setup.get_session()
        
        try:
            total_records = session.query(ArgoProfile).count()
            unique_floats = session.query(ArgoProfile.float_id).distinct().count()
            
            schema = {
                "table": "argo_profiles",
                "total_records": total_records,
                "unique_floats": unique_floats,
                "columns": {
                    "core": [
                        {"name": "latitude", "type": "FLOAT", "description": "Latitude (-90 to 90)"},
                        {"name": "longitude", "type": "FLOAT", "description": "Longitude (-180 to 180)"},
                        {"name": "timestamp", "type": "TIMESTAMP", "description": "Measurement datetime"},
                        {"name": "pressure", "type": "FLOAT", "description": "Water pressure in dbar"},
                        {"name": "temperature", "type": "FLOAT", "description": "Temperature in Celsius"},
                        {"name": "salinity", "type": "FLOAT", "description": "Salinity in PSU"}
                    ],
                    "bgc": [
                        {"name": "dissolved_oxygen", "type": "FLOAT", "description": "DO in μmol/kg"},
                        {"name": "chlorophyll", "type": "FLOAT", "description": "Chlorophyll in mg/m³"},
                        {"name": "ph", "type": "FLOAT", "description": "pH value"}
                    ],
                    "metadata": [
                        {"name": "float_id", "type": "VARCHAR", "description": "Float identifier"},
                        {"name": "cycle_number", "type": "INTEGER", "description": "Measurement cycle"},
                        {"name": "data_mode", "type": "VARCHAR", "description": "R/D/A mode"},
                        {"name": "platform_type", "type": "VARCHAR", "description": "Platform type"}
                    ],
                    "quality": [
                        {"name": "temp_qc", "type": "INTEGER", "description": "Temperature QC flag"},
                        {"name": "sal_qc", "type": "INTEGER", "description": "Salinity QC flag"}
                    ]
                },
                "indexes": [
                    "idx_lat_lon (latitude, longitude)",
                    "idx_timestamp (timestamp)",
                    "idx_float_id (float_id)"
                ]
            }
            
            session.close()
            return schema
        
        except Exception as e:
            session.close()
            return {"error": str(e)}
    
    def _handle_search_similar(self, query_text: str, top_k: int = 5) -> Dict:
        """Handle semantic search"""
        from vector_store.embeddings import EmbeddingGenerator
        
        generator = EmbeddingGenerator()
        embedding = generator.generate_embedding(query_text)
        results = self.vector_store.search(embedding, k=top_k)
        
        return {
            "query": query_text,
            "results": [
                {
                    "similarity_score": float(score),
                    "profile": metadata
                }
                for score, metadata in results
            ]
        }
    
    def _handle_analyze_profile(self, float_id: str, cycle_number: int = None) -> Dict:
        """Handle profile analysis"""
        session = self.db_setup.get_session()
        
        # Float IDs are stored as string representations of bytes: "b'1901766 '"
        # Use LIKE to match the float_id regardless of format
        query = f"SELECT * FROM argo_profiles WHERE float_id LIKE '%{float_id}%'"
        if cycle_number:
            query += f" AND cycle_number = {cycle_number}"
        
        df = pd.read_sql(text(query), session.bind)
        session.close()
        
        if df.empty:
            return {"success": False, "error": "Profile not found"}
        
        analysis = {
            "float_id": float_id,
            "cycle_number": cycle_number,
            "measurements": len(df),
            "location": {
                "lat": float(df['latitude'].mean()),
                "lon": float(df['longitude'].mean())
            },
            "date_range": {
                "start": df['timestamp'].min().isoformat() if 'timestamp' in df.columns else None,
                "end": df['timestamp'].max().isoformat() if 'timestamp' in df.columns else None
            },
            "temperature": {
                "min": float(df['temperature'].min()),
                "max": float(df['temperature'].max()),
                "mean": float(df['temperature'].mean()),
                "std": float(df['temperature'].std())
            } if 'temperature' in df.columns else None,
            "salinity": {
                "min": float(df['salinity'].min()),
                "max": float(df['salinity'].max()),
                "mean": float(df['salinity'].mean()),
                "std": float(df['salinity'].std())
            } if 'salinity' in df.columns else None,
            "depth_range": {
                "min": float(df['pressure'].min()),
                "max": float(df['pressure'].max())
            } if 'pressure' in df.columns else None
        }
        
        return {"success": True, "analysis": analysis}
    
    def _handle_calculate_thermocline(self, query: str) -> Dict:
        """Handle thermocline calculation"""
        
        # Extract region from query for better SQL generation
        region_query = f"Get temperature and pressure profiles from {query.lower().replace('calculate thermocline', '').replace('characteristics for', '').strip()}"
        
        # Add specific requirements for thermocline calculation
        data_query = f"{region_query}. Need temperature and pressure at multiple depths for vertical profile analysis."
        
        result = self.query_processor.process_query(data_query)
        
        if not result['success']:
            # Try a simpler direct query
            session = self.db_setup.get_session()
            try:
                # Extract region name
                region_name = 'Bay of Bengal' if 'bengal' in query.lower() else 'Arabian Sea' if 'arabian' in query.lower() else None
                
                if region_name:
                    # Direct SQL for Bay of Bengal or Arabian Sea
                    if 'Bengal' in region_name:
                        sql = """
                        SELECT pressure, temperature, latitude, longitude, timestamp
                        FROM argo_profiles
                        WHERE latitude BETWEEN 5 AND 22
                          AND longitude BETWEEN 80 AND 95
                          AND pressure IS NOT NULL
                          AND temperature IS NOT NULL
                          AND temp_qc IN (1, 2, 3)
                        ORDER BY pressure ASC
                        LIMIT 5000;
                        """
                    else:  # Arabian Sea
                        sql = """
                        SELECT pressure, temperature, latitude, longitude, timestamp
                        FROM argo_profiles
                        WHERE latitude BETWEEN 8 AND 24
                          AND longitude BETWEEN 50 AND 78
                          AND pressure IS NOT NULL
                          AND temperature IS NOT NULL
                          AND temp_qc IN (1, 2, 3)
                        ORDER BY pressure ASC
                        LIMIT 5000;
                        """
                    
                    from sqlalchemy import text
                    df = pd.read_sql(text(sql), session.connection())
                    session.close()
                    
                    if df.empty:
                        return {"success": False, "error": "No data found for thermocline calculation"}
                else:
                    return {"success": False, "error": "Could not identify region for thermocline calculation"}
                    
            except Exception as e:
                session.close()
                return {"success": False, "error": f"Database error: {str(e)}"}
        else:
            df = result['results']
        
        if df.empty:
            return {"success": False, "error": "No data available for thermocline calculation"}
        
        # Calculate thermocline using the advanced method
        thermocline = self.analytics.calculate_thermocline_advanced(df)
        
        return {
            "success": True,
            "thermocline": thermocline,
            "record_count": len(df),
            "region": "Bay of Bengal" if 'bengal' in query.lower() else "Arabian Sea" if 'arabian' in query.lower() else "Unknown"
        }
    
    def _handle_identify_water_masses(self, query: str) -> Dict:
        """Handle water mass identification"""
        result = self.query_processor.process_query(query)
        
        if not result['success']:
            return {"success": False, "error": result.get('error')}
        
        df = result['results']
        # Use the advanced method for more detailed water mass identification
        water_masses = self.analytics.identify_water_masses_advanced(df)
        
        return {
            "success": True,
            "water_masses": water_masses,
            "record_count": len(df)
        }
    
    def _handle_compare_regions(self, region1: str, region2: str, parameter: str = "temperature") -> Dict:
        """Handle regional comparison"""
        return self.analytics.regional_comparison(region1, region2, parameter)
    
    def _handle_temporal_trends(self, region: str, parameter: str, days: int = 90) -> Dict:
        """Handle temporal trend analysis"""
        return self.analytics.trend_analysis(region, parameter, days)
    
    def _handle_get_bgc(self, parameters: List[str], region: str = None) -> Dict:
        """Handle BGC parameter retrieval"""
        session = self.db_setup.get_session()
        
        cols = ", ".join(parameters)
        query = f"SELECT latitude, longitude, timestamp, {cols} FROM argo_profiles"
        
        conditions = []
        for param in parameters:
            conditions.append(f"{param} IS NOT NULL")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        if region:
            query += f" AND ocean_region ILIKE '%{region}%'"
        
        query += " LIMIT 1000"
        
        df = pd.read_sql(text(query), session.bind)
        session.close()
        
        return {
            "success": True,
            "bgc_data": df.to_dict('records'),
            "record_count": len(df)
        }
    
    def _handle_calculate_mld(self, query: str, threshold: float = 0.5) -> Dict:
        """Handle mixed layer depth calculation"""
        result = self.query_processor.process_query(query)
        
        if not result['success']:
            return {"success": False, "error": result.get('error')}
        
        df = result['results']
        mld = self.analytics.calculate_mixed_layer_depth(df, threshold)
        
        return {
            "success": True,
            "mixed_layer_depth": mld,
            "threshold": threshold,
            "unit": "dbar"
        }
    
    def _register_resources(self):
        """Register MCP resources"""
        
        # ARGO Database Resource
        self.resource_provider.register_resource(
            MCPResource(
                uri="argo://database/profiles",
                name="ARGO Profiles Database",
                description="PostgreSQL database containing ARGO float measurements",
                mimeType="application/sql"
            )
        )
        
        # Vector Store Resource
        self.resource_provider.register_resource(
            MCPResource(
                uri="argo://vectorstore/embeddings",
                name="ARGO Profile Embeddings",
                description="FAISS vector store with profile summaries",
                mimeType="application/faiss"
            )
        )
        
        # NetCDF Files Resource
        self.resource_provider.register_resource(
            MCPResource(
                uri="argo://files/netcdf",
                name="ARGO NetCDF Files",
                description="Raw ARGO float data in NetCDF format",
                mimeType="application/netcdf"
            )
        )
    
    def _register_prompts(self):
        """Register MCP prompt templates"""
        
        # Query Generation Prompt
        self.prompt_provider.register_prompt(
            MCPPromptTemplate(
                name="generate_argo_query",
                description="Generate SQL query for ARGO data",
                arguments=[
                    {"name": "user_question", "description": "Natural language question", "required": True},
                    {"name": "context", "description": "Additional context", "required": False}
                ]
            )
        )
        
        # Analysis Prompt
        self.prompt_provider.register_prompt(
            MCPPromptTemplate(
                name="analyze_profile",
                description="Analyze oceanographic profile",
                arguments=[
                    {"name": "profile_data", "description": "Profile measurements", "required": True},
                    {"name": "analysis_type", "description": "Type of analysis", "required": True}
                ]
            )
        )
    
    # MCP Protocol Methods
    def list_tools(self) -> List[Dict]:
        """List all available tools (MCP standard)"""
        return self.protocol.list_tools()
    
    def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Call a tool (MCP standard)"""
        tool_call = MCPToolCall(name=tool_name, arguments=arguments)
        result = self.protocol.call_tool(tool_call)
        return result.to_dict()
    
    def list_resources(self) -> List[Dict]:
        """List all resources (MCP standard)"""
        return self.resource_provider.list_resources()
    
    def read_resource(self, uri: str) -> Dict:
        """Read a resource (MCP standard)"""
        return self.resource_provider.read_resource(uri)
    
    def list_prompts(self) -> List[Dict]:
        """List all prompt templates (MCP standard)"""
        return self.prompt_provider.list_prompts()
    
    def get_prompt(self, name: str, arguments: Dict = None) -> Dict:
        """Get a prompt template (MCP standard)"""
        return self.prompt_provider.get_prompt(name, arguments)


# Create singleton instance
mcp_server = ARGOMCPServer()


if __name__ == "__main__":
    # Test MCP server
    print("\n" + "="*60)
    print("ARGO MCP Server - Testing")
    print("="*60)
    
    # List tools
    print("\n📋 Available Tools:")
    tools = mcp_server.list_tools()
    for tool in tools:
        print(f"  • {tool['name']}: {tool['description']}")
    
    # Test tool call
    print("\n🔧 Testing Tool Call:")
    result = mcp_server.call_tool("get_database_schema", {})
    print(json.dumps(result, indent=2))
    
    # List resources
    print("\n📚 Available Resources:")
    resources = mcp_server.list_resources()
    for resource in resources:
        print(f"  • {resource['name']}: {resource['uri']}")
    
    print("\n✅ MCP Server ready for integration!")