# Weather Digest & Field Intelligence Tools

Python automation scripts and command-line tools that fetch, chain, and archive real-time atmospheric and environmental metrics for agricultural and field operations in Kenya.

## Problem Solved
Field operations require both immediate local weather readings and daily precipitation/elevation context without manually cross-referencing multiple weather portals. This repository automates data collection, chains geographic coordinates across multiple APIs, and archives structured JSON logs locally for offline analysis.

## Scripts Included

* **`week1/weather_digest.py` (Day 1 — Public API):** Connects to the Open-Meteo API, parses nested JSON responses, and outputs current temperature, relative humidity, surface pressure, and wind speed for Eldoret.
* **`week1/day2_weather.py` (Day 2 — Authenticated API):** Connects to the OpenWeatherMap API using credentials loaded securely from `.env` via `python-dotenv`, with explicit HTTP status error handling (`400`, `401`, `404`, `429`, `500+`).
* **`week1/day3_travel_info.py` (Day 3 — Chained CLI Tool):** Interactive command-line tool that accepts user input for any city, queries OpenWeatherMap for live conditions and GPS coordinates (`lat`/`lon`), chains those coordinates into the Open-Meteo Forecast API for elevation and daily precipitation metrics, and saves the combined payload to a local `.json` file.

## Technical Stack
* **Language:** Python 3
* **Libraries:** `requests`, `python-dotenv`

## Setup & Execution

1. **Install dependencies:**
   ```bash
   pip install requests python-dotenv
   ```

2. **Configure environment variables:**
   Create a `.env` file in the root directory:
   ```env
   OPENWEATHER_API_KEY=your_api_key_here
   ```

3. **Run the Day 3 interactive CLI tool:**
   ```bash
   python3 week1/day3_travel_info.py
   ```