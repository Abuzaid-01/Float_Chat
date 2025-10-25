import streamlit as st
import pandas as pd
from visualization.profile_plots import ProfilePlotter

class ProfileViewer:
    """Profile visualization component"""
    
    def __init__(self):
        self.plotter = ProfilePlotter()
    
    def render(self, df: pd.DataFrame):
        """Render profile visualizations"""
        
        # Check required columns
        required_cols = ['pressure', 'temperature']
        if not all(col in df.columns for col in required_cols):
            st.warning("⚠️ Pressure and temperature data required for profile plots")
            return
        
        # Visualization options
        st.sidebar.subheader("📊 Profile Options")
        
        plot_type = st.sidebar.selectbox(
            "Plot Type",
            ["Temperature Profile", "T-S Diagram", "Multi-Parameter", "Comparison"]
        )
        
        if plot_type == "Temperature Profile":
            # Filter by float ID if available
            float_ids = None
            if 'float_id' in df.columns:
                all_floats = df['float_id'].unique()
                if len(all_floats) > 1:
                    selected_floats = st.sidebar.multiselect(
                        "Select Float IDs",
                        all_floats,
                        default=list(all_floats)[:5]  # Max 5 by default
                    )
                    float_ids = selected_floats if selected_floats else None
            
            fig = self.plotter.create_temperature_profile(
                df,
                float_ids=float_ids,
                title="Temperature-Depth Profile"
            )
            
        elif plot_type == "T-S Diagram":
            if 'salinity' not in df.columns:
                st.warning("⚠️ Salinity data required for T-S diagram")
                return
            
            fig = self.plotter.create_ts_diagram(
                df,
                title="Temperature-Salinity Diagram"
            )
            
        elif plot_type == "Multi-Parameter":
            available_params = [col for col in df.columns 
                              if col in ['temperature', 'salinity', 
                                        'dissolved_oxygen', 'chlorophyll']]
            
            selected_params = st.sidebar.multiselect(
                "Select Parameters",
                available_params,
                default=available_params[:2]
            )
            
            if selected_params:
                fig = self.plotter.create_multi_parameter_profile(
                    df,
                    parameters=selected_params,
                    title="Multi-Parameter Profile"
                )
            else:
                st.warning("Please select at least one parameter")
                return
                
        else:  # Comparison
            if 'timestamp' in df.columns:
                # Only show available grouping columns
                group_options = [col for col in ['timestamp', 'float_id', 'cycle_number'] if col in df.columns]
                if group_options:
                    group_by = st.sidebar.selectbox("Group By", group_options)
                else:
                    group_by = 'timestamp'  # fallback
            else:
                group_by = 'float_id' if 'float_id' in df.columns else list(df.columns)[0]
            
            fig = self.plotter.create_profile_comparison(
                df,
                group_by=group_by,
                title=f"Profile Comparison by {group_by}"
            )
        
        # Display plot
        st.plotly_chart(fig, use_container_width=True)
        
        # Display profile statistics
        self._display_profile_stats(df)
    
    def _display_profile_stats(self, df: pd.DataFrame):
        """Display profile statistics"""
        st.subheader("📊 Profile Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if 'pressure' in df.columns:
                st.metric("Max Depth", f"{df['pressure'].max():.1f} dbar")
        
        with col2:
            if 'temperature' in df.columns:
                st.metric("Temp Range", 
                         f"{df['temperature'].min():.1f}°C - {df['temperature'].max():.1f}°C")
        
        with col3:
            if 'salinity' in df.columns:
                st.metric("Salinity Range",
                         f"{df['salinity'].min():.2f} - {df['salinity'].max():.2f} PSU")
        
        with col4:
            if 'float_id' in df.columns and 'cycle_number' in df.columns:
                st.metric("Unique Profiles", df.groupby(['float_id', 'cycle_number']).ngroups)
            elif 'float_id' in df.columns:
                st.metric("Unique Floats", df['float_id'].nunique())
