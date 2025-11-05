



import streamlit as st

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="FloatChat - ARGO Data Explorer",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go

# Add project root to path FIRST (before any local imports)
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_processing.netcdf_exporter import NetCDFExporter, export_dataframe_to_netcdf, export_dataframe_to_ascii

from streamlit_app.components.mcp_chat_interface import MCPChatInterface, render_mcp_capabilities
from streamlit_app.components.advanced_viz_panel import AdvancedVizPanel
from mcp_server.mcp_query_processor import mcp_query_processor
from streamlit_app.components.chat_interface import ChatInterface
from streamlit_app.components.map_view import MapView
from streamlit_app.components.profile_viewer import ProfileViewer
from streamlit_app.components.sidebar import Sidebar
from streamlit_app.utils.session_state import SessionStateManager
from rag_engine.query_processor import QueryProcessor
from database.db_setup import DatabaseSetup
from database.models import ArgoProfile, QueryLog
from dotenv import load_dotenv

load_dotenv()

# Custom CSS - Production Grade
st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main Header */
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(120deg, #1e3a8a, #0891b2, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1.5rem 0;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        font-size: 1.1rem;
        color: #64748b;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 500;
    }
    
    /* Chat Messages - Enhanced Contrast */
    .stChatMessage {
        background-color: #ffffff !important;
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    /* User message */
    .stChatMessage[data-testid="stChatMessage"]:has([aria-label="user"]) {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%) !important;
        border-left: 4px solid #3b82f6;
    }
    
    /* Assistant message */
    .stChatMessage[data-testid="stChatMessage"]:has([aria-label="assistant"]) {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%) !important;
        border-left: 4px solid #10b981;
    }
    
    /* Text Contrast */
    .stChatMessage p, .stChatMessage span, .stChatMessage div {
        color: #1e293b !important;
        line-height: 1.6;
    }
    
    /* Code blocks */
    .stCodeBlock {
        background-color: #1e293b !important;
        border-radius: 8px;
        border: 1px solid #334155;
    }
    
    code {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
        padding: 3px 8px;
        border-radius: 4px;
        font-family: 'Fira Code', monospace;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 700;
        font-size: 1.75rem;
    }
    
    [data-testid="stMetricLabel"] {
        color: #475569 !important;
        font-weight: 600;
        font-size: 0.875rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        transform: translateY(-1px);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8fafc;
        padding: 0.5rem;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: transparent;
        border-radius: 8px;
        color: #64748b;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e2e8f0;
        color: #1e293b;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        color: white !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #f8fafc;
        border-radius: 8px;
        font-weight: 600;
        color: #1e293b !important;
    }
    
    /* Info/Warning/Success boxes */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid;
        padding: 1rem;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    }
    
    /* Dataframe */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
    }
    
    /* Loading spinner */
    .stSpinner > div {
        border-top-color: #3b82f6 !important;
    }
    
    /* Input fields */
    .stTextInput>div>div>input, .stSelectbox>div>div>select {
        border-radius: 8px;
        border: 2px solid #e2e8f0;
        padding: 0.6rem;
        transition: all 0.2s ease;
    }
    
    .stTextInput>div>div>input:focus, .stSelectbox>div>div>select:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .status-success {
        background-color: #d1fae5;
        color: #065f46;
    }
    
    .status-warning {
        background-color: #fef3c7;
        color: #92400e;
    }
    
    .status-info {
        background-color: #dbeafe;
        color: #1e40af;
    }
    </style>
""", unsafe_allow_html=True)


class ProductionFloatChatApp:
    """
    Production-grade FloatChat Application with:
    - Error handling
    - Performance monitoring
    - User analytics
    - Data validation
    - Export capabilities
    """
    
    # def __init__(self):
    #     # Initialize session state
    #     self.session_manager = SessionStateManager()
    #     self.session_manager.initialize()
        
    #     # Initialize database
    #     try:
    #         self.db_setup = DatabaseSetup()
    #         if not self.db_setup.test_connection():
    #             st.error("🔴 Database connection failed. Please check configuration.")
    #             st.stop()
    #     except Exception as e:
    #         st.error(f"🔴 Database initialization error: {e}")
    #         st.stop()
        
    #     # Initialize components
    #     try:
    #         self.query_processor = QueryProcessor()
    #         self.sidebar = Sidebar()
    #         self.chat_interface = ChatInterface(self.query_processor)
    #         self.map_view = MapView()
    #         self.profile_viewer = ProfileViewer()
    #     except Exception as e:
    #         st.error(f"🔴 Component initialization error: {e}")
    #         st.stop()
        
    #     # Analytics
    #     self._init_analytics()
    
    def __init__(self):
        # Initialize session state
        self.session_manager = SessionStateManager()
        self.session_manager.initialize()
    
        # Initialize database
        try:
            self.db_setup = DatabaseSetup()
            if not self.db_setup.test_connection():
                st.error("🔴 Database connection failed. Please check configuration.")
                st.stop()
        except Exception as e:
            st.error(f"🔴 Database initialization error: {e}")
            st.stop()
        
        # Initialize components - MCP ENABLED
        try:
            self.mcp_processor = mcp_query_processor  # MCP Query Processor
            self.sidebar = Sidebar()
            self.mcp_chat_interface = MCPChatInterface()  # MCP Chat Interface
            self.map_view = MapView()
            self.profile_viewer = ProfileViewer()
            self.advanced_viz = AdvancedVizPanel()  # Advanced Visualizations
        except Exception as e:
            st.error(f"🔴 Component initialization error: {e}")
            st.stop()
        
        # Analytics
        self._init_analytics()
        
        print("✅ FloatChat initialized with MCP support")
    
    def _render_advanced_viz_tab(self):
        """Advanced visualization tab"""
        st.subheader("🔬 Advanced Oceanographic Visualizations")
        
        if st.session_state.get('last_query_results') is not None:
            results = st.session_state.last_query_results
            if results['success'] and not results['results'].empty:
                self.advanced_viz.render(results['results'])
            else:
                st.info("🔍 No data to display. Run a query in the Chat tab first.")
        else:
            self._render_empty_state("advanced visualizations")








    
    def _init_analytics(self):
        """Initialize analytics tracking"""
        if 'session_start' not in st.session_state:
            st.session_state.session_start = datetime.now()
        if 'total_queries' not in st.session_state:
            st.session_state.total_queries = 0
        if 'successful_queries' not in st.session_state:
            st.session_state.successful_queries = 0
    
    def run(self):
        """Main application loop"""
        
        # Header with status indicator
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown('<div class="main-header">🌊 FloatChat Pro</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="sub-header">AI-Powered ARGO Ocean Data Discovery & Analysis Platform</div>',
                unsafe_allow_html=True
            )
        
        with col3:
            self._render_status_indicator()
        
        # Sidebar
        self.sidebar.render()
        
        # Main content area - Enhanced Tabs
        # tab1, tab2, tab3, tab4, tab5 = st.tabs([
        #     "💬 Intelligent Chat",
        #     "🗺️ Geographic Explorer",
        #     "📊 Profile Analysis",
        #     "📈 Data Analytics",
        #     "📥 Export & Reports"
        # ])
        
        # with tab1:
        #     self._render_chat_tab()
        
        # with tab2:
        #     self._render_map_tab()
        
        # with tab3:
        #     self._render_profile_tab()
        
        # with tab4:
        #     self._render_analytics_tab()
        
        # with tab5:
        #     self._render_export_tab()
        
        # # Footer with session info
        # self._render_footer()
        
        # Main content area - Enhanced Tabs with MCP
        # tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        #     "💬 Intelligent Chat (MCP)",
        #     "🗺️ Geographic Explorer",
        #     "📊 Profile Analysis",
        #     "🔬 Advanced Visualizations",
        #     "📈 Data Analytics",
        #     "📥 Export & Reports"
        # ])
        # REPLACE WITH THIS:
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "💬 Intelligent Chat (MCP)",
    "🗺️ Geographic Explorer (Plotly)",
    "🗺️ Geographic Explorer (Leaflet)",  # NEW TAB
    "📊 Profile Analysis",
    "🔬 Advanced Visualizations",
    "📈 Data Analytics",
    "📥 Export & Reports"
])
        
        with tab1:
            self._render_chat_tab()
        
        with tab2:
            self._render_map_tab()

        with tab3:
             
             self._render_leaflet_map_tab()    
        
        with tab3:
            self._render_profile_tab()
        
        with tab4:
            self._render_advanced_viz_tab()
        
        with tab5:
            self._render_analytics_tab()
        
        with tab6:
            self._render_export_tab()







    
    def _render_status_indicator(self):
        """Show system status"""
        try:
            session = self.db_setup.get_session()
            count = session.query(ArgoProfile).count()
            session.close()
            
            status_html = f"""
            <div style="text-align: right; padding-top: 1rem;">
                <span class="status-badge status-success">● ONLINE</span><br>
                <small style="color: #64748b;">{count:,} records</small>
            </div>
            """
            st.markdown(status_html, unsafe_allow_html=True)
        except:
            st.markdown(
                '<span class="status-badge status-warning">● LIMITED</span>',
                unsafe_allow_html=True
            )
    
    # def _render_chat_tab(self):
    #     """Enhanced chat interface"""
    #     st.subheader("🤖 Ask Questions About ARGO Data")
        
    #     # Quick action buttons
    #     col1, col2, col3, col4 = st.columns(4)
        
    #     with col1:
    #         if st.button("🌊 Recent Data", use_container_width=True):
    #             st.session_state.quick_query = "Show me data from the last 30 days"
    #     with col2:
    #         if st.button("📍 Arabian Sea", use_container_width=True):
    #             st.session_state.quick_query = "Show profiles in Arabian Sea"
    #     with col3:
    #         if st.button("📊 Statistics", use_container_width=True):
    #             st.session_state.quick_query = "Show me temperature statistics by region"
    #     with col4:
    #         if st.button("🔍 Deep Profiles", use_container_width=True):
    #             st.session_state.quick_query = "Show profiles deeper than 1000m"
        
    #     # Example queries in expander
    #     with st.expander("💡 Example Queries & Tips", expanded=False):
    #         st.markdown("""
    #         **Geographic Queries:**
    #         - Show me salinity profiles in the Arabian Sea
    #         - Find floats between 10°N-20°N and 60°E-80°E
    #         - What's the data coverage in Bay of Bengal?
            
    #         **Temporal Queries:**
    #         - Show recent data from last month
    #         - Temperature trends in March 2023
    #         - Compare winter vs summer profiles
            
    #         **Statistical Queries:**
    #         - Average temperature by depth in Indian Ocean
    #         - Salinity range in equatorial regions
    #         - Count of profiles by region
            
    #         **Profile Analysis:**
    #         - Show temperature profile for float 2902696
    #         - Compare salinity at different depths
    #         - Find deepest measurements
            
    #         **BGC Queries:**
    #         - Show dissolved oxygen levels
    #         - Chlorophyll distribution in coastal areas
    #         - pH measurements in Southern Ocean
            
    #         **💡 Tips:**
    #         - Be specific about regions, dates, and parameters
    #         - Use depth or pressure for vertical queries
    #         - Combine multiple conditions for precise results
    #         """)
        
    #     # Render chat
    #     self.chat_interface.render()
        
    #     # Query performance metrics
    #     if st.session_state.get('last_query_results'):
    #         self._render_query_metrics()
    
    def _render_chat_tab(self):
        """Enhanced chat interface with MCP"""
        st.subheader("🤖 AI-Powered Query Interface (MCP Enabled)")
        
        # Quick action buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🌊 Recent Data", use_container_width=True):
                st.session_state.quick_query = "Show me data from the last 30 days"
        with col2:
            if st.button("📍 Arabian Sea", use_container_width=True):
                st.session_state.quick_query = "Show profiles in Arabian Sea"
        with col3:
            if st.button("📊 Calculate Thermocline", use_container_width=True):
                st.session_state.quick_query = "Calculate thermocline for Bay of Bengal"
        with col4:
            if st.button("🔬 Water Masses", use_container_width=True):
                st.session_state.quick_query = "Identify water masses in Arabian Sea"
        
        # Example queries
        with st.expander("💡 MCP-Powered Query Examples", expanded=False):
            st.markdown("""
            **Basic Queries:**
            - Show me temperature profiles in the Arabian Sea
            - What is the database structure?
            - Find recent data from October 2025
            
            **Advanced Analytics (MCP Tools):**
            - Calculate thermocline characteristics for Bay of Bengal
            - Identify water masses in the Indian Ocean
            - Compare temperature between Arabian Sea and Bay of Bengal
            - Calculate mixed layer depth for recent profiles
            - Analyze salinity gradients in coastal regions
            
            **Spatial Queries:**
            - Find nearest floats to 15°N, 75°E
            - Show profiles within 500km of Mumbai
            
            **Profile Analysis:**
            - Analyze float 2902696 profile statistics
            - Find profiles similar to warm tropical surface water
            
            **Note:** Database contains Core ARGO data only (Temperature, Salinity, Pressure).
            BGC parameters (pH, dissolved oxygen, chlorophyll) are not available.
            
            **💡 MCP automatically selects the right tools for your question!**
            """)
        
        # Render MCP chat interface
        self.mcp_chat_interface.render()
        
        # Query performance metrics
        if st.session_state.get('last_query_results'):
            results = st.session_state.last_query_results
            if results.get('mcp_enabled'):
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🔧 MCP Tools Used", len(results.get('tools_used', [])))
            with col2:
                st.metric("📊 Records Retrieved", 
                         len(results['results']) if 'results' in results else 0)
            with col3:
                tools_str = ", ".join(results.get('tools_used', []))
                st.info(f"Tools: {tools_str}")









    def _render_query_metrics(self):
        """Show query performance metrics"""
        result = st.session_state.last_query_results
        
        if result.get('success'):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "⚡ Query Time",
                    f"{result.get('execution_time', 0):.2f}s",
                    delta=None
                )
            with col2:
                st.metric(
                    "📊 Records",
                    f"{result.get('result_count', 0):,}",
                    delta=None
                )
            with col3:
                complexity = result.get('complexity', 'medium')
                st.metric("🔧 Complexity", complexity.upper())
            with col4:
                st.metric("✅ Status", "SUCCESS", delta="Good")
    
    def _render_map_tab(self):
        """Enhanced map visualization"""
        st.subheader("🗺️ Geographic Distribution")
        
        if st.session_state.get('last_query_results') is not None:
            results = st.session_state.last_query_results
            if results['success'] and not results['results'].empty:
                df = results['results']
                
                # Map controls
                col1, col2 = st.columns([3, 1])
                
                with col2:
                    st.markdown("**Map Settings**")
                    map_type = st.selectbox(
                        "Visualization",
                        ["Scatter Plot", "Density Heatmap", "Time Animation"],
                        key="map_type_select"
                    )
                    
                    if 'temperature' in df.columns:
                        color_by = st.selectbox(
                            "Color By",
                            [c for c in df.columns if c in ['temperature', 'salinity', 'pressure', 'dissolved_oxygen']],
                            key="color_by_select"
                        )
                    else:
                        color_by = 'temperature'
                
                with col1:
                    self.map_view.render(df)
                
                # Geographic summary
                st.markdown("---")
                self._render_geographic_summary(df)
            else:
                st.info("🔍 No data to display. Run a query in the Chat tab first.")
        else:
            self._render_empty_state("map")

    
    def _render_geographic_summary(self, df: pd.DataFrame):
        """Show geographic coverage summary"""
        st.subheader("📍 Geographic Coverage")
        
        # Check if geographic columns exist
        has_lat = 'latitude' in df.columns
        has_lon = 'longitude' in df.columns
        
        if not has_lat or not has_lon:
            st.info("📊 This query returned aggregated statistics without geographic coordinates.")
            return
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Latitude Range", 
                     f"{df['latitude'].min():.1f}° to {df['latitude'].max():.1f}°")
        with col2:
            st.metric("Longitude Range",
                     f"{df['longitude'].min():.1f}° to {df['longitude'].max():.1f}°")
        with col3:
            if 'ocean_region' in df.columns:
                st.metric("Regions", df['ocean_region'].nunique())
        with col4:
            st.metric("Spatial Coverage", 
                     f"{(df['latitude'].max() - df['latitude'].min()) * (df['longitude'].max() - df['longitude'].min()):.0f} deg²")
    
    def _render_profile_tab(self):
        """Enhanced profile visualization"""
        st.subheader("📊 Oceanographic Profiles")
        
        if st.session_state.get('last_query_results') is not None:
            results = st.session_state.last_query_results
            if results['success'] and not results['results'].empty:
                df = results['results']
                
                # Profile controls
                col1, col2 = st.columns([3, 1])
                
                with col2:
                    st.markdown("**Profile Settings**")
                    plot_type = st.selectbox(
                        "Plot Type",
                        ["Temperature Profile", "T-S Diagram", "Multi-Parameter", "Comparison"],
                        key="profile_plot_type"
                    )
                    
                    if 'float_id' in df.columns and df['float_id'].nunique() > 1:
                        max_floats = min(10, df['float_id'].nunique())
                        selected_floats = st.multiselect(
                            "Select Floats",
                            df['float_id'].unique()[:20],
                            default=list(df['float_id'].unique()[:3]),
                            key="float_selector"
                        )
                
                with col1:
                    self.profile_viewer.render(df)
                
                # Profile statistics
                st.markdown("---")
                self._render_profile_statistics(df)
            else:
                st.info("🔍 No data to display. Run a query in the Chat tab first.")
        else:
            self._render_empty_state("profile")

    def _render_leaflet_map_tab(self):
        """Render Leaflet-based interactive map"""
        st.subheader("🗺️ Interactive Leaflet Map")
        
        if st.session_state.get('last_query_results') is not None:
            results = st.session_state.last_query_results
            if results['success'] and not results['results'].empty:
                from streamlit_app.components.leaflet_map import render_leaflet_map_tab
                render_leaflet_map_tab(results['results'])
            else:
                st.info("🔍 No data to display. Run a query in the Chat tab first.")
        else:
            self._render_empty_state("Leaflet map")        
    
    def _render_profile_statistics(self, df: pd.DataFrame):
        """Show profile statistics"""
        st.subheader("📈 Profile Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if 'pressure' in df.columns:
                st.metric("Max Depth", f"{df['pressure'].max():.0f} dbar")
                st.metric("Avg Depth", f"{df['pressure'].mean():.0f} dbar")
        
        with col2:
            if 'temperature' in df.columns:
                st.metric("Temp Range", 
                         f"{df['temperature'].min():.1f}°C - {df['temperature'].max():.1f}°C")
                st.metric("Avg Temp", f"{df['temperature'].mean():.1f}°C")
        
        with col3:
            if 'salinity' in df.columns:
                st.metric("Salinity Range",
                         f"{df['salinity'].min():.2f} - {df['salinity'].max():.2f} PSU")
                st.metric("Avg Salinity", f"{df['salinity'].mean():.2f} PSU")
        
        with col4:
            if 'float_id' in df.columns:
                st.metric("Unique Floats", df['float_id'].nunique())
                profiles = df.groupby(['float_id', 'cycle_number']).ngroups if 'cycle_number' in df.columns else 0
                st.metric("Total Profiles", profiles)
    
    def _render_analytics_tab(self):
        """Data analytics and insights"""
        st.subheader("📈 Data Analytics & Insights")
        
        if st.session_state.get('last_query_results') is not None:
            results = st.session_state.last_query_results
            if results['success'] and not results['results'].empty:
                df = results['results']
                
                # Time series analysis
                if 'timestamp' in df.columns:
                    st.markdown("### 📅 Temporal Analysis")
                    self._render_temporal_analysis(df)
                
                st.markdown("---")
                
                # Statistical analysis
                st.markdown("### 📊 Statistical Summary")
                self._render_statistical_analysis(df)
                
                st.markdown("---")
                
                # Regional analysis
                if 'ocean_region' in df.columns:
                    st.markdown("### 🗺️ Regional Distribution")
                    self._render_regional_analysis(df)
            else:
                st.info("🔍 No data to display. Run a query in the Chat tab first.")
        else:
            self._render_empty_state("analytics")
    
    def _render_temporal_analysis(self, df: pd.DataFrame):
        """Temporal trends analysis"""
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['year_month'] = df['timestamp'].dt.to_period('M').astype(str)
        
        # Measurements over time
        temporal = df.groupby('year_month').size().reset_index(name='count')
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=temporal['year_month'],
            y=temporal['count'],
            mode='lines+markers',
            name='Measurements',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            title="Measurements Over Time",
            xaxis_title="Month",
            yaxis_title="Number of Measurements",
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_statistical_analysis(self, df: pd.DataFrame):
        """Statistical summary"""
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        
        if len(numeric_cols) > 0:
            stats_df = df[numeric_cols].describe().T
            st.dataframe(stats_df.style.format("{:.2f}"), use_container_width=True)
    
    def _render_regional_analysis(self, df: pd.DataFrame):
        """Regional distribution analysis"""
        region_counts = df['ocean_region'].value_counts()
        
        fig = go.Figure(data=[
            go.Bar(
                x=region_counts.index,
                y=region_counts.values,
                marker=dict(
                    color=region_counts.values,
                    colorscale='Viridis',
                    showscale=True
                )
            )
        ])
        
        fig.update_layout(
            title="Data Distribution by Ocean Region",
            xaxis_title="Region",
            yaxis_title="Number of Measurements",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # def _render_export_tab(self):
    #     """Export and reporting"""
    #     st.subheader("📥 Export Data & Generate Reports")
        
    #     if st.session_state.get('last_query_results') is not None:
    #         results = st.session_state.last_query_results
    #         if results['success'] and not results['results'].empty:
    #             df = results['results']
                
    #             st.markdown("### 💾 Download Options")
                
    #             col1, col2, col3 = st.columns(3)
                
    #             with col1:
    #                 csv = df.to_csv(index=False)
    #                 st.download_button(
    #                     label="📄 Download CSV",
    #                     data=csv,
    #                     file_name=f"argo_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    #                     mime="text/csv",
    #                     use_container_width=True
    #                 )
                
    #             with col2:
    #                 json_data = df.to_json(orient='records', indent=2)
    #                 st.download_button(
    #                     label="📋 Download JSON",
    #                     data=json_data,
    #                     file_name=f"argo_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    #                     mime="application/json",
    #                     use_container_width=True
    #                 )
                
    #             with col3:
    #                 excel_buffer = self._create_excel_export(df)
    #                 st.download_button(
    #                     label="📊 Download Excel",
    #                     data=excel_buffer,
    #                     file_name=f"argo_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
    #                     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    #                     use_container_width=True
    #                 )
                
    #             # Report generation
    #             st.markdown("---")
    #             st.markdown("### 📑 Generate Report")
                
    #             if st.button("🎯 Generate Summary Report", use_container_width=True):
    #                 report = self._generate_summary_report(df)
    #                 st.markdown(report)
                    
    #                 st.download_button(
    #                     label="📥 Download Report (MD)",
    #                     data=report,
    #                     file_name=f"argo_report_{datetime.now().strftime('%Y%m%d')}.md",
    #                     mime="text/markdown",
    #                     use_container_width=True
    #                 )
    #         else:
    #             st.info("🔍 No data to export. Run a query first.")
    #     else:
    #         self._render_empty_state("export")
    
    def _render_export_tab(self):
        """Export and reporting - ENHANCED with NetCDF"""
        st.subheader("📥 Export Data & Generate Reports")
        
        if st.session_state.get('last_query_results') is not None:
            results = st.session_state.last_query_results
            if results['success'] and not results['results'].empty:
                df = results['results']
                
                st.markdown("### 💾 Download Options")
                
                # Create tabs for different export formats
                export_tab1, export_tab2, export_tab3, export_tab4 = st.tabs([
                    "📄 CSV/JSON", "🌊 NetCDF", "📋 ARGO ASCII", "📊 Excel"
                ])
                
                with export_tab1:
                    st.markdown("#### Standard Formats")
                    col1, col2 = st.columns(2)
                
                    with col1:
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="📄 Download CSV",
                            data=csv,
                            file_name=f"argo_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        st.caption(f"Comma-separated values • {len(csv)} bytes")
                
                    with col2:
                        json_data = df.to_json(orient='records', indent=2)
                        st.download_button(
                            label="📋 Download JSON",
                            data=json_data,
                            file_name=f"argo_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                        st.caption(f"JSON format • {len(json_data)} bytes")
                
                # with export_tab2:
                #     st.markdown("#### NetCDF Format (CF-Compliant)")
                #     st.info("📦 NetCDF export creates ARGO-compliant files with full metadata")
                
                #     # NetCDF export options
                #     include_bgc = st.checkbox("Include BGC parameters", value=True)
                #     add_metadata = st.checkbox("Add custom metadata", value=False)
                
                #     custom_metadata = {}
                #     if add_metadata:
                #         custom_metadata['author'] = st.text_input("Author", "FloatChat User")
                #         custom_metadata['project'] = st.text_input("Project", "Smart India Hackathon 2025")
                #         custom_metadata['purpose'] = st.text_area("Purpose", "ARGO data analysis")
                
                #     if st.button("🌊 Generate NetCDF File", use_container_width=True):
                #         with st.spinner("Creating NetCDF file..."):
                #             try:
                #                 from data_processing.netcdf_exporter import NetCDFExporter
                #                 from io import BytesIO
                #                 import tempfile
                            
                #                 # Create temporary file
                #                 with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as tmp:
                #                     exporter = NetCDFExporter()
                #                     success = exporter.export_to_netcdf(
                #                         df, 
                #                         tmp.name,
                #                         metadata=custom_metadata if custom_metadata else None
                #                     )
                                
                #                     if success:
                #                         # Read file for download
                #                         with open(tmp.name, 'rb') as f:
                #                             netcdf_data = f.read()
                                    
                #                         st.download_button(
                #                             label="📥 Download NetCDF File",
                #                             data=netcdf_data,
                #                             file_name=f"argo_profiles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.nc",
                #                             mime="application/x-netcdf",
                #                             use_container_width=True
                #                         )
                                    
                #                         st.success(f"✅ NetCDF file created successfully ({len(netcdf_data) / 1024:.2f} KB)")
                                    
                #                         # Show validation
                #                         validation = exporter.validate_netcdf(tmp.name)
                #                         with st.expander("📋 File Validation"):
                #                             st.json(validation)
                #                     else:
                #                         st.error("❌ NetCDF export failed")
                            
                #                 # Cleanup
                #                 import os
                #                 os.unlink(tmp.name)
                            
                #             except Exception as e:
                #                 st.error(f"❌ Error creating NetCDF: {e}")
                #                 import traceback
                #                 st.code(traceback.format_exc())
                with export_tab2:
                    st.markdown("#### NetCDF Format (CF-Compliant)")
                    st.info("📦 NetCDF export creates ARGO-compliant files with full metadata and validation")
                
                    # NetCDF export options
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        include_bgc = st.checkbox("Include BGC parameters", value=True)
                    
                    with col2:
                        validate_output = st.checkbox("Validate output file", value=True)
                    
                    add_metadata = st.checkbox("Add custom metadata", value=False)
                
                    custom_metadata = {}
                    if add_metadata:
                        custom_metadata['author'] = st.text_input("Author", "FloatChat User")
                        custom_metadata['project'] = st.text_input("Project", "Smart India Hackathon 2025")
                        custom_metadata['purpose'] = st.text_area("Purpose", "ARGO data analysis")
                
                    if st.button("🌊 Generate NetCDF File", use_container_width=True):
                        # Create progress bar
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        def update_progress(value, message):
                            progress_bar.progress(value)
                            status_text.info(f"⏳ {message}")
                        
                        try:
                            from data_processing.netcdf_exporter import NetCDFExporter
                            import tempfile
                            import os
                        
                            # Create temporary file
                            with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as tmp:
                                tmp_path = tmp.name
                            
                            exporter = NetCDFExporter()
                            
                            # Export with progress
                            result = exporter.export_with_progress(
                                df,
                                tmp_path,
                                metadata=custom_metadata if custom_metadata else None,
                                progress_callback=update_progress
                            )
                            
                            if result['success']:
                                # Read file for download
                                with open(tmp_path, 'rb') as f:
                                    netcdf_data = f.read()
                                
                                progress_bar.empty()
                                status_text.empty()
                                
                                st.success(f"✅ {result['message']}")
                                st.info(f"📦 File size: {result['file_size_mb']:.2f} MB | Records: {result['records_exported']:,}")
                                
                                st.download_button(
                                    label="📥 Download NetCDF File",
                                    data=netcdf_data,
                                    file_name=f"argo_profiles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.nc",
                                    mime="application/x-netcdf",
                                    use_container_width=True
                                )
                                
                                # Show validation if requested
                                if validate_output:
                                    with st.expander("📋 File Validation Report", expanded=True):
                                        validation = exporter.validate_netcdf(tmp_path)
                                        if validation['valid']:
                                            st.success(f"✅ {validation['message']}")
                                            st.json(validation)
                                        else:
                                            st.error("❌ Validation failed")
                                            st.json(validation)
                            else:
                                progress_bar.empty()
                                status_text.empty()
                                st.error(f"❌ {result['message']}")
                            
                            # Cleanup
                            os.unlink(tmp_path)
                        
                        except Exception as e:
                            progress_bar.empty()
                            status_text.empty()
                            st.error(f"❌ Error creating NetCDF: {e}")
                            import traceback
                            with st.expander("🔍 Error Details"):
                                st.code(traceback.format_exc())
                
                with export_tab3:
                    st.markdown("#### ARGO ASCII Format")
                    st.info("📄 ARGO-specific ASCII format for data exchange")
                
                    if st.button("📋 Generate ARGO ASCII", use_container_width=True):
                        with st.spinner("Creating ASCII file..."):
                            try:
                                from data_processing.netcdf_exporter import NetCDFExporter
                                import tempfile
                            
                                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
                                    exporter = NetCDFExporter()
                                    exporter._write_argo_ascii(df, Path(tmp.name))
                                
                                    with open(tmp.name, 'r') as f:
                                        ascii_data = f.read()
                                
                                    st.download_button(
                                        label="📥 Download ARGO ASCII",
                                        data=ascii_data,
                                        file_name=f"argo_ascii_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                        mime="text/plain",
                                        use_container_width=True
                                    )
                                
                                    # Preview
                                    with st.expander("👁️ Preview (first 20 lines)"):
                                        st.code('\n'.join(ascii_data.split('\n')[:20]))
                            
                                os.unlink(tmp.name)
                                st.success("✅ ARGO ASCII file generated")
                            
                            except Exception as e:
                                st.error(f"❌ Error: {e}")
                
                with export_tab4:
                    st.markdown("#### Excel Workbook")
                    excel_buffer = self._create_excel_export(df)
                    st.download_button(
                        label="📊 Download Excel",
                        data=excel_buffer,
                        file_name=f"argo_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    st.caption("Multi-sheet workbook with data, statistics, and metadata")
                
                # Report generation
                st.markdown("---")
                st.markdown("### 📑 Generate Analysis Report")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    report_format = st.selectbox(
                        "Report Format",
                        ["Markdown", "HTML", "PDF (Future)"]
                    )
                
                with col2:
                    include_viz = st.checkbox("Include visualizations", value=True)
                
                if st.button("🎯 Generate Summary Report", use_container_width=True):
                    report = self._generate_summary_report(df)
                    st.markdown(report)
                    
                    st.download_button(
                        label="📥 Download Report (MD)",
                        data=report,
                        file_name=f"argo_report_{datetime.now().strftime('%Y%m%d')}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
            else:
                st.info("🔍 No data to export. Run a query first.")
        else:
            self._render_empty_state("export")
    
    def _create_excel_export(self, df: pd.DataFrame):
        """Create Excel file with multiple sheets"""
        from io import BytesIO
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Main data
            df.to_excel(writer, sheet_name='Data', index=False)
            
            # Summary statistics
            numeric_df = df.select_dtypes(include=['float64', 'int64'])
            if not numeric_df.empty:
                numeric_df.describe().to_excel(writer, sheet_name='Statistics')
            
            # Metadata
            metadata = pd.DataFrame({
                'Property': ['Export Date', 'Total Records', 'Date Range', 'Columns'],
                'Value': [
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    len(df),
                    f"{df['timestamp'].min()} to {df['timestamp'].max()}" if 'timestamp' in df.columns else 'N/A',
                    ', '.join(df.columns.tolist())
                ]
            })
            metadata.to_excel(writer, sheet_name='Metadata', index=False)
        
        output.seek(0)
        return output
    
    def _generate_summary_report(self, df: pd.DataFrame) -> str:
        """Generate markdown summary report"""
        report = f"""# ARGO Float Data Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 Dataset Overview

- **Total Records**: {len(df):,}
- **Unique Floats**: {df['float_id'].nunique() if 'float_id' in df.columns else 'N/A'}
"""
        
        # Add date range only if timestamp exists
        if 'timestamp' in df.columns:
            report += f"- **Date Range**: {df['timestamp'].min()} to {df['timestamp'].max()}\n"
        
        report += "\n---\n\n"
        
        # Add geographic coverage only if lat/lon exist
        if 'latitude' in df.columns and 'longitude' in df.columns:
            report += f"""## 🗺️ Geographic Coverage

- **Latitude Range**: {df['latitude'].min():.2f}°N to {df['latitude'].max():.2f}°N
- **Longitude Range**: {df['longitude'].min():.2f}°E to {df['longitude'].max():.2f}°E
"""
        else:
            report += "## 📊 Data Summary\n\n"
            report += "*This query returned aggregated statistics without geographic coordinates.*\n\n"
            # Show what columns ARE available
            report += f"**Available Columns**: {', '.join(df.columns.tolist())}\n"

        
        if 'ocean_region' in df.columns:
            report += f"\n### Regional Distribution\n\n"
            for region, count in df['ocean_region'].value_counts().items():
                report += f"- **{region}**: {count:,} measurements ({count/len(df)*100:.1f}%)\n"
        
        report += f"\n---\n\n## 🌡️ Temperature Analysis\n\n"
        if 'temperature' in df.columns:
            report += f"""
- **Range**: {df['temperature'].min():.2f}°C to {df['temperature'].max():.2f}°C
- **Mean**: {df['temperature'].mean():.2f}°C
- **Median**: {df['temperature'].median():.2f}°C
- **Std Dev**: {df['temperature'].std():.2f}°C
"""
        
        report += f"\n---\n\n## 💧 Salinity Analysis\n\n"
        if 'salinity' in df.columns:
            report += f"""
- **Range**: {df['salinity'].min():.2f} to {df['salinity'].max():.2f} PSU
- **Mean**: {df['salinity'].mean():.2f} PSU
- **Median**: {df['salinity'].median():.2f} PSU
- **Std Dev**: {df['salinity'].std():.2f} PSU
"""
        
        report += f"\n---\n\n## 📏 Depth Analysis\n\n"
        if 'pressure' in df.columns:
            report += f"""
- **Maximum Depth**: {df['pressure'].max():.0f} dbar
- **Mean Depth**: {df['pressure'].mean():.0f} dbar
- **Median Depth**: {df['pressure'].median():.0f} dbar
"""
        
        if any(col in df.columns for col in ['dissolved_oxygen', 'chlorophyll', 'ph']):
            report += f"\n---\n\n## 🧪 BGC Parameters\n\n"
            
            if 'dissolved_oxygen' in df.columns:
                report += f"### Dissolved Oxygen\n"
                report += f"- Range: {df['dissolved_oxygen'].min():.2f} to {df['dissolved_oxygen'].max():.2f} μmol/kg\n"
                report += f"- Mean: {df['dissolved_oxygen'].mean():.2f} μmol/kg\n\n"
            
            if 'chlorophyll' in df.columns:
                report += f"### Chlorophyll\n"
                report += f"- Range: {df['chlorophyll'].min():.3f} to {df['chlorophyll'].max():.3f} mg/m³\n"
                report += f"- Mean: {df['chlorophyll'].mean():.3f} mg/m³\n\n"
            
            if 'ph' in df.columns:
                report += f"### pH\n"
                report += f"- Range: {df['ph'].min():.2f} to {df['ph'].max():.2f}\n"
                report += f"- Mean: {df['ph'].mean():.2f}\n\n"
        
        report += f"\n---\n\n## ℹ️ Data Quality\n\n"
        report += f"- **Data Mode**: {df['data_mode'].value_counts().to_dict() if 'data_mode' in df.columns else 'N/A'}\n"
        report += f"- **Missing Values**: {df.isnull().sum().sum()} cells\n"
        report += f"- **Completeness**: {(1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100:.1f}%\n"
        
        report += f"\n---\n\n*Report generated by FloatChat Pro - ARGO Data Analysis Platform*\n"
        
        return report
    
    def _render_empty_state(self, tab_name: str):
        """Render empty state for tabs"""
        st.info(f"""
        ### 🔍 No Data Available
        
        To view {tab_name} visualizations:
        1. Go to the **Chat** tab
        2. Ask a question about ARGO data
        3. Results will appear here automatically
        
        **Try these examples:**
        - "Show me recent data from the last 30 days"
        - "Temperature profiles in Arabian Sea"
        - "Statistics by ocean region"
        """)
    
    def _render_footer(self):
        """Render application footer"""
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **FloatChat Pro**  
            Version 2.0 | Production Release  
            Ministry of Earth Sciences (MoES) | INCOIS
            """)
        
        with col2:
            session_duration = datetime.now() - st.session_state.session_start
            st.markdown(f"""
            **Session Info**  
            Duration: {session_duration.seconds // 60} minutes  
            Queries: {st.session_state.total_queries}  
            Success Rate: {(st.session_state.successful_queries / max(st.session_state.total_queries, 1) * 100):.0f}%
            """)
        
        with col3:
            st.markdown("""
            **Support**  
            📧 [support@floatchat.org](mailto:support@floatchat.org)  
            📚 [Documentation](https://docs.floatchat.org)  
            💬 [Feedback](https://feedback.floatchat.org)
            """)


# Run the app
if __name__ == "__main__":
    try:
        app = ProductionFloatChatApp()
        app.run()
    except Exception as e:
        st.error(f"🔴 Critical Application Error: {e}")
        st.error("Please contact support if this issue persists.")
        
        if st.button("🔄 Restart Application"):
            st.rerun()