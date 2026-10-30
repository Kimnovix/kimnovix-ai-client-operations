"""
Day 14: Kericho Tea Harvest Agent
---------------------------------
Demonstrates function calling (tool use). The AI determines if a weather 
check is needed, triggers a local Python function to hit the OpenWeatherMap API, 
and synthesizes a recommendation based on strict environmental parameters.
"""

import os
import requests
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
owm_api_key = os.getenv("OPENWEATHER_API_KEY")

SYSTEM_PROMPT = """You are the AI Field Supervisor Assistant for a Kericho Tea Estate.
Your job is to advise field staff. 

Harvesting Rules:
- GOOD conditions: No rain in the next 6 hours, temperature between 15-25°C, low humidity.
- BAD conditions: Active rain or temperatures above 28°C.
- MARGINAL conditions: Anything in between. Proceed with caution.

When asked about harvest conditions, you MUST use the `get_weather_forecast` tool to get live data.
Synthesize the tool's data into a brief, practical recommendation in plain English.
If asked about non-harvest topics (e.g., payroll, tea varieties), answer directly without using tools.
"""

# 1. Define the tool for Anthropic
weather_tool = {
    "name": "get_weather_forecast",
    "description": "Get the current weather and 6-hour forecast for a location to determine agricultural conditions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city name, e.g., 'Kericho'"
            }
        },
        "required": ["location"]
    }
}

# 2. Write the local Python function
def get_weather_forecast(location):
    """Fetches a 6-hour forecast (2 periods) from OpenWeatherMap."""
    if not owm_api_key:
        return "Error: Missing OPENWEATHER_API_KEY."
        
    print(f"\n[SYSTEM: Executing local tool get_weather_forecast('{location}')]...")
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={location},KE&appid={owm_api_key}&units=metric"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Extract the next 6 hours (2 data points, spaced 3 hours apart)
            forecasts = []
            for item in data['list'][:2]:
                time = item['dt_txt']
                temp = item['main']['temp']
                hum = item['main']['humidity']
                desc = item['weather'][0]['description']
                forecasts.append(f"At {time}: {temp}°C, {hum}% humidity, {desc}")
            return "\n".join(forecasts)
        else:
            return f"Weather API returned status code {response.status_code}."
    except Exception as e:
        return f"Network error during API call: {e}"

# 3. Build the Agent loop
def agent_loop():
    print("==========================================")
    print("   KERICHO TEA ESTATE FIELD ASSISTANT     ")
    print("==========================================")
    print("Type 'q', 'quit', or 'exit' to end the session.\n")
    
    messages = []
    
    while True:
        user_input = input("Supervisor: ").strip()
        if user_input.lower() in ['q', 'quit', 'exit']:
            break
        if not user_input:
            continue
            
        messages.append({"role": "user", "content": user_input})
        
        # Initial call to Claude with the tool available
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            tools=[weather_tool],
            messages=messages
        )
        
        # Check if Claude decided to use the tool
        if response.stop_reason == "tool_use":
            # Extract tool use request
            tool_use = next(block for block in response.content if block.type == "tool_use")
            fn_name = tool_use.name
            fn_input = tool_use.input
            
            # Execute the local function
            if fn_name == "get_weather_forecast":
                tool_result = get_weather_forecast(fn_input["location"])
            else:
                tool_result = f"Unknown tool: {fn_name}"
                
            print(f"[SYSTEM: Tool returned data -> passing back to AI for synthesis]")
            
            # Append Claude's tool use request AND the local tool result to history
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": tool_result
                    }
                ]
            })
            
            # Second call to Claude to generate the final human-readable answer
            final_response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                system=SYSTEM_PROMPT,
                tools=[weather_tool],
                messages=messages
            )
            
            final_text = final_response.content[0].text
            messages.append({"role": "assistant", "content": final_text})
            print(f"\nAI: {final_text}\n")
            
        else:
            # Claude answered directly without tools
            text = response.content[0].text
            messages.append({"role": "assistant", "content": text})
            print(f"AI: {text}\n")

if __name__ == "__main__":
    agent_loop()