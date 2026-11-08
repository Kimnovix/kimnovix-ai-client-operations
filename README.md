# Kimnovix AI & Client Operations Portfolio

API-powered Python command-line tools, AI automated workflows, and cloud-deployed full-stack web applications built for field operations and enterprise integration in Kenya.

## Live Deployed Applications (Render Cloud)

### 1. SME Customer Complaint Responder AI (Week 4 Capstone)
- **Live Demo:** https://kimnovix-complaint-responder.onrender.com
- **Portfolio Overview:** A web application that turns heated customer complaints into polite, de-escalated reply drafts in under 5 seconds. Built for Kenyan SMEs—including courier services, retail shops, Airbnbs, and restaurants—that handle high volumes of WhatsApp and email inquiries daily. Business owners paste a customer's complaint, click **Generate Reply**, and receive a ready-to-send response that acknowledges the issue and offers a clear next step without blaming or over-promising. Built with Python, Flask, the Anthropic Claude API (`claude-haiku-4-5-20251001`), and asynchronous JavaScript (`fetch`). Deployed on Render under Gunicorn.

### 2. Kiambu Poultry Farm — Live Egg Production Tracker (Day 18 & 19)
- **Live Demo:** https://kimnovix-egg-tracker.onrender.com
- **Live REST API Endpoint (`GET` / `POST`):** `https://kimnovix-egg-tracker.onrender.com/api/eggs`

*(Note: Both live applications are hosted on Render's free tier; initial page load after inactivity may take 30–50 seconds for the container to wake up.)*

---

## What Is This Repository?

This repository contains a progressive suite of practical software tools demonstrating API integrations, prompt engineering, stateful memory, autonomous tool-calling agents, production CLI utilities, and cloud-deployed full-stack RESTful web applications.

The portfolio spans multiple domains, including:
- **Agriculture & Logistics:** Interactive local client trackers, real-time weather monitoring (OpenWeatherMap API), autonomous tea harvest advisory agents, and cloud-deployed poultry production web trackers.
- **Financial Operations:** Dairy co-op payment calculators utilizing dynamic CLI interfaces.
- **Customer Service, Healthcare & Enterprise Productivity:** Matatu SACCO assistants, Kisumu Pharmacy stateful chatbots, Real Estate JSON extractors, an AI Meeting Notes Summarizer, and a live AI Customer Complaint Responder powered by the Anthropic SDK (`claude-haiku-4-5-20251001`).
- **Web Applications & Cloud Deployment:** Production Flask servers running under Gunicorn on Render, CORS-enabled JSON endpoints, and asynchronous JavaScript (`fetch`) dashboards.

## Week 1: API Integrations & Automation

- **`week1/day5_client_tool.py` (Week 1 Capstone Project — Client Action & Dispatch Logger):** An interactive command-line tool that logs client follow-up tasks in a continuous loop, enriches each entry with live location weather from the OpenWeatherMap API, prints a formatted action summary, and archives all records to `week1/tasks.txt`.
- **`week1/day4_fetch.html` (Browser Telemetry Dashboard):** A single-page web application using JavaScript `fetch()` and `async/await` to geocode cities and display live temperature, humidity, pressure, wind speed, elevation, and precipitation outlooks.
- **`week1/day3_travel_info.py` (Chained API CLI Tool):** Chains OpenWeatherMap GPS coordinates (`lat`/`lon`) into the Open-Meteo Forecast API and caches the combined response to a local `.json` file.
- **`week1/day2_weather.py` (Authenticated Weather Script):** Loads API credentials securely from `.env` using `python-dotenv` and handles HTTP `400`, `401`, `404`, `429`, and `500+` errors explicitly.
- **`week1/weather_digest.py` (Public API Baseline):** Fetches and formats real-time Eldoret atmospheric metrics from Open-Meteo.

## Week 3: AI API Integrations

- **`week3/day11_sacco_bot.py`:** An AI-powered command-line assistant using the Anthropic SDK (`claude-haiku-4-5-20251001`). It acts as a Matatu SACCO secretary, using a strict system prompt to answer member queries about balances, meetings, and fees while gracefully handling API errors and token tracking.
- **`week3/day12_property_parser.py`:** An extraction script demonstrating Prompt Engineering. It takes messy, unstructured WhatsApp inquiries and uses few-shot prompting to force Claude into returning strictly formatted JSON. The JSON is then parsed into a Python dictionary.
  - **Extracted Fields & Purpose:**
    - `property_type` & `bedrooms`: Filters inventory matches.
    - `location`: Determines geographic routing.
    - `budget_kes`: Standardizes financial data to raw integers for numerical sorting (e.g., converting "80k" to 80000).
    - `rental_or_sale`: Routes the lead to the correct sales or letting department.
- **`week3/day13_kisumu_pharmacy_bot.py`:** A stateful command-line chatbot demonstrating conversational memory across multiple turns. It enforces a rolling window (retaining the last 10 messages) to manage API token limits and automatically exports the full session history to `week3/chat_log.json` upon exit.
- **`week3/day14_tea_harvest_agent.py`:** A tool-using AI agent demonstrating the two-stage function calling loop. It evaluates field supervisor queries for a Kericho tea estate, autonomously triggers a local Python function (`get_weather_forecast`) to fetch live 6-hour OpenWeatherMap telemetry when harvest conditions are mentioned, and synthesizes an agronomic recommendation against strict temperature, rain, and humidity rules.
- **`week3/day15_meeting_summarizer.py` (Week 3 Capstone Project — AI Meeting Notes Summarizer CLI):** A production command-line tool that converts raw, unstructured meeting notes into three actionable sections: Decisions Made, Action Items with Owners, and Unresolved Questions. Supports direct CLI arguments (`sys.argv`) and interactive input, handles API/network/input errors cleanly, and calculates real-time token costs in KES (~KES 0.15 per summary).

## Week 4: Web Applications & Cloud Deployment (Flask + Gunicorn + Render)

- **`week4/day16_hardware_balances.py`:** A lightweight Flask web server for a local hardware shop. Features an HTML frontend form that submits query parameters to a JSON API endpoint to retrieve customer credit balances. Includes 200, 400, and 404 HTTP status code handling.
- **`week4/day17_egg_tracker_api.py`:** A RESTful Flask API for a multi-shed poultry operation in Kiambu. Exposes `POST /api/eggs` to validate and log daily egg collections per shed (`201 Created` / `400 Bad Request`) and `GET /api/eggs` (`200 OK`) to return the complete production ledger alongside live per-shed subtotals and an overall running total.
- **`week4/day18_egg_tracker_fullstack.py` & `week4/templates/index.html` (Deployed to Render in Day 19):** A full-stack browser application connecting an asynchronous JavaScript (`fetch`) frontend to a CORS-enabled Flask backend (`flask-cors`), served in production via `gunicorn`. Farm managers log daily shed egg counts via a single-page dashboard that chains `POST` and `GET` calls to update running totals, per-shed breakdowns, and the ledger table in place without reloading the page.
- **`week4/day20_complaint_responder.py` & `week4/templates/complaint_responder.html` (Week 4 Capstone — Deployed AI Web App):** A cloud-deployed AI web application that converts raw customer complaints into professional, de-escalated reply drafts. Features one-click scenario testing, asynchronous `POST /api/process` processing via Claude Haiku 4.5, strict system prompt guardrails (polite tone, issue acknowledgment, clear next step, zero blame, zero unauthorized promises), one-click clipboard copy, and live token/KES cost telemetry.

---

## Setup & Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Kimnovix/kimnovix-ai-client-operations.git
   cd kimnovix-ai-client-operations
   ```
2. Install required Python libraries:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root folder with your OpenWeatherMap and Anthropic API keys:
   ```env
   OPENWEATHER_API_KEY=your_openweather_key_here
   ANTHROPIC_API_KEY=your_anthropic_key_here
   ```

## Usage & Examples

### Running Week 1 Tools
```bash
python3 week1/day5_client_tool.py
python3 week1/day3_travel_info.py
python3 week1/day2_weather.py
python3 week1/weather_digest.py
xdg-open week1/day4_fetch.html
```

**Day 5 Client Tool Example Output:**
```text
==================================================
     KIMNOVIX CLIENT ACTION & DISPATCH LOGGER     
==================================================
Log client tasks with live site weather telemetry.
Type 'q' or 'quit' as the client name to exit.

Enter client name (or 'q' to quit): Kamau Auto Spares
Enter task description: Follow up on invoice #014
Enter client city [press Enter for Eldoret]: Nairobi
Fetching live site weather...

--- ACTION SUMMARY LOGGED ---
Kamau Auto Spares, Task: Follow up on invoice #014
Site Weather : Nairobi: 21.4°C, scattered clouds, humidity 64%
Saved to     : week1/tasks.txt
-----------------------------
```

### Running Week 3 AI Tools
```bash
python3 week3/day11_sacco_bot.py
python3 week3/day12_property_parser.py
python3 week3/day13_kisumu_pharmacy_bot.py
python3 week3/day14_tea_harvest_agent.py
python3 week3/day15_meeting_summarizer.py "Eldoret Agro-Tech sync: Approved KES 45,000 budget for sensor housing. Dennis to finalize CAD mounts by Thursday. Joy to contact Nakuru supplier for solar cells by Tuesday. Still unsure if LoRa gateway range covers Section B."
```

**Day 11 SACCO Bot Example Output:**
```text
==========================================
    THIKA MATATU SACCO AI ASSISTANT       
==========================================
Type 'q' or 'quit' to exit.

Member Question: Can I get a loan to buy a new engine?
Drafting response...

SACCO Bot:
I cannot process loan applications for engine purchases here. Please call the main office at 0700 123 456 to discuss asset financing options with our team.
------------------------------------------
Cost: 271 input tokens | 106 output tokens
==========================================
```

**Day 13 Kisumu Pharmacy Bot Example Output:**
```text
==========================================
      KISUMU PHARMACY ASSISTANT BOT       
==========================================
Type 'q', 'quit', or 'exit' to end the session.

Customer: I have a prescription that needs to be filled.
Assistant: We can process your prescription for you. Please bring the original physical prescription along with your patient ID.

Customer: How long will that take?
Assistant: Prescription processing takes between 15 and 30 minutes.
```

**Day 14 Kericho Tea Harvest Agent Example Output:**
```text
==========================================
   KERICHO TEA ESTATE FIELD ASSISTANT     
==========================================
Type 'q', 'quit', or 'exit' to end the session.

Supervisor: Is today a good day for harvesting in Kericho?

[SYSTEM: Executing local tool get_weather_forecast('Kericho')]...
[SYSTEM: Tool returned data -> passing back to AI for synthesis]

AI: Based on the 6-hour forecast for Kericho, conditions are MARGINAL to BAD for harvesting. While temperatures are ideal (18.5°C–20.1°C), light rain is forecasted within the next 6 hours with high humidity (82%). Hold off on deploying harvesting crews or proceed with caution under cover.
```

**Day 15 Meeting Notes Summarizer CLI Example Output:**
```text
======================================================
     KIMNOVIX AI MEETING NOTES SUMMARIZER (v1.0)      
======================================================
Processing CLI argument payload...

1. DECISIONS MADE
- Approved a KES 45,000 budget for sensor housing.

2. ACTION ITEMS & OWNERS
- Dennis -> Finalize CAD mounts (Deadline: Thursday)
- Joy -> Contact Nakuru supplier for solar cells (Deadline: Tuesday)

3. UNRESOLVED QUESTIONS & BLOCKERS
- Whether the LoRa gateway range is sufficient to cover Section B.

------------------------------------------------------
Telemetry : 242 input tokens | 118 output tokens
Est. Cost : KES 0.1079 (claude-haiku-4-5-20251001)
======================================================
```

### Running Week 4 Web Applications (Local & Production)
```bash
# Local development
python3 week4/day16_hardware_balances.py
python3 week4/day17_egg_tracker_api.py
python3 week4/day18_egg_tracker_fullstack.py
python3 week4/day20_complaint_responder.py

# Production WSGI server (Gunicorn)
gunicorn --chdir week4 day18_egg_tracker_fullstack:app
gunicorn --chdir week4 day20_complaint_responder:app
```

**Day 20 AI Complaint Responder Example (`POST /api/process`):**
- **Input Complaint:** *"Hello, I paid for express boda delivery to Kilimani at 10 AM today (Order #409). It is now 3 PM and my client hasn't received the spare parts, and your rider's phone is switched off! What kind of service is this?"*
- **AI Generated Reply Draft:**
```text
Dear Customer,

Thank you for reaching out to us regarding Order #409, and please accept our sincere apologies for the delay with your Kilimani delivery and the difficulty reaching the dispatch line. We completely understand how urgent these spare parts are for your client and how frustrating this delay is.

Our dispatch team is immediately tracing Order #409 and establishing direct contact with the assigned rider on that route. We will call you directly within the next 15 minutes with the exact status of your parcel and the confirmed delivery time to your client.
```

---

## Commercial Pricing & Kenyan SME Market Valuation

| Module | Target Client / Sector | Build & Deployment Fee | Monthly Retainer | Valuation & Kenyan SME Fit |
| :--- | :--- | :--- | :--- | :--- |
| **`day16_hardware_balances.py`** | Eldoret Hardware Shop | **KES 15,000** (One-off) | N/A (Local LAN execution) | Priced on the business value of recovering unpaid credit accounts and preventing counter revenue leakage. |
| **`day17_egg_tracker_api.py`** | Kiambu Multi-Shed Poultry Farm | **KES 30,000** (One-off) | **KES 5,000 / month** | Build fee covers API setup and shed telemetry validation; monthly retainer covers cloud hosting, automated daily ledger backups, and uptime monitoring. |
| **`day18_egg_tracker_fullstack.py` (Live on Render)** | Kenyan Agribusinesses & High-Frequency SMEs | **KES 45,000 – 65,000** (One-off) | **KES 6,500 / month** | Cloud-deployed full-stack single-page operational dashboard + REST API. Ideal for: **(1) Commercial Poultry & Dairy Farms**, **(2) Posho Mills & Cereal Depots**, **(3) Dairy Collection Coolers & Co-ops**, and **(4) Agro-Vet & Wholesale Distributors**. |
| **`day20_complaint_responder.py` (Branded AI Web App — Live on Render)** | Nairobi & Eldoret Courier Services, E-Commerce Shops, Airbnbs & Restaurants | **KES 35,000** (One-off Branded Build) | **KES 4,500 / month** | Custom-branded version includes company logo, custom domain setup, and a tailored system prompt trained on the client's specific refund, delivery, and escalation policies. Monthly retainer covers cloud hosting and up to 2,500 AI-generated responses per month (actual Claude Haiku token cost is ~KES 0.12 per reply, yielding a >90% gross margin on the retainer). |