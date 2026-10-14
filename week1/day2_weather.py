import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY")
URL = "https://api.openweathermap.org/data/2.5/weather"


def fetch_city_weather(city_name):
    if not API_KEY:
        print("[CONFIG ERROR] OPENWEATHER_API_KEY is missing. Check your .env file.")
        return

    params = {
        "q": city_name,
        "appid": API_KEY,
        "units": "metric"
    }

    try:
        response = requests.get(URL, params=params, timeout=10)
        status = response.status_code

        if status == 200:
            data = response.json()
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            pressure = data["main"]["pressure"]
            condition = data["weather"][0]["description"].title()
            wind_speed = data["wind"]["speed"]

            print("==========================================")
            print(f"   AUTHENTICATED WEATHER REPORT: {city_name.upper()}")
            print("==========================================")
            print(f"Condition:      {condition}")
            print(f"Temperature:    {temp}°C (Feels like {feels_like}°C)")
            print(f"Humidity:       {humidity}%")
            print(f"Pressure:       {pressure} hPa")
            print(f"Wind Speed:     {wind_speed} m/s")
            print("==========================================")

        elif status == 400:
            print("[ERROR 400] Bad Request: Check query parameters.")

        elif status == 401:
            print("[ERROR 401] Unauthorized: API key is invalid or still awaiting activation.")

        elif status == 404:
            print(f"[ERROR 404] Not Found: City '{city_name}' does not exist in the database.")

        elif status == 429:
            print("[ERROR 429] Rate Limit Exceeded: Too many requests. Wait before retrying.")

        elif status >= 500:
            print(f"[ERROR {status}] Server Error: OpenWeatherMap is experiencing an outage.")

        else:
            print(f"[ERROR {status}] Unexpected response: {response.text}")

    except requests.exceptions.RequestException:
        print("[NETWORK ERROR] Connection failed. Check your internet connection or DNS.")


if __name__ == "__main__":
    fetch_city_weather("Eldoret")