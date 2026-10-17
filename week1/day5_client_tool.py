"""
Build Plan
----------
1. The problem: Field consultants and business operators need a fast command-line
   tool to log client follow-up tasks alongside live local weather conditions for
   site visits, saved persistently to a local file.
2. The input: Client name, task description, and optional client city (defaults to Eldoret).
3. The processing: Queries the OpenWeatherMap API (using .env credentials) for live
   temperature and weather conditions at the client's location, formats the action
   summary with a timestamp, and appends each entry to tasks.txt inside a loop.
4. The output: A clean terminal action summary after each entry, a final session
   count, and a persistent tasks.txt log file.

Usage:
    python3 week1/day5_client_tool.py
"""

from datetime import datetime
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY")
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
TASKS_FILE = "week1/tasks.txt"


def get_client_weather(city):
    """Fetch live weather context for the client's location via OpenWeatherMap API."""
    if not API_KEY:
        return "Weather unavailable (No API key configured)"

    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    }

    try:
        response = requests.get(WEATHER_URL, params=params, timeout=8)
        if response.status_code == 200:
            data = response.json()
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            humidity = data["main"]["humidity"]
            return f"{city.title()}: {temp}°C, {desc}, humidity {humidity}%"
        elif response.status_code == 404:
            return f"City '{city}' not found in weather database"
        elif response.status_code == 401:
            return "Weather API key unauthorized (401)"
        else:
            return f"Weather service returned HTTP {response.status_code}"
    except requests.exceptions.RequestException:
        return "Weather offline (Network/DNS error)"


def save_task_to_file(entry_line):
    """Append a formatted task entry to tasks.txt."""
    with open(TASKS_FILE, "a", encoding="utf-8") as file:
        file.write(entry_line + "\n")


def run_client_logger():
    print("==================================================")
    print("     KIMNOVIX CLIENT ACTION & DISPATCH LOGGER     ")
    print("==================================================")
    print("Log client tasks with live site weather telemetry.")
    print("Type 'q' or 'quit' as the client name to exit.\n")

    logged_count = 0

    while True:
        client_name = input("Enter client name (or 'q' to quit): ").strip()

        if client_name.lower() in ("q", "quit", "exit"):
            break

        if not client_name:
            print("[ERROR] Client name cannot be empty. Please try again.\n")
            continue

        task = input("Enter task description: ").strip()
        if not task:
            print("[ERROR] Task description cannot be empty. Please try again.\n")
            continue

        city = input("Enter client city [press Enter for Eldoret]: ").strip() or "Eldoret"

        print("Fetching live site weather...")
        weather_summary = get_client_weather(city)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Format required action summary
        action_summary = f"{client_name}, Task: {task}"
        full_log_entry = f"[{timestamp}] {action_summary} | Site Weather ({weather_summary})"

        save_task_to_file(full_log_entry)
        logged_count += 1

        print("\n--- ACTION SUMMARY LOGGED ---")
        print(action_summary)
        print(f"Site Weather : {weather_summary}")
        print(f"Saved to     : {TASKS_FILE}")
        print("-----------------------------\n")

    print("==================================================")
    print(f"Session complete. Total tasks logged: {logged_count}")
    print(f"All entries archived in: {TASKS_FILE}")
    print("==================================================")


if __name__ == "__main__":
    run_client_logger()