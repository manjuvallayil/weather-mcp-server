# Weather Prediction MCP Server + Agent

A weather-prediction MCP server built with FastMCP, backed by the Open-Meteo API, wired to a Databricks Agent Bricks agent for natural-language weather queries.

## Architecture

```
User (natural language)
        |
        v
┌─────────────────────────────┐
│   Databricks Agent Bricks   │
│   (LLM + system prompt)     │
└──────────────┬──────────────┘
               │ MCP protocol (streamable-HTTP)
               v
┌─────────────────────────────┐
│   MCP Server (FastMCP)      │
│   Databricks App            │
│   weather_mcp_server.py     │
│   ├── get_current_weather   │
│   ├── get_forecast          │
│   └── predict_umbrella      │
└──────────────┬──────────────┘
               │ calls
               v
┌─────────────────────────────┐
│   weather_adapter.py        │
│   (Open-Meteo API client)   │
└──────────────┬──────────────┘
               │ HTTP
               v
┌─────────────────────────────┐
│   Open-Meteo API            │
│   (free, no key)            │
└─────────────────────────────┘

┌─────────────────────────────┐
│   Dashboard App (Flask)     │
│   Databricks App #2         │
│   Shows recent queries      │
└─────────────────────────────┘
```

## Weather API: Open-Meteo

**Why Open-Meteo?**
- Free, no signup, no API key required
- Global coverage (not limited to US like NWS)
- Rich data: current conditions, multi-day forecasts, precipitation probability
- ~10,000 calls/day (non-commercial)
- Zero secrets management complexity

## MCP Tools

| Tool | Purpose | Logic |
|------|---------|-------|
| `get_current_weather(location)` | Real-time conditions | Geocodes location, fetches current temp/humidity/wind/conditions from Open-Meteo |
| `get_forecast(location, days)` | Multi-day outlook | Returns day-by-day forecast with highs, lows, precipitation %, and conditions |
| `predict_umbrella_needed(location, date)` | Rain recommendation | Applies threshold logic: precip > 40% OR rain > 2mm = bring umbrella; 20-40% = maybe; else = not needed |

### Prediction Logic (predict_umbrella_needed)

This tool goes beyond raw API passthrough — it applies reasoning:
- **BRING_UMBRELLA**: precipitation_probability > 40% OR precipitation_sum > 2.0mm
- **MAYBE**: precipitation_probability 20-40% AND precipitation_sum > 0.5mm
- **NOT_NEEDED**: below both thresholds

The response includes the reasoning and underlying data so the agent can explain the recommendation to the user.

## Project Structure

```
weather-mcp-server/
├── mcp_server/
│   ├── weather_mcp_server.py    # FastMCP server with @mcp.tool decorators
│   ├── weather_adapter.py       # Open-Meteo HTTP client (all API logic)
│   ├── app.yaml                 # Databricks App config
│   └── requirements.txt
├── dashboard/
│   ├── app.py                   # Flask UI showing agent query log
│   ├── app.yaml                 # Databricks App config
│   └── requirements.txt
├── agent/
│   ├── system_prompt.md         # Agent system prompt
│   └── setup_instructions.md   # Agent Bricks registration steps
├── screenshots/                 # Example query results
├── README.md
└── .gitignore
```

## Setup Steps

### 1. Deploy the MCP Server

```bash
# In Databricks workspace:
# Create a new App pointing to mcp_server/ folder
# The app.yaml runs: python weather_mcp_server.py
```

The MCP server will be available at:
`https://<app-name>-<workspace-id>.aws.databricksapps.com/mcp`

### 2. Register as External MCP Tool

In Databricks Agent Bricks:
1. Go to **Tools** > **Create Tool** > **External MCP Server**
2. Enter your MCP server app URL + `/mcp`
3. Test the connection (should discover 3 tools)

### 3. Create the Agent

1. Go to **Agents** > **Create Agent**
2. Paste the system prompt from `agent/system_prompt.md`
3. Attach the weather MCP tool
4. Test with example queries

### 4. Deploy the Dashboard (optional)

Create a second Databricks App pointing to the `dashboard/` folder.

## Example Queries

1. **"What's the weather like in Chicago right now?"**
   - Agent calls: `get_current_weather("Chicago")`
   - Returns current temperature, humidity, wind, conditions

2. **"Should I bring an umbrella to Austin this weekend?"**
   - Agent calls: `predict_umbrella_needed("Austin, TX", "2026-08-10")`
   - Returns recommendation with reasoning

3. **"Give me a 5-day forecast for Auckland, New Zealand"**
   - Agent calls: `get_forecast("Auckland, New Zealand", 5)`
   - Returns daily breakdown with highs, lows, precipitation chances

## Authentication

- **Open-Meteo API**: No key needed (free, public)
- **MCP Server**: Protected by Databricks App authentication (workspace users only)
- **No secrets committed to git**

## Known Limitations

- Open-Meteo forecasts are limited to 16 days ahead
- Geocoding uses city names; ambiguous names may resolve to unexpected locations
- Dashboard uses in-memory storage (resets on app restart)
- No severe weather alerts (would need NWS or WeatherAPI.com for that)
