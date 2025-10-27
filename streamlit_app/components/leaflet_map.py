"""
Leaflet-based interactive map component
Alternative to Plotly maps with more detailed controls
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium import plugins
import numpy as np


class LeafletMapView:
    """
    Enhanced map visualization using Folium/Leaflet
    """
    
    def __init__(self):
        self.default_location = [10.0, 75.0]  # Indian Ocean center
        self.default_zoom = 5
    
    def render(self, df: pd.DataFrame, map_type: str = "markers"):
        """Render Leaflet map"""
        
        if df.empty or 'latitude' not in df.columns or 'longitude' not in df.columns:
            st.info("📍 No geographic data available for mapping")
            return
        
        # Create base map
        center_lat = df['latitude'].mean()
        center_lon = df['longitude'].mean()
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=self.default_zoom,
            tiles='OpenStreetMap'
        )
        
        # Add map controls
        if map_type == "markers":
            self._add_markers(m, df)
        elif map_type == "heatmap":
            self._add_heatmap(m, df)
        elif map_type == "clusters":
            self._add_clusters(m, df)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Add minimap
        plugins.MiniMap().add_to(m)
        
        # Add fullscreen button
        plugins.Fullscreen().add_to(m)
        
        # Display map
        st_folium(m, width=None, height=600)
    
    def _add_markers(self, m: folium.Map, df: pd.DataFrame):
        """Add individual markers for each float"""
        
        for idx, row in df.iterrows():
            # Create popup content
            popup_html = self._create_popup(row)
            
            # Determine marker color based on temperature
            if 'temperature' in df.columns:
                temp = row['temperature']
                if temp > 28:
                    color = 'red'
                elif temp > 25:
                    color = 'orange'
                elif temp > 20:
                    color = 'green'
                else:
                    color = 'blue'
            else:
                color = 'blue'
            
            # Add marker
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"Float: {row.get('float_id', 'Unknown')}",
                icon=folium.Icon(color=color, icon='tint', prefix='fa')
            ).add_to(m)
    
    def _add_heatmap(self, m: folium.Map, df: pd.DataFrame):
        """Add heatmap layer"""
        
        heat_data = [[row['latitude'], row['longitude']] for idx, row in df.iterrows()]
        
        plugins.HeatMap(
            heat_data,
            radius=15,
            blur=25,
            max_zoom=13,
            gradient={0.4: 'blue', 0.65: 'lime', 0.8: 'yellow', 1.0: 'red'}
        ).add_to(m)
    
    def _add_clusters(self, m: folium.Map, df: pd.DataFrame):
        """Add marker clusters for large datasets"""
        
        marker_cluster = plugins.MarkerCluster().add_to(m)
        
        for idx, row in df.iterrows():
            popup_html = self._create_popup(row)
            
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"Float: {row.get('float_id', 'Unknown')}"
            ).add_to(marker_cluster)
    
    def _create_popup(self, row: pd.Series) -> str:
        """Create HTML popup content"""
        
        html = "<div style='font-family: Arial; font-size: 12px;'>"
        html += "<b>🌊 ARGO Float Data</b><br><hr>"
        
        if 'float_id' in row:
            html += f"<b>Float ID:</b> {row['float_id']}<br>"
        
        html += f"<b>📍 Location:</b><br>"
        html += f"&nbsp;&nbsp;Lat: {row['latitude']:.4f}°N<br>"
        html += f"&nbsp;&nbsp;Lon: {row['longitude']:.4f}°E<br>"
        
        if 'timestamp' in row:
            html += f"<b>📅 Date:</b> {row['timestamp']}<br>"
        
        if 'temperature' in row:
            html += f"<b>🌡️ Temp:</b> {row['temperature']:.2f}°C<br>"
        
        if 'salinity' in row:
            html += f"<b>💧 Salinity:</b> {row['salinity']:.2f} PSU<br>"
        
        if 'pressure' in row:
            html += f"<b>🌊 Depth:</b> {row['pressure']:.0f} dbar<br>"
        
        html += "</div>"
        
        return html


def render_leaflet_map_tab(df: pd.DataFrame):
    """Render Leaflet map in Streamlit tab"""
    
    st.subheader("🗺️ Interactive Leaflet Map")
    
    if df.empty:
        st.info("📍 No data to display. Run a query first!")
        return
    
    # Map type selector
    col1, col2 = st.columns([1, 3])
    
    with col1:
        map_type = st.selectbox(
            "Map Style",
            ["markers", "heatmap", "clusters"],
            format_func=lambda x: {
                "markers": "📍 Individual Markers",
                "heatmap": "🔥 Density Heatmap",
                "clusters": "🎯 Clustered Markers"
            }[x]
        )
    
    with col2:
        st.info("🗺️ **Leaflet Map Features:** Zoom, pan, fullscreen, and interactive popups")
    
    # Render map
    leaflet = LeafletMapView()
    leaflet.render(df, map_type)
    
    # Add download button for map
    st.download_button(
        label="📥 Download Map HTML",
        data=_export_map_html(df),
        file_name="argo_map.html",
        mime="text/html"
    )


def _export_map_html(df: pd.DataFrame) -> str:
    """Export map as standalone HTML"""
    
    center_lat = df['latitude'].mean()
    center_lon = df['longitude'].mean()
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=5)
    
    for idx, row in df.iterrows():
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=f"Float: {row.get('float_id', 'Unknown')}"
        ).add_to(m)
    
    return m._repr_html_()