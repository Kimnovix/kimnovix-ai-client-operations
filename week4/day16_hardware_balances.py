"""
Day 16: Eldoret Hardware Customer Balance API
---------------------------------------------
A basic Flask web server demonstrating HTML rendering on a root route 
and JSON data retrieval via query parameters on an API route.
"""

from flask import Flask, request, jsonify

app = Flask(__name__)

# Hardcoded customer database (all names in lowercase for easier matching)
customer_balances = {
    "kamau": 4500,
    "njeri": 12000,
    "otieno": 0,
    "wambui": 850,
    "kiprotich": 3400
}

@app.route("/")
def home():
    """Serves the frontend HTML search form."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Eldoret Hardware - Balance Lookup</title>
        <style>
            body { font-family: system-ui, sans-serif; max-width: 400px; margin: 40px auto; padding: 20px; }
            input, button { padding: 10px; margin-top: 10px; width: 100%; box-sizing: border-box; }
            button { background-color: #0056b3; color: white; border: none; cursor: pointer; font-weight: bold; }
            button:hover { background-color: #004494; }
        </style>
    </head>
    <body>
        <h2>Eldoret Hardware Shop</h2>
        <p>Customer Credit Lookup</p>
        <!-- The form submits a GET request to the /api/balance endpoint -->
        <form action="/api/balance" method="GET">
            <label for="name">Customer Name (e.g., Kamau):</label>
            <input type="text" id="name" name="name" required autocomplete="off">
            <button type="submit">Check Balance</button>
        </form>
    </body>
    </html>
    """

@app.route("/api/balance")
def get_balance():
    """API endpoint that accepts a 'name' query parameter and returns JSON."""
    # request.args.get() extracts parameters from the URL (e.g., ?name=kamau)
    name_param = request.args.get("name")
    
    if not name_param:
        return jsonify({"error": "Missing 'name' query parameter."}), 400
        
    clean_name = name_param.strip().lower()
    
    if clean_name in customer_balances:
        return jsonify({
            "status": "success",
            "customer": clean_name.capitalize(),
            "balance_kes": customer_balances[clean_name]
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": f"Customer '{name_param}' not found in the ledger."
        }), 404

if __name__ == "__main__":
    # debug=True automatically reloads the server when you save code changes
    app.run(debug=True, port=5000)