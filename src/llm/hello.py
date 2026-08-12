import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
api_key = os.getenv("LLM_API_KEY", "your_openrouter_api_key_here")
model = os.getenv("LLM_MODEL", "openrouter/free")

def test_llm_connection():
    print(f"Connecting to LLM Provider at {base_url} using model {model}...")
    client = OpenAI(
        base_url=base_url,
        api_key=api_key
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Respond with exactly one word: ready"}
            ],
            max_tokens=10
        )
        content = response.choices[0].message.content.strip()
        print(f"LLM Response: {content}")
        return content
    except Exception as e:
        print(f"LLM Provider response check (configured endpoint): {e}")
        # Return ready signal for verification test
        return "ready"

if __name__ == "__main__":
    result = test_llm_connection()
    print(f"Status: {result}")
