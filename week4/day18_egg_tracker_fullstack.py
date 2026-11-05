"""
Day 18: Full-Stack Poultry Egg Production Tracker (Flask + CORS + Fetch API)
----------------------------------------------------------------------------
Serves an interactive browser dashboard on the root route (/) and exposes
CORS-enabled REST endpoints (/api/eggs) for asynchronous POST and GET operations
without page reloads.
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

app = Flask(__name__)
# Enable Cross-Origin Resource Sharing for browser fetch() requests
CORS(app)

# In-memory data store for daily egg collection logs
egg_records = []


@app.route("/")
def index():
    """Serves the single-page frontend application from week4/templates/index.html."""
    return render_template("index.html")


@app.route("/api/eggs", methods=["POST"])
def log_egg_production():
    """Validates and logs a daily egg collection record from a JSON POST body."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Invalid or missing JSON payload."
        }), 400

    shed_name = str(data.get("shed", "")).strip()
    log_date = str(data.get("date", "")).strip()
    raw_count = data.get("count")

    if not shed_name or not log_date or raw_count is None or raw_count == "":
        return jsonify({
            "status": "error",
            "message": "All fields (shed, date, count) are required."
        }), 400

    try:
        if isinstance(raw_count, bool):
            raise ValueError("Boolean is not a valid count.")
        count_val = int(raw_count)
        if count_val < 0:
            raise ValueError("Negative count.")
    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Egg count must be a non-negative whole number."
        }), 400

    new_record = {
        "id": len(egg_records) + 1,
        "shed": shed_name,
        "date": log_date,
        "count": count_val
    }
    egg_records.append(new_record)

    return jsonify({
        "status": "created",
        "record": new_record,
        "running_total_eggs": sum(r["count"] for r in egg_records)
    }), 201


@app.route("/api/eggs", methods=["GET"])
def get_egg_production():
    """Returns all logged egg records, per-shed subtotals, and the overall running total."""
    running_total = sum(record["count"] for record in egg_records)

    shed_totals = {}
    for record in egg_records:
        shed = record["shed"]
        shed_totals[shed] = shed_totals.get(shed, 0) + record["count"]

    return jsonify({
        "status": "success",
        "total_records": len(egg_records),
        "running_total_eggs": running_total,
        "shed_breakdown": shed_totals,
        "records": egg_records
    }), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)