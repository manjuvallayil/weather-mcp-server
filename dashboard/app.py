"""
Weather MCP Dashboard — shows recent agent queries and tool call results.

A lightweight Flask app that:
1. Accepts POST /log from the MCP server (or agent) to record tool invocations
2. Displays recent queries and predictions in a web UI

Deploy as Databricks App #2 using dashboard/app.yaml.
"""

import os
from datetime import datetime
from collections import deque

from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

# In-memory log of recent queries (last 50)
_query_log = deque(maxlen=50)


@app.route("/", methods=["GET"])
def index():
    return render_template_string(DASHBOARD_HTML, queries=list(_query_log))


@app.route("/log", methods=["POST"])
def log_query():
    """Accept a tool invocation log entry from the MCP server or agent."""
    data = request.json or {}
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tool": data.get("tool", "unknown"),
        "input": data.get("input", {}),
        "result_summary": data.get("result_summary", ""),
        "user_query": data.get("user_query", ""),
    }
    _query_log.appendleft(entry)
    return jsonify({"status": "logged"}), 201


@app.route("/queries", methods=["GET"])
def get_queries():
    """Return recent queries as JSON (for programmatic access)."""
    return jsonify(list(_query_log))


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Weather Agent Dashboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #0f172a; color: #e2e8f0; min-height: 100vh; padding: 2rem; }
  h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
  .subtitle { color: #94a3b8; margin-bottom: 2rem; }
  .empty { color: #64748b; font-style: italic; margin-top: 2rem; }
  .card { background: #1e293b; border: 1px solid #334155; border-radius: 8px;
           padding: 1rem; margin-bottom: 0.8rem; }
  .card .time { font-size: 0.75rem; color: #64748b; }
  .card .tool { display: inline-block; background: #1d4ed8; color: #bfdbfe;
                padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem;
                margin-left: 0.5rem; }
  .card .query { font-size: 0.95rem; color: #f1f5f9; margin: 0.5rem 0; }
  .card .result { font-size: 0.85rem; color: #94a3b8; }
  .refresh { margin-top: 1rem; padding: 0.5rem 1rem; border: 1px solid #334155;
             border-radius: 6px; background: #1e293b; color: #94a3b8; cursor: pointer; }
  .refresh:hover { background: #334155; }
</style>
</head>
<body>
<h1>Weather Agent Dashboard</h1>
<p class="subtitle">Recent agent queries and tool invocations</p>

{% if not queries %}
<p class="empty">No queries logged yet. Use the Weather Agent to generate some activity.</p>
{% else %}
{% for q in queries %}
<div class="card">
  <span class="time">{{ q.timestamp }}</span>
  <span class="tool">{{ q.tool }}</span>
  {% if q.user_query %}
  <p class="query">{{ q.user_query }}</p>
  {% endif %}
  <p class="result">{{ q.result_summary }}</p>
</div>
{% endfor %}
{% endif %}

<button class="refresh" onclick="location.reload()">Refresh</button>
</body>
</html>
"""


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", 8001))
    app.run(debug=True, host=host, port=port)
