import streamlit as st
from database.db_setup import DatabaseSetup
from database.models import ArgoProfile

class Sidebar:
    """Sidebar component with database info and settings"""
    
    def __init__(self):
        self.db_setup = DatabaseSetup()
    
    def render(self):
        """Render sidebar content"""
        
        with st.sidebar:
            # Enhanced title with gradient
            st.markdown("""
                <div style='background: linear-gradient(135deg, #0066cc, #00c6ff); padding: 1rem; border-radius: 10px; margin-bottom: 1rem;'>
                    <h1 style='color: white; margin: 0; text-align: center; font-weight: 800;'>⚙️ Settings</h1>
                </div>
            """, unsafe_allow_html=True)
            
            # Database statistics
            self._render_database_stats()
            
            st.markdown("---")
            
            # Query settings
            self._render_query_settings()
            
            st.markdown("---")
            
            # Information
            self._render_info()
            
            st.markdown("---")
            
            # Clear chat button with enhanced styling
            if st.button("🗑️ Clear Chat History", use_container_width=True, type="primary"):
                st.session_state.chat_history = []
                st.session_state.last_query_results = None
                st.success("✅ Chat history cleared!")
                st.rerun()
    
    def _render_database_stats(self):
        """Display database statistics"""
        st.markdown("""
            <h3 style='color: #0066cc; font-weight: 700;'>📊 Database Statistics</h3>
        """, unsafe_allow_html=True)
        
        try:
            session = self.db_setup.get_session()
            
            # Get counts
            total_records = session.query(ArgoProfile).count()
            unique_floats = session.query(ArgoProfile.float_id).distinct().count()
            
            # Get date range
            date_range = session.query(
                ArgoProfile.timestamp
            ).order_by(ArgoProfile.timestamp).first()
            
            session.close()
            
            # Display metrics in styled boxes
            st.markdown(f"""
                <div style='background: linear-gradient(135deg, #e3f2fd, #bbdefb); padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #0066cc;'>
                    <p style='margin: 0; color: #666; font-weight: 600; font-size: 0.85rem;'>TOTAL RECORDS</p>
                    <h2 style='margin: 0; color: #0066cc; font-weight: 800;'>{total_records:,}</h2>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
                <div style='background: linear-gradient(135deg, #e8f5e9, #c8e6c9); padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #00b894;'>
                    <p style='margin: 0; color: #666; font-weight: 600; font-size: 0.85rem;'>UNIQUE FLOATS</p>
                    <h2 style='margin: 0; color: #00b894; font-weight: 800;'>{unique_floats}</h2>
                </div>
            """, unsafe_allow_html=True)
            
            if date_range:
                st.info(f"📅 **Data starts from:** {date_range[0].strftime('%B %d, %Y')}")
            
        except Exception as e:
            st.error(f"❌ Database connection error: {e}")
    
    def _render_query_settings(self):
        """Render query settings"""
        st.markdown("""
            <h3 style='color: #0066cc; font-weight: 700;'>🔧 Query Configuration</h3>
        """, unsafe_allow_html=True)
        
        # Number of similar profiles to retrieve
        top_k = st.slider(
            "📊 Similar Profiles to Retrieve",
            min_value=1,
            max_value=10,
            value=3,
            help="Number of similar profiles to use for AI context generation"
        )
        st.session_state.top_k = top_k
        
        # Max results to display
        max_results = st.slider(
            "📈 Maximum Results to Display",
            min_value=100,
            max_value=10000,
            value=1000,
            step=100,
            help="Maximum number of database records to return and display"
        )
        st.session_state.max_results = max_results
        
        # Show current settings
        st.success(f"✅ Settings Active: {top_k} profiles, max {max_results:,} results")
    
    def _render_info(self):
        """Render information section"""
        st.markdown("""
            <h3 style='color: #0066cc; font-weight: 700;'>ℹ️ About FloatChat</h3>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style='background: linear-gradient(135deg, #f8f9fa, #e9ecef); padding: 1rem; border-radius: 8px; border: 2px solid #dee2e6;'>
            <p style='color: #000000; font-weight: 600; margin: 0.5rem 0;'>
                <strong style='color: #0066cc;'>FloatChat</strong> is an AI-powered conversational 
                interface for exploring ARGO ocean float data with natural language.
            </p>
            
            <h4 style='color: #0066cc; margin-top: 1rem; margin-bottom: 0.5rem;'>✨ Key Features:</h4>
            <ul style='color: #000000; font-weight: 600; margin: 0; padding-left: 1.2rem;'>
                <li>🤖 Natural language queries</li>
                <li>📍 Spatial search (nearest floats)</li>  <!-- NEW -->
                <li>🗺️ Interactive Plotly + Leaflet maps</li>  <!-- UPDATED -->
                <li>📊 Real-time data analysis</li>
                <li>💾 Multi-format export (CSV, JSON, NetCDF)</li>  <!-- UPDATED -->
                <li>🌊 1.2M+ ocean measurements</li>
            </ul>
            
            <h4 style='color: #0066cc; margin-top: 1rem; margin-bottom: 0.5rem;'>📡 Data Source:</h4>
            <p style='color: #000000; font-weight: 600; margin: 0;'>
                ARGO Global Ocean Observing System<br/>
                via INCOIS (Indian National Centre for Ocean Information Services)
            </p>
            
            <h4 style='color: #0066cc; margin-top: 1rem; margin-bottom: 0.5rem;'>🏆 Developed For:</h4>
            <p style='color: #000000; font-weight: 600; margin: 0;'>
                Smart India Hackathon 2025<br/>
                Ministry of Earth Sciences (MoES)
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Links
        st.markdown("**Resources:**")
        st.markdown("- [ARGO Program](https://argo.ucsd.edu/)")
        st.markdown("- [INCOIS](https://incois.gov.in/)")
        st.markdown("- [GitHub](https://github.com)")
