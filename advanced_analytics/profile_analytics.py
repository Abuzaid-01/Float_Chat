"""
Advanced oceanographic profile analytics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from scipy import stats
from database.db_setup import DatabaseSetup
from sqlalchemy import text

class AdvancedProfileAnalytics:
    """Advanced analysis tools for ARGO profiles"""
    
    def identify_water_masses_advanced(self, df: pd.DataFrame) -> Dict:
        """
        Advanced water mass identification using T-S characteristics
        
        Identifies major Indian Ocean water masses:
        - Indian Ocean Surface Water (IOSW)
        - Indian Ocean Central Water (IOCW)
        - Arabian Sea High Salinity Water (ASHSW)
        - Bay of Bengal Low Salinity Water (BBLSW)
        - Antarctic Intermediate Water (AAIW)
        - Indonesian Throughflow Water (ITW)
        - Indian Deep Water (IDW)
        - Antarctic Bottom Water (AABW)
        """
        
        if df.empty or 'temperature' not in df.columns or 'salinity' not in df.columns:
            return {
                'success': False,
                'error': 'Temperature and salinity data required'
            }
        
        df = df.sort_values('pressure').copy()
        water_masses = []
        
        water_mass_criteria = {
            'Indian Ocean Surface Water (IOSW)': {
                'temp_range': (25, 30),
                'sal_range': (33.0, 36.0),
                'depth_range': (0, 100),
                'characteristics': 'Warm, variable salinity surface layer'
            },
            'Arabian Sea High Salinity Water (ASHSW)': {
                'temp_range': (20, 28),
                'sal_range': (36.0, 37.5),
                'depth_range': (50, 300),
                'characteristics': 'High salinity due to excess evaporation'
            },
            'Bay of Bengal Low Salinity Water (BBLSW)': {
                'temp_range': (25, 30),
                'sal_range': (30.0, 34.5),
                'depth_range': (0, 100),
                'characteristics': 'Low salinity due to river discharge and precipitation'
            },
            'Indian Ocean Central Water (IOCW)': {
                'temp_range': (10, 20),
                'sal_range': (34.5, 35.5),
                'depth_range': (100, 700),
                'characteristics': 'Formed by mixing of surface and intermediate waters'
            },
            'Indonesian Throughflow Water (ITW)': {
                'temp_range': (12, 18),
                'sal_range': (34.3, 34.8),
                'depth_range': (100, 500),
                'characteristics': 'Low salinity Pacific water entering Indian Ocean'
            },
            'Antarctic Intermediate Water (AAIW)': {
                'temp_range': (3, 8),
                'sal_range': (33.8, 34.5),
                'depth_range': (500, 1500),
                'characteristics': 'Low salinity minimum layer from Southern Ocean'
            },
            'Indian Deep Water (IDW)': {
                'temp_range': (1.5, 3),
                'sal_range': (34.7, 34.8),
                'depth_range': (1500, 3500),
                'characteristics': 'Deep water mass filling Indian Ocean basins'
            },
            'Antarctic Bottom Water (AABW)': {
                'temp_range': (-0.5, 2),
                'sal_range': (34.65, 34.72),
                'depth_range': (3500, 6000),
                'characteristics': 'Cold, dense bottom water from Antarctica'
            }
        }
        
        # Identify water masses
        for wm_name, criteria in water_mass_criteria.items():
            temp_min, temp_max = criteria['temp_range']
            sal_min, sal_max = criteria['sal_range']
            depth_min, depth_max = criteria['depth_range']
            
            # Filter data
            mask = (
                (df['temperature'] >= temp_min) &
                (df['temperature'] <= temp_max) &
                (df['salinity'] >= sal_min) &
                (df['salinity'] <= sal_max) &
                (df['pressure'] >= depth_min) &
                (df['pressure'] <= depth_max)
            )
            
            if mask.any():
                subset = df[mask]
                
                # Calculate core properties
                core_depth = subset['pressure'].mean()
                core_temp = subset['temperature'].mean()
                core_sal = subset['salinity'].mean()
                
                # Calculate thickness
                thickness = subset['pressure'].max() - subset['pressure'].min()
                
                # Calculate potential density (simplified)
                potential_density = 1000 + 0.7 * core_sal - 0.2 * core_temp
                
                water_masses.append({
                    'name': wm_name,
                    'characteristics': criteria['characteristics'],
                    'detected': True,
                    'core_depth_m': float(core_depth),
                    'depth_range_m': (float(subset['pressure'].min()), float(subset['pressure'].max())),
                    'thickness_m': float(thickness),
                    'core_temperature_C': float(core_temp),
                    'core_salinity_PSU': float(core_sal),
                    'temperature_range_C': (float(subset['temperature'].min()), float(subset['temperature'].max())),
                    'salinity_range_PSU': (float(subset['salinity'].min()), float(subset['salinity'].max())),
                    'potential_density_kgm3': float(potential_density),
                    'measurements': int(mask.sum()),
                    'percentage_of_profile': float(mask.sum() / len(df) * 100)
                })
        
        # Calculate water column structure
        stratification = self._calculate_stratification(df)
        
        # Identify mixing zones (transitions between water masses)
        mixing_zones = self._identify_mixing_zones(df, water_masses)
        
        return {
            'success': True,
            'water_masses_detected': len(water_masses),
            'water_masses': water_masses,
            'stratification': stratification,
            'mixing_zones': mixing_zones,
            'profile_classification': self._classify_water_column(water_masses),
            'total_measurements': len(df),
            'depth_coverage_m': float(df['pressure'].max())
        }
    
    def _calculate_stratification(self, df: pd.DataFrame) -> Dict:
        """Calculate water column stratification metrics"""
        
        if len(df) < 5:
            return {'status': 'insufficient_data'}
        
        # Calculate density (simplified)
        df['density'] = 1000 + 0.7 * df['salinity'] - 0.2 * df['temperature']
        
        # Stratification index (density difference per meter)
        surface_density = df[df['pressure'] <= 10]['density'].mean()
        deep_density = df[df['pressure'] >= df['pressure'].max() * 0.8]['density'].mean()
        
        density_diff = deep_density - surface_density
        depth_diff = df['pressure'].max() - 10
        
        stratification_index = density_diff / depth_diff if depth_diff > 0 else 0
        
        # Classify stratification
        if stratification_index > 0.1:
            classification = "highly_stratified"
        elif stratification_index > 0.05:
            classification = "moderately_stratified"
        elif stratification_index > 0.01:
            classification = "weakly_stratified"
        else:
            classification = "well_mixed"
        
        return {
            'stratification_index': float(stratification_index),
            'classification': classification,
            'surface_density': float(surface_density),
            'deep_density': float(deep_density),
            'density_range': float(density_diff)
        }
    
    def _identify_mixing_zones(self, df: pd.DataFrame, water_masses: List[Dict]) -> List[Dict]:
        """Identify zones where water masses mix"""
        
        mixing_zones = []
        
        if len(water_masses) < 2:
            return mixing_zones
        
        # Sort water masses by depth
        sorted_wm = sorted(water_masses, key=lambda x: x['core_depth_m'])
        
        # Find gaps between water masses (potential mixing zones)
        for i in range(len(sorted_wm) - 1):
            wm1 = sorted_wm[i]
            wm2 = sorted_wm[i + 1]
            
            # Check if there's a gap
            gap_start = wm1['depth_range_m'][1]
            gap_end = wm2['depth_range_m'][0]
            
            if gap_end > gap_start:
                # There's a mixing zone
                gap_data = df[(df['pressure'] >= gap_start) & (df['pressure'] <= gap_end)]
                
                if len(gap_data) > 0:
                    mixing_zones.append({
                        'between': f"{wm1['name']} and {wm2['name']}",
                        'depth_range_m': (float(gap_start), float(gap_end)),
                        'thickness_m': float(gap_end - gap_start),
                        'temperature_range_C': (float(gap_data['temperature'].min()), 
                                               float(gap_data['temperature'].max())),
                        'salinity_range_PSU': (float(gap_data['salinity'].min()), 
                                              float(gap_data['salinity'].max())),
                        'gradient_strength': self._calculate_mixing_strength(gap_data)
                    })
        
        return mixing_zones
    
    def _calculate_mixing_strength(self, gap_data: pd.DataFrame) -> str:
        """Calculate mixing intensity in transition zones"""
        
        if len(gap_data) < 3:
            return "unknown"
        
        # Calculate gradients
        temp_gradient = np.abs(gap_data['temperature'].diff() / gap_data['pressure'].diff()).mean()
        sal_gradient = np.abs(gap_data['salinity'].diff() / gap_data['pressure'].diff()).mean()
        
        # Classify based on gradients
        if temp_gradient > 0.1 or sal_gradient > 0.05:
            return "strong_mixing"
        elif temp_gradient > 0.05 or sal_gradient > 0.02:
            return "moderate_mixing"
        else:
            return "weak_mixing"
    
    def _classify_water_column(self, water_masses: List[Dict]) -> Dict:
        """Classify overall water column structure"""
        
        if not water_masses:
            return {
                'type': 'unclassified',
                'description': 'Insufficient water mass identification'
            }
        
        # Count layers
        n_layers = len(water_masses)
        
        # Check for specific patterns
        has_surface = any('Surface' in wm['name'] for wm in water_masses)
        has_intermediate = any('Intermediate' in wm['name'] for wm in water_masses)
        has_deep = any('Deep' in wm['name'] or 'Bottom' in wm['name'] for wm in water_masses)
        
        if has_surface and has_intermediate and has_deep:
            wc_type = "complete_stratification"
            description = "Well-defined surface, intermediate, and deep layers"
        elif has_surface and has_intermediate:
            wc_type = "upper_ocean_stratification"
            description = "Clear surface and intermediate layers"
        elif has_surface and has_deep:
            wc_type = "two_layer_system"
            description = "Surface and deep layers with limited intermediate water"
        elif n_layers >= 4:
            wc_type = "multi_layered"
            description = "Complex multi-layered water column structure"
        else:
            wc_type = "simple_structure"
            description = "Simple water column with few distinct layers"
        
        return {
            'type': wc_type,
            'description': description,
            'n_layers': n_layers,
            'complexity': 'high' if n_layers >= 4 else 'moderate' if n_layers >= 2 else 'low'
        }
    
    def __init__(self):
        self.db_setup = DatabaseSetup()
    
    
    def calculate_thermocline_advanced(self, df: pd.DataFrame) -> Dict:
        """
        Advanced thermocline calculation with multiple methods
        
        Returns comprehensive thermocline characteristics:
        - Depth and strength
        - Seasonal thermocline
        - Permanent thermocline
        - Mixed layer depth
        - Thermocline width and gradient
        """
        if df.empty or 'pressure' not in df.columns or 'temperature' not in df.columns:
            return {
                'success': False,
                'error': 'Insufficient data for thermocline calculation'
            }
        
        df = df.sort_values('pressure').copy()
        df = df.dropna(subset=['pressure', 'temperature'])
        df = df.drop_duplicates(subset=['pressure'])
        
        if len(df) < 10:
            return {
                'success': False,
                'error': 'Not enough data points (minimum 10 required)'
            }
        
        # Calculate temperature gradient (°C per meter)
        pressure_diff = df['pressure'].diff()
        temp_diff = df['temperature'].diff()
        
        # Filter significant pressure differences
        mask = pressure_diff > 1.0
        df.loc[mask, 'temp_gradient'] = np.abs(temp_diff[mask] / pressure_diff[mask])
        df.loc[~mask, 'temp_gradient'] = 0
        
        # Smooth gradient using rolling window
        df['temp_gradient_smooth'] = df['temp_gradient'].rolling(
            window=3, center=True, min_periods=1
        ).mean()
        
        # Method 1: Maximum gradient method
        middle_idx = df.iloc[2:-2]  # Exclude surface and bottom
        if len(middle_idx) == 0:
            return {'success': False, 'error': 'Insufficient middle layer data'}
        
        max_grad_idx = middle_idx['temp_gradient_smooth'].idxmax()
        thermocline_depth = df.loc[max_grad_idx, 'pressure']
        thermocline_strength = df.loc[max_grad_idx, 'temp_gradient_smooth']
        
        # Method 2: Temperature difference method (0.5°C threshold)
        surface_temp = df['temperature'].iloc[0]
        temp_diff_from_surface = np.abs(df['temperature'] - surface_temp)
        thermocline_depth_alt = df[temp_diff_from_surface > 0.5]['pressure'].iloc[0] if any(temp_diff_from_surface > 0.5) else thermocline_depth
        
        # Calculate thermocline width (where gradient > 50% of max)
        threshold = thermocline_strength * 0.5
        thermocline_zone = df[df['temp_gradient_smooth'] > threshold]
        thermocline_width = (
            thermocline_zone['pressure'].max() - thermocline_zone['pressure'].min()
        ) if len(thermocline_zone) > 1 else 0.0
        
        # Calculate mixed layer depth (MLD)
        # Using temperature criterion: 0.2°C difference from surface
        mld_temp_criterion = df[np.abs(df['temperature'] - surface_temp) > 0.2]['pressure'].iloc[0] if any(np.abs(df['temperature'] - surface_temp) > 0.2) else 10.0
        
        # Identify seasonal vs permanent thermocline
        # Seasonal: typically in upper 100m
        # Permanent: typically below 100m in tropical/subtropical waters
        is_seasonal = thermocline_depth < 100
        
        # Calculate stratification index (N² - Brunt-Väisälä frequency)
        # Simplified calculation without salinity effects
        g = 9.81  # gravity
        rho_0 = 1025  # reference density (kg/m³)
        
        # Temperature contribution to density
        alpha = 2e-4  # thermal expansion coefficient
        dT_dz = -thermocline_strength  # negative because temp decreases with depth
        
        # Stratification (s⁻²)
        N_squared = (g / rho_0) * alpha * dT_dz * 100  # multiply by 100 to convert per m
        buoyancy_frequency = np.sqrt(max(N_squared, 0)) if N_squared > 0 else 0
        
        # Temperature characteristics at key depths
        surface_layer = df[df['pressure'] <= 10]
        thermocline_layer = df[(df['pressure'] >= thermocline_depth - 25) & 
                              (df['pressure'] <= thermocline_depth + 25)]
        deep_layer = df[df['pressure'] >= 500]
        
        surface_temp_mean = surface_layer['temperature'].mean() if len(surface_layer) > 0 else surface_temp
        thermocline_temp_mean = thermocline_layer['temperature'].mean() if len(thermocline_layer) > 0 else df.loc[max_grad_idx, 'temperature']
        deep_temp_mean = deep_layer['temperature'].mean() if len(deep_layer) > 0 else df['temperature'].iloc[-1]
        
        # Calculate temperature inversion if present
        has_inversion = False
        inversion_depth = None
        
        # Check for temperature increase with depth (inversion)
        for i in range(1, len(df) - 1):
            if df.iloc[i]['temperature'] > df.iloc[i-1]['temperature']:
                if df.iloc[i]['pressure'] > 50:  # Only consider below surface layer
                    has_inversion = True
                    inversion_depth = df.iloc[i]['pressure']
                    break
        
        # Classify thermocline strength
        strength_classification = self._classify_thermocline_strength(thermocline_strength)
        
        # Calculate Richardson number (stability indicator)
        # Ri = N²/(du/dz)² - simplified without velocity data
        # Just use stratification as proxy
        stability = "stable" if N_squared > 0 else "unstable"
        
        return {
            'success': True,
            'method': 'maximum_gradient',
            
            # Primary characteristics
            'thermocline_depth_dbar': float(thermocline_depth),
            'thermocline_depth_m': float(thermocline_depth * 1.0),  # Approximation
            'thermocline_strength_deg_per_m': float(thermocline_strength),
            'thermocline_strength_classification': strength_classification,
            'thermocline_width_m': float(thermocline_width),
            
            # Alternative method
            'thermocline_depth_temp_criterion_dbar': float(thermocline_depth_alt),
            
            # Mixed layer
            'mixed_layer_depth_dbar': float(mld_temp_criterion),
            'mixed_layer_depth_m': float(mld_temp_criterion * 1.0),
            'mixed_layer_temperature': float(surface_temp_mean),
            
            # Layer temperatures
            'surface_temp_celsius': float(surface_temp_mean),
            'thermocline_temp_celsius': float(thermocline_temp_mean),
            'deep_temp_celsius': float(deep_temp_mean),
            'temp_range_celsius': float(surface_temp_mean - deep_temp_mean),
            
            # Classification
            'thermocline_type': 'seasonal' if is_seasonal else 'permanent',
            'is_seasonal': is_seasonal,
            
            # Physical properties
            'stratification_N_squared': float(N_squared),
            'buoyancy_frequency_Hz': float(buoyancy_frequency),
            'stability': stability,
            
            # Temperature inversion
            'has_temperature_inversion': has_inversion,
            'inversion_depth_dbar': float(inversion_depth) if inversion_depth else None,
            
            # Data quality
            'data_points': len(df),
            'depth_coverage_m': float(df['pressure'].max()),
            'vertical_resolution_m': float(df['pressure'].diff().mean()),
            
            # Statistical confidence
            'confidence': self._calculate_thermocline_confidence(df, thermocline_strength)
        }
    
    def _classify_thermocline_strength(self, gradient: float) -> str:
        """
        Classify thermocline strength based on temperature gradient
        
        Typical values:
        - Weak: < 0.05 °C/m
        - Moderate: 0.05 - 0.15 °C/m
        - Strong: 0.15 - 0.30 °C/m
        - Very Strong: > 0.30 °C/m
        """
        if gradient < 0.05:
            return "weak"
        elif gradient < 0.15:
            return "moderate"
        elif gradient < 0.30:
            return "strong"
        else:
            return "very_strong"
    
    def _calculate_thermocline_confidence(self, df: pd.DataFrame, strength: float) -> str:
        """
        Calculate confidence level in thermocline detection
        
        Based on:
        - Data points in thermocline zone
        - Gradient strength
        - Vertical resolution
        """
        score = 0
        
        # Data points
        if len(df) > 50:
            score += 3
        elif len(df) > 20:
            score += 2
        elif len(df) > 10:
            score += 1
        
        # Gradient strength
        if strength > 0.15:
            score += 3
        elif strength > 0.08:
            score += 2
        elif strength > 0.04:
            score += 1
        
        # Vertical resolution
        resolution = df['pressure'].diff().mean()
        if resolution < 5:
            score += 2
        elif resolution < 10:
            score += 1
        
        if score >= 7:
            return "high"
        elif score >= 4:
            return "medium"
        else:
            return "low"










    
    
    def calculate_mixed_layer_depth(self, df: pd.DataFrame, threshold: float = 0.5) -> float:
        """
        Calculate Mixed Layer Depth (MLD)
        Depth where temperature decreases by threshold from surface
        """
        df = df.sort_values('pressure')
        surface_temp = df['temperature'].iloc[0]
        mld_mask = df['temperature'] < (surface_temp - threshold)
        
        if mld_mask.any():
            return float(df[mld_mask]['pressure'].iloc[0])
        else:
            return float(df['pressure'].max())
    
    def identify_water_masses(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify water masses using T-S characteristics
        """
        water_masses = []
        
        if 'salinity' not in df.columns:
            return water_masses
        
        df = df.sort_values('pressure')
        
        # Temperature-Salinity thresholds for common water masses
        thresholds = {
            'Tropical Surface Water': {'temp_min': 20, 'sal_min': 34.5, 'sal_max': 35.5},
            'Central Water': {'temp_min': 10, 'temp_max': 20, 'sal_min': 34.2, 'sal_max': 35.5},
            'Antarctic Intermediate Water': {'temp_max': 5, 'sal_min': 33.8, 'sal_max': 34.4},
            'Deep Water': {'temp_max': 5, 'sal_min': 34.6}
        }
        
        for wm, criteria in thresholds.items():
            mask = pd.Series([True] * len(df))
            for key, val in criteria.items():
                if key == 'temp_min':
                    mask &= df['temperature'] >= val
                elif key == 'temp_max':
                    mask &= df['temperature'] <= val
                elif key == 'sal_min':
                    mask &= df['salinity'] >= val
                elif key == 'sal_max':
                    mask &= df['salinity'] <= val
            
            if mask.any():
                subset = df[mask]
                water_masses.append({
                    'water_mass': wm,
                    'depth_range': (float(subset['pressure'].min()), float(subset['pressure'].max())),
                    'count': int(mask.sum())
                })
        
        return water_masses
    
    def calculate_oxygen_statistics(self, df: pd.DataFrame) -> Dict:
        """Calculate dissolved oxygen statistics"""
        if 'dissolved_oxygen' not in df.columns:
            return {}
        
        do = df['dissolved_oxygen'].dropna()
        
        if len(do) == 0:
            return {}
        
        return {
            'min_oxygen': float(do.min()),
            'max_oxygen': float(do.max()),
            'mean_oxygen': float(do.mean()),
            'std_oxygen': float(do.std()),
            'oxygen_minimum_zone': float(do[do == do.min()].index[0]) if len(do) > 0 else None
        }
    
    def detect_anomalies(self, df: pd.DataFrame, parameter: str = 'temperature',
                        threshold: float = 2.0) -> List[Dict]:
        """
        Detect anomalies using statistical methods
        threshold: number of standard deviations
        """
        df = df.copy()
        
        if parameter not in df.columns:
            return []
        
        data = df[parameter].dropna()
        mean = data.mean()
        std = data.std()
        
        df['is_anomaly'] = np.abs(df[parameter] - mean) > (threshold * std)
        
        anomalies = []
        for idx, row in df[df['is_anomaly']].iterrows():
            anomalies.append({
                'depth': float(row['pressure']) if 'pressure' in row else None,
                'value': float(row[parameter]),
                'deviation_std': float((row[parameter] - mean) / std),
                'timestamp': row['timestamp'] if 'timestamp' in row else None
            })
        
        return anomalies
    
    def regional_comparison(self, region1: str, region2: str,
                           parameter: str = 'temperature') -> Dict:
        """Compare parameters between regions"""
        session = self.db_setup.get_session()
        
        try:
            results = {}
            
            for region in [region1, region2]:
                query = text(f"""
                SELECT 
                    AVG({parameter}) as avg_value,
                    MIN({parameter}) as min_value,
                    MAX({parameter}) as max_value,
                    STDDEV({parameter}) as std_dev,
                    COUNT(*) as count
                FROM argo_profiles
                WHERE ocean_region ILIKE '%{region}%'
                  AND {parameter} IS NOT NULL
                  AND temp_qc IN (1,2,3)
                  AND sal_qc IN (1,2,3)
                """)
                
                df = pd.read_sql(query, session.bind)
                
                if len(df) > 0 and df.iloc[0]['count'] > 0:
                    results[region] = {
                        'average': float(df.iloc[0]['avg_value']) if df.iloc[0]['avg_value'] is not None else None,
                        'min': float(df.iloc[0]['min_value']) if df.iloc[0]['min_value'] is not None else None,
                        'max': float(df.iloc[0]['max_value']) if df.iloc[0]['max_value'] is not None else None,
                        'std_dev': float(df.iloc[0]['std_dev']) if df.iloc[0]['std_dev'] is not None else None,
                        'measurements': int(df.iloc[0]['count'])
                    }
                else:
                    results[region] = None
            
            session.close()
            
            # Determine which is warmer/higher
            if results.get(region1) and results.get(region2):
                diff = results[region1]['average'] - results[region2]['average']
                warmer = region1 if diff > 0 else region2
                
                return {
                    "success": True,
                    "region1": region1,
                    "region2": region2,
                    "parameter": parameter,
                    "region1_stats": results[region1],
                    "region2_stats": results[region2],
                    "difference": abs(diff),
                    "warmer_region": warmer if parameter == 'temperature' else None,
                    "higher_region": warmer  # For other parameters
                }
            else:
                return {
                    "success": False,
                    "error": "Insufficient data for one or both regions",
                    "region1": region1,
                    "region2": region2,
                    "region1_stats": results.get(region1),
                    "region2_stats": results.get(region2)
                }
                
        except Exception as e:
            session.close()
            return {
                "success": False,
                "error": str(e),
                "region1": region1,
                "region2": region2
            }
    
    def trend_analysis(self, region: str, parameter: str, days: int = 90) -> Dict:
        """Analyze trends over time"""
        session = self.db_setup.get_session()
        
        query = text(f"""
        SELECT DATE_TRUNC('week', timestamp) as week,
               AVG({parameter}) as avg_value,
               COUNT(*) as measurements
        FROM argo_profiles
        WHERE ocean_region ILIKE '%{region}%'
          AND timestamp >= CURRENT_DATE - INTERVAL '{days} days'
          AND {parameter} IS NOT NULL
        GROUP BY DATE_TRUNC('week', timestamp)
        ORDER BY week
        """)
        
        df = pd.read_sql(query, session.bind)
        session.close()
        
        if len(df) < 2:
            return {"success": False, "message": "Insufficient data"}
        
        # Calculate trend
        x = np.arange(len(df))
        y = df['avg_value'].values
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        return {
            "region": region,
            "parameter": parameter,
            "trend": "increasing" if slope > 0 else "decreasing",
            "slope": float(slope),
            "r_squared": float(r_value ** 2),
            "significant": p_value < 0.05,
            "weeks_analyzed": len(df)
        }