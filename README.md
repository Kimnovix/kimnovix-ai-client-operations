# Kimnovix Weather Digest & Client Operations Suite

API-powered Python command-line tools and a browser telemetry dashboard built for field operations, environmental monitoring, and client task dispatching in Kenya.

## What Is This?

This repository contains the complete Week 1 suite of API integrations and client automation tools:

* **`week1/day5_client_tool.py` (Week 1 Capstone Project — Client Action & Dispatch Logger):** An interactive command-line tool that logs client follow-up tasks in a continuous loop, enriches each entry with live location weather from the OpenWeatherMap API, prints a formatted action summary, and archives all records to `week1/tasks.txt`.
* **`week1/day4_fetch.html` (Browser Telemetry Dashboard):** A single-page web application using JavaScript `fetch()` and `async/await` to geocode cities and display live temperature, humidity, pressure, wind speed, elevation, and precipitation outlooks.
* **`week1/day3_travel_info.py` (Chained API CLI Tool):** Chains OpenWeatherMap GPS coordinates (`lat`/`lon`) into the Open-Meteo Forecast API and caches the combined response to a local `.json` file.
* **`week1/day2_weather.py` (Authenticated Weather Script):** Loads API credentials securely from `.env` using `python-dotenv` and handles HTTP `400`, `401`, `404`, `429`, and `500+` errors explicitly.
* **`week1/weather_digest.py` (Public API Baseline):** Fetches and formats real-time Eldoret atmospheric metrics from Open-Meteo.

## Setup

1. Clone the repository:
   ```bash
   git clone [https://github.com/Kimnovix/weather-digest.git](https://github.com/Kimnovix/weather-digest.git)
   cd weather-digest
   ```
2. Install required Python libraries:
   ```bash
   pip install requests python-dotenv
   ```
3. Create a `.env` file in the root folder with your free OpenWeatherMap key (from [openweathermap.org](https://openweathermap.org)):
   ```env
   OPENWEATHER_API_KEY=your_key_here
   ```

## Usage

Run the Day 5 Client Action & Dispatch Logger:
```bash
python3 week1/day5_client_tool.py
```

Run the other Week 1 tools:
```bash
python3 week1/day3_travel_info.py
python3 week1/day2_weather.py
python3 week1/weather_digest.py
xdg-open week1/day4_fetch.html
```

## Example Output

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

Enter client name (or 'q' to quit): q
==================================================
Session complete. Total tasks logged: 1
All entries archived in: week1/tasks.txt
==================================================
```
## Week 3: AI API Integrations

* **`week3/day11_sacco_bot.py`:** An AI-powered command-line assistant using the Anthropic SDK (`claude-haiku-4-5-20251001`). It acts as a Matatu SACCO secretary, using a strict system prompt to answer member queries about balances, meetings, and fees while gracefully handling API errors and token tracking.

**Usage:**
```bash
python3 week3/day11_sacco_bot.py

**Example Output:**

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

* **`week3/day12_property_parser.py`:** An extraction script demonstrating Prompt Engineering. It takes messy, unstructured WhatsApp inquiries and uses few-shot prompting to force Claude into returning strictly formatted JSON. The JSON is then parsed into a Python dictionary.
  * **Extracted Fields & Purpose:**
    * `property_type` & `bedrooms`: Filters inventory matches.
    * `location`: Determines geographic routing.
    * `budget_kes`: Standardizes financial data to raw integers for numerical sorting (e.g., converting "80k" to 80000).
    * `rental_or_sale`: Routes the lead to the correct sales or letting department.

**Usage:**
```bash
python3 week3/day12_property_parser.py