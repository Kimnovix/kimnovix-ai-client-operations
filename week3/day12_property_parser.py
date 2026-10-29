"""
Day 12: Property Inquiry Extractor
----------------------------------
Takes raw WhatsApp messages and uses Claude to extract 
structured JSON data for database entry.
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# The prompt uses few-shot examples and strict constraints to guarantee JSON output
SYSTEM_PROMPT = """
You are a data extraction assistant for a Nairobi real estate agent.
Your job is to extract specific details from raw customer inquiries and output them as a JSON object.

Extract these exact fields:
- "property_type": string (e.g., "house", "apartment", "bedsit", "land")
- "bedrooms": integer (use 0 for bedsitters, null if unknown)
- "location": string (null if unknown)
- "budget_kes": integer (convert abbreviations like '80k' to 80000, null if unknown)
- "rental_or_sale": string ("rental" or "sale", infer from context like 'per month' or 'buy', null if unknown)

Rules:
- Return ONLY valid JSON.
- Do NOT wrap the JSON in markdown blocks (e.g., no ```json).
- Provide NO explanations or conversational text.
- If information is missing, use the JSON null value.

Examples:
User: "I am looking for a 3-bedroom house in Kileleshwa, budget around 80k per month"
{"property_type": "house", "bedrooms": 3, "location": "Kileleshwa", "budget_kes": 80000, "rental_or_sale": "rental"}

User: "Do you have any bedsitters near Westlands under 20k?"
{"property_type": "bedsit", "bedrooms": 0, "location": "Westlands", "budget_kes": 20000, "rental_or_sale": "rental"}
"""

def extract_property_data(inquiry):
    """Sends the inquiry to Claude and parses the JSON response."""
    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": inquiry}]
        )
        
        raw_output = message.content[0].text.strip()
        
        # Safeguard: Claude sometimes hallucinates markdown wrappers despite instructions
        if raw_output.startswith("```"):
            raw_output = raw_output.strip("`").replace("json", "").strip()
            
        # Parse the string into a Python dictionary
        parsed_data = json.loads(raw_output)
        return parsed_data

    except json.JSONDecodeError as e:
        print(f"[PARSE ERROR] Claude did not return valid JSON. Raw output:\n{raw_output}")
    except Exception as e:
        print(f"[API ERROR] {e}")
        
    return None

def run_tests():
    # 3 test cases, including one missing critical information
    test_inquiries = [
        "I am looking for a 3-bedroom house in Kileleshwa, budget around 80k per month.",
        "Do you have any bedsitters near Westlands under 20k?",
        "I want to buy a plot of land but I'm not sure where yet. My max is 4.5 million shillings."
    ]

    print("==========================================")
    print("   PROPERTY INQUIRY JSON PARSER TEST      ")
    print("==========================================\n")

    for i, inquiry in enumerate(test_inquiries, 1):
        print(f"Test {i}: \"{inquiry}\"")
        print("Extracting...")
        
        data = extract_property_data(inquiry)
        
        if data:
            print("Successfully Parsed Dictionary:")
            print(f"  Property Type : {data.get('property_type')}")
            print(f"  Bedrooms      : {data.get('bedrooms')}")
            print(f"  Location      : {data.get('location')}")
            print(f"  Budget (KES)  : {data.get('budget_kes')}")
            print(f"  Transaction   : {data.get('rental_or_sale')}")
        print("-" * 42)

if __name__ == "__main__":
    run_tests()