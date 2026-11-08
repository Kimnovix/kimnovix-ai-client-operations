"""
Day 20 (Week 4 Capstone): Deployed AI Customer Complaint Responder
------------------------------------------------------------------
Full-stack Flask + Anthropic Claude web application. Accepts raw customer
complaints from a browser interface (/api/process) and returns a polite,
de-escalated, ready-to-send response draft without blaming or over-promising.
"""

import os
import anthropic
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)

MODEL_NAME = "claude-haiku-4-5-20251001"
INPUT_COST_PER_M = 1.00
OUTPUT_COST_PER_M = 5.00
USD_TO_KES = 129.79

SYSTEM_PROMPT = """You are a senior customer relations specialist for Kenyan small and medium businesses (couriers, retail shops, Airbnbs, restaurants, and agro-enterprises).
Your task is to take a frustrated customer's complaint message (from WhatsApp, SMS, or email) and write a professional, ready-to-send reply draft.

You MUST follow these strict rules:
1. REPLY POLITELY: Maintain a calm, warm, and respectful Kenyan business tone.
2. ACKNOWLEDGE THE ISSUE: Directly validate the customer's specific frustration so they feel heard.
3. OFFER A CLEAR NEXT STEP: State one practical, immediate action to resolve or investigate the issue (e.g., checking dispatch logs, scheduling a replacement check, or following up via direct call within a set timeframe).
4. NO BLAME: Never blame the customer, third-party riders, traffic, or staff members.
5. NO OVER-PROMISING: Never promise automatic cash refunds, free giveaways, or impossible guarantees that the business owner has not approved.
6. FORMAT: Keep the reply concise (1 to 3 short paragraphs) so it is immediately ready to copy and paste into WhatsApp or email. Output ONLY the reply draft itself, with no preamble."""


def calculate_cost_kes(input_tokens: int, output_tokens: int) -> float:
    """Calculates exact API call cost in Kenyan Shillings (KES)."""
    usd_cost = ((input_tokens / 1_000_000) * INPUT_COST_PER_M) + (
        (output_tokens / 1_000_000) * OUTPUT_COST_PER_M
    )
    return usd_cost * USD_TO_KES


@app.route("/")
def home():
    """Serves the single-page AI Complaint Responder interface."""
    return render_template("complaint_responder.html")


@app.route("/api/process", methods=["POST"])
def process_complaint():
    """Receives a customer complaint in JSON and returns a professional AI reply draft."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body provided."}), 400

    complaint_text = str(data.get("text", "")).strip()
    if not complaint_text:
        return jsonify({"error": "Please paste a customer complaint message before clicking Generate Reply."}), 400

    if len(complaint_text) < 10:
        return jsonify({"error": "Complaint message is too short. Paste the full customer message."}), 400

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({
            "error": "Server configuration error: ANTHROPIC_API_KEY is missing in environment variables."
        }), 500

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=450,
            timeout=30.0,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Draft a professional response to this customer complaint:\n\n{complaint_text}",
                }
            ],
        )

        if not response.content or not response.content[0].text.strip():
            return jsonify({"error": "AI returned an empty response. Please try again."}), 500

        reply_draft = response.content[0].text.strip()
        in_tokens = response.usage.input_tokens
        out_tokens = response.usage.output_tokens
        cost_kes = calculate_cost_kes(in_tokens, out_tokens)

        return jsonify({
            "status": "success",
            "result": reply_draft,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "cost_kes": round(cost_kes, 4),
        }), 200

    except anthropic.AuthenticationError:
        return jsonify({"error": "Invalid ANTHROPIC_API_KEY. Check your Render Environment Variables."}), 401
    except anthropic.RateLimitError:
        return jsonify({"error": "AI rate limit reached. Wait 60 seconds and try again."}), 429
    except anthropic.APITimeoutError:
        return jsonify({"error": "Request timed out after 30 seconds. Please try again."}), 504
    except anthropic.APIConnectionError:
        return jsonify({"error": "Unable to reach Anthropic servers. Check network connectivity."}), 502
    except Exception as e:
        return jsonify({"error": f"Unexpected server error: {str(e)}"}), 500


if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=PORT, debug=False)