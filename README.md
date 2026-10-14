# Weather Digest

Python automation scripts that fetch and format real-time atmospheric metrics for Eldoret, Kenya.

## Scripts Included

* **`week1/weather_digest.py` (Day 1 — Public API):** Connects to the Open-Meteo API (no key required), parses nested JSON responses, and outputs current temperature, relative humidity, surface pressure, and wind speed.
* **`week1/day2_weather.py` (Day 2 — Authenticated API):** Connects to the OpenWeatherMap API using an API key loaded securely from a `.env` file via `python-dotenv`, with explicit HTTP status error handling (`400`, `401`, `404`, `429`, `500+`).

## Technical Stack
* **Language:** Python 3
* **Libraries:** `requests`, `python-dotenv`

## Setup & Execution

1. **Install dependencies:**
   ```bash
   pip install requests python-dotenv
   ```

2. **Configure environment variables (Required for Day 2):**
   Create a `.env` file in the root directory:
   ```env
   OPENWEATHER_API_KEY=your_api_key_here
   ```

3. **Run the scripts:**
   ```bash
   python3 week1/weather_digest.py
   python3 week1/day2_weather.py
   ```