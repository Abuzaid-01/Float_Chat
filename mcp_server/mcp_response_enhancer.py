"""
MCP Response Enhancer
Enriches responses with MCP tool results and structured data
"""

import pandas as pd
from typing import Dict, List, Optional
import json


class MCPResponseEnhancer:
    """
    Enhance LLM responses with MCP tool results
    Provides structured, rich responses
    """
    
    def __init__(self):
        self.enhancement_templates = self._load_templates()
    
    def _load_templates(self) -> Dict:
        """Load response enhancement templates"""
        return {
            'thermocline': """
**Thermocline Analysis:**
- Thermocline Depth: {thermocline_depth_dbar:.1f} dbar
- Thermocline Strength: {thermocline_strength:.3f} °C/m
- Surface Temperature: {surface_temp:.2f}°C
- Deep Temperature: {deep_temp:.2f}°C
""",
            'water_mass': """
**Water Mass Identification:**
{water_masses}
""",
            'regional_comparison': """
**Regional Comparison:**
Region 1: {region1}
Region 2: {region2}
Parameter: {parameter}

{comparison_data}
""",
            'temporal_trend': """
**Temporal Trend Analysis:**
Region: {region}
Parameter: {parameter}
Period: {weeks_analyzed} weeks

Trend: {trend} (slope: {slope:.4f})
Statistical Significance: {'Yes' if significant else 'No'}
R²: {r_squared:.3f}
""",
            'bgc_analysis': """
**Bio-Geo-Chemical Parameters:**
{bgc_data}
""",
            'profile_analysis': """
**Profile Analysis:**
Float ID: {float_id}
Total Measurements: {measurements}
Location: {lat:.2f}°N, {lon:.2f}°E
Date Range: {start_date} to {end_date}

Temperature: {temp_min:.2f}°C to {temp_max:.2f}°C (mean: {temp_mean:.2f}°C)
Salinity: {sal_min:.2f} to {sal_max:.2f} PSU (mean: {sal_mean:.2f} PSU)
Depth Range: {depth_min:.1f} to {depth_max:.1f} dbar
"""
        }
    
    def enhance_response(
        self,
        base_response: str,
        tool_results: Dict,
        query_type: str = None
    ) -> str:
        """
        Enhance base response with structured tool results
        """
        
        enhanced = base_response
        
        # Add thermocline data
        if 'calculate_thermocline' in tool_results:
            thermo_data = self._extract_tool_data(tool_results['calculate_thermocline'])
            if thermo_data and 'thermocline' in thermo_data:
                enhanced += "\n\n" + self.enhancement_templates['thermocline'].format(
                    **thermo_data['thermocline']
                )
        
        # Add water mass data
        if 'identify_water_masses' in tool_results:
            wm_data = self._extract_tool_data(tool_results['identify_water_masses'])
            if wm_data:
                # Check if water_masses key exists or if it's a success response
                if 'water_masses' in wm_data and wm_data.get('water_masses_detected', 0) > 0:
                    wm_text = self._format_water_masses(wm_data)
                    enhanced += "\n\n" + self.enhancement_templates['water_mass'].format(
                        water_masses=wm_text
                    )
                elif wm_data.get('success') is False:
                    # Add error explanation if water mass identification failed
                    error_msg = wm_data.get('error', 'Water mass identification failed')
                    enhanced += f"\n\n**Note:** {error_msg}"
        
        # Add temporal trend data
        if 'analyze_temporal_trends' in tool_results:
            trend_data = self._extract_tool_data(tool_results['analyze_temporal_trends'])
            if trend_data:
                enhanced += "\n\n" + self.enhancement_templates['temporal_trend'].format(
                    **trend_data
                )
        
        # Add profile analysis
        if 'analyze_float_profile' in tool_results:
            profile_data = self._extract_tool_data(tool_results['analyze_float_profile'])
            if profile_data and 'analysis' in profile_data:
                analysis = profile_data['analysis']
                enhanced += "\n\n" + self.enhancement_templates['profile_analysis'].format(
                    float_id=analysis['float_id'],
                    measurements=analysis['measurements'],
                    lat=analysis['location']['lat'],
                    lon=analysis['location']['lon'],
                    start_date=analysis['date_range']['start'],
                    end_date=analysis['date_range']['end'],
                    temp_min=analysis['temperature']['min'],
                    temp_max=analysis['temperature']['max'],
                    temp_mean=analysis['temperature']['mean'],
                    sal_min=analysis['salinity']['min'],
                    sal_max=analysis['salinity']['max'],
                    sal_mean=analysis['salinity']['mean'],
                    depth_min=analysis['depth_range']['min'],
                    depth_max=analysis['depth_range']['max']
                )
        
        return enhanced
    
    def _extract_tool_data(self, tool_result: Dict) -> Optional[Dict]:
        """Extract data from MCP tool result"""
        if tool_result.get('isError'):
            return None
        
        content = tool_result.get('content', [])
        if not content:
            return None
        
        try:
            text = content[0].get('text', '')
            data = json.loads(text)
            return data
        except:
            return None
    
    def _format_water_masses(self, water_masses_data: Dict) -> str:
        """Format water mass list"""
        # Handle both list format and dict format
        if isinstance(water_masses_data, dict):
            water_masses = water_masses_data.get('water_masses', [])
        else:
            water_masses = water_masses_data
            
        if not water_masses:
            return "No distinct water masses identified."
        
        formatted = []
        for wm in water_masses:
            # Handle different key names (backwards compatibility)
            name = wm.get('name') or wm.get('water_mass', 'Unknown')
            depth_range = wm.get('depth_range_m') or wm.get('depth_range', (0, 0))
            count = wm.get('measurements') or wm.get('count', 0)
            
            # Add detailed info if available
            details = []
            if 'core_temperature_C' in wm:
                details.append(f"Temp: {wm['core_temperature_C']:.1f}°C")
            if 'core_salinity_PSU' in wm:
                details.append(f"Sal: {wm['core_salinity_PSU']:.1f} PSU")
            
            formatted.append(
                f"- **{name}**: "
                f"Depth {depth_range[0]:.0f}-{depth_range[1]:.0f}m "
                f"({count} measurements)" +
                (f" - {', '.join(details)}" if details else "")
            )
        
        return "\n".join(formatted)
    
    def create_structured_summary(self, tool_results: Dict) -> Dict:
        """
        Create structured summary from all tool results
        """
        summary = {
            'data_summary': {},
            'analytics': {},
            'tools_executed': []
        }
        
        for tool_name, result in tool_results.items():
            summary['tools_executed'].append({
                'tool': tool_name,
                'success': not result.get('isError', True)
            })
            
            data = self._extract_tool_data(result)
            if data:
                if tool_name == 'query_argo_data':
                    summary['data_summary'] = {
                        'record_count': data.get('record_count', 0),
                        'execution_time': data.get('execution_time', 0)
                    }
                else:
                    summary['analytics'][tool_name] = data
        
        return summary
    
    def generate_export_metadata(self, tool_results: Dict, query: str) -> Dict:
        """
        Generate metadata for data export
        """
        metadata = {
            'query': query,
            'timestamp': pd.Timestamp.now().isoformat(),
            'tools_used': list(tool_results.keys()),
            'mcp_enabled': True
        }
        
        # Add data statistics
        if 'query_argo_data' in tool_results:
            data = self._extract_tool_data(tool_results['query_argo_data'])
            if data:
                metadata['record_count'] = data.get('record_count', 0)
                metadata['sql_query'] = data.get('sql', '')
        
        return metadata