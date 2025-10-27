"""
Enhanced Chat Interface with MCP Integration
Displays MCP tool execution and structured results
"""

import streamlit as st
from typing import Dict
from mcp_server.mcp_query_processor import mcp_query_processor
from mcp_server.mcp_response_enhancer import MCPResponseEnhancer
import pandas as pd
import json


class MCPChatInterface:
    """
    MCP-enabled chat interface
    Shows tool execution, structured results, and enhanced responses
    """
    
    def __init__(self):
        self.mcp_processor = mcp_query_processor
        self.enhancer = MCPResponseEnhancer()
        
        # Initialize chat history
        if 'mcp_chat_history' not in st.session_state:
            st.session_state.mcp_chat_history = []
    
    def render(self):
        """Render MCP-enabled chat interface"""
        
        # Display MCP capabilities badge
        self._render_mcp_badge()
        
        # Display chat history
        for idx, message in enumerate(st.session_state.mcp_chat_history):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Show MCP execution details
                if message.get("mcp_details"):
                    self._render_mcp_details(message["mcp_details"], message_id=idx)
                
                # Show data
                if message.get("data") is not None:
                    with st.expander("📊 View Query Results"):
                        st.dataframe(message["data"].head(20))
                        st.caption(f"Showing first 20 of {len(message['data'])} records")
        
        # Chat input
        if prompt := st.chat_input("Ask about ARGO data (MCP-powered)..."):
            self._handle_user_input(prompt)
    
    def _render_mcp_badge(self):
        """Display MCP enabled badge"""
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 0.5rem 1rem; 
                    border-radius: 8px; 
                    margin-bottom: 1rem;
                    text-align: center;'>
            <span style='color: white; font-weight: 700; font-size: 0.9rem;'>
                🔧 MCP (Model Context Protocol) ENABLED
            </span>
            <br>
            <span style='color: #e0e7ff; font-size: 0.75rem;'>
                Intelligent tool orchestration for advanced ocean data analysis
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    def _handle_user_input(self, prompt: str):
        """Handle user input with MCP processing"""
        
        # Add user message
        st.session_state.mcp_chat_history.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process with MCP
        with st.chat_message("assistant"):
            with st.spinner("🔧 MCP tools working..."):
                result = self.mcp_processor.process_query_with_mcp(prompt)
                
                if result['success']:
                    # Display response
                    st.markdown(result['response'])
                    
                    # Display MCP details (use current message count as ID)
                    mcp_details = {
                        'tools_used': result['tools_used'],
                        'execution_time': result['execution_time'],
                        'tool_results': result['tool_results']
                    }
                    current_msg_id = len(st.session_state.mcp_chat_history)
                    self._render_mcp_details(mcp_details, message_id=current_msg_id)
                    
                    # Extract data for visualization
                    data = self._extract_data_from_results(result['tool_results'])
                    
                    # Add to history
                    st.session_state.mcp_chat_history.append({
                        "role": "assistant",
                        "content": result['response'],
                        "mcp_details": mcp_details,
                        "data": data
                    })
                    
                    # Store for other tabs (only if data has meaningful visualization columns)
                    if data is not None and not data.empty:
                        # Only store if data has actual profile/geographic data for visualization
                        # Skip storing simple aggregates (count, avg, etc.) that can't be visualized
                        has_viz_columns = any(col in data.columns for col in ['latitude', 'longitude', 'temperature', 'salinity', 'pressure'])
                        
                        if has_viz_columns:
                            st.session_state.last_query_results = {
                                'success': True,
                                'results': data,
                                'mcp_enabled': True,
                                'tools_used': result['tools_used']
                            }
                else:
                    error_msg = f"❌ Error: {result.get('error', 'Unknown error')}"
                    st.error(error_msg)
                    st.session_state.mcp_chat_history.append({
                        "role": "assistant",
                        "content": error_msg
                    })
    
    def _render_mcp_details(self, mcp_details: Dict, message_id: int = 0):
        """Render MCP execution details"""
        
        with st.expander("🔧 MCP Execution Details", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Tools Executed:**")
                for tool in mcp_details['tools_used']:
                    st.markdown(f"✅ `{tool}`")
            
            with col2:
                st.metric("Execution Time", f"{mcp_details['execution_time']:.2f}s")
                st.metric("Tools Used", len(mcp_details['tools_used']))
        
        with st.expander("💡 MCP-Powered Query Examples", expanded=False):
            st.markdown("""
            **Basic Queries:**
            - Show me temperature profiles in the Arabian Sea
            - What is the database structure?
            - Find recent data from October 2025
            
            **Spatial Queries (NEW!):**  <!-- NEW SECTION -->
            - Find nearest floats to 15°N, 75°E
            - Show floats within 50km of Mumbai
            - What floats are closest to 10.5N 70.3E
            - Find floats within 100 kilometers of Chennai
            
            **Advanced Analytics (MCP Tools):**
            - Calculate thermocline characteristics for Bay of Bengal
            - Identify water masses in the Indian Ocean
            - Compare temperature between Arabian Sea and Bay of Bengal
            - Analyze temporal trends in dissolved oxygen
            - Calculate mixed layer depth for recent profiles
            
            **BGC Queries:**
            - Show dissolved oxygen levels in Arabian Sea
            - Get chlorophyll and pH data for coastal regions
            
            **Profile Analysis:**
            - Analyze float 2902696 profile statistics
            - Find profiles similar to warm tropical surface water
            
            **💡 MCP automatically selects the right tools for your question!**
            """)
            
            # Show individual tool results with unique key
            if st.checkbox("Show detailed tool results", key=f"show_details_{message_id}"):
                for tool_name, result in mcp_details['tool_results'].items():
                    st.markdown(f"**{tool_name}:**")
                    if result.get('isError'):
                        st.error("Tool execution failed")
                    else:
                        content = result.get('content', [])
                        if content:
                            text = content[0].get('text', '')
                            try:
                                # Try to format as JSON
                                data = json.loads(text)
                                st.json(data)
                            except:
                                st.code(text)
    
    def _extract_data_from_results(self, tool_results: Dict) -> pd.DataFrame:
        """Extract DataFrame from tool results"""
        
        if 'query_argo_data' not in tool_results:
            return None
        
        result = tool_results['query_argo_data']
        if result.get('isError'):
            return None
        
        content = result.get('content', [])
        if not content:
            return None
        
        try:
            text = content[0].get('text', '')
            data_dict = json.loads(text)
            
            if data_dict.get('success') and data_dict.get('data'):
                return pd.DataFrame(data_dict['data'])
        except:
            pass
        
        return None


def render_mcp_capabilities():
    """Render MCP capabilities sidebar"""
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔧 MCP Capabilities")
    
    capabilities = mcp_query_processor.get_mcp_capabilities()
    
    st.sidebar.metric("Available Tools", capabilities['total_tools'])
    
    with st.sidebar.expander("📋 View All Tools"):
        for tool in capabilities['tools']:
            st.markdown(f"**{tool['name']}**")
            st.caption(tool['description'])
            st.markdown("---")
    
    with st.sidebar.expander("📚 Available Resources"):
        for resource in capabilities['resources']:
            st.markdown(f"**{resource['name']}**")
            st.caption(f"URI: `{resource['uri']}`")
            st.caption(f"Type: {resource['mimeType']}")
            st.markdown("---")