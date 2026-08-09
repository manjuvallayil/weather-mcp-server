"""
Weather prediction MCP server.

Exposes weather tools over MCP (Model Context Protocol) so a
Databricks Agent Bricks agent can call them like any other tool:
    - get_current_weather(location)
    - get_forecast(location, days)
    - predict_umbrella_needed(location, date)

These tools are backed by Open-Meteo's free API (no key required),
so no secrets management is needed.

Deploy this as its own Databricks App (same app.yaml + FastMCP entrypoint
pattern documented at
https://docs.databricks.com/aws/en/agents/mcp-tools/custom-mcp), separate
from the dashboard app, so an Agent Bricks agent (or any MCP client) can
register its URL as an external MCP server.

Run locally:
    python weather_mcp_server.py
"""

import os
import logging

from fastmcp import FastMCP

import weather_broker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("weather-mcp-server")

mcp = FastMCP("weather-prediction")


@mcp.tool
def get_current_weather(location: str) -> dict:
    """
    Get current weather conditions for a location.

    Args:
        location: City name, e.g. "Chicago", "Auckland, New Zealand", "London, UK"

    Returns:
        A dict with location name, current temperature (Celsius), feels-like
        temperature, humidity percentage, wind speed (km/h), wind direction,
        and conditions description.
    """
    try:
        geo = weather_broker.geocode(location)
        current = weather_broker.get_current(geo["latitude"], geo["longitude"])
        return {
            "status": "success",
            "location": f"{geo['name']}, {geo['country']}",
            "latitude": geo["latitude"],
            "longitude": geo["longitude"],
            **current,
        }
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception(f"Failed to get current weather for {location}")
        return {"status": "error", "message": f"API error: {str(e)}"}


@mcp.tool
def get_forecast(location: str, days: int = 7) -> dict:
    """
    Get a multi-day weather forecast for a location.

    Args:
        location: City name, e.g. "Austin, TX", "Sydney, Australia"
        days: Number of forecast days (1-16, default 7)

    Returns:
        A dict with the resolved location and a list of daily forecasts,
        each containing: date, high/low temperatures (Celsius), precipitation
        probability (%), total precipitation (mm), and conditions description.
    """
    try:
        geo = weather_broker.geocode(location)
        forecasts = weather_broker.get_daily_forecast(geo["latitude"], geo["longitude"], days)
        return {
            "status": "success",
            "location": f"{geo['name']}, {geo['country']}",
            "days_requested": days,
            "forecast": forecasts,
        }
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception(f"Failed to get forecast for {location}")
        return {"status": "error", "message": f"API error: {str(e)}"}


@mcp.tool
def predict_umbrella_needed(location: str, date: str = "") -> dict:
    """
    Predict whether an umbrella is needed for a specific date.

    Applies threshold logic:
    - Precipitation probability > 40% OR expected rainfall > 2mm = BRING UMBRELLA
    - Precipitation probability 20-40% with some rain expected = MAYBE (be prepared)
    - Otherwise = NO UMBRELLA NEEDED

    Args:
        location: City name, e.g. "New York, NY"
        date: Target date in YYYY-MM-DD format. If empty, uses tomorrow.

    Returns:
        A dict with the recommendation (BRING_UMBRELLA / MAYBE / NOT_NEEDED),
        reasoning text explaining the decision, and the underlying forecast data.
    """
    from datetime import date as date_type, timedelta

    if not date:
        target = date_type.today() + timedelta(days=1)
        date = target.isoformat()

    try:
        geo = weather_broker.geocode(location)
        forecasts = weather_broker.get_daily_forecast(geo["latitude"], geo["longitude"], days=16)
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception(f"Failed to get forecast for {location}")
        return {"status": "error", "message": f"API error: {str(e)}"}

    # Find the matching date
    match = None
    for f in forecasts:
        if f["date"] == date:
            match = f
            break

    if not match:
        return {
            "status": "error",
            "location": f"{geo['name']}, {geo['country']}",
            "date": date,
            "recommendation": "UNAVAILABLE",
            "reasoning": f"No forecast data available for {date}. Open-Meteo provides up to 16 days ahead.",
        }

    precip_prob = match["precipitation_probability_pct"] or 0
    rain_mm = match["precipitation_sum_mm"] or 0

    if precip_prob > 40 or rain_mm > 2.0:
        recommendation = "BRING_UMBRELLA"
        reasoning = (
            f"High chance of rain: {precip_prob}% precipitation probability "
            f"with {rain_mm:.1f}mm expected. Conditions: {match['conditions']}. "
            f"Definitely bring an umbrella."
        )
    elif precip_prob > 20 and rain_mm > 0.5:
        recommendation = "MAYBE"
        reasoning = (
            f"Moderate chance of rain: {precip_prob}% probability "
            f"with {rain_mm:.1f}mm possible. Conditions: {match['conditions']}. "
            f"Consider packing an umbrella just in case."
        )
    else:
        recommendation = "NOT_NEEDED"
        reasoning = (
            f"Low chance of rain: only {precip_prob}% probability "
            f"with {rain_mm:.1f}mm expected. Conditions: {match['conditions']}. "
            f"No umbrella needed."
        )

    return {
        "status": "success",
        "location": f"{geo['name']}, {geo['country']}",
        "date": date,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "forecast_data": {
            "temp_high_c": match["temp_high_c"],
            "temp_low_c": match["temp_low_c"],
            "precipitation_probability_pct": precip_prob,
            "precipitation_sum_mm": rain_mm,
            "conditions": match["conditions"],
        },
    }


if __name__ == "__main__":
    port = int(os.getenv("DATABRICKS_APP_PORT", os.getenv("PORT", 8000)))
    mcp.run(transport="http", host="0.0.0.0", port=port)
