import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional, List

class MapVisualizer:
    """
    Create interactive geographic visualizations.
    Uses Plotly for rich, zoomable maps.
    """
    
    def __init__(self):
        self.default_mapbox_style = "open-street-map"
    
    def create_float_trajectory_map(
        self,
        df: pd.DataFrame,
        color_by: str = 'temperature',
        title: str = "ARGO Float Locations"
    ) -> go.Figure:
        """
        Create interactive map showing float locations colored by parameter.
        
        Args:
            df: DataFrame with latitude, longitude, and parameter columns
            color_by: Column name to color points by
            title: Map title
            
        Returns:
            Plotly Figure object
        """
        if df.empty:
            return self._create_empty_map(title)
        
        # Check if color_by column exists, if not use default or first available numeric column
        if color_by not in df.columns:
            # Try to find a suitable numeric column
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
            # Remove lat/lon from options
            numeric_cols = [col for col in numeric_cols if col not in ['latitude', 'longitude', 'id']]
            
            if numeric_cols:
                color_by = numeric_cols[0]
            else:
                # No numeric column available, create a simple map without coloring
                return self._create_simple_location_map(df, title)
        
        # Build hover_data dictionary with only available columns
        hover_data = {
            'latitude': ':.2f',
            'longitude': ':.2f'
        }
        
        # Add color_by column to hover_data if it's numeric
        if color_by in df.columns and pd.api.types.is_numeric_dtype(df[color_by]):
            hover_data[color_by] = ':.2f'
        
        # Add other commonly useful columns if they exist
        optional_cols = ['float_id', 'cycle_number', 'pressure', 'salinity', 'dissolved_oxygen']
        for col in optional_cols:
            if col in df.columns and col != color_by:
                if pd.api.types.is_numeric_dtype(df[col]):
                    hover_data[col] = ':.2f'
        
        # Add timestamp separately (don't format it)
        if 'timestamp' in df.columns and 'timestamp' != color_by:
            hover_data['timestamp'] = True
        
        # Create scatter mapbox
        fig = px.scatter_mapbox(
            df,
            lat='latitude',
            lon='longitude',
            color=color_by,
            size=[10] * len(df),  # Fixed size for visibility
            hover_data=hover_data,
            color_continuous_scale='Viridis',
            title=title,
            zoom=3
        )
        
        # Update layout
        fig.update_layout(
            mapbox_style=self.default_mapbox_style,
            height=600,
            margin={"r": 0, "t": 40, "l": 0, "b": 0}
        )
        
        return fig
    
    def create_density_heatmap(
        self,
        df: pd.DataFrame,
        title: str = "ARGO Float Density"
    ) -> go.Figure:
        """
        Create heatmap showing concentration of measurements.
        Useful for identifying data-rich regions.
        """
        if df.empty:
            return self._create_empty_map(title)
        
        # Check for required columns
        if 'latitude' not in df.columns or 'longitude' not in df.columns:
            return self._create_empty_map(title, "Geographic data (latitude/longitude) required for heatmap")
        
        fig = go.Figure(go.Densitymapbox(
            lat=df['latitude'],
            lon=df['longitude'],
            radius=20,
            colorscale='Hot',
            showscale=True,
            hoverinfo='none'
        ))
        
        fig.update_layout(
            mapbox_style=self.default_mapbox_style,
            mapbox=dict(
                center=dict(
                    lat=df['latitude'].mean(),
                    lon=df['longitude'].mean()
                ),
                zoom=3
            ),
            title=title,
            height=600,
            margin={"r": 0, "t": 40, "l": 0, "b": 0}
        )
        
        return fig
    
    def create_time_animated_map(
        self,
        df: pd.DataFrame,
        time_column: str = 'timestamp',
        title: str = "ARGO Float Trajectories Over Time"
    ) -> go.Figure:
        """
        Create animated map showing float movements over time.
        Great for visualizing temporal patterns.
        """
        if df.empty or time_column not in df.columns:
            return self._create_empty_map(title)
        
        # Convert timestamp to datetime
        df[time_column] = pd.to_datetime(df[time_column])
        df = df.sort_values(time_column)
        
        # Create time bins (monthly)
        df['time_period'] = df[time_column].dt.to_period('M').astype(str)
        
        # Find a suitable color column
        color_col = None
        if 'temperature' in df.columns:
            color_col = 'temperature'
        else:
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
            numeric_cols = [col for col in numeric_cols if col not in ['latitude', 'longitude', 'id']]
            if numeric_cols:
                color_col = numeric_cols[0]
        
        # Build hover_data with available columns
        hover_data = {'latitude': ':.2f', 'longitude': ':.2f'}
        optional_cols = ['temperature', 'salinity', 'pressure', 'float_id', 'cycle_number', 'dissolved_oxygen']
        for col in optional_cols:
            if col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    hover_data[col] = ':.2f'
        
        # Add timestamp separately
        if 'timestamp' in df.columns:
            hover_data['timestamp'] = True
        
        # Create map
        if color_col:
            fig = px.scatter_mapbox(
                df,
                lat='latitude',
                lon='longitude',
                animation_frame='time_period',
                color=color_col,
                size=[10] * len(df),
                hover_data=hover_data,
                color_continuous_scale='RdYlBu_r',
                title=title,
                zoom=3
            )
        else:
            # No color column available
            fig = px.scatter_mapbox(
                df,
                lat='latitude',
                lon='longitude',
                animation_frame='time_period',
                size=[10] * len(df),
                hover_data=hover_data,
                title=title,
                zoom=3
            )
        
        fig.update_layout(
            mapbox_style=self.default_mapbox_style,
            height=600,
            margin={"r": 0, "t": 40, "l": 0, "b": 0}
        )
        
        return fig
    
    def _create_simple_location_map(self, df: pd.DataFrame, title: str) -> go.Figure:
        """
        Create a simple map showing locations without color coding.
        Used when no numeric columns are available for coloring.
        """
        # Build hover_data dictionary with available columns
        hover_data = {
            'latitude': ':.2f',
            'longitude': ':.2f'
        }
        
        # Add other available columns, properly checking types
        for col in df.columns:
            if col not in ['latitude', 'longitude', 'id']:
                if pd.api.types.is_numeric_dtype(df[col]):
                    hover_data[col] = ':.2f'
                elif col != 'timestamp':  # Don't format timestamp
                    hover_data[col] = True
        
        # Add timestamp separately
        if 'timestamp' in df.columns:
            hover_data['timestamp'] = True
        
        # Create scatter mapbox without color
        fig = px.scatter_mapbox(
            df,
            lat='latitude',
            lon='longitude',
            size=[10] * len(df),
            hover_data=hover_data,
            title=title,
            zoom=3
        )
        
        # Update layout
        fig.update_layout(
            mapbox_style=self.default_mapbox_style,
            height=600,
            margin={"r": 0, "t": 40, "l": 0, "b": 0}
        )
        
        return fig
    
    def _create_hover_text(self, df: pd.DataFrame) -> List[str]:
        """Create informative hover text for each point"""
        hover_texts = []
        for _, row in df.iterrows():
            text = f"Lat: {row['latitude']:.2f}°N<br>"
            text += f"Lon: {row['longitude']:.2f}°E<br>"
            if 'temperature' in row:
                text += f"Temp: {row['temperature']:.2f}°C<br>"
            if 'salinity' in row:
                text += f"Salinity: {row['salinity']:.2f} PSU"
            hover_texts.append(text)
        return hover_texts
    
    def _create_empty_map(self, title: str, message: str = "No data to display") -> go.Figure:
        """Create empty map with message"""
        fig = go.Figure(go.Scattermapbox())
        fig.update_layout(
            mapbox_style=self.default_mapbox_style,
            mapbox=dict(center=dict(lat=0, lon=70), zoom=2),
            title=title,
            height=600,
            annotations=[
                dict(
                    text=message,
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5
                )
            ]
        )
        return fig

# Usage
if __name__ == "__main__":
    # Test with sample data
    sample_df = pd.DataFrame({
        'latitude': [10.5, 11.2, 12.8, 13.5],
        'longitude': [75.3, 76.1, 77.5, 78.2],
        'temperature': [28.5, 27.8, 29.2, 28.9],
        'salinity': [34.5, 34.7, 34.3, 34.6],
        'timestamp': pd.date_range('2023-01-01', periods=4, freq='M')
    })
    
    visualizer = MapVisualizer()
    fig = visualizer.create_float_trajectory_map(sample_df)
    fig.show()
