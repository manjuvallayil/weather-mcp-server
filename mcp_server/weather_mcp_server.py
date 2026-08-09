"""
Weather MCP Server — exposes weather tools via the Model Context Protocol.

Uses FastMCP with streamable-HTTP transport (same pattern as alpaca_mcp_server.py
in the Day 3 reference). Tool functions are thin wrappers that delegate all
HTTP/parsing work to weather_adapter.py.

Run locally:
    python weather_mcp_server.py

Deploy as a Databricks App using app.yaml.
"""

from fastmcp import FastMCP

import weather_adapter as adapter

mcp = FastMCP(
    "Weather Prediction Server",
    instructions=(
        "This MCP server provides weather data and predictions via Open-Meteo. "
        "Use get_current_weather for real-time conditions, get_forecast for multi-day "
        "outlooks, and predict_umbrella_needed for rain recommendations."
    ),
)


@mcp.tool
def get_current_weather(location: str) -> dict:
    """Get current weather conditions for a location.

    Args:
        location: City name, e.g. "Chicago", "Auckland, New Zealand", "London, UK"

    Returns:
        Dictionary with current temperature (Celsius), feels-like temperature,
        humidity percentage, wind speed (km/h), wind direction, and conditions
        description. Also includes the resolved location name and country.
    """
    geo = adapter.geocode(location)
    current = adapter.get_current(geo["latitude"], geo["longitude"])
    return {
        "location": f"{geo['name']}, {geo['country']}",
        "latitude": geo["latitude"],
        "longitude": geo["longitude"],
        **current,
    }


@mcp.tool
def get_forecast(location: str, days: int = 7) -> dict:
    """Get a multi-day weather forecast for a location.

    Args:
        location: City name, e.g. "Austin, TX", "Sydney, Australia"
        days: Number of forecast days (1-16, default 7)

    Returns:
        Dictionary with the resolved location and a list of daily forecasts,
        each containing: date, high/low temperatures (Celsius), precipitation
        probability (%), total precipitation (mm), and conditions description.
    """
    geo = adapter.geocode(location)
    forecasts = adapter.get_daily_forecast(geo["latitude"], geo["longitude"], days)
    return {
        "location": f"{geo['name']}, {geo['country']}",
        "days_requested": days,
        "forecast": forecasts,
    }


@mcp.tool
def predict_umbrella_needed(location: str, date: str = "") -> dict:
    """Predict whether an umbrella is needed for a specific date.

    Applies threshold logic:
    - Precipitation probability > 40% OR expected rainfall > 2mm = BRING UMBRELLA
    - Precipitation probability 20-40% with some rain expected = MAYBE (be prepared)
    - Otherwise = NO UMBRELLA NEEDED

    Args:
        location: City name, e.g. "New York, NY"
        date: Target date in YYYY-MM-DD format. If empty, uses tomorrow.

    Returns:
        Dictionary with the recommendation (BRING_UMBRELLA / MAYBE / NOT_NEEDED),
        reasoning text, and the underlying forecast data used for the decision.
    """
    from datetime import date as date_type, timedelta

    # Default to tomorrow if no date provided
    if not date:
        target = date_type.today() + timedelta(days=1)
        date = target.isoformat()

    geo = adapter.geocode(location)
    forecasts = adapter.get_daily_forecast(geo["latitude"], geo["longitude"], days=16)

    # Find the matching date
    match = None
    for f in forecasts:
        if f["date"] == date:
            match = f
            break

    if not match:
        return {
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
            f"High chance of rain — {precip_prob}% precipitation probability "
            f"with {rain_mm:.1f}mm expected. Conditions: {match['conditions']}. "
            f"Definitely bring an umbrella."
        )
    elif precip_prob > 20 and rain_mm > 0.5:
        recommendation = "MAYBE"
        reasoning = (
            f"Moderate chance of rain — {precip_prob}% probability "
            f"with {rain_mm:.1f}mm possible. Conditions: {match['conditions']}. "
            f"Consider packing an umbrella just in case."
        )
    else:
        recommendation = "NOT_NEEDED"
        reasoning = (
            f"Low chance of rain — only {precip_prob}% probability "
            f"with {rain_mm:.1f}mm expected. Conditions: {match['conditions']}. "
            f"No umbrella needed."
        )

    return {
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
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
