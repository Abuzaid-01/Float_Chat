"""
Intent Classification System for FloatChat
Routes queries based on user intent, making the chatbot more human-like and intelligent
"""

import re
from groq import Groq
from typing import Dict, List
import json

from rag_engine import llm_config


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
        self.model = llm_config.setting("GROQ_MODEL", llm_config.DEFAULT_MODEL)
        
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
            'mcp_info': {
                'keywords': ['mcp', 'mcp tool', 'mcp tools', 'model context protocol',
                           'how many mcp', 'how many tools', 'available tools', 'what tools',
                           'which tools', 'list tools', 'mcp server', 'benefit of mcp',
                           'benefits of mcp', 'why mcp', 'mcp protocol', 'tell me about mcp',
                           'about mcp', 'how does mcp work', 'what is mcp'],
                'response_template': self._get_mcp_info
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

        self.client = llm_config.make_client()
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

        # Questions about the app or its author are answered directly, whatever
        # else they mention ("what is FloatChat?" is not a data query).
        specific_meta = ('developer_info', 'assistant_identity', 'about_floatchat', 'mcp_info')
        mentions_data = self._mentions_data(user_query_lower)
        # A greeting, thanks or plea for help only wins when the message is not
        # also a data question: "What features does the Arabian Sea temperature
        # have?" must reach the data pipeline, while "thanks!" must not.
        is_short = len(user_query_lower.split()) <= 3

        for intent_name, intent_data in self.intents.items():
            if intent_name == 'data_query':
                continue
            if intent_name not in specific_meta and mentions_data and not is_short:
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
        if mentions_data:
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
        
        # It's a data query, route to the archive query pipeline
        return {
            'intent': 'data_query',
            'confidence': llm_intent['confidence'],
            'requires_data_query': True,
            'direct_response': None
        }
    
    # Words that mark a question as being about the ocean data itself.
    _DATA_TERMS = re.compile(
        r"\b(?:dataset|data\s+range|date\s+range|from\s+which\s+date|temperatures?|temp|salinit\w+|"
        r"pressures?|floats?|profiles?|cycles?|depths?|thermoclines?|mixed\s+layers?|water\s+mass\w*|"
        r"oxygen|chlorophyll|arabian|bengal|andaman|red\s+sea|indian\s+ocean|equatorial|southern\s+ocean|"
        r"measurements?|records|observations?|latitude|longitude|trajectory|warmest|coldest|saltiest|"
        r"when\s+was\s+data\s+collected|time\s+period|coverage|show|plot|compare|average|how\s+many)\b"
    )

    def _mentions_data(self, user_query_lower: str) -> bool:
        return self._DATA_TERMS.search(user_query_lower) is not None

    def _classify_with_llm(self, user_query: str) -> Dict:
        """Use LLM to classify intent when keywords don't match"""
        
        prompt = f"""You are an intent classifier for FloatChat, an oceanographic data chatbot.

Classify the following user query into ONE of these categories:

1. developer_info - Questions about who built/created/developed the app
2. greeting - Greetings, hello, hi, etc.
3. help - Requests for help, how to use, what can you do
4. thanks - Thanking or expressing gratitude
5. about_floatchat - Questions about what FloatChat is or does (NOT about the data itself)
6. mcp_info - Questions about MCP (Model Context Protocol), MCP tools, available tool count, tool list, tool benefits, or connecting external AI agents
7. data_query - Questions about oceanographic data, dataset, date ranges, measurements, temperature, salinity, floats, regions, time periods, etc.

IMPORTANT: If the question asks about data, dataset, dates, measurements, or any ocean parameters, classify as "data_query".

User Query: "{user_query}"

Respond ONLY with a JSON object in this format:
{{"intent": "category_name", "confidence": 0.95}}

JSON Response:"""

        try:
            # Shared helper: bounded timeout and retries, low temperature for consistency.
            completion = self._get_llm_client().chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_completion_tokens=350,
                response_format={"type": "json_object"},
            )
            response_text = (completion.choices[0].message.content or "").strip()
            
            # Parse JSON response
            # Remove markdown code blocks if present
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            result = json.loads(response_text)
            if result.get('intent') not in self.intents:
                return {'intent': 'data_query', 'confidence': 0.5}
            result.setdefault('confidence', 0.7)
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
- 🗺️ Find data from specific regions (Arabian Sea, Bay of Bengal, Southern Indian Ocean…)
- 📊 Analyze water masses and thermocline depths
- 📈 Compare data across different locations and time periods
- 🔍 Search for specific float measurements

**Try asking me something like:**
- "Show me temperature data from the Arabian Sea"
- "Calculate the thermocline depth for float 2903956"
- "Compare salinity between the Arabian Sea and Bay of Bengal"

How can I help you today? 🚀"""

    def _get_help(self) -> str:
        """Help information response"""
        return """## 🆘 How to Use FloatChat

Ask a question about the Argo archive or request a profile analysis.

### 📋 **What I Can Do:**

1. **Data Queries** 
   - "Show me all floats in the Arabian Sea"
   - "What's the average temperature at 100m depth?"

2. **Water Mass Analysis**
   - "Identify water masses in this region"
   - "Show me T-S diagram data"

3. **Thermocline Calculations**
   - "Calculate thermocline depth for float 2903956"
   - "Show temperature gradients"

4. **Regional Comparisons**
   - "Compare Arabian Sea vs Bay of Bengal"
   - "What's the temperature difference between regions?"

5. **Temporal Analysis**
   - "Show temperature trends over time"
   - "How did temperature change day by day in the Arabian Sea?"

### 💡 **Tips:**
- Be specific about locations, parameters, or time periods
- I understand casual language - no need for formal queries!
- Ask follow-up questions to dig deeper

### 🔧 **Powered By:**
- Rule-based question understanding, with a large language model (via Groq) for free-form questions
- Thermocline, mixed-layer and water-mass analysis of individual profiles
- Real ARGO float data, with the SQL and rows shown beside every answer

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


    def _get_mcp_info(self) -> str:
        return (
            "This version of FloatChat uses FastAPI for archive queries and profile analysis. "
            "MCP is a protocol for exposing tools to external AI clients. Earlier FloatChat "
            "prototypes included an internal tool registry."
        )


# Singleton instance
intent_classifier = IntentClassifier()
