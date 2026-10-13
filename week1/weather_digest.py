import requests

# Open-Meteo API endpoint for Eldoret, Kenya
URL = "https://api.open-meteo.com/v1/forecast"
PARAMS = {
    "latitude": 0.5143,
    "longitude": 35.2698,
    "current": ["temperature_2m", "relative_humidity_2m", "surface_pressure", "wind_speed_10m"],
    "timezone": "Africa/Nairobi"
}

def get_weather_report():
    print("Connecting to Open-Meteo API...")
    try:
        response = requests.get(URL, params=PARAMS, timeout=10)
        
        if response.status_code != 200:
            print(f"API Error: Received status code {response.status_code}")
            return

        payload = response.json()
        current = payload.get("current", {})
        units = payload.get("current_units", {})

        temp = current.get("temperature_2m")
        temp_unit = units.get("temperature_2m", "°C")

        humidity = current.get("relative_humidity_2m")
        humidity_unit = units.get("relative_humidity_2m", "%")

        pressure = current.get("surface_pressure")
        pressure_unit = units.get("surface_pressure", "hPa")

        wind = current.get("wind_speed_10m")
        wind_unit = units.get("wind_speed_10m", "km/h")

        timestamp = current.get("time")

        print("==========================================")
        print("     FIELD OPERATIONS: WEATHER DIGEST     ")
        print("==========================================")
        print(f"Location:       Eldoret, Kenya")
        print(f"Timestamp:      {timestamp} (EAT)")
        print(f"Temperature:    {temp}{temp_unit}")
        print(f"Humidity:       {humidity}{humidity_unit}")
        print(f"Pressure:       {pressure} {pressure_unit}")
        print(f"Wind Speed:     {wind} {wind_unit}")
        print("==========================================")

    except requests.exceptions.RequestException as err:
        print(f"Network error encountered: {err}")

if __name__ == "__main__":
    get_weather_report()