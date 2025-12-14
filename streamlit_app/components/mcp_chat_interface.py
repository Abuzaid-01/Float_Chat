"""
Enhanced Chat Interface with MCP Integration
Displays MCP tool execution and structured results
"""

import streamlit as st
from typing import Dict
from datetime import datetime
from mcp_server.mcp_query_processor import mcp_query_processor
from mcp_server.mcp_response_enhancer import MCPResponseEnhancer
from streamlit_app.components.smart_suggestions import SmartSuggestionGenerator
from rag_engine.intent_classifier import intent_classifier
import pandas as pd
import json


class MCPChatInterface:
    """
    MCP-enabled chat interface with intelligent intent classification
    Shows tool execution, structured results, and enhanced responses
    """
    
    def __init__(self):
        self.mcp_processor = mcp_query_processor
        self.enhancer = MCPResponseEnhancer()
        self.suggestion_generator = SmartSuggestionGenerator()
        self.intent_classifier = intent_classifier
        
        # Initialize chat history
        if 'mcp_chat_history' not in st.session_state:
            st.session_state.mcp_chat_history = []
    
    def render(self):
        """Render MCP-enabled chat interface"""
        
        # Display MCP capabilities badge
        self._render_mcp_badge()
        
        # Check if there's a queued suggestion query
        if 'next_query' in st.session_state and st.session_state.next_query:
            prompt = st.session_state.next_query
            st.session_state.next_query = None  # Clear it
            self._handle_user_input(prompt)
            return  # Rerender will happen
        
        # Display chat history
        for idx, message in enumerate(st.session_state.mcp_chat_history):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Show MCP execution details with user query for smart suggestions
                if message.get("mcp_details"):
                    # Get the previous user message for context
                    user_query = None
                    if idx > 0 and st.session_state.mcp_chat_history[idx-1]["role"] == "user":
                        user_query = st.session_state.mcp_chat_history[idx-1]["content"]
                    self._render_mcp_details(message["mcp_details"], message_id=idx, user_query=user_query)
                
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
        """Handle user input with intelligent intent classification"""
        
        # Add user message
        st.session_state.mcp_chat_history.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Classify intent using AI (with conversation context)
        with st.chat_message("assistant"):
            with st.spinner("🤔 Understanding your question..."):
                # Pass conversation history to help detect follow-ups
                intent_result = self.intent_classifier.classify_intent(
                    prompt, 
                    conversation_history=st.session_state.mcp_chat_history
                )
            
            # Handle based on intent
            if not intent_result['requires_data_query']:
                # Direct response for conversational queries
                st.markdown(intent_result['direct_response'])
                
                # Add to history
                st.session_state.mcp_chat_history.append({
                    "role": "assistant",
                    "content": intent_result['direct_response']
                })
                return
            
            # Data query - process with MCP (pass conversation history for context)
            with st.spinner("🔧 MCP tools working..."):
                # Get recent conversation history (last 6 messages for context)
                conversation_context = st.session_state.mcp_chat_history[-6:] if len(st.session_state.mcp_chat_history) > 0 else []
                result = self.mcp_processor.process_query_with_mcp(prompt, conversation_history=conversation_context)
                
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
                    self._render_mcp_details(mcp_details, message_id=current_msg_id, user_query=prompt)
                    
                    # Extract data for visualization
                    data = self._extract_data_from_results(result['tool_results'])
                    
                    # Add to history
                    st.session_state.mcp_chat_history.append({
                        "role": "assistant",
                        "content": result['response'],
                        "mcp_details": mcp_details,
                        "data": data
                    })
                    
                    # Store for other tabs - ALWAYS store the last query
                    if data is not None and not data.empty:
                        # Determine what type of data this is
                        has_geographic = any(col in data.columns for col in ['latitude', 'longitude'])
                        has_profile = any(col in data.columns for col in ['temperature', 'salinity', 'pressure'])
                        has_temporal = 'timestamp' in data.columns
                        
                        # DEBUG: Show what we're storing
                        st.success(f"✅ **Data stored for visualization tabs:** {len(data)} records")
                        if 'temperature' in data.columns:
                            st.caption(f"🌡️ Temperature range: {data['temperature'].min():.3f}°C - {data['temperature'].max():.3f}°C")
                        if 'pressure' in data.columns:
                            st.caption(f"📊 Pressure range: {data['pressure'].min():.3f} - {data['pressure'].max():.3f} dbar")
                        
                        st.session_state.last_query_results = {
                            'success': True,
                            'results': data,
                            'mcp_enabled': True,
                            'tools_used': result['tools_used'],
                            'query': prompt,  # Store the original query
                            'has_geographic': has_geographic,
                            'has_profile': has_profile,
                            'has_temporal': has_temporal,
                            'is_aggregated': len(data) <= 100 and not has_geographic  # Likely aggregated stats
                        }
                        
                        # Also store a summary for quick access
                        st.session_state.last_query_summary = {
                            'query': prompt,
                            'record_count': len(data),
                            'data_type': 'profile' if has_profile else ('geographic' if has_geographic else 'statistical'),
                            'timestamp': datetime.now()
                        }
                    else:
                        # Even if no data, store the query info
                        st.session_state.last_query_results = {
                            'success': False,
                            'results': pd.DataFrame(),
                            'query': prompt,
                            'message': 'No data returned for this query'
                        }
                else:
                    error_msg = f"❌ Error: {result.get('error', 'Unknown error')}"
                    st.error(error_msg)
                    st.session_state.mcp_chat_history.append({
                        "role": "assistant",
                        "content": error_msg
                    })
    
    def _render_mcp_details(self, mcp_details: Dict, message_id: int = 0, user_query: str = None):
        """Render MCP execution details and smart suggestions"""
        
        with st.expander("🔧 MCP Execution Details", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Tools Executed:**")
                for tool in mcp_details['tools_used']:
                    # Check both isError flag and success field in content
                    tool_result = mcp_details['tool_results'].get(tool, {})
                    is_error = tool_result.get('isError', False)
                    
                    # Also check if the tool returned success: False in its content
                    tool_success = True  # Default to success
                    if not is_error and 'content' in tool_result:
                        try:
                            content_text = tool_result['content'][0].get('text', '{}')
                            content_data = json.loads(content_text)
                            # Only treat as failure if success is explicitly False
                            # Missing success field is treated as success
                            if 'success' in content_data:
                                tool_success = content_data['success']
                        except:
                            pass  # If we can't parse, assume success
                    
                    # Determine final status
                    if is_error or not tool_success:
                        status = "❌"
                    else:
                        status = "✅"
                    
                    st.markdown(f"{status} `{tool}`")
            
            with col2:
                st.metric("Execution Time", f"{mcp_details['execution_time']:.2f}s")
                st.metric("Tools Used", len(mcp_details['tools_used']))
        
        # Smart contextual suggestions based on user query
        if user_query:
            suggestions = self.suggestion_generator.generate_suggestions(user_query)
            
            with st.expander("💡 Related Questions You Might Ask", expanded=True):
                st.markdown("**Based on your query, you might also want to:**")
                st.markdown("")
                
                # Display suggestions as clickable buttons
                for i, suggestion in enumerate(suggestions, 1):
                    col1, col2 = st.columns([0.08, 0.92])
                    with col1:
                        st.markdown(f"**{i}.**")
                    with col2:
                        if st.button(suggestion, key=f"suggest_{message_id}_{i}", use_container_width=True):
                            # Trigger new query
                            st.session_state.next_query = suggestion
                            st.rerun()
                
                st.markdown("---")
                st.caption("💡 Click any suggestion to explore further!")
        else:
            # Fallback to general examples if no user query
            with st.expander("💡 MCP-Powered Query Examples", expanded=False):
                st.markdown("""
                **Basic Queries:**
                - Show me temperature profiles in the Arabian Sea
                - What is the database structure?
                - Find recent data from October 2025
                
                **Spatial Queries:**
                - Find nearest floats to 15°N, 75°E
                - Show floats within 50km of Mumbai
                
                **Advanced Analytics (MCP Tools):**
                - Calculate thermocline characteristics for Bay of Bengal
                - Identify water masses in the Indian Ocean
                - Compare temperature between Arabian Sea and Bay of Bengal
                
                **Profile Analysis:**
                - Analyze float 2902696 profile statistics
                
                **Note:** Database contains Core ARGO data only (Temperature, Salinity, Pressure).
                
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