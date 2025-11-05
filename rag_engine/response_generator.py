




import os
from typing import Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
import pandas as pd
import re


class ResponseGenerator:
    """
    Generate natural language responses using Gemini.
    Enhanced with context-aware tone and emoji support.
    """
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
            temperature=0.7,
            google_api_key=os.getenv('GOOGLE_API_KEY'),
            timeout=30,
            max_retries=2
        )
        
        print(f"✅ Response Generator using: {os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')}")
        
        # Enhanced prompt template with tone instructions
        self.prompt_template = PromptTemplate(
            input_variables=["question", "context", "query_results", "query_type"],
            template=self._get_enhanced_prompt_template()
        )
    
    def _get_enhanced_prompt_template(self) -> str:
        """Get enhanced prompt template with tone instructions"""
        return """You are FloatChat, a friendly and enthusiastic AI oceanographer! 🌊

Your personality:
- Enthusiastic about ocean data discoveries 🎉
- Use relevant emojis to make responses engaging
- Adjust tone based on query type (see below)
- Be precise with numbers but conversational in explanation
- Show excitement for interesting findings

Query Type: {query_type}

TONE GUIDELINES BY QUERY TYPE:

1. SIMPLE DATA QUERIES (show, get, find):
   - Tone: Helpful and informative 📊
   - Emoji use: Moderate (2-3 per response)
   - Example: "I found some interesting data for you! 📊 Here's what I discovered..."

2. COMPARISON QUERIES (compare, difference, vs):
   - Tone: Analytical and insightful 🔍
   - Emoji use: Analytical emojis (📈, 📉, ⚖️, 🔬)
   - Example: "Great question! Let me compare these regions for you 🔍..."

3. STATISTICAL QUERIES (average, count, max, min):
   - Tone: Precise and data-focused 📈
   - Emoji use: Chart/graph emojis
   - Example: "Let me crunch those numbers for you! 📊 Here's what the statistics show..."

4. SCIENTIFIC QUERIES (thermocline, water mass, salinity):
   - Tone: Educational and scientific 🔬
   - Emoji use: Science emojis (🌡️, 🧪, 🔬, 🌊)
   - Example: "Fascinating oceanographic question! 🔬 Let me explain what I found..."

5. LOCATION QUERIES (where, region, area):
   - Tone: Exploratory and geographic 🗺️
   - Emoji use: Location emojis (📍, 🗺️, 🌍)
   - Example: "Let's explore that region together! 🗺️ I've located the data you need..."

6. TIME-BASED QUERIES (recent, last month, trend):
   - Tone: Temporal and observant ⏰
   - Emoji use: Time emojis (⏰, 📅, 🕐, ⌚)
   - Example: "Looking at the timeline... ⏰ Here's how things have changed over time..."

7. ANOMALY/UNUSUAL QUERIES (unusual, anomaly, extreme):
   - Tone: Alert and investigative 🚨
   - Emoji use: Alert emojis (🚨, ⚠️, 🔍, 👀)
   - Example: "Interesting! I've detected some unusual patterns... 👀 Let's investigate!"

User Question: {question}

Retrieved Context:
{context}

ACTUAL DATA FROM DATABASE:
{query_results}

CRITICAL INSTRUCTIONS:
1. Start with an appropriate emoji based on query type
2. Use 2-4 relevant emojis throughout your response
3. Adjust your enthusiasm level to match the query type
4. ALWAYS cite specific numbers from the data
5. Keep responses friendly but professional
6. Use emojis naturally, not excessively
7. End with a helpful suggestion or follow-up question when appropriate
8. **IMPORTANT**: If query asks for multiple criteria but some data is missing:
   - Show what IS available with enthusiasm
   - Politely explain what's missing
   - Suggest alternative queries
   - Example: "I found 23,311 records with temperature > 25°C and good QC! 🌡️ However, dissolved oxygen data is not available in this dataset (Core ARGO only). Would you like to explore temperature and salinity patterns instead?"

Structure your response:
1. **Opening** (with emoji): Brief acknowledgment of the question
2. **Key Findings**: Main insights with specific numbers from available data
3. **Details**: Elaborate on important patterns (use emojis for emphasis)
4. **Missing Data Note** (if applicable): Explain what's not available and why
5. **Helpful Suggestion**: Alternative queries or follow-up questions

Generate your engaging response:"""
    
    def generate_response(
        self,
        question: str,
        query_results: pd.DataFrame,
        context: str = ""
    ) -> str:
        """
        Generate natural language response with enhanced tone
        """
        try:
            # Detect query type for appropriate tone
            query_type = self._detect_query_type(question)
            
            # Format query results
            results_summary = self._format_results(query_results)
            
            # Generate response using Gemini with enhanced prompt
            formatted_prompt = self.prompt_template.format(
                question=question,
                context=context,
                query_results=results_summary,
                query_type=query_type
            )
            
            print(f"🎭 Generating {query_type} response...")
            response = self.llm.invoke(formatted_prompt)
            return response.content
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error generating response: {error_msg}")
            
            if "timeout" in error_msg.lower() or "504" in error_msg or "deadline" in error_msg.lower():
                return self._generate_fallback_response(question, query_results, query_type)
            
            return "I encountered an error while generating the response. Please try again. 🔄"
    
    def _detect_query_type(self, question: str) -> str:
        """Detect the type of query for appropriate tone"""
        question_lower = question.lower()
        
        # Query type patterns
        patterns = {
            'comparison': ['compare', 'difference', 'versus', 'vs', 'between'],
            'statistical': ['average', 'mean', 'count', 'sum', 'max', 'min', 'total', 'statistics'],
            'scientific': ['thermocline', 'water mass', 'salinity', 'density', 'stratification', 'mixing'],
            'location': ['where', 'region', 'area', 'location', 'near', 'arabian', 'bengal'],
            'temporal': ['recent', 'last', 'trend', 'over time', 'historical', 'change'],
            'anomaly': ['unusual', 'anomaly', 'extreme', 'highest', 'lowest', 'maximum', 'minimum'],
        }
        
        for query_type, keywords in patterns.items():
            if any(keyword in question_lower for keyword in keywords):
                return query_type
        
        return 'simple'  # Default
    
    def _generate_fallback_response(self, question: str, df: pd.DataFrame, query_type: str) -> str:
        """Enhanced fallback response with appropriate tone and emojis"""
        if df.empty:
            return "I couldn't find any data matching your query. 🔍 Try adjusting your search parameters!"
        
        # Select emoji based on query type
        emoji_map = {
            'comparison': '⚖️',
            'statistical': '📊',
            'scientific': '🔬',
            'location': '🗺️',
            'temporal': '⏰',
            'anomaly': '🚨',
            'simple': '📊'
        }
        
        opening_emoji = emoji_map.get(query_type, '📊')
        
        response_parts = [
            f"{opening_emoji} **Quick Results Summary**\n",
            f"\nI found **{len(df)} records** that match your query! Here's what stands out:\n"
        ]
        
        # Add geographic info
        if 'latitude' in df.columns and 'longitude' in df.columns and not df.empty:
            try:
                response_parts.append(f"\n📍 **Geographic Coverage:**")
                response_parts.append(f"- Latitude: {df['latitude'].min():.2f}°N to {df['latitude'].max():.2f}°N")
                response_parts.append(f"- Longitude: {df['longitude'].min():.2f}°E to {df['longitude'].max():.2f}°E\n")
            except (KeyError, ValueError):
                pass  # Skip if columns don't exist or have no valid data
        
        # Add temperature info
        if 'temperature' in df.columns:
            temp_emoji = '🌡️' if query_type == 'scientific' else '🌡️'
            response_parts.append(f"\n{temp_emoji} **Temperature Insights:**")
            response_parts.append(f"- Range: {df['temperature'].min():.2f}°C to {df['temperature'].max():.2f}°C")
            response_parts.append(f"- Average: {df['temperature'].mean():.2f}°C")
            
            if df['temperature'].mean() > 28:
                response_parts.append("- *That's quite warm! 🔥*")
            elif df['temperature'].mean() < 10:
                response_parts.append("- *Pretty cold waters! ❄️*")
        
        # Add salinity info
        if 'salinity' in df.columns:
            response_parts.append(f"\n💧 **Salinity Details:**")
            response_parts.append(f"- Range: {df['salinity'].min():.2f} to {df['salinity'].max():.2f} PSU")
            response_parts.append(f"- Average: {df['salinity'].mean():.2f} PSU")
        
        # Add depth info
        if 'pressure' in df.columns:
            response_parts.append(f"\n🌊 **Depth Coverage:**")
            response_parts.append(f"- Maximum: {df['pressure'].max():.0f} dbar")
            
            if df['pressure'].max() > 1000:
                response_parts.append("- *Deep ocean measurements! 🏊‍♂️*")
        
        # Add float info
        if 'float_id' in df.columns:
            unique_floats = df['float_id'].nunique()
            response_parts.append(f"\n🎈 **Float Information:**")
            response_parts.append(f"- {unique_floats} unique float(s) contributed to this data")
        
        # Add helpful closing
        closings = {
            'comparison': "\n💡 *Want to see a detailed comparison chart? Just ask!*",
            'statistical': "\n💡 *Need more detailed statistics? I can break it down further!*",
            'scientific': "\n💡 *Curious about the oceanographic significance? I can explain!*",
            'location': "\n💡 *Want to see this on a map? Check the Geographic Explorer tab!*",
            'temporal': "\n💡 *Interested in seeing the trend over time? Just ask!*",
            'anomaly': "\n💡 *Want to investigate these patterns further? I'm here to help!*",
            'simple': "\n💡 *Want to explore this data further? I can show you maps, profiles, and more!*"
        }
        
        response_parts.append(closings.get(query_type, closings['simple']))
        
        response_parts.append("\n\n*Note: For full AI analysis with detailed insights, the complete data is available for visualization in the other tabs!* 📊")
        
        return "\n".join(response_parts)
    
    def _format_results(self, df: pd.DataFrame, max_rows: int = 10) -> str:
        """Format DataFrame results for Gemini - includes actual data rows"""
        if df.empty:
            return "No data found matching the query."
        
        summary_parts = [
            f"📊 ACTUAL Query Results: {len(df)} records retrieved from database",
            f"Available Columns: {', '.join(df.columns)}",
            ""
        ]
        
        # Add geographic info if available
        if 'latitude' in df.columns and 'longitude' in df.columns and not df.empty:
            try:
                summary_parts.append(f"Geographic Coverage:")
                summary_parts.append(f"  • Latitude: MIN={df['latitude'].min():.4f}°N, MAX={df['latitude'].max():.4f}°N")
                summary_parts.append(f"  • Longitude: MIN={df['longitude'].min():.4f}°E, MAX={df['longitude'].max():.4f}°E")
                summary_parts.append("")
            except (KeyError, ValueError):
                pass  # Skip if columns don't exist or have no valid data
        
        # Add numeric statistics
        summary_parts.append("Statistical Summary:")
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_cols:
            if col in df.columns and df[col].notna().sum() > 0:
                summary_parts.append(
                    f"  • {col}: MIN={df[col].min():.4f}, MAX={df[col].max():.4f}, "
                    f"AVG={df[col].mean():.4f}"
                )
        
        # Add float/profile info if available
        if 'float_id' in df.columns:
            unique_floats = df['float_id'].nunique()
            summary_parts.append(f"\n  • Total unique floats: {unique_floats}")
        
        summary_parts.append("")
        
        # Add ACTUAL DATA ROWS
        summary_parts.append(f"SAMPLE DATA (first {min(max_rows, len(df))} of {len(df)} records):")
        summary_parts.append("=" * 80)
        
        sample_df = df.head(max_rows)
        for idx, row in sample_df.iterrows():
            summary_parts.append(f"\nRecord {idx + 1}:")
            for col in df.columns:
                value = row[col]
                if pd.isna(value):
                    value = "NULL"
                elif isinstance(value, float):
                    value = f"{value:.4f}"
                summary_parts.append(f"  - {col}: {value}")
        
        summary_parts.append("=" * 80)
        
        if len(df) > max_rows:
            summary_parts.append(f"\n(Showing {max_rows} sample rows out of {len(df)} total)")
        
        return "\n".join(summary_parts)
    
    def generate_summary(self, df: pd.DataFrame) -> str:
        """Generate quick summary without LLM call"""
        if df.empty:
            return "No results found. 🔍"
        
        summary = f"Found {len(df)} records 📊"
        
        if 'latitude' in df.columns and 'longitude' in df.columns and not df.empty:
            try:
                lat_range = (df['latitude'].min(), df['latitude'].max())
                lon_range = (df['longitude'].min(), df['longitude'].max())
                summary += f" spanning {lat_range[0]:.2f}°N to {lat_range[1]:.2f}°N, "
                summary += f"{lon_range[0]:.2f}°E to {lon_range[1]:.2f}°E 🗺️"
            except (KeyError, ValueError):
                pass  # Skip if columns don't exist or have no valid data
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            time_range = (df['timestamp'].min(), df['timestamp'].max())
            summary += f" from {time_range[0].strftime('%Y-%m-%d')} to {time_range[1].strftime('%Y-%m-%d')} ⏰"
        
        return summary