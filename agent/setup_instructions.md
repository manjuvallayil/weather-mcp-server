# Agent Bricks Setup Instructions

## Prerequisites

- The MCP server must be deployed as a Databricks App (see `mcp_server/app.yaml`)
- Note your MCP server's app URL (e.g. `https://weather-mcp-server-<workspace-id>.aws.databricksapps.com`)

## Step 1: Register the MCP Server as an External MCP Tool

1. In your Databricks workspace, navigate to **Machine Learning** > **Agent Bricks** > **Tools**
2. Click **Create Tool** > **External MCP Server**
3. Fill in:
   - **Name**: `weather-mcp-server`
   - **URL**: `https://<your-mcp-server-app-url>/mcp`  (the FastMCP streamable-HTTP endpoint)
   - **Authentication**: None (Open-Meteo needs no API key; the MCP server itself is protected by Databricks App auth)
4. Click **Test Connection** to verify the tools are discovered
5. Save

## Step 2: Create the Agent Bricks Agent

1. Navigate to **Machine Learning** > **Agent Bricks** > **Agents**
2. Click **Create Agent**
3. Configure:
   - **Name**: `weather-prediction-agent`
   - **System Prompt**: Paste the contents of `agent/system_prompt.md`
   - **Tools**: Select `weather-mcp-server` (the external MCP tool registered in Step 1)
   - **Model**: Choose a model (e.g. `databricks-meta-llama-3-1-70b-instruct` or equivalent)
4. Save and test with example queries

## Step 3: Test the Agent

Try these queries in the Agent Bricks playground:

1. "What's the weather like in Chicago right now?"
2. "Will it rain in Austin, TX this weekend? Should I bring an umbrella?"
3. "Give me a 5-day forecast for Auckland, New Zealand"

Verify that:
- The agent calls the appropriate tool(s)
- Responses are grounded in tool results (no hallucinated data)
- Error cases are handled gracefully (e.g. misspelled city names)

## Notes

- The agent uses the MCP server over streamable-HTTP transport
- No secrets are needed — Open-Meteo is free and keyless
- The MCP server's Databricks App URL serves as the tool endpoint
