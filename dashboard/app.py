"""
Weather dashboard: a small Flask app to view recent weather queries
made by the Agent Bricks agent via the weather MCP server.

Deploy this as its OWN Databricks App (separate from weather_mcp_server.py).

Run locally:
    python app.py
"""

import os
from datetime import datetime
from collections import deque

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# In-memory log of recent weather queries (last 100)
_query_log = deque(maxlen=100)


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.errorhandler(Exception)
def handle_exception(err):
    status_code = getattr(err, "code", 500)
    if not isinstance(status_code, int):
        status_code = 500
    return jsonify({"error": str(err)}), status_code


@app.route("/")
def index():
    return render_template("index.html", queries=list(_query_log))


@app.route("/api/log", methods=["POST"])
def log_query():
    """Accept a tool invocation log entry from the MCP server or agent."""
    data = request.json or {}
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tool": data.get("tool", "unknown"),
        "input": data.get("input", {}),
        "result_summary": data.get("result_summary", ""),
    }
    _query_log.appendleft(entry)
    return jsonify({"status": "logged"}), 201


@app.route("/api/queries")
def get_queries():
    """Return recent queries as JSON."""
    return jsonify(list(_query_log))


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", 8001))
    app.run(debug=True, host=host, port=port)
