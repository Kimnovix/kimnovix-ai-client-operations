"""
Thika Matatu SACCO Secretary Assistant (Anthropic Production Version)
--------------------------------------------------------------------
An AI-powered CLI tool that answers common SACCO member questions
using hardcoded factual data (Balance, Meetings, Fees).

Usage:
    python3 week3/day11_sacco_bot.py
"""

import os
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """
You are the helpful, professional WhatsApp assistant for the Thika Matatu SACCO secretary.
You must use ONLY the following factual information to answer member questions:

1. Member Balance: "To check your exact savings and loan balance, please reply with your National ID number. Note: Minimum share capital is KES 20,000."
2. Next Meeting: "Our next Annual General Meeting (AGM) is on Saturday, 28th November at Thika Town Hall, starting at 9:00 AM."
3. Membership Fees: "New member registration is a non-refundable fee of KES 2,500. The mandatory monthly contribution is KES 1,000."

Rules:
- Keep your answers brief, friendly, and formatted perfectly for a quick WhatsApp read.
- You can understand Swahili or Sheng, but reply in professional English or Swahili depending on the user's tone.
- If a member asks something NOT covered in the 3 points above, politely tell them to call the main office at 0700 123 456. Do not make up answers.
"""

def get_ai_response(question):
    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": question}]
        )
        return message
        
    except anthropic.APIConnectionError:
        print("\n[ERROR] No internet connection. Check your connection and try again.")
    except anthropic.AuthenticationError:
        print("\n[ERROR] API key is wrong, missing, or out of credits. Check your Anthropic Console.")
    except anthropic.RateLimitError:
        print("\n[ERROR] Too many requests. Wait 60 seconds and try again.")
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")
        
    return None

def run_sacco_bot():
    print("==========================================")
    print("    THIKA MATATU SACCO AI ASSISTANT       ")
    print("==========================================")
    print("Type 'q' or 'quit' to exit.\n")
    
    while True:
        question = input("Member Question: ").strip()
        
        if question.lower() in ['q', 'quit', 'exit']:
            print("Shutting down assistant...")
            break
            
        if not question:
            continue
            
        print("Drafting response...\n")
        response_msg = get_ai_response(question)
        
        if response_msg:
            print(f"SACCO Bot:\n{response_msg.content[0].text}")
            print("-" * 42)
            print(f"Cost: {response_msg.usage.input_tokens} input tokens | {response_msg.usage.output_tokens} output tokens")
            print("==========================================\n")

if __name__ == "__main__":
    run_sacco_bot()