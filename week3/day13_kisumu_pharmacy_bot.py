"""
Day 13: Kisumu Pharmacy Conversational Bot
------------------------------------------
A stateful command-line chatbot using Claude Haiku. 
Maintains memory across turns, enforces a 10-message rolling window, 
and exports conversation logs to a JSON file.
"""

import os
import json
import anthropic
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are the official assistant for Kisumu Pharmacy.

Pharmacy Details:
- Hours: Mon-Sat 8:00 AM - 8:00 PM, Sun 10:00 AM - 4:00 PM.
- Services: 
  1. Prescription processing (takes 15-30 minutes; requires original physical prescription and patient ID).
  2. Over-the-counter (OTC) medication sales.
  3. Basic health and wellness consultations.
  4. Blood pressure and BMI monitoring.
  5. First aid and wound care supplies.

Rules:
- Answer questions accurately based ONLY on the provided details.
- Be polite, concise, and professional.
- If asked about services, stock, or clinical advice not listed above, politely state you only handle the core pharmacy services and advise them to call the main pharmacist desk.
"""

def run_pharmacy_bot():
    messages = []
    
    print("==========================================")
    print("      KISUMU PHARMACY ASSISTANT BOT       ")
    print("==========================================")
    print("Type 'q', 'quit', or 'exit' to end the session.\n")
    
    while True:
        user_input = input("Customer: ").strip()
        
        if user_input.lower() in ['q', 'quit', 'exit']:
            print("\nShutting down and saving conversation log...")
            break
            
        if not user_input:
            continue
            
        # 1. Append user message to the active history list
        messages.append({"role": "user", "content": user_input})
        
        try:
            # 2. Send the ENTIRE history list to Claude
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=messages
            )
            
            reply = response.content[0].text
            
            # 3. Append the AI's response to the history list before the next loop
            messages.append({"role": "assistant", "content": reply})
            
            print(f"Assistant: {reply}\n")
            
            # 4. Enforce rolling window (keep last 10 messages: 5 user, 5 assistant)
            if len(messages) > 10:
                messages = messages[-10:]
                
        except Exception as e:
            print(f"[API ERROR] {e}\n")
            # If the API fails, remove the orphaned user message to prevent state corruption
            messages.pop()
            
    # 5. Save the final session to a local JSON log file
    if messages:
        log_data = {
            "session_date": datetime.now().isoformat(),
            "conversation": messages
        }
        
        log_file = "week3/chat_log.json"
        with open(log_file, "w") as f:
            json.dump(log_data, f, indent=2)
            
        print(f"Session archived to {log_file}")
        print("==========================================")

if __name__ == "__main__":
    run_pharmacy_bot()