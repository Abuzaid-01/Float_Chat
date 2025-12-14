import os
from groq import Groq

def verify_groq():
    print("Testing Groq API connection...")
    try:
        client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": "Hello, are you working?"
                }
            ],
            temperature=1,
            max_completion_tokens=1024,
            top_p=1,
            stream=False,
            stop=None
        )
        
        print("✅ Groq API Success!")
        print(f"Response: {completion.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ Groq API Failed: {e}")
        return False

if __name__ == "__main__":
    verify_groq()
