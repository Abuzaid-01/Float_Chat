"""
Data Dashboard Component
User-friendly overview of available ARGO data
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database.db_setup import DatabaseSetup
from sqlalchemy import text


class DataDashboard:
    """Interactive dashboard showing data availability and statistics"""
    
    def __init__(self):
        self.db_setup = DatabaseSetup()
    
    def render(self):
        """Render the complete dashboard"""
        
        # Header with gradient
        st.markdown("""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 2rem; 
                        border-radius: 12px; 
                        margin-bottom: 2rem;
                        text-align: center;'>
                <h1 style='color: white; margin: 0; font-weight: 800;'>
                    📊 ARGO Data Dashboard
                </h1>
                <p style='color: #e0e7ff; margin-top: 0.5rem; font-size: 1.1rem;'>
                    Real-time overview of available oceanographic data
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        # Load data statistics
        with st.spinner("Loading dashboard data..."):
            stats = self._get_database_statistics()
        
        # Top-level metrics
        self._render_top_metrics(stats)
        
        st.markdown("---")
        
        # Main dashboard content in tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🗺️ Regional Distribution",
            "📈 Temporal Coverage",
            "🔬 Data Quality",
            "🌊 Parameter Availability",
            "🏆 Top Floats"
        ])
        
        with tab1:
            self._render_regional_distribution(stats)
        
        with tab2:
            self._render_temporal_coverage(stats)
        
        with tab3:
            self._render_data_quality(stats)
        
        with tab4:
            self._render_parameter_availability(stats)
        
        with tab5:
            self._render_top_floats(stats)
    
    def _get_database_statistics(self):
        """Fetch comprehensive database statistics"""
        session = self.db_setup.get_session()
        
        try:
            # Overall statistics
            overall_query = text("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT float_id) as unique_floats,
                    COUNT(DISTINCT cycle_number) as total_cycles,
                    MIN(timestamp) as earliest_date,
                    MAX(timestamp) as latest_date,
                    MIN(latitude) as min_lat,
                    MAX(latitude) as max_lat,
                    MIN(longitude) as min_lon,
                    MAX(longitude) as max_lon,
                    MIN(pressure) as min_depth,
                    MAX(pressure) as max_depth
                FROM argo_profiles;
            """)
            
            overall_df = pd.read_sql(overall_query, session.bind)
            
            # Regional distribution
            regional_query = text("""
                SELECT 
                    CASE 
                        WHEN latitude BETWEEN 5 AND 30 AND longitude BETWEEN 40 AND 80 
                            THEN 'Arabian Sea'
                        WHEN latitude BETWEEN -50 AND -10 AND longitude BETWEEN 20 AND 120 
                            THEN 'Southern Indian Ocean'
                        WHEN latitude BETWEEN 5 AND 25 AND longitude BETWEEN 80 AND 100 
                            THEN 'Bay of Bengal'
                        WHEN latitude BETWEEN -10 AND 5 AND longitude BETWEEN 40 AND 100 
                            THEN 'Equatorial Indian Ocean'
                        ELSE 'Other Regions'
                    END as region,
                    COUNT(*) as record_count,
                    COUNT(DISTINCT float_id) as float_count,
                    AVG(temperature) as avg_temp,
                    AVG(salinity) as avg_salinity
                FROM argo_profiles
                WHERE temperature IS NOT NULL AND salinity IS NOT NULL
                GROUP BY region
                ORDER BY record_count DESC;
            """)
            
            regional_df = pd.read_sql(regional_query, session.bind)
            
            # Temporal distribution (monthly)
            temporal_query = text("""
                SELECT 
                    DATE_TRUNC('month', timestamp) as month,
                    COUNT(*) as measurements,
                    COUNT(DISTINCT float_id) as active_floats
                FROM argo_profiles
                WHERE timestamp >= CURRENT_DATE - INTERVAL '12 months'
                GROUP BY month
                ORDER BY month;
            """)
            
            temporal_df = pd.read_sql(temporal_query, session.bind)
            
            # Data quality distribution
            quality_query = text("""
                SELECT 
                    CASE 
                        WHEN temp_qc = 1 THEN 'Good (QC=1)'
                        WHEN temp_qc = 2 THEN 'Probably Good (QC=2)'
                        WHEN temp_qc = 3 THEN 'Questionable (QC=3)'
                        WHEN temp_qc = 4 THEN 'Bad (QC=4)'
                        WHEN temp_qc = 9 THEN 'Missing (QC=9)'
                        ELSE 'Unknown'
                    END as quality,
                    COUNT(*) as count
                FROM argo_profiles
                GROUP BY quality
                ORDER BY count DESC;
            """)
            
            quality_df = pd.read_sql(quality_query, session.bind)
            
            # Parameter availability
            param_query = text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN temperature IS NOT NULL THEN 1 ELSE 0 END) as has_temperature,
                    SUM(CASE WHEN salinity IS NOT NULL THEN 1 ELSE 0 END) as has_salinity,
                    SUM(CASE WHEN dissolved_oxygen IS NOT NULL THEN 1 ELSE 0 END) as has_oxygen,
                    SUM(CASE WHEN chlorophyll IS NOT NULL THEN 1 ELSE 0 END) as has_chlorophyll,
                    SUM(CASE WHEN ph IS NOT NULL THEN 1 ELSE 0 END) as has_ph
                FROM argo_profiles;
            """)
            
            param_df = pd.read_sql(param_query, session.bind)
            
            # Top floats by measurements
            top_floats_query = text("""
                SELECT 
                    float_id,
                    COUNT(*) as measurements,
                    COUNT(DISTINCT cycle_number) as cycles,
                    MIN(timestamp) as first_measurement,
                    MAX(timestamp) as last_measurement,
                    AVG(latitude) as avg_lat,
                    AVG(longitude) as avg_lon
                FROM argo_profiles
                GROUP BY float_id
                ORDER BY measurements DESC
                LIMIT 10;
            """)
            
            top_floats_df = pd.read_sql(top_floats_query, session.bind)
            
            session.close()
            
            return {
                'overall': overall_df,
                'regional': regional_df,
                'temporal': temporal_df,
                'quality': quality_df,
                'parameters': param_df,
                'top_floats': top_floats_df
            }
            
        except Exception as e:
            session.close()
            st.error(f"Error loading statistics: {e}")
            return None
    
    def _render_top_metrics(self, stats):
        """Render key metrics at the top"""
        if not stats:
            return
        
        overall = stats['overall'].iloc[0]
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                label="📦 Total Records",
                value=f"{overall['total_records']:,}",
                help="Total measurements in database"
            )
        
        with col2:
            st.metric(
                label="🎈 Active Floats",
                value=f"{overall['unique_floats']:,}",
                help="Number of unique ARGO floats"
            )
        
        with col3:
            st.metric(
                label="🔄 Total Cycles",
                value=f"{overall['total_cycles']:,}",
                help="Measurement cycles completed"
            )
        
        with col4:
            days_covered = (overall['latest_date'] - overall['earliest_date']).days
            st.metric(
                label="📅 Days Covered",
                value=f"{days_covered}",
                help=f"From {overall['earliest_date'].strftime('%Y-%m-%d')} to {overall['latest_date'].strftime('%Y-%m-%d')}"
            )
        
        with col5:
            st.metric(
                label="🌊 Max Depth",
                value=f"{overall['max_depth']:,.0f} m",
                help="Maximum measurement depth in meters"
            )
    
    def _render_regional_distribution(self, stats):
        """Render regional distribution charts"""
        if not stats or stats['regional'].empty:
            st.warning("No regional data available")
            return
        
        st.subheader("📍 Data Distribution by Ocean Region")
        
        regional_df = stats['regional']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart of records
            fig_pie = px.pie(
                regional_df,
                values='record_count',
                names='region',
                title='Measurement Distribution',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Bar chart of float counts
            fig_bar = px.bar(
                regional_df,
                x='region',
                y='float_count',
                title='Active Floats per Region',
                color='float_count',
                color_continuous_scale='Blues'
            )
            fig_bar.update_layout(showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Detailed table
        st.markdown("### 📊 Regional Statistics")
        
        display_df = regional_df.copy()
        display_df['record_count'] = display_df['record_count'].apply(lambda x: f"{x:,}")
        display_df['avg_temp'] = display_df['avg_temp'].apply(lambda x: f"{x:.2f}°C" if pd.notna(x) else "N/A")
        display_df['avg_salinity'] = display_df['avg_salinity'].apply(lambda x: f"{x:.2f} PSU" if pd.notna(x) else "N/A")
        
        display_df.columns = ['Region', 'Total Records', 'Active Floats', 'Avg Temperature', 'Avg Salinity']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    def _render_temporal_coverage(self, stats):
        """Render temporal coverage charts"""
        if not stats or stats['temporal'].empty:
            st.warning("No temporal data available")
            return
        
        st.subheader("📅 Data Collection Timeline")
        
        temporal_df = stats['temporal']
        temporal_df['month'] = pd.to_datetime(temporal_df['month'])
        
        # Line chart for measurements over time
        fig_line = go.Figure()
        
        fig_line.add_trace(go.Scatter(
            x=temporal_df['month'],
            y=temporal_df['measurements'],
            mode='lines+markers',
            name='Measurements',
            line=dict(color='#667eea', width=3),
            fill='tozeroy',
            fillcolor='rgba(102, 126, 234, 0.2)'
        ))
        
        fig_line.update_layout(
            title='Monthly Measurements Trend',
            xaxis_title='Month',
            yaxis_title='Number of Measurements',
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig_line, use_container_width=True)
        
        # Active floats over time
        fig_floats = go.Figure()
        
        fig_floats.add_trace(go.Bar(
            x=temporal_df['month'],
            y=temporal_df['active_floats'],
            name='Active Floats',
            marker_color='#764ba2'
        ))
        
        fig_floats.update_layout(
            title='Active Floats per Month',
            xaxis_title='Month',
            yaxis_title='Number of Active Floats',
            height=400
        )
        
        st.plotly_chart(fig_floats, use_container_width=True)
        
        # Summary stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_measurements = temporal_df['measurements'].mean()
            st.metric("📊 Avg Monthly Measurements", f"{avg_measurements:,.0f}")
        
        with col2:
            total_recent = temporal_df['measurements'].sum()
            st.metric("📦 Last 12 Months Total", f"{total_recent:,}")
        
        with col3:
            avg_floats = temporal_df['active_floats'].mean()
            st.metric("🎈 Avg Active Floats/Month", f"{avg_floats:.0f}")
    
    def _render_data_quality(self, stats):
        """Render data quality metrics"""
        if not stats or stats['quality'].empty:
            st.warning("No quality data available")
            return
        
        st.subheader("✅ Data Quality Overview")
        
        quality_df = stats['quality']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Donut chart for quality distribution
            fig_donut = px.pie(
                quality_df,
                values='count',
                names='quality',
                title='Quality Flag Distribution',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        
        with col2:
            # Quality metrics
            total_records = quality_df['count'].sum()
            good_records = quality_df[quality_df['quality'].str.contains('Good', case=False, na=False)]['count'].sum()
            good_percentage = (good_records / total_records * 100) if total_records > 0 else 0
            
            st.markdown("### 📈 Quality Metrics")
            st.metric("✅ Good Quality Data", f"{good_percentage:.1f}%", help="QC flags 1 and 2")
            st.metric("📦 Total Records Checked", f"{total_records:,}")
            st.metric("⭐ High Quality Records", f"{good_records:,}")
            
            # Quality interpretation
            st.info("""
            **Quality Control Flags:**
            - **QC = 1**: Good data ✅
            - **QC = 2**: Probably good data ✔️
            - **QC = 3**: Questionable ⚠️
            - **QC = 4**: Bad data ❌
            - **QC = 9**: Missing data 🔍
            """)
    
    def _render_parameter_availability(self, stats):
        """Render parameter availability"""
        if not stats or stats['parameters'].empty:
            st.warning("No parameter data available")
            return
        
        st.subheader("🔬 Available Measurements")
        
        param_df = stats['parameters'].iloc[0]
        total = param_df['total']
        
        # Create availability data
        params = {
            'Temperature': param_df['has_temperature'],
            'Salinity': param_df['has_salinity'],
            'Dissolved Oxygen': param_df['has_oxygen'],
            'Chlorophyll': param_df['has_chlorophyll'],
            'pH': param_df['has_ph']
        }
        
        param_availability = pd.DataFrame([
            {
                'Parameter': name,
                'Count': count,
                'Percentage': (count / total * 100) if total > 0 else 0,
                'Available': '✅' if count > 0 else '❌'
            }
            for name, count in params.items()
        ])
        
        # Horizontal bar chart
        fig_bar = px.bar(
            param_availability,
            y='Parameter',
            x='Percentage',
            orientation='h',
            title='Parameter Coverage (%)',
            color='Percentage',
            color_continuous_scale='Greens',
            text='Percentage'
        )
        
        fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_bar.update_layout(showlegend=False, height=400)
        
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Detailed table
        st.markdown("### 📋 Parameter Details")
        
        display_param = param_availability.copy()
        display_param['Count'] = display_param['Count'].apply(lambda x: f"{x:,}")
        display_param['Percentage'] = display_param['Percentage'].apply(lambda x: f"{x:.2f}%")
        
        st.dataframe(display_param, use_container_width=True, hide_index=True)
        
        # Key insights
        core_params = param_df['has_temperature'] + param_df['has_salinity']
        core_percentage = (core_params / (total * 2) * 100) if total > 0 else 0
        
        bgc_params = param_df['has_oxygen'] + param_df['has_chlorophyll'] + param_df['has_ph']
        bgc_percentage = (bgc_params / (total * 3) * 100) if total > 0 else 0
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("🌡️ Core Parameters Coverage", f"{core_percentage:.1f}%", 
                     help="Temperature & Salinity")
        
        with col2:
            st.metric("🔬 BGC Parameters Coverage", f"{bgc_percentage:.1f}%",
                     help="Oxygen, Chlorophyll, pH")
    
    def _render_top_floats(self, stats):
        """Render top floats by activity"""
        if not stats or stats['top_floats'].empty:
            st.warning("No float data available")
            return
        
        st.subheader("🏆 Most Active ARGO Floats")
        
        top_floats_df = stats['top_floats']
        
        # Bar chart of measurements
        fig_top = px.bar(
            top_floats_df,
            x='float_id',
            y='measurements',
            title='Top 10 Floats by Measurements',
            color='measurements',
            color_continuous_scale='Viridis',
            text='measurements'
        )
        
        fig_top.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig_top.update_layout(showlegend=False, xaxis_title='Float ID', yaxis_title='Total Measurements')
        
        st.plotly_chart(fig_top, use_container_width=True)
        
        # Detailed table
        st.markdown("### 📊 Float Details")
        
        display_floats = top_floats_df.copy()
        display_floats['measurements'] = display_floats['measurements'].apply(lambda x: f"{x:,}")
        display_floats['first_measurement'] = pd.to_datetime(display_floats['first_measurement']).dt.strftime('%Y-%m-%d')
        display_floats['last_measurement'] = pd.to_datetime(display_floats['last_measurement']).dt.strftime('%Y-%m-%d')
        display_floats['avg_lat'] = display_floats['avg_lat'].apply(lambda x: f"{x:.2f}°N")
        display_floats['avg_lon'] = display_floats['avg_lon'].apply(lambda x: f"{x:.2f}°E")
        
        display_floats.columns = ['Float ID', 'Total Measurements', 'Cycles', 'First Seen', 'Last Seen', 'Avg Latitude', 'Avg Longitude']
        
        st.dataframe(display_floats, use_container_width=True, hide_index=True)
        
        # Float activity summary
        total_top_measurements = top_floats_df['measurements'].sum()
        total_database = stats['overall'].iloc[0]['total_records']
        top_percentage = (total_top_measurements / total_database * 100) if total_database > 0 else 0
        
        st.info(f"💡 **Insight:** The top 10 floats account for **{top_percentage:.1f}%** of all measurements!")
