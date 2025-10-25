import os
from typing import Dict
from langchain_google_genai import ChatGoogleGenerativeAI  # ← CHANGED
# from langchain.prompts import PromptTemplate
from langchain_core.prompts import PromptTemplate
from rag_engine.prompt_templates import RESPONSE_GENERATION_PROMPT
import pandas as pd

class ResponseGenerator:
    """
    Generate natural language responses using Gemini.
    FREE Google Gemini API!
    """
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
            temperature=0.7,  # Higher for natural responses
            google_api_key=os.getenv('GOOGLE_API_KEY'),
            timeout=30,  # 30 second timeout to prevent hanging
            max_retries=2  # Only retry twice to avoid long waits
        )
        
        print(f"✅ Response Generator using: {os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')}")
        
        self.prompt_template = PromptTemplate(
            input_variables=["question", "context", "query_results"],
            template=RESPONSE_GENERATION_PROMPT
        )
    
    def generate_response(
        self,
        question: str,
        query_results: pd.DataFrame,
        context: str = ""
    ) -> str:
        """
        Generate natural language response from query results.
        
        Args:
            question: User's original question
            query_results: DataFrame with query results
            context: Retrieved context from vector store
            
        Returns:
            Natural language response
        """
        try:
            # Format query results (optimized to prevent timeouts)
            results_summary = self._format_results(query_results)
            
            # Generate response using Gemini
            formatted_prompt = self.prompt_template.format(
                question=question,
                context=context,
                query_results=results_summary
            )
            
            print(f"🤖 Generating AI response (prompt size: {len(formatted_prompt)} chars)...")
            response = self.llm.invoke(formatted_prompt)
            return response.content
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error generating response: {error_msg}")
            
            # If timeout, return a structured fallback response
            if "timeout" in error_msg.lower() or "504" in error_msg or "deadline" in error_msg.lower():
                return self._generate_fallback_response(question, query_results)
            
            return "I encountered an error while generating the response. Please try again."
    
    def _generate_fallback_response(self, question: str, df: pd.DataFrame) -> str:
        """Generate a fallback response when LLM times out"""
        if df.empty:
            return "No data found matching your query."
        
        response_parts = [
            f"✅ **Query Results**",
            f"",
            f"Found **{len(df)} records** matching your query.",
            f""
        ]
        
        # Add geographic info
        if 'latitude' in df.columns and 'longitude' in df.columns:
            response_parts.append(f"**Geographic Coverage:**")
            response_parts.append(f"- Latitude: {df['latitude'].min():.2f}°N to {df['latitude'].max():.2f}°N")
            response_parts.append(f"- Longitude: {df['longitude'].min():.2f}°E to {df['longitude'].max():.2f}°E")
            response_parts.append("")
        
        # Add key statistics
        if 'temperature' in df.columns:
            response_parts.append(f"**Temperature:**")
            response_parts.append(f"- Range: {df['temperature'].min():.2f}°C to {df['temperature'].max():.2f}°C")
            response_parts.append(f"- Average: {df['temperature'].mean():.2f}°C")
            response_parts.append("")
        
        if 'salinity' in df.columns:
            response_parts.append(f"**Salinity:**")
            response_parts.append(f"- Range: {df['salinity'].min():.2f} to {df['salinity'].max():.2f} PSU")
            response_parts.append(f"- Average: {df['salinity'].mean():.2f} PSU")
            response_parts.append("")
        
        if 'pressure' in df.columns:
            response_parts.append(f"**Depth (Pressure):**")
            response_parts.append(f"- Range: {df['pressure'].min():.2f} to {df['pressure'].max():.2f} dbar")
            response_parts.append("")
        
        if 'float_id' in df.columns:
            unique_floats = df['float_id'].nunique()
            response_parts.append(f"**Floats:** {unique_floats} unique float(s)")
            response_parts.append("")
        
        response_parts.append("*Note: Full AI analysis unavailable due to response generation timeout. The data has been successfully retrieved and is available for visualization.*")
        
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
        if 'latitude' in df.columns and 'longitude' in df.columns:
            summary_parts.append(f"Geographic Coverage (Latitude/Longitude Ranges):")
            summary_parts.append(f"  • Latitude: MIN={df['latitude'].min():.4f}°N, MAX={df['latitude'].max():.4f}°N")
            summary_parts.append(f"  • Longitude: MIN={df['longitude'].min():.4f}°E, MAX={df['longitude'].max():.4f}°E")
            summary_parts.append("")
        
        # Add numeric statistics (COMPREHENSIVE)
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
        
        # Add ACTUAL DATA ROWS (10 rows by default)
        summary_parts.append(f"SAMPLE DATA ROWS (showing {min(max_rows, len(df))} of {len(df)} total records):")
        summary_parts.append("=" * 80)
        
        # Format sample data with all columns
        sample_df = df.head(max_rows)
        for idx, row in sample_df.iterrows():
            summary_parts.append(f"\nRow {idx + 1}:")
            for col in df.columns:
                value = row[col]
                if pd.isna(value):
                    value = "NULL"
                elif isinstance(value, float):
                    value = f"{value:.4f}"
                summary_parts.append(f"  - {col}: {value}")
        
        summary_parts.append("=" * 80)
        
        if len(df) > max_rows:
            summary_parts.append(f"\n(Note: Showing {max_rows} sample rows out of {len(df)} total records)")
        
        return "\n".join(summary_parts)
    
    def generate_summary(self, df: pd.DataFrame) -> str:
        """Generate quick summary without LLM call"""
        if df.empty:
            return "No results found."
        
        summary = f"Found {len(df)} records"
        
        if 'latitude' in df.columns and 'longitude' in df.columns:
            lat_range = (df['latitude'].min(), df['latitude'].max())
            lon_range = (df['longitude'].min(), df['longitude'].max())
            summary += f" spanning {lat_range[0]:.2f}°N to {lat_range[1]:.2f}°N, "
            summary += f"{lon_range[0]:.2f}°E to {lon_range[1]:.2f}°E"
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            time_range = (df['timestamp'].min(), df['timestamp'].max())
            summary += f" from {time_range[0].strftime('%Y-%m-%d')} to {time_range[1].strftime('%Y-%m-%d')}"
        
        return summary







# import os
# from typing import Dict, List
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_core.prompts import PromptTemplate
# from rag_engine.prompt_templates import RESPONSE_GENERATION_PROMPT
# import pandas as pd
# import json


# class EnhancedResponseGenerator:
#     """Production-grade response generator with context awareness"""
    
#     def __init__(self):
#         self.llm = ChatGoogleGenerativeAI(
#             model=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
#             temperature=0.7,
#             google_api_key=os.getenv('GOOGLE_API_KEY')
#         )
        
#         self.prompt_template = PromptTemplate(
#             input_variables=["question", "context", "query_results", "statistics"],
#             template="""You are FloatChat, an expert oceanographic data analyst.

# User Question: {question}

# Retrieved Context:
# {context}

# Query Results Summary:
# {statistics}

# Sample Data:
# {query_results}

# Provide a comprehensive, professional response that includes:
# 1. Direct answer to the question
# 2. Key findings from the data
# 3. Statistical insights
# 4. Oceanographic interpretation
# 5. Relevant recommendations or follow-up suggestions

# Use precise scientific language but keep it accessible. Always cite specific numbers from the data.

# Response:"""
#         )
    
#     def generate_response(
#         self,
#         question: str,
#         query_results: pd.DataFrame,
#         context: str = "",
#         include_interpretation: bool = True
#     ) -> Dict:
#         """
#         Generate comprehensive response with statistics
        
#         Returns:
#             Dict with 'response', 'statistics', 'recommendations'
#         """
#         try:
#             # Calculate statistics
#             stats = self._calculate_statistics(query_results)
            
#             # Format results for LLM
#             results_summary = self._format_results_for_llm(query_results)
            
#             # Generate response
#             formatted_prompt = self.prompt_template.format(
#                 question=question,
#                 context=context,
#                 query_results=results_summary,
#                 statistics=json.dumps(stats, indent=2)
#             )
            
#             response = self.llm.invoke(formatted_prompt)
            
#             # Generate recommendations
#             recommendations = self._generate_recommendations(question, query_results)
            
#             return {
#                 'response': response.content,
#                 'statistics': stats,
#                 'recommendations': recommendations,
#                 'data_quality': self._assess_data_quality(query_results)
#             }
            
#         except Exception as e:
#             print(f"❌ Response generation error: {e}")
#             return {
#                 'response': "I encountered an error generating a detailed response.",
#                 'statistics': {},
#                 'recommendations': [],
#                 'data_quality': 'unknown'
#             }
    
#     def _calculate_statistics(self, df: pd.DataFrame) -> Dict:
#         """Calculate comprehensive statistics"""
#         stats = {
#             'total_records': len(df),
#             'date_range': {},
#             'geographic_extent': {},
#             'parameters': {}
#         }
        
#         # Temporal
#         if 'timestamp' in df.columns:
#             df['timestamp'] = pd.to_datetime(df['timestamp'])
#             stats['date_range'] = {
#                 'start': df['timestamp'].min().strftime('%Y-%m-%d'),
#                 'end': df['timestamp'].max().strftime('%Y-%m-%d'),
#                 'duration_days': (df['timestamp'].max() - df['timestamp'].min()).days
#             }
        
#         # Geographic
#         if 'latitude' in df.columns and 'longitude' in df.columns:
#             stats['geographic_extent'] = {
#                 'lat_range': [float(df['latitude'].min()), float(df['latitude'].max())],
#                 'lon_range': [float(df['longitude'].min()), float(df['longitude'].max())],
#                 'center': [float(df['latitude'].mean()), float(df['longitude'].mean())]
#             }
        
#         # Parameters
#         param_cols = ['temperature', 'salinity', 'pressure', 'dissolved_oxygen', 'chlorophyll', 'ph']
#         for col in param_cols:
#             if col in df.columns:
#                 stats['parameters'][col] = {
#                     'min': float(df[col].min()),
#                     'max': float(df[col].max()),
#                     'mean': float(df[col].mean()),
#                     'median': float(df[col].median()),
#                     'std': float(df[col].std())
#                 }
        
#         return stats
    
#     def _format_results_for_llm(self, df: pd.DataFrame, max_rows: int = 5) -> str:
#         """Format DataFrame for LLM context"""
#         if df.empty:
#             return "No data available"
        
#         # Select important columns
#         important_cols = ['latitude', 'longitude', 'timestamp', 'temperature', 'salinity', 'pressure']
#         available_cols = [col for col in important_cols if col in df.columns]
        
#         sample_df = df[available_cols].head(max_rows)
#         return sample_df.to_string()
    
#     def _generate_recommendations(self, question: str, df: pd.DataFrame) -> List[str]:
#         """Generate follow-up recommendations"""
#         recommendations = []
        
#         # Based on data characteristics
#         if 'ocean_region' in df.columns and df['ocean_region'].nunique() > 1:
#             recommendations.append("Compare results across different ocean regions")
        
#         if 'timestamp' in df.columns:
#             recommendations.append("Analyze temporal trends with time-series visualization")
        
#         if len(df) > 1000:
#             recommendations.append("Consider filtering by date range or region for detailed analysis")
        
#         if 'float_id' in df.columns and df['float_id'].nunique() > 1:
#             recommendations.append("Examine individual float trajectories")
        
#         return recommendations[:3]  # Top 3
    
#     def _assess_data_quality(self, df: pd.DataFrame) -> str:
#         """Assess data quality"""
#         if df.empty:
#             return 'no_data'
        
#         # Check QC flags if available
#         if 'temp_qc' in df.columns:
#             good_quality = (df['temp_qc'].isin([1, 2])).sum() / len(df)
#             if good_quality > 0.95:
#                 return 'excellent'
#             elif good_quality > 0.80:
#                 return 'good'
#             else:
#                 return 'moderate'
        
#         return 'unvalidated'