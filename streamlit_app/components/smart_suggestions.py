"""
Smart Suggestion Generator for FloatChat
Generates contextual, relevant follow-up questions based on user queries
"""

import re
from typing import List, Dict


class SmartSuggestionGenerator:
    """Generate context-aware follow-up questions"""
    
    def __init__(self):
        # Define patterns and their corresponding suggestions
        self.suggestion_patterns = {
            # Location-based queries
            'location': {
                'patterns': [
                    r'(arabian sea|bay of bengal|indian ocean|southern ocean)',
                    r'(region|area|location)',
                    r'(latitude|longitude|lat|lon|coordinates)'
                ],
                'suggestions': [
                    "Compare {location} with Bay of Bengal temperatures",
                    "Show salinity profiles in {location}",
                    "Calculate thermocline depth in {location}",
                    "Find extreme temperature events in {location}",
                    "Analyze seasonal variations in {location}"
                ]
            },
            
            # Temperature queries
            'temperature': {
                'patterns': [
                    r'temperature',
                    r'thermal',
                    r'warm|cold|hot|cool'
                ],
                'suggestions': [
                    "Compare temperature with salinity in the same region",
                    "Calculate mixed layer depth for these profiles",
                    "Show temperature trends over time",
                    "Identify thermocline characteristics",
                    "Find profiles with similar temperature patterns"
                ]
            },
            
            # Salinity queries
            'salinity': {
                'patterns': [
                    r'salinity',
                    r'salt',
                    r'psu'
                ],
                'suggestions': [
                    "Compare salinity with temperature",
                    "Identify water masses based on T-S properties",
                    "Show salinity at different depths",
                    "Find regions with extreme salinity values",
                    "Analyze salinity gradients over time"
                ]
            },
            
            # Float-specific queries
            'float': {
                'patterns': [
                    r'float\s+\d+',
                    r'float\s+id',
                    r'specific float'
                ],
                'suggestions': [
                    "Show all cycles for this float",
                    "Analyze this float's temporal trends",
                    "Compare this float with nearby floats",
                    "Show this float's geographic trajectory",
                    "Calculate statistics for this float"
                ]
            },
            
            # Depth/Pressure queries
            'depth': {
                'patterns': [
                    r'depth',
                    r'pressure',
                    r'profile',
                    r'vertical'
                ],
                'suggestions': [
                    "Show temperature-salinity diagram",
                    "Calculate mixed layer depth",
                    "Identify thermocline depth",
                    "Compare surface vs deep water properties",
                    "Analyze vertical stratification"
                ]
            },
            
            # Time-based queries
            'temporal': {
                'patterns': [
                    r'recent|latest|newest',
                    r'\d{4}',  # Year
                    r'(january|february|march|april|may|june|july|august|september|october|november|december)',
                    r'trend|time|temporal'
                ],
                'suggestions': [
                    "Compare with historical data from previous years",
                    "Show seasonal variations",
                    "Analyze long-term trends",
                    "Find anomalies in this time period",
                    "Compare this month with same month last year"
                ]
            },
            
            # Statistical queries
            'statistics': {
                'patterns': [
                    r'average|mean|median',
                    r'maximum|minimum|max|min',
                    r'statistics|stats',
                    r'count|total|number'
                ],
                'suggestions': [
                    "Show spatial distribution of these values",
                    "Calculate standard deviation and variability",
                    "Identify outliers and extreme values",
                    "Compare statistics across different regions",
                    "Visualize distribution in histogram"
                ]
            },
            
            # Comparison queries
            'comparison': {
                'patterns': [
                    r'compare|versus|vs|difference',
                    r'between'
                ],
                'suggestions': [
                    "Add more regions to comparison",
                    "Show time-series comparison",
                    "Calculate statistical significance",
                    "Visualize differences on map",
                    "Analyze causes of differences"
                ]
            },
            
            # Water mass queries
            'water_mass': {
                'patterns': [
                    r'water mass',
                    r'thermocline',
                    r'mixed layer'
                ],
                'suggestions': [
                    "Identify water mass characteristics",
                    "Compare with standard water mass definitions",
                    "Show T-S diagram for water mass identification",
                    "Analyze water mass distribution",
                    "Track water mass movements over time"
                ]
            }
        }
    
    def generate_suggestions(self, user_query: str, query_results: Dict = None) -> List[str]:
        """
        Generate contextual suggestions based on user query
        
        Args:
            user_query: The user's original question
            query_results: Optional results from the query
            
        Returns:
            List of 5 contextual suggestion questions
        """
        query_lower = user_query.lower()
        matched_categories = []
        
        # Find matching categories
        for category, data in self.suggestion_patterns.items():
            for pattern in data['patterns']:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    matched_categories.append(category)
                    break
        
        # If no matches, use general suggestions
        if not matched_categories:
            return self._get_general_suggestions()
        
        # Extract location if present
        location = self._extract_location(query_lower)
        
        # Collect suggestions from matched categories
        all_suggestions = []
        for category in matched_categories:
            suggestions = self.suggestion_patterns[category]['suggestions']
            for suggestion in suggestions:
                # Replace {location} placeholder if found
                if '{location}' in suggestion and location:
                    suggestion = suggestion.replace('{location}', location.title())
                    all_suggestions.append(suggestion)
                elif '{location}' not in suggestion:
                    all_suggestions.append(suggestion)
        
        # Remove duplicates and return top 5
        unique_suggestions = list(dict.fromkeys(all_suggestions))
        return unique_suggestions[:5]
    
    def _extract_location(self, query: str) -> str:
        """Extract location name from query"""
        locations = [
            'arabian sea',
            'bay of bengal',
            'indian ocean',
            'southern ocean',
            'southern indian ocean',
            'equatorial indian ocean'
        ]
        
        for location in locations:
            if location in query:
                return location
        
        return None
    
    def _get_general_suggestions(self) -> List[str]:
        """Return general suggestions when no specific pattern matches"""
        return [
            "Show temperature profiles in Arabian Sea",
            "Compare salinity between regions",
            "Find recent data from this month",
            "Calculate mixed layer depth",
            "Identify water masses in Indian Ocean"
        ]
    
    def generate_smart_examples(self, user_query: str = None) -> str:
        """
        Generate smart examples section based on context
        
        Args:
            user_query: Optional user query to generate contextual examples
            
        Returns:
            Formatted markdown string with suggestions
        """
        if user_query:
            suggestions = self.generate_suggestions(user_query)
            
            markdown = "### 💡 Based on your query, you might want to:\n\n"
            for i, suggestion in enumerate(suggestions, 1):
                markdown += f"{i}. {suggestion}\n"
            
            return markdown
        else:
            # Return default examples
            return """
**Basic Queries:**
- Show me temperature profiles in the Arabian Sea
- What is the database structure?
- Find recent data from October 2025

**Advanced Analytics:**
- Calculate thermocline characteristics for Bay of Bengal
- Identify water masses in the Indian Ocean
- Compare temperature between Arabian Sea and Bay of Bengal

**Spatial Queries:**
- Find nearest floats to 15°N, 75°E
- Show floats within 50km of Mumbai
"""
