# Weather Prediction MCP Server + Agent

A weather-prediction MCP server built with FastMCP, backed by the Open-Meteo API, wired to a Databricks Agent Bricks agent for natural-language weather queries. Based on the [Day 3 reference](https://github.com/EcZachly/databricks-lakebase-app-day-3) pattern.

**Live MCP Server**: https://mcp-weather-server-7474645954729443.aws.databricksapps.com/

**GitHub Repo**: https://github.com/manjuvallayil/weather-mcp-server

## Architecture

```
Agent Bricks agent  --(MCP tool calls)-->  mcp_server/weather_mcp_server.py  --(REST)-->  Open-Meteo API
                                                                                          (free, no key)
                                           dashboard/app.py  <--(shows recent agent queries)
```

- `mcp_server/` and `dashboard/` are **two separate Databricks Apps** — one serves MCP tool calls to the agent, the other serves a human-facing dashboard.
- `mcp_server/weather_broker.py` is the adapter: it wraps Open-Meteo's geocoding and forecast APIs. No API key needed.
- `mcp_server/weather_mcp_server.py` wraps `weather_broker.py` with FastMCP `@mcp.tool` decorators and serves them over HTTP — the transport Databricks' MCP client/gateway expects.

## Weather API: Open-Meteo

**Why Open-Meteo?**
- Free, no signup, no API key required — zero secrets management
- Global coverage (not limited to US like NWS)
- Rich data: current conditions, multi-day forecasts, precipitation probability
- ~10,000 calls/day (non-commercial)

## MCP Tools

| Tool | Args | Returns |
|------|------|---------|
| `get_current_weather` | `location` (str) | Current temp, feels-like, humidity, wind, conditions |
| `get_forecast` | `location` (str), `days` (int, 1-16) | Day-by-day forecast: high/low temp, precip %, conditions |
| `predict_umbrella_needed` | `location` (str), `date` (YYYY-MM-DD) | Recommendation (BRING_UMBRELLA / MAYBE / NOT_NEEDED) with reasoning |

### Prediction Logic (predict_umbrella_needed)

This tool goes beyond raw API passthrough — it applies reasoning:
- **BRING_UMBRELLA**: precipitation_probability > 40% OR precipitation_sum > 2.0mm
- **MAYBE**: precipitation_probability 20-40% AND precipitation_sum > 0.5mm
- **NOT_NEEDED**: below both thresholds

## Files

- `mcp_server/weather_mcp_server.py` — FastMCP server exposing 3 weather tools
- `mcp_server/weather_broker.py` — Adapter wrapping Open-Meteo APIs
- `mcp_server/app.yaml` / `mcp_server/requirements.txt` — Databricks App config for MCP server
- `dashboard/app.py` — Flask dashboard (recent agent queries)
- `dashboard/templates/index.html` — Dashboard UI template
- `dashboard/app.yaml` / `dashboard/requirements.txt` — Databricks App config for dashboard
- `agent/system_prompt.md` — Agent system prompt

## Setup

### 1. Deploy the MCP server app

In Databricks: Compute > Apps > Create App
- Source: this repo's `mcp_server/` folder
- Name: e.g. `weather-mcp-server`
- Deploy and copy the app URL

### 2. Register the MCP server as an external MCP

Follow [Connect agents to external MCPs](https://docs.databricks.com/aws/en/agents/mcp-tools/connect-external):

1. Go to **AI Gateway** > **MCPs** > **Add MCP**
2. Paste the MCP server app URL as the endpoint
3. Name it `weather-prediction`
4. Auth: OAuth U2M shared (Databricks App auth)
5. Databricks will introspect and list the 3 tools

### 3. Build the Agent Bricks agent

1. **Agents** > **Create agent**
2. Under **Tools**, add the `weather-prediction` MCP server
3. Paste the system prompt from `agent/system_prompt.md`
4. Choose a model (e.g. `databricks-meta-llama-3-1-70b-instruct`)
5. Test with example queries

### 4. Deploy the dashboard (optional)

Create a second Databricks App pointing at `dashboard/`.

## Example Queries

1. "What's the weather like in Chicago right now?"
2. "Should I bring an umbrella to Austin this weekend?"
3. "Give me a 5-day forecast for Auckland, New Zealand"

## No Secrets Required

Open-Meteo needs no API key. The MCP server is protected by Databricks App workspace authentication. Nothing to configure in secrets.
