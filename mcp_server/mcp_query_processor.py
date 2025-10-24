"""
MCP-Enabled Query Processor
Integrates Model Context Protocol with RAG pipeline
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Dict, List, Optional
from mcp_server.argo_mcp_server import mcp_server
from rag_engine.query_processor import QueryProcessor
from rag_engine.response_generator import ResponseGenerator
import pandas as pd
import time
import json


class MCPQueryProcessor:
    """
    Enhanced Query Processor with MCP integration
    Provides intelligent tool selection and orchestration
    """
    
    def __init__(self):
        self.mcp_server = mcp_server
        self.base_processor = QueryProcessor()
        self.response_generator = ResponseGenerator()
        
        # Query patterns to tool mapping
        self.query_patterns = self._initialize_patterns()
        
        print("✅ MCP Query Processor initialized")
    
    def _initialize_patterns(self) -> Dict:
        """Initialize query pattern to tool mapping"""
        return {
            'schema': ['schema', 'structure', 'columns', 'database', 'table'],
            'thermocline': ['thermocline', 'temperature gradient', 'thermal structure'],
            'water_mass': ['water mass', 'water masses', 'T-S', 'temperature-salinity'],
            'comparison': ['compare', 'comparison', 'difference between', 'versus', 'vs'],
            'temporal': ['trend', 'time series', 'temporal', 'over time', 'historical'],
            'bgc': ['dissolved oxygen', 'chlorophyll', 'ph', 'oxygen', 'nutrients', 'bgc'],
            'mld': ['mixed layer', 'mld', 'surface layer'],
            'analysis': ['analyze', 'analysis', 'statistics', 'summary'],
            'similar': ['similar', 'like', 'comparable', 'find profiles']
        }
    
    def process_query_with_mcp(self, user_query: str) -> Dict:
        """
        Process query using MCP tool orchestration
        
        Returns complete result with:
        - Query results
        - Tools used
        - MCP execution trace
        - Response generation
        """
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"🔍 MCP Query Processing: {user_query}")
        print(f"{'='*60}")
        
        # Step 1: Analyze query and select appropriate tools
        selected_tools = self._select_tools(user_query)
        print(f"\n🔧 Selected MCP Tools: {selected_tools}")
        
        # Step 2: Execute tools in sequence
        tool_results = {}
        for tool_name in selected_tools:
            print(f"\n⚙️ Executing: {tool_name}")
            result = self._execute_mcp_tool(tool_name, user_query)
            tool_results[tool_name] = result
        
        # Step 3: Generate comprehensive response
        print(f"\n🤖 Generating AI response...")
        final_response = self._generate_mcp_response(
            user_query,
            tool_results,
            selected_tools
        )
        
        execution_time = time.time() - start_time
        
        print(f"\n✅ MCP Query completed in {execution_time:.2f}s")
        
        return {
            'success': True,
            'query': user_query,
            'tools_used': selected_tools,
            'tool_results': tool_results,
            'response': final_response,
            'execution_time': execution_time,
            'mcp_enabled': True
        }
    
    def _select_tools(self, query: str) -> List[str]:
        """
        Intelligently select MCP tools based on query content
        """
        query_lower = query.lower()
        selected = []
        
        # Always start with data query for most questions
        needs_data = any(word in query_lower for word in [
            'show', 'get', 'find', 'retrieve', 'display', 'list',
            'temperature', 'salinity', 'pressure', 'ocean', 'sea',
            'float', 'profile', 'data', 'measurement'
        ])
        
        if needs_data:
            selected.append('query_argo_data')
        
        # Check for schema/structure questions
        if any(word in query_lower for word in self.query_patterns['schema']):
            selected.append('get_database_schema')
            return selected  # Schema questions don't need other tools
        
        # Check for thermocline analysis
        if any(word in query_lower for word in self.query_patterns['thermocline']):
            selected.append('calculate_thermocline')
        
        # Check for water mass identification
        if any(word in query_lower for word in self.query_patterns['water_mass']):
            selected.append('identify_water_masses')
        
        # Check for regional comparison
        if any(word in query_lower for word in self.query_patterns['comparison']):
            # Extract region names if possible
            if 'arabian' in query_lower and 'bengal' in query_lower:
                selected.append('compare_regions')
        
        # Check for temporal analysis
        if any(word in query_lower for word in self.query_patterns['temporal']):
            selected.append('analyze_temporal_trends')
        
        # Check for BGC parameters
        if any(word in query_lower for word in self.query_patterns['bgc']):
            selected.append('get_bgc_parameters')
        
        # Check for MLD calculation
        if any(word in query_lower for word in self.query_patterns['mld']):
            selected.append('calculate_mixed_layer_depth')
        
        # Check for profile analysis
        if any(word in query_lower for word in self.query_patterns['analysis']):
            if 'float' in query_lower and any(char.isdigit() for char in query):
                selected.append('analyze_float_profile')
        
        # Check for semantic search
        if any(word in query_lower for word in self.query_patterns['similar']):
            selected.append('search_similar_profiles')
        
        # Default to basic query if nothing selected
        if not selected:
            selected.append('query_argo_data')
        
        return selected
    
    def _execute_mcp_tool(self, tool_name: str, query: str) -> Dict:
        """Execute an MCP tool with appropriate arguments"""
        
        try:
            if tool_name == 'query_argo_data':
                result = self.mcp_server.call_tool('query_argo_data', {
                    'query': query,
                    'limit': 1000
                })
            
            elif tool_name == 'get_database_schema':
                result = self.mcp_server.call_tool('get_database_schema', {})
            
            elif tool_name == 'calculate_thermocline':
                result = self.mcp_server.call_tool('calculate_thermocline', {
                    'query': query
                })
            
            elif tool_name == 'identify_water_masses':
                result = self.mcp_server.call_tool('identify_water_masses', {
                    'query': query
                })
            
            elif tool_name == 'compare_regions':
                # Extract regions from query
                regions = self._extract_regions(query)
                result = self.mcp_server.call_tool('compare_regions', {
                    'region1': regions[0] if len(regions) > 0 else 'Arabian Sea',
                    'region2': regions[1] if len(regions) > 1 else 'Bay of Bengal',
                    'parameter': 'temperature'
                })
            
            elif tool_name == 'analyze_temporal_trends':
                # Extract region and parameter
                region = self._extract_region(query)
                parameter = self._extract_parameter(query)
                result = self.mcp_server.call_tool('analyze_temporal_trends', {
                    'region': region,
                    'parameter': parameter,
                    'days': 90
                })
            
            elif tool_name == 'get_bgc_parameters':
                bgc_params = self._extract_bgc_parameters(query)
                result = self.mcp_server.call_tool('get_bgc_parameters', {
                    'parameters': bgc_params
                })
            
            elif tool_name == 'calculate_mixed_layer_depth':
                result = self.mcp_server.call_tool('calculate_mixed_layer_depth', {
                    'query': query,
                    'threshold': 0.5
                })
            
            elif tool_name == 'analyze_float_profile':
                float_id = self._extract_float_id(query)
                result = self.mcp_server.call_tool('analyze_float_profile', {
                    'float_id': float_id
                })
            
            elif tool_name == 'search_similar_profiles':
                result = self.mcp_server.call_tool('search_similar_profiles', {
                    'query_text': query,
                    'top_k': 5
                })
            
            else:
                result = {'content': [{'type': 'text', 'text': f'Unknown tool: {tool_name}'}], 'isError': True}
            
            return result
        
        except Exception as e:
            return {
                'content': [{'type': 'text', 'text': f'Tool execution error: {str(e)}'}],
                'isError': True
            }
    
    def _generate_mcp_response(
        self,
        query: str,
        tool_results: Dict,
        tools_used: List[str]
    ) -> str:
        """
        Generate comprehensive response from MCP tool results
        """
        
        # Extract main data and metadata
        main_data = None
        sql_query = None
        record_count = 0
        
        if 'query_argo_data' in tool_results:
            tool_result = tool_results['query_argo_data']
            content = tool_result.get('content', [])
            
            if content and not tool_result.get('isError'):
                try:
                    text = content[0].get('text', '')
                    data_dict = json.loads(text)
                    
                    if data_dict.get('success') and data_dict.get('data'):
                        main_data = pd.DataFrame(data_dict['data'])
                        record_count = data_dict.get('record_count', len(main_data))
                        sql_query = data_dict.get('sql', '')
                except Exception as e:
                    print(f"❌ Error parsing query_argo_data result: {e}")
        
        # Build enhanced context from tool results
        context_parts = []
        
        # Add data summary if available
        if main_data is not None and not main_data.empty:
            context_parts.append(f"**Query Results Summary:**")
            context_parts.append(f"- Total records found: {record_count}")
            
            # Add column information
            context_parts.append(f"- Available columns: {', '.join(main_data.columns.tolist())}")
            
            # Add sample statistics
            if 'temperature' in main_data.columns:
                temp_stats = main_data['temperature'].describe()
                context_parts.append(f"- Temperature range: {temp_stats['min']:.2f}°C to {temp_stats['max']:.2f}°C (avg: {temp_stats['mean']:.2f}°C)")
            
            if 'salinity' in main_data.columns:
                sal_stats = main_data['salinity'].describe()
                context_parts.append(f"- Salinity range: {sal_stats['min']:.2f} to {sal_stats['max']:.2f} PSU (avg: {sal_stats['mean']:.2f} PSU)")
            
            if 'pressure' in main_data.columns:
                pres_stats = main_data['pressure'].describe()
                context_parts.append(f"- Depth range: {pres_stats['min']:.0f} to {pres_stats['max']:.0f} dbar")
            
            if 'float_id' in main_data.columns:
                unique_floats = main_data['float_id'].nunique()
                context_parts.append(f"- Unique floats: {unique_floats}")
            
            context_parts.append("")
        
        # Add other tool results
        for tool_name, result in tool_results.items():
            if tool_name != 'query_argo_data' and not result.get('isError'):
                content = result.get('content', [])
                if content:
                    text = content[0].get('text', '')
                    # Try to format JSON results nicely
                    try:
                        data = json.loads(text)
                        formatted_text = json.dumps(data, indent=2)
                        context_parts.append(f"**{tool_name}**:\n```json\n{formatted_text}\n```\n")
                    except:
                        context_parts.append(f"**{tool_name}**:\n{text}\n")
        
        combined_context = "\n".join(context_parts)
        
        # Generate response using LLM
        if main_data is not None and not main_data.empty:
            response = self.response_generator.generate_response(
                query,
                main_data,
                combined_context
            )
        else:
            # Generate response without data
            response = self._generate_text_response(query, combined_context)
        
        # Add MCP execution summary
        mcp_summary = self._format_mcp_summary(tools_used, tool_results)
        
        return f"{response}\n\n{mcp_summary}"
    
    def _generate_text_response(self, query: str, context: str) -> str:
        """Generate response for non-data queries"""
        
        prompt = f"""Based on the following information about ARGO ocean data, answer this question:

Question: {query}

Available Information:
{context}

Provide a clear, comprehensive answer:"""
        
        try:
            response = self.response_generator.llm.invoke(prompt)
            return response.content
        except:
            return context
    
    def _format_mcp_summary(self, tools_used: List[str], tool_results: Dict) -> str:
        """Format MCP execution summary"""
        
        summary = "\n---\n**🔧 MCP Tools Executed:**\n"
        
        for tool in tools_used:
            status = "✅" if not tool_results.get(tool, {}).get('isError') else "❌"
            summary += f"- {status} `{tool}`\n"
        
        return summary
    
    # Helper methods for query parsing
    def _extract_regions(self, query: str) -> List[str]:
        """Extract region names from query"""
        regions = []
        query_lower = query.lower()
        
        region_keywords = {
            'arabian sea': 'Arabian Sea',
            'bay of bengal': 'Bay of Bengal',
            'indian ocean': 'Indian Ocean',
            'southern ocean': 'Southern Ocean',
            'equatorial': 'Equatorial Indian Ocean'
        }
        
        for keyword, region_name in region_keywords.items():
            if keyword in query_lower:
                regions.append(region_name)
        
        return regions
    
    def _extract_region(self, query: str) -> str:
        """Extract single region from query"""
        regions = self._extract_regions(query)
        return regions[0] if regions else 'Indian Ocean'
    
    def _extract_parameter(self, query: str) -> str:
        """Extract parameter from query"""
        query_lower = query.lower()
        
        if 'temperature' in query_lower or 'temp' in query_lower:
            return 'temperature'
        elif 'salinity' in query_lower or 'salt' in query_lower:
            return 'salinity'
        elif 'pressure' in query_lower or 'depth' in query_lower:
            return 'pressure'
        elif 'oxygen' in query_lower:
            return 'dissolved_oxygen'
        elif 'chlorophyll' in query_lower:
            return 'chlorophyll'
        else:
            return 'temperature'
    
    def _extract_bgc_parameters(self, query: str) -> List[str]:
        """Extract BGC parameters from query"""
        query_lower = query.lower()
        params = []
        
        if 'oxygen' in query_lower or 'dissolved oxygen' in query_lower:
            params.append('dissolved_oxygen')
        if 'chlorophyll' in query_lower:
            params.append('chlorophyll')
        if 'ph' in query_lower:
            params.append('ph')
        if 'nitrate' in query_lower:
            params.append('nitrate')
        
        return params if params else ['dissolved_oxygen', 'chlorophyll']
    
    def _extract_float_id(self, query: str) -> str:
        """Extract float ID from query"""
        import re
        # Look for patterns like "float 2902696" or "float ID 2902696"
        match = re.search(r'float\s*(?:id)?\s*(\d+)', query, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Look for standalone numbers
        match = re.search(r'\b(\d{7})\b', query)
        if match:
            return match.group(1)
        
        return '2902696'  # Default
    
    def get_mcp_capabilities(self) -> Dict:
        """Return MCP server capabilities"""
        return {
            'tools': self.mcp_server.list_tools(),
            'resources': self.mcp_server.list_resources(),
            'prompts': self.mcp_server.list_prompts(),
            'total_tools': len(self.mcp_server.list_tools())
        }


# Singleton instance
mcp_query_processor = MCPQueryProcessor()


if __name__ == "__main__":
    # Test MCP Query Processor
    processor = MCPQueryProcessor()
    
    test_queries = [
        "Show me temperature profiles in Arabian Sea",
        "Calculate thermocline for Bay of Bengal",
        "Compare Arabian Sea and Bay of Bengal temperature",
        "What is the database structure?",
        "Find similar profiles to warm tropical water"
    ]
    
    print("\n" + "="*60)
    print("Testing MCP Query Processor")
    print("="*60)
    
    for query in test_queries:
        print(f"\n\n📝 Query: {query}")
        result = processor.process_query_with_mcp(query)
        print(f"\n✅ Tools Used: {result['tools_used']}")
        print(f"⏱️ Time: {result['execution_time']:.2f}s")