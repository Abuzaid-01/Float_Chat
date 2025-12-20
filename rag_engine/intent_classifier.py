"""
Intent Classification System for FloatChat
Routes queries based on user intent, making the chatbot more human-like and intelligent
"""

import os
import re
from groq import Groq
from typing import Dict, List
import json


class IntentClassifier:
    """
    Classifies user query intent using LLM to provide human-like conversation
    Handles both data queries and conversational/meta queries
    """
    
    def __init__(self):
        # Note: Don't hard-require GROQ_API_KEY at import time.
        # Many paths (keyword intent match) don't need the LLM at all.
        # We'll initialize the Groq client lazily only when needed.
        self.client = None
        self.model = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
        
        # Define intent categories
        self.intents = {
            'developer_info': {
                'keywords': ['who built', 'who created', 'who made', 'who developed', 'developer', 
                           'creator', 'author', 'your creator', 'your developer',
                           'built by', 'created by', 'made by', 'developed by', 'whi built'],
                'response_template': self._get_developer_info
            },
            'assistant_identity': {
                'keywords': ['who are you', 'what are you', 'what is your name', 'tell me about you',
                           'introduce yourself', 'who r u'],
                'response_template': self._get_assistant_identity
            },
            'greeting': {
                'keywords': ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 
                           'good evening', 'howdy', 'sup'],
                'response_template': self._get_greeting
            },
            'help': {
                'keywords': ['help', 'how to', 'how do i', 'can you help', 'guide', 'tutorial',
                           'what can you do', 'capabilities', 'features', 'how to use'],
                'response_template': self._get_help
            },
            'thanks': {
                'keywords': ['thank', 'thanks', 'thx', 'appreciate', 'grateful'],
                'response_template': self._get_thanks
            },
            'about_floatchat': {
                'keywords': ['what is floatchat', 'about floatchat', 'what does floatchat do',
                           'purpose of floatchat', 'what is this app', 'about this app',
                           'tell me about this app'],
                'response_template': self._get_about_floatchat
            },
            'data_query': {
                'keywords': [],  # Default for oceanographic queries
                'response_template': None
            }
        }
        
        print("✅ Intent Classifier initialized")

    def _get_llm_client(self) -> Groq:
        """Lazily create Groq client only when needed."""
        if self.client is not None:
            return self.client

        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. LLM-based intent classification can't run, "
                "but keyword-based routing still works."
            )

        self.client = Groq(api_key=api_key)
        return self.client
    
    def classify_intent(self, user_query: str, conversation_history: List[Dict] = None) -> Dict:
        """
        Classify the intent of user query using both keyword matching and LLM
        NOW CONTEXT-AWARE: Checks conversation history to detect follow-ups
        
        Args:
            user_query: Current user query
            conversation_history: Previous conversation messages
        
        Returns:
            {
                'intent': str,  # Intent category
                'confidence': float,  # Confidence score
                'requires_data_query': bool,  # Whether to route to data pipeline
                'direct_response': str or None  # Pre-generated response if available
            }
        """
        user_query_lower = user_query.lower().strip()
        
        # CRITICAL: Detect follow-up queries that need data access
        follow_up_keywords = ['more', 'tell me more', 'give more', 'more data', 'more information',
                             'elaborate', 'explain', 'details', 'tell more', 'show more',
                             'more about', 'about this', 'about that', 'more on', 'expand']
        
        is_follow_up = any(keyword in user_query_lower for keyword in follow_up_keywords)
        has_recent_data_query = False
        
        if conversation_history and len(conversation_history) >= 2:
            # Check if the last exchange was a data query
            for msg in reversed(conversation_history[-4:]):
                if msg.get('role') == 'user':
                    last_query = msg.get('content', '').lower()
                    # Check if last query was data-related
                    data_indicators = ['show', 'data', 'temperature', 'salinity', 'pressure', 
                                     'ocean', 'sea', 'floats', 'records', 'measurements']
                    if any(indicator in last_query for indicator in data_indicators):
                        has_recent_data_query = True
                        break
        
        # If this is a follow-up to a data query, route to data pipeline
        if is_follow_up and has_recent_data_query:
            print(f"🔄 Detected follow-up query, routing to data pipeline")
            return {
                'intent': 'data_query_followup',
                'confidence': 0.95,
                'requires_data_query': True,
                'direct_response': None
            }

        # Prefer explicit conversational/meta intents before generic data keyword routing.
        # This prevents questions like "what is FloatChat?" from being treated as a data query.
        for intent_name, intent_data in self.intents.items():
            if intent_name == 'data_query':
                continue

            for keyword in intent_data['keywords']:
                keyword = keyword.lower().strip()
                if not keyword:
                    continue

                # Prevent false matches like "hi" in "this".
                if len(keyword) <= 3:
                    if re.search(rf"\b{re.escape(keyword)}\b", user_query_lower):
                        direct_response = intent_data['response_template']()
                        return {
                            'intent': intent_name,
                            'confidence': 0.95,
                            'requires_data_query': False,
                            'direct_response': direct_response
                        }
                    continue

                if keyword in user_query_lower:
                    direct_response = intent_data['response_template']()
                    return {
                        'intent': intent_name,
                        'confidence': 0.95,
                        'requires_data_query': False,
                        'direct_response': direct_response
                    }
        
        # Force route data-specific questions to data pipeline
        data_keywords = ['dataset', 'data range', 'date range', 'from which date',
                        'temperature', 'salinity', 'pressure', 'float',
                        'arabian sea', 'bay of bengal', 'measurements', 'records',
                        'when was data collected', 'time period', 'coverage', 'show']
        
        if any(keyword in user_query_lower for keyword in data_keywords):
            # This is definitely a data query
            return {
                'intent': 'data_query',
                'confidence': 0.99,
                'requires_data_query': True,
                'direct_response': None
            }
        
    # Use LLM for more nuanced intent classification
        llm_intent = self._classify_with_llm(user_query)
        
        if llm_intent['intent'] != 'data_query':
            # Non-data query, get appropriate response
            response_func = self.intents[llm_intent['intent']]['response_template']
            if response_func:
                direct_response = response_func()
                return {
                    'intent': llm_intent['intent'],
                    'confidence': llm_intent['confidence'],
                    'requires_data_query': False,
                    'direct_response': direct_response
                }
        
        # It's a data query, route to MCP pipeline
        return {
            'intent': 'data_query',
            'confidence': llm_intent['confidence'],
            'requires_data_query': True,
            'direct_response': None
        }
    
    def _classify_with_llm(self, user_query: str) -> Dict:
        """Use LLM to classify intent when keywords don't match"""
        
        prompt = f"""You are an intent classifier for FloatChat, an oceanographic data chatbot.

Classify the following user query into ONE of these categories:

1. developer_info - Questions about who built/created/developed the app
2. greeting - Greetings, hello, hi, etc.
3. help - Requests for help, how to use, what can you do
4. thanks - Thanking or expressing gratitude
5. about_floatchat - Questions about what FloatChat is or does (NOT about the data itself)
6. data_query - Questions about oceanographic data, dataset, date ranges, measurements, temperature, salinity, floats, regions, time periods, etc.

IMPORTANT: If the question asks about data, dataset, dates, measurements, or any ocean parameters, classify as "data_query".

User Query: "{user_query}"

Respond ONLY with a JSON object in this format:
{{"intent": "category_name", "confidence": 0.95}}

JSON Response:"""

        try:
            client = self._get_llm_client()
            completion = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Low temperature for consistent classification
                max_completion_tokens=100,
                top_p=1,
                stream=False
            )
            
            response_text = completion.choices[0].message.content.strip()
            
            # Parse JSON response
            # Remove markdown code blocks if present
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            result = json.loads(response_text)
            return result
            
        except Exception as e:
            print(f"⚠️ LLM classification error: {e}")
            # Default to data_query on error
            return {'intent': 'data_query', 'confidence': 0.5}
    
    # Response templates for different intents
    
    def _get_developer_info(self) -> str:
        """Developer information response"""
        return """👨‍💻 Built by Abuzaid

FloatChat was created by **Abuzaid**.

- LinkedIn: https://www.linkedin.com/in/abuzaid01
- GitHub: https://github.com/Abuzaid-01

If you want, tell me what you’re trying to do (research, class project, dashboard), and I’ll point you to the best features."""

    def _get_assistant_identity(self) -> str:
        """Assistant identity response (who am I?)"""
        return """I’m **FloatChat** — an AI assistant inside this app.

My job is to help you explore **ARGO float ocean data** by chatting in normal language. You can ask for:
- Maps (where floats are)
- Profiles (temperature/salinity vs depth)
- Comparisons (region to region, time to time)
- Quick explanations of ocean terms

If you tell me what you’re curious about (a region, date range, float ID, or a parameter), I’ll guide you to the right analysis and visuals."""

    def _get_greeting(self) -> str:
        """Greeting response"""
        return """Hello! 👋 Welcome to **FloatChat**!

I'm your AI assistant for exploring ARGO oceanographic data. I can help you:

- 🌊 Query ocean temperature, salinity, and pressure data
- 🗺️ Find data from specific regions (Arabian Sea, Pacific Ocean, etc.)
- 📊 Analyze water masses and thermocline depths
- 📈 Compare data across different locations and time periods
- 🔍 Search for specific float measurements

**Try asking me something like:**
- "Show me temperature data from the Arabian Sea"
- "What water masses are present at 15°N, 75°E?"
- "Compare salinity between the Arabian Sea and Bay of Bengal"

How can I help you today? 🚀"""

    def _get_help(self) -> str:
        """Help information response"""
        return """## 🆘 How to Use FloatChat

I'm powered by **MCP (Model Context Protocol)** and can understand natural language queries about oceanographic data!

### 📋 **What I Can Do:**

1. **Data Queries** 
   - "Show me all floats in the Arabian Sea"
   - "What's the average temperature at 100m depth?"

2. **Water Mass Analysis**
   - "Identify water masses in this region"
   - "Show me T-S diagram data"

3. **Thermocline Calculations**
   - "Calculate thermocline depth for float 2903871"
   - "Show temperature gradients"

4. **Regional Comparisons**
   - "Compare Arabian Sea vs Bay of Bengal"
   - "What's the temperature difference between regions?"

5. **Temporal Analysis**
   - "Show temperature trends over time"
   - "What's changed in the last 5 years?"

### 💡 **Tips:**
- Be specific about locations, parameters, or time periods
- I understand casual language - no need for formal queries!
- Ask follow-up questions to dig deeper

### 🔧 **Powered By:**
- 9 specialized MCP tools for oceanographic analysis
- Llama 3.3-70B AI model via Groq
- Real ARGO float data from the global ocean

**Ready to explore? Ask me anything about ocean data!** 🌊"""

    def _get_thanks(self) -> str:
        """Thank you response"""
        return """You're welcome! 😊

I'm happy to help you explore oceanographic data. If you have any more questions about:
- 🌊 Ocean temperatures, salinity, or pressure
- 🗺️ Specific regions or floats
- 📊 Water mass identification
- 📈 Data trends and comparisons

Just ask away! I'm here to assist. 🚀"""

    def _get_about_floatchat(self) -> str:
        """About FloatChat response"""
        return """## 🌊 Hey! Let me tell you about FloatChat

I'm **FloatChat** - your AI companion for exploring the fascinating world of ocean data! 🌊

Think of me as your personal oceanography expert who speaks your language. No need to learn complex commands or programming - just **chat with me naturally**, and I'll help you discover insights from ARGO float data.

### 💬 **How I Work:**
You ask me questions like you'd ask a friend - *"What's the temperature in the Arabian Sea?"* or *"Show me salinity patterns near India"* - and I instantly understand what you need, analyze the data, and show you beautiful visualizations.

### ✨ **What Makes Me Special:**
- **🧠 Smart & Conversational** - I understand context, remember our conversation, and can answer follow-up questions
- **🔍 Deep Analysis** - I can identify water masses, calculate thermocline depths, compare regions, and much more
- **🎨 Visual Storytelling** - Interactive maps, depth profiles, and charts that bring ocean data to life
- **⚡ Lightning Fast** - Powered by advanced AI to give you instant, accurate answers

### 🎯 **Who I Help:**
Whether you're a researcher diving deep into ocean patterns, a student learning about marine science, or just someone curious about our oceans - I'm here to make ocean data accessible and exciting for you!

### 👨‍💻 **Created By:**
Built with ❤️ by **Abuzaid** - [LinkedIn](https://www.linkedin.com/in/abuzaid01) | [GitHub](https://github.com/Abuzaid-01)

**Ready to explore? Just ask me anything about the ocean!** 🚀🌊"""


# Singleton instance
intent_classifier = IntentClassifier()
