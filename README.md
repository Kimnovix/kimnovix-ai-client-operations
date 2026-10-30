# Kimnovix AI & Client Operations Portfolio

API-powered Python command-line tools, AI automated workflows, and client task dispatchers built for field operations and enterprise integration in Kenya.

## What Is This?

This repository contains a progressive suite of practical software tools demonstrating API integrations, prompt engineering, stateful memory, and autonomous tool-calling agents.

The portfolio spans multiple domains, including:
- **Agriculture & Logistics:** Interactive local client trackers, real-time weather monitoring (OpenWeatherMap API), and autonomous tea harvest advisory agents.
- **Financial Operations:** Dairy co-op payment calculators utilizing dynamic CLI interfaces.
- **Customer Service & Healthcare:** Matatu SACCO assistants, Kisumu Pharmacy stateful chatbots, and Real Estate data extraction tools powered by the Anthropic SDK (`claude-haiku-4-5-20251001`).

## Week 1: API Integrations & Automation

- **`week1/day5_client_tool.py` (Week 1 Capstone Project — Client Action & Dispatch Logger):** An interactive command-line tool that logs client follow-up tasks in a continuous loop, enriches each entry with live location weather from the OpenWeatherMap API, prints a formatted action summary, and archives all records to `week1/tasks.txt`.
- **`week1/day4_fetch.html` (Browser Telemetry Dashboard):** A single-page web application using JavaScript `fetch()` and `async/await` to geocode cities and display live temperature, humidity, pressure, wind speed, elevation, and precipitation outlooks.
- **`week1/day3_travel_info.py` (Chained API CLI Tool):** Chains OpenWeatherMap GPS coordinates (`lat`/`lon`) into the Open-Meteo Forecast API and caches the combined response to a local `.json` file.
- **`week1/day2_weather.py` (Authenticated Weather Script):** Loads API credentials securely from `.env` using `python-dotenv` and handles HTTP `400`, `401`, `404`, `429`, and `500+` errors explicitly.
- **`week1/weather_digest.py` (Public API Baseline):** Fetches and formats real-time Eldoret atmospheric metrics from Open-Meteo.

## Week 3: AI API Integrations

- **`week3/day11_sacco_bot.py`:** An AI-powered command-line assistant using the Anthropic SDK (`claude-haiku-4-5-20251001`). It acts as a Matatu SACCO secretary, using a strict system prompt to answer member queries about balances, meetings, and fees while gracefully handling API errors and token tracking.
- **`week3/day12_property_parser.py`:** An extraction script demonstrating Prompt Engineering. It takes messy, unstructured WhatsApp inquiries and uses few-shot prompting to force Claude into returning strictly formatted JSON. The JSON is then parsed into a Python dictionary.
  - **Extracted Fields & Purpose:**
    - `property_type` & `bedrooms`: Filters inventory matches.
    - `location`: Determines geographic routing.
    - `budget_kes`: Standardizes financial data to raw integers for numerical sorting (e.g., converting "80k" to 80000).
    - `rental_or_sale`: Routes the lead to the correct sales or letting department.
- **`week3/day13_kisumu_pharmacy_bot.py`:** A stateful command-line chatbot demonstrating conversational memory across multiple turns. It enforces a rolling window (retaining the last 10 messages) to manage API token limits and automatically exports the full session history to `week3/chat_log.json` upon exit.
- **`week3/day14_tea_harvest_agent.py`:** A tool-using AI agent demonstrating the two-stage function calling loop. It evaluates field supervisor queries for a Kericho tea estate, autonomously triggers a local Python function (`get_weather_forecast`) to fetch live 6-hour OpenWeatherMap telemetry when harvest conditions are mentioned, and synthesizes an agronomic recommendation against strict temperature, rain, and humidity rules.

---

## Setup & Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Kimnovix/kimnovix-ai-client-operations.git
   cd kimnovix-ai-client-operations
   ```
2. Install required Python libraries:
   ```bash
   pip install requests python-dotenv anthropic
   ```
3. Create a `.env` file in the root folder with your OpenWeatherMap and Anthropic API keys:
   ```env
   OPENWEATHER_API_KEY=your_openweather_key_here
   ANTHROPIC_API_KEY=your_anthropic_key_here
   ```

## Usage & Examples

### Running Week 1 Tools
```bash
python3 week1/day5_client_tool.py
python3 week1/day3_travel_info.py
python3 week1/day2_weather.py
python3 week1/weather_digest.py
xdg-open week1/day4_fetch.html
```

**Day 5 Client Tool Example Output:**
```text
==================================================
     KIMNOVIX CLIENT ACTION & DISPATCH LOGGER     
==================================================
Log client tasks with live site weather telemetry.
Type 'q' or 'quit' as the client name to exit.

Enter client name (or 'q' to quit): Kamau Auto Spares
Enter task description: Follow up on invoice #014
Enter client city [press Enter for Eldoret]: Nairobi
Fetching live site weather...

--- ACTION SUMMARY LOGGED ---
Kamau Auto Spares, Task: Follow up on invoice #014
Site Weather : Nairobi: 21.4°C, scattered clouds, humidity 64%
Saved to     : week1/tasks.txt
-----------------------------
```

### Running Week 3 AI Tools
```bash
python3 week3/day11_sacco_bot.py
python3 week3/day12_property_parser.py
python3 week3/day13_kisumu_pharmacy_bot.py
python3 week3/day14_tea_harvest_agent.py
```

**Day 11 SACCO Bot Example Output:**
```text
==========================================
    THIKA MATATU SACCO AI ASSISTANT       
==========================================
Type 'q' or 'quit' to exit.

Member Question: Can I get a loan to buy a new engine?
Drafting response...

SACCO Bot:
I cannot process loan applications for engine purchases here. Please call the main office at 0700 123 456 to discuss asset financing options with our team.
------------------------------------------
Cost: 271 input tokens | 106 output tokens
==========================================
```

**Day 13 Kisumu Pharmacy Bot Example Output:**
```text
==========================================
      KISUMU PHARMACY ASSISTANT BOT       
==========================================
Type 'q', 'quit', or 'exit' to end the session.

Customer: I have a prescription that needs to be filled.
Assistant: We can process your prescription for you. Please bring the original physical prescription along with your patient ID.

Customer: How long will that take?
Assistant: Prescription processing takes between 15 and 30 minutes.
```

**Day 14 Kericho Tea Harvest Agent Example Output:**
```text
==========================================
   KERICHO TEA ESTATE FIELD ASSISTANT     
==========================================
Type 'q', 'quit', or 'exit' to end the session.

Supervisor: Is today a good day for harvesting in Kericho?

[SYSTEM: Executing local tool get_weather_forecast('Kericho')]...
[SYSTEM: Tool returned data -> passing back to AI for synthesis]

AI: Based on the 6-hour forecast for Kericho, conditions are MARGINAL to BAD for harvesting. While temperatures are ideal (18.5°C–20.1°C), light rain is forecasted within the next 6 hours with high humidity (82%). Hold off on deploying harvesting crews or proceed with caution under cover.
```