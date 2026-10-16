# Weather Digest & Field Intelligence Tools

Python automation scripts and JavaScript browser tools that fetch, chain, and archive real-time atmospheric and environmental metrics for agricultural and field operations in Kenya.

## Problem Solved
Field operations require both immediate local weather readings and daily precipitation/elevation context without manually cross-referencing multiple weather portals. This repository provides both command-line automation and a browser-based dashboard to query, chain, and log live telemetry.

## Scripts & Tools Included

* **`week1/weather_digest.py` (Day 1 — Public API):** Connects to the Open-Meteo API, parses nested JSON responses, and outputs current temperature, relative humidity, surface pressure, and wind speed for Eldoret.
* **`week1/day2_weather.py` (Day 2 — Authenticated API):** Connects to the OpenWeatherMap API using credentials loaded securely from `.env` via `python-dotenv`, with explicit HTTP status error handling (`400`, `401`, `404`, `429`, `500+`).
* **`week1/day3_travel_info.py` (Day 3 — Chained CLI Tool):** Interactive command-line tool that accepts user input for any city, queries OpenWeatherMap for live conditions and GPS coordinates (`lat`/`lon`), chains those coordinates into the Open-Meteo Forecast API for elevation and daily precipitation metrics, and saves the combined payload to a local `.json` file.
* **`week1/day4_fetch.html` (Day 4 — Browser Fetch API Dashboard):** Client-side web application using JavaScript `fetch()` and `async/await` to geocode city names and render live atmospheric telemetry in the DOM with explicit loading and error states (no API key exposed in browser code).

## Technical Stack
* **Languages:** Python 3, JavaScript (ES6+), HTML5, CSS3
* **Libraries & APIs:** `requests`, `python-dotenv`, Browser `fetch()` API, Open-Meteo API, OpenWeatherMap API

## Setup & Execution

1. **Install Python dependencies:**
   ```bash
   pip install requests python-dotenv
   ```

2. **Configure environment variables (for Python authenticated scripts):**
   Create a `.env` file in the root directory:
   ```env
   OPENWEATHER_API_KEY=your_api_key_here
   ```

3. **Run the tools:**
   ```bash
   # Python CLI Tools
   python3 week1/weather_digest.py
   python3 week1/day2_weather.py
   python3 week1/day3_travel_info.py

   # Browser Dashboard
   xdg-open week1/day4_fetch.html
   ```