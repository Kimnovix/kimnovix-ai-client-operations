# Weather Digest

A Python automation script that fetches real-time atmospheric metrics for Eldoret, Kenya, using the Open-Meteo API.

## What It Does
This script connects to a public weather API, parses the nested JSON response, and extracts specific data points to output a clean terminal digest. 

It tracks:
* Current Temperature
* Relative Humidity
* Surface Pressure
* Wind Speed

## Technical Details
* **Language:** Python 3
* **Libraries used:** `requests`
* **API Endpoint:** Open-Meteo (No API key required)

## How to Run
From the `week1` directory, execute:
```bash
python3 weather_digest.py