"""
Field & Travel Weather Intelligence Tool
----------------------------------------
A command-line tool that accepts a city name, chains OpenWeatherMap
and Open-Meteo APIs using geographic coordinates, displays an operational
summary, and saves the combined payload to a local JSON file.

Usage:
    python3 week1/day3_travel_info.py

Requirements:
    pip install requests python-dotenv
    OPENWEATHER_API_KEY configured in a .env file
"""

import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"


def get_current_weather(city):
    """API Call 1: Fetch current weather and GPS coordinates from OpenWeatherMap."""
    if not API_KEY:
        print("[CONFIG ERROR] OPENWEATHER_API_KEY is missing. Check your .env file.")
        return None

    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    }

    try:
        response = requests.get(OPENWEATHER_URL, params=params, timeout=10)
        status = response.status_code

        if status == 200:
            return response.json()
        elif status == 401:
            print("[ERROR 401] Unauthorized: API key is invalid or inactive.")
        elif status == 404:
            print(f"[ERROR 404] City '{city}' not found. Check the spelling and try again.")
        elif status == 429:
            print("[ERROR 429] Rate limit exceeded. Wait before retrying.")
        else:
            print(f"[ERROR {status}] Unexpected error from OpenWeatherMap.")
        return None

    except requests.exceptions.RequestException:
        print("[NETWORK ERROR] Could not reach OpenWeatherMap. Check your internet/DNS.")
        return None


def get_daily_forecast(lat, lon):
    """API Call 2: Use chained lat/lon coordinates to fetch forecast & elevation from Open-Meteo."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "precipitation_probability_max"
        ],
        "timezone": "auto",
        "forecast_days": 1
    }

    try:
        response = requests.get(OPENMETEO_URL, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        print(f"[WARNING] Forecast API returned status {response.status_code}.")
        return None

    except requests.exceptions.RequestException:
        print("[NETWORK WARNING] Could not reach Open-Meteo for supplementary forecast data.")
        return None


def save_to_file(data, filename):
    """Save the combined API dictionary to a formatted local JSON file."""
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
    print(f"\n[SAVED] Full response archived locally to: {filename}")


def run_tool():
    print("==========================================")
    print("   FIELD & TRAVEL WEATHER INTELLIGENCE    ")
    print("==========================================")
    city = input("Enter a city name (e.g., Eldoret, Nairobi): ").strip()

    if not city:
        print("[INPUT ERROR] No city entered. Exiting tool.")
        return

    print(f"\n1. Fetching live weather & coordinates for '{city}'...")
    weather_data = get_current_weather(city)

    if not weather_data:
        return

    # Extract coordinates from API 1 to chain into API 2
    lat = weather_data["coord"]["lat"]
    lon = weather_data["coord"]["lon"]
    country_code = weather_data["sys"].get("country", "N/A")
    resolved_name = weather_data.get("name", city.title())

    print(f"2. Chaining coordinates ({lat}, {lon}) to Open-Meteo Forecast API...")
    forecast_data = get_daily_forecast(lat, lon)

    # Display clean, human-readable output
    print("\n==========================================")
    print(f"   LOCATION: {resolved_name.upper()}, {country_code}")
    print("==========================================")
    print(f"Coordinates   : {lat}, {lon}")
    print(f"Condition     : {weather_data['weather'][0]['description'].title()}")
    print(f"Current Temp  : {weather_data['main']['temp']}°C (Feels like {weather_data['main']['feels_like']}°C)")
    print(f"Humidity      : {weather_data['main']['humidity']}%")
    print(f"Pressure      : {weather_data['main']['pressure']} hPa")
    print(f"Wind Speed    : {weather_data['wind']['speed']} m/s")

    if forecast_data and "daily" in forecast_data:
        daily = forecast_data["daily"]
        elevation = forecast_data.get("elevation", "N/A")
        max_temp = daily["temperature_2m_max"][0]
        min_temp = daily["temperature_2m_min"][0]
        rain_prob = daily["precipitation_probability_max"][0]
        rain_mm = daily["precipitation_sum"][0]

        print("\n--- DAILY OUTLOOK & TERRAIN (CHAINED) ----")
        print(f"Elevation     : {elevation:,.0f} m above sea level" if isinstance(elevation, (int, float)) else f"Elevation     : {elevation}")
        print(f"Today's Range : {min_temp}°C to {max_temp}°C")
        print(f"Rain Chance   : {rain_prob}%")
        print(f"Expected Rain : {rain_mm} mm")
    print("==========================================")

    # Combine both payloads and save locally to JSON
    combined_payload = {
        "query_city": resolved_name,
        "country_code": country_code,
        "coordinates": {"latitude": lat, "longitude": lon},
        "current_weather": weather_data,
        "daily_forecast": forecast_data
    }

    safe_city_name = resolved_name.lower().replace(" ", "_")
    output_filename = f"week1/{safe_city_name}_weather.json"
    save_to_file(combined_payload, output_filename)


if __name__ == "__main__":
    run_tool()