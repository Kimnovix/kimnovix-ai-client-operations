"""
Day 17: Kiambu Poultry Farm Egg Production REST API
---------------------------------------------------
A RESTful Flask API with POST and GET endpoints on a single resource (/api/eggs).
Logs daily egg counts per shed into an in-memory store and computes a live
running total and per-shed breakdown on retrieval.
"""

from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory data store for daily egg collection logs
egg_records = []


@app.route("/api/eggs", methods=["POST"])
def log_egg_production():
    """Accepts a JSON payload (shed, date, count) and appends a new production record."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Invalid or missing JSON body. Ensure Content-Type is application/json."
        }), 400

    required_fields = ["shed", "date", "count"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({
            "status": "error",
            "message": f"Missing required fields: {', '.join(missing_fields)}"
        }), 400

    shed_name = str(data["shed"]).strip()
    log_date = str(data["date"]).strip()
    raw_count = data["count"]

    if not shed_name or not log_date:
        return jsonify({
            "status": "error",
            "message": "Both 'shed' and 'date' must be non-empty strings."
        }), 400

    if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 0:
        return jsonify({
            "status": "error",
            "message": "'count' must be a non-negative integer."
        }), 400

    new_record = {
        "id": len(egg_records) + 1,
        "shed": shed_name,
        "date": log_date,
        "count": raw_count
    }
    egg_records.append(new_record)

    return jsonify({
        "status": "created",
        "record": new_record,
        "running_total": sum(r["count"] for r in egg_records)
    }), 201


@app.route("/api/eggs", methods=["GET"])
def get_egg_production():
    """Returns all logged egg production records, per-shed subtotals, and the overall running total."""
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