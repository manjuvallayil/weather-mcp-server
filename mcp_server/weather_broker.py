"""
Weather adapter module — all Open-Meteo HTTP calls and response parsing.

This is the "broker" layer (analogous to alpaca_broker.py in the reference).
MCP tool functions call these helpers; no raw HTTP calls belong in the MCP server file.

API: Open-Meteo (https://open-meteo.com/) — free, no API key required.
"""

import requests

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO Weather interpretation codes -> human-readable descriptions
_WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


def _weather_description(code: int) -> str:
    return _WMO_CODES.get(code, f"Unknown (code {code})")


def geocode(location: str) -> dict:
    """Resolve a location string to lat/lon via Open-Meteo Geocoding API.

    Args:
        location: City name, e.g. "Chicago", "Auckland, New Zealand"

    Returns:
        dict with: name, country, latitude, longitude, timezone.
        Raises ValueError if location cannot be resolved.
    """
    resp = requests.get(_GEOCODE_URL, params={"name": location, "count": 1, "language": "en"}, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results")
    if not results:
        raise ValueError(f"Could not resolve location: '{location}'. Try a different city name.")

    r = results[0]
    return {
        "name": r.get("name"),
        "country": r.get("country", ""),
        "latitude": r["latitude"],
        "longitude": r["longitude"],
        "timezone": r.get("timezone", "UTC"),
    }


def get_current(latitude: float, longitude: float) -> dict:
    """Fetch current weather conditions from Open-Meteo.

    Returns:
        dict with: temperature_c, feels_like_c, humidity_pct, wind_speed_kmh,
                   wind_direction_deg, conditions, weather_code
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m",
        "wind_speed_unit": "kmh",
    }
    resp = requests.get(_FORECAST_URL, params=params, timeout=10)
    resp.raise_for_status()
    current = resp.json()["current"]

    return {
        "temperature_c": current["temperature_2m"],
        "feels_like_c": current["apparent_temperature"],
        "humidity_pct": current["relative_humidity_2m"],
        "wind_speed_kmh": current["wind_speed_10m"],
        "wind_direction_deg": current["wind_direction_10m"],
        "weather_code": current["weather_code"],
        "conditions": _weather_description(current["weather_code"]),
    }


def get_daily_forecast(latitude: float, longitude: float, days: int = 7) -> list[dict]:
    """Fetch multi-day daily forecast from Open-Meteo.

    Returns:
        List of dicts per day: date, temp_high_c, temp_low_c,
        precipitation_probability_pct, precipitation_sum_mm, conditions, weather_code
    """
    days = max(1, min(days, 16))
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,weather_code",
        "forecast_days": days,
        "wind_speed_unit": "kmh",
    }
    resp = requests.get(_FORECAST_URL, params=params, timeout=10)
    resp.raise_for_status()
    daily = resp.json()["daily"]

    forecasts = []
    for i in range(len(daily["time"])):
        forecasts.append({
            "date": daily["time"][i],
            "temp_high_c": daily["temperature_2m_max"][i],
            "temp_low_c": daily["temperature_2m_min"][i],
            "precipitation_probability_pct": daily["precipitation_probability_max"][i],
            "precipitation_sum_mm": daily["precipitation_sum"][i],
            "weather_code": daily["weather_code"][i],
            "conditions": _weather_description(daily["weather_code"][i]),
        })

    return forecasts
