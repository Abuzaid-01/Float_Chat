





# import os
# from typing import Dict
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_core.prompts import PromptTemplate
# import pandas as pd
# import re


# class ResponseGenerator:
#     """
#     Generate natural language responses using Gemini.
#     Enhanced with natural, ChatGPT-like tone.
#     """
    
#     def __init__(self):
#         self.llm = ChatGoogleGenerativeAI(
#             model=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
#             temperature=0.7,
#             google_api_key=os.getenv('GOOGLE_API_KEY'),
#             timeout=30,
#             max_retries=2
#         )
        
#         print(f"✅ Response Generator using: {os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')}")
        
#         # Enhanced prompt template with natural tone
#         self.prompt_template = PromptTemplate(
#             input_variables=["question", "context", "query_results", "query_type"],
#             template=self._get_enhanced_prompt_template()
#         )
    
#     def _get_enhanced_prompt_template(self) -> str:
#         """Get enhanced prompt template with natural, ChatGPT-like tone"""
#         return """You are FloatChat, an expert AI assistant for ARGO oceanographic data. Respond naturally and conversationally, like ChatGPT.

# **CORE PRINCIPLES:**
# 1. Be conversational and human-like - adapt your tone to the question
# 2. Only use data from {query_results} - never make up information
# 3. Be concise but complete - don't over-explain unless needed
# 4. Use emojis sparingly (1-2 max) and only when natural
# 5. Structure matters: make responses scannable with headers and bullet points

# **USER'S QUESTION:** {question}
# **QUERY TYPE:** {query_type}
# **DATA RETRIEVED:** {query_results}

# ---

# **HOW TO RESPOND:**

# **For Simple Queries ("show me data", "what floats"):**
# - Direct and brief opening: "I found X records/floats..."
# - Present key data immediately (no lengthy intro)
# - Use tables only if multiple records (3+)
# - For 1-2 records, use bullet points

# **For Statistical Queries ("average", "count", "total"):**
# - Start with the answer: "The average temperature is X°C based on Y measurements"
# - Add context only if helpful
# - Show ranges when relevant
# - Skip unnecessary details

# **For Comparison Queries ("compare A vs B"):**
# - Lead with the comparison result: "Region A is warmer/cooler/similar to Region B"
# - Show stats for EACH region separately  
# - Highlight the key difference
# - NEVER aggregate across compared groups

# **For Location Queries ("Arabian Sea", "where"):**
# - Brief geographic context if needed
# - Focus on the data for that region
# - Skip lengthy ocean descriptions unless asked

# **For Aggregated Data (counts, averages across many records):**
# - Just present the summary stats
# - Skip per-record tables (they don't make sense for aggregated data)
# - Example: "Based on 1.2M records across 668 floats, the average temperature is X°C"

# ---

# **FORMATTING RULES:**

# ✓ **DO:**
# - Match response length to question complexity
# - Use markdown headers (##, ###) to organize
# - Present data in the clearest format (table, bullets, or paragraph)
# - Include units (°C, PSU, dbar, m)
# - Note data quality issues briefly if critical

# ✗ **DON'T:**
# - Start with "Hello! 🌊 I'm thrilled..." (too enthusiastic)
# - Use per-measurement tables for aggregated statistics
# - Over-explain obvious things
# - Add unnecessary flourishes or excitement
# - Force emojis into every sentence
# - Create tables when a sentence works better

# ---

# **RESPONSE STRUCTURE (adapt as needed):**

# 1. **Direct Answer** (1-2 sentences)
#    Answer the question immediately with key findings

# 2. **Supporting Data** (if relevant)
#    - Use the most appropriate format:
#      * Single number → state it
#      * Few values → bullets
#      * Many records → table
#      * Comparisons → side-by-side
#      * Aggregated data → summary stats only

# 3. **Context** (only if helpful)
#    - Geographic info if location query
#    - Quality notes if data has issues
#    - Interpretation if scientific query

# 4. **Optional Follow-up** (brief, one line)
#    - Only suggest next steps if natural
#    - Examples: "Need more details on a specific float?" or "Want to see this visualized?"

# ---

# **DATA ACCURACY:**
# - Use ONLY values from {query_results}
# - If data is missing, say so briefly: "Oxygen data not available for this region"
# - For comparisons: show each group's stats separately, then compare
# - Never calculate averages across comparison groups
# - Exclude invalid QC flags (3, 4, 9) from statistics

# ---

# **Example Tone Adjustments:**

# ❌ Too formal: "Greetings! I shall now present the oceanographic parameters..."
# ✓ Natural: "Here's what I found for the Arabian Sea:"

# ❌ Too excited: "Hello there! 🌊 I'm thrilled to dive into this fascinating data! 📊"
# ✓ Natural: "I found 1.2M records across 668 floats. Here are the key stats:"

# ❌ Too robotic: "Aggregated Statistics Across All Measurements (N=1164744)..."
# ✓ Natural: "Based on 1.16M measurements, the average temperature is 12.4°C"

# ---

# Now generate a natural, helpful response to: "{question}"
# Use the data in {query_results} and match the tone to the {query_type} query type.
# """
    
#     def generate_response(
#         self,
#         question: str,
#         query_results: pd.DataFrame,
#         context: str = ""
#     ) -> str:
#         """
#         Generate natural language response with natural tone
#         """
#         try:
#             # Detect query type for appropriate tone
#             query_type = self._detect_query_type(question)
            
#             # Format query results
#             results_summary = self._format_results(query_results)
            
#             # Generate response using Gemini with enhanced prompt
#             formatted_prompt = self.prompt_template.format(
#                 question=question,
#                 context=context,
#                 query_results=results_summary,
#                 query_type=query_type
#             )
            
#             print(f"🎭 Generating {query_type} response...")
#             response = self.llm.invoke(formatted_prompt)
#             return response.content
            
#         except Exception as e:
#             # Fallback response
#             print(f"⚠️  Error generating response: {e}")
#             return self._generate_fallback_response(query_results, query_type)
    
#     def _detect_query_type(self, question: str) -> str:
#         """Detect the type of query for tone adjustment"""
#         question_lower = question.lower()
        
#         # Comparison queries
#         if any(word in question_lower for word in ['compare', 'versus', 'vs', 'difference between', 'warmer than', 'colder than']):
#             return "comparison"
        
#         # Statistical queries
#         if any(word in question_lower for word in ['average', 'mean', 'median', 'max', 'min', 'count', 'total', 'statistics', 'stats']):
#             return "statistical"
        
#         # Location queries
#         if any(word in question_lower for word in ['region', 'area', 'sea', 'ocean', 'where', 'location', 'lat', 'lon', 'geographic']):
#             return "location"
        
#         # Time queries
#         if any(word in question_lower for word in ['when', 'time', 'date', 'recent', 'latest', 'oldest', 'period', 'trend']):
#             return "time"
        
#         # Anomaly queries
#         if any(word in question_lower for word in ['anomaly', 'extreme', 'unusual', 'strange', 'weird', 'outlier']):
#             return "anomaly"
        
#         # Scientific queries
#         if any(word in question_lower for word in ['why', 'how', 'explain', 'what is', 'process', 'mechanism']):
#             return "scientific"
        
#         # Default: simple data query
#         return "simple"
    
#     def _generate_fallback_response(self, results: pd.DataFrame, query_type: str) -> str:
#         """Generate simple fallback response if LLM fails"""
#         if results.empty:
#             return "I couldn't find any data matching your query. Please try rephrasing or checking the parameters."
        
#         count = len(results)
#         emoji = "📊" if query_type in ["statistical", "simple"] else "🌊"
        
#         response = f"{emoji} I found {count} record{'s' if count != 1 else ''}.\n\n"
#         response += "**Summary:**\n"
#         response += results.head(10).to_markdown(index=False)
        
#         if count > 10:
#             response += f"\n\n... and {count - 10} more records."
        
#         return response
    
#     def _format_results(self, results: pd.DataFrame) -> str:
#         """Format results for LLM consumption"""
#         if results.empty:
#             return "No data found."
        
#         # If small dataset, include full details
#         if len(results) <= 20:
#             return results.to_string(index=False)
        
#         # For larger datasets, provide summary statistics
#         summary = f"Dataset contains {len(results)} records.\n\n"
#         summary += "**Sample Records (first 10):**\n"
#         summary += results.head(10).to_string(index=False)
#         summary += "\n\n**Statistical Summary:**\n"
        
#         # Add numeric column summaries
#         numeric_cols = results.select_dtypes(include=['float64', 'int64']).columns
#         for col in numeric_cols:
#             if col not in ['float_id', 'cycle_number']:  # Skip ID columns
#                 valid_data = results[col].dropna()
#                 if len(valid_data) > 0:
#                     summary += f"- {col}: mean={valid_data.mean():.2f}, min={valid_data.min():.2f}, max={valid_data.max():.2f}\n"
        
#         return summary

import os
from typing import Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
import pandas as pd
import re


class ResponseGenerator:
    """
    Generate natural language responses using Gemini.
    Enhanced with natural, ChatGPT-like tone.
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
        
        # Enhanced prompt template with natural tone
        self.prompt_template = PromptTemplate(
            input_variables=["question", "context", "query_results", "query_type"],
            template=self._get_enhanced_prompt_template()
        )
    
    def _get_enhanced_prompt_template(self) -> str:
        """Get enhanced prompt template with natural, ChatGPT-like tone"""
        return """You are FloatChat, an expert AI assistant for ARGO oceanographic data. Respond naturally and conversationally, like ChatGPT.

**CORE PRINCIPLES:**
1. Be conversational and human-like - adapt your tone to the question
2. Only use data from {query_results} - never make up information
3. Be concise but complete - don't over-explain unless needed
4. Use emojis sparingly (1-2 max) and only when natural
5. Structure matters: make responses scannable with headers and bullet points

**USER'S QUESTION:** {question}
**QUERY TYPE:** {query_type}
**DATA RETRIEVED:** {query_results}

---

**HOW TO RESPOND:**

**For Simple Queries ("show me data", "what floats"):**
- Direct and brief opening: "I found X records/floats..."
- Present key data immediately (no lengthy intro)
- Use tables only if multiple records (3+)
- For 1-2 records, use bullet points

**For Statistical Queries ("average", "count", "total"):**
- Start with the answer: "The average temperature is X°C based on Y measurements"
- Add context only if helpful
- Show ranges when relevant
- Skip unnecessary details

**For Comparison Queries ("compare A vs B"):**
- Lead with the comparison result: "Region A is warmer/cooler/similar to Region B"
- Show stats for EACH region separately  
- Highlight the key difference
- NEVER aggregate across compared groups

**For Location Queries ("Arabian Sea", "where"):**
- Brief geographic context if needed
- Focus on the data for that region
- Skip lengthy ocean descriptions unless asked

**For Aggregated Data (counts, averages across many records):**
- Just present the summary stats
- Skip per-record tables (they don't make sense for aggregated data)
- Example: "Based on 1.2M records across 668 floats, the average temperature is X°C"

---

**FORMATTING RULES:**

✓ **DO:**
- Match response length to question complexity
- Use markdown headers (##, ###) to organize
- Present data in the clearest format (table, bullets, or paragraph)
- Include units (°C, PSU, dbar, m)
- Note data quality issues briefly if critical

✗ **DON'T:**
- Start with "Hello! 🌊 I'm thrilled..." (too enthusiastic)
- Use per-measurement tables for aggregated statistics
- Over-explain obvious things
- Add unnecessary flourishes or excitement
- Force emojis into every sentence
- Create tables when a sentence works better

---

**RESPONSE STRUCTURE (adapt as needed):**

1. **Direct Answer** (1-2 sentences)
   Answer the question immediately with key findings

2. **Supporting Data** (if relevant)
   - Use the most appropriate format:
     * Single number → state it
     * Few values → bullets
     * Many records → table
     * Comparisons → side-by-side
     * Aggregated data → summary stats only

3. **Context** (only if helpful)
   - Geographic info if location query
   - Quality notes if data has issues
   - Interpretation if scientific query

4. **Optional Follow-up** (brief, one line)
   - Only suggest next steps if natural
   - Examples: "Need more details on a specific float?" or "Want to see this visualized?"

---

**DATA ACCURACY:**
- Use ONLY values from {query_results}
- If data is missing, say so briefly: "Oxygen data not available for this region"
- For comparisons: show each group's stats separately, then compare
- Never calculate averages across comparison groups
- Exclude invalid QC flags (3, 4, 9) from statistics

---

**Example Tone Adjustments:**

❌ Too formal: "Greetings! I shall now present the oceanographic parameters..."
✓ Natural: "Here's what I found for the Arabian Sea:"

❌ Too excited: "Hello there! 🌊 I'm thrilled to dive into this fascinating data! 📊"
✓ Natural: "I found 1.2M records across 668 floats. Here are the key stats:"

❌ Too robotic: "Aggregated Statistics Across All Measurements (N=1164744)..."
✓ Natural: "Based on 1.16M measurements, the average temperature is 12.4°C"

---

Now generate a natural, helpful response to: "{question}"
Use the data in {query_results} and match the tone to the {query_type} query type.
"""
    
    def generate_response(
        self,
        question: str,
        query_results: pd.DataFrame,
        context: str = ""
    ) -> str:
        """
        Generate natural language response with natural tone
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
            # Fallback response
            print(f"⚠️  Error generating response: {e}")
            return self._generate_fallback_response(query_results, query_type)
    
    def _detect_query_type(self, question: str) -> str:
        """Detect the type of query for tone adjustment"""
        question_lower = question.lower()
        
        # Comparison queries
        if any(word in question_lower for word in ['compare', 'versus', 'vs', 'difference between', 'warmer than', 'colder than']):
            return "comparison"
        
        # Statistical queries
        if any(word in question_lower for word in ['average', 'mean', 'median', 'max', 'min', 'count', 'total', 'statistics', 'stats']):
            return "statistical"
        
        # Location queries
        if any(word in question_lower for word in ['region', 'area', 'sea', 'ocean', 'where', 'location', 'lat', 'lon', 'geographic']):
            return "location"
        
        # Time queries
        if any(word in question_lower for word in ['when', 'time', 'date', 'recent', 'latest', 'oldest', 'period', 'trend']):
            return "time"
        
        # Anomaly queries
        if any(word in question_lower for word in ['anomaly', 'extreme', 'unusual', 'strange', 'weird', 'outlier']):
            return "anomaly"
        
        # Scientific queries
        if any(word in question_lower for word in ['why', 'how', 'explain', 'what is', 'process', 'mechanism']):
            return "scientific"
        
        # Default: simple data query
        return "simple"
    
    def _generate_fallback_response(self, results: pd.DataFrame, query_type: str) -> str:
        """Generate simple fallback response if LLM fails"""
        if results.empty:
            return "I couldn't find any data matching your query. Please try rephrasing or checking the parameters."
        
        count = len(results)
        emoji = "📊" if query_type in ["statistical", "simple"] else "🌊"
        
        response = f"{emoji} I found {count} record{'s' if count != 1 else ''}.\n\n"
        response += "**Summary:**\n"
        response += results.head(10).to_markdown(index=False)
        
        if count > 10:
            response += f"\n\n... and {count - 10} more records."
        
        return response
    
    def _format_results(self, results: pd.DataFrame) -> str:
        """Format results for LLM consumption"""
        if results.empty:
            return "No data found."
        
        # If small dataset, include full details
        if len(results) <= 20:
            return results.to_string(index=False)
        
        # For larger datasets, provide summary statistics
        summary = f"Dataset contains {len(results)} records.\n\n"
        summary += "**Sample Records (first 10):**\n"
        summary += results.head(10).to_string(index=False)
        summary += "\n\n**Statistical Summary:**\n"
        
        # Add numeric column summaries
        numeric_cols = results.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_cols:
            if col not in ['float_id', 'cycle_number']:  # Skip ID columns
                valid_data = results[col].dropna()
                if len(valid_data) > 0:
                    summary += f"- {col}: mean={valid_data.mean():.2f}, min={valid_data.min():.2f}, max={valid_data.max():.2f}\n"
        
        return summary
