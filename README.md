# Kimnovix AI & Client Operations Portfolio

API-powered Python command-line tools, AI automated workflows, full-stack web applications, and local file automation scripts built for field operations and enterprise integration in Kenya.

## Live Deployed Applications (Render Cloud)

### 1. SME Customer Complaint Responder AI (Week 4 Capstone)
- **Live Demo:** https://kimnovix-complaint-responder.onrender.com
- **Overview:** A web application that turns heated customer complaints into polite, de-escalated reply drafts in under 5 seconds. Built for Kenyan SMEs (couriers, retail shops, Airbnbs) that handle high volumes of WhatsApp/email inquiries daily. Users paste a complaint, click **Generate Reply**, and receive a ready-to-send response that acknowledges the issue and offers a clear next step without blaming or over-promising. Built with Python, Flask, the Anthropic Claude API (`claude-haiku-4-5-20251001`), and asynchronous JavaScript (`fetch`).

### 2. Kiambu Poultry Farm: Live Egg Production Tracker (Days 18 & 19)
- **Live Demo:** https://kimnovix-egg-tracker.onrender.com
- **REST API Endpoint (`GET` / `POST`):** `https://kimnovix-egg-tracker.onrender.com/api/eggs`

*Note: Both apps run on Render's free tier. The first page load after inactivity may take 30 to 50 seconds while the container wakes up.*

---

## What Is This Repository?

A progressive suite of practical software tools demonstrating API integrations, prompt engineering, stateful memory, autonomous tool-calling agents, production CLI utilities, cloud-deployed RESTful web applications, and local file automation.

Domains covered:
- **Agriculture & Logistics:** client trackers, real-time weather monitoring (OpenWeatherMap API), an autonomous tea harvest advisory agent, and a cloud-deployed poultry production tracker.
- **Financial & Legal Operations:** dairy co-op payment calculators and an automated file sorter for law firms.
- **Customer Service, Healthcare & Productivity:** Matatu SACCO assistant, Kisumu Pharmacy stateful chatbot, real estate JSON extractor, AI meeting notes summarizer, and the AI complaint responder.
- **Web Applications & Cloud Deployment:** Flask servers under Gunicorn on Render, CORS-enabled JSON endpoints, and asynchronous JavaScript (`fetch`) dashboards.

## Week 1: API Integrations & Automation

- **`week1/day5_client_tool.py` (Capstone):** Interactive CLI that logs client follow-up tasks, enriches each entry with live location weather from OpenWeatherMap, and archives records to `tasks.txt`.
- **`week1/day4_fetch.html`:** Single-page app using JavaScript `fetch()` and `async/await` to display live atmospheric metrics.
- **`week1/day3_travel_info.py` & `week1/day2_weather.py`:** Chained, authenticated API scripts that keep secrets in `.env`.

## Week 3: AI API Integrations (Claude API)

- **`week3/day11_sacco_bot.py`:** Matatu SACCO assistant using strict system prompts, API error handling, and token tracking.
- **`week3/day12_property_parser.py`:** Turns unstructured WhatsApp property inquiries into strictly formatted Python dictionaries using few-shot prompting.
- **`week3/day13_kisumu_pharmacy_bot.py`:** Stateful chatbot with a rolling window (last 10 messages) to manage memory and token limits.
- **`week3/day14_tea_harvest_agent.py`:** Autonomous two-stage function-calling agent that runs local Python weather tools to judge harvest conditions.
- **`week3/day15_meeting_summarizer.py` (Capstone):** Production CLI that converts raw meeting notes into Decisions, Action Items, and Blockers, tracking cost in KES.

## Week 4: Web Applications & Cloud Deployment (Flask + Render)

- **`week4/day16_hardware_balances.py`:** Lightweight Flask server with an HTML frontend and JSON endpoint for customer credit balances.
- **`week4/day17_egg_tracker_api.py`:** RESTful API for a multi-shed poultry operation exposing `POST /api/eggs` and `GET /api/eggs`.
- **`week4/day18_egg_tracker_fullstack.py` & `week4/day20_complaint_responder.py`:** Full-stack browser apps with CORS-enabled endpoints, served by `gunicorn` in production.

## Week 5: Automation & Productivity Tools

- **`week5/day21_file_sorter.py`:** Local productivity script for a busy Nairobi law firm.
  - Sorts a messy downloads folder by extension (`.pdf` to Filings, images to Evidence, `.docx`/`.doc` to Contracts, `.txt`/`.eml` to Correspondence, everything else to Other) and creates missing folders on the fly.
  - Previews every move with a **dry run** before touching a file.
  - **Never overwrites:** name collisions become `scan001 (1).pdf`, `scan001 (2).pdf`, and so on.
  - Skips files locked by other programs (for example a PDF open in Acrobat), skips temporary and partial-download files, logs the failure, and continues.
  - Resolves paths from the script's own location using `pathlib`, so it behaves the same on Windows and Linux regardless of where you launch it.
  - Writes a permanent UTF-8 timestamped audit trail to `sort_log.txt`.

---

## Setup & Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Kimnovix/kimnovix-ai-client-operations.git
   cd kimnovix-ai-client-operations
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   # Windows (PowerShell): .\venv\Scripts\Activate.ps1
   # Linux/macOS:          source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the repository root (never commit it; make sure `.env` is listed in `.gitignore`):
   ```
   ANTHROPIC_API_KEY=your_key_here
   OPENWEATHER_API_KEY=your_key_here
   ```
4. Run any script, for example:
   ```bash
   python week5/day21_file_sorter.py
   ```

---

## Commercial Pricing & Kenyan SME Market Valuation

| Module | Target Client / Sector | Build & Deployment Fee | Monthly Retainer | Valuation & Kenyan SME Fit |
| :--- | :--- | :--- | :--- | :--- |
| **`day16_hardware_balances.py`** | Eldoret Hardware Shop | **KES 15,000** (one-off) | N/A (local LAN) | Priced on the value of recovering unpaid credit accounts and preventing counter revenue leakage. |
| **`day17_egg_tracker_api.py`** | Kiambu Multi-Shed Poultry Farm | **KES 30,000** (one-off) | **KES 5,000 / month** | Build fee covers API setup; retainer covers cloud hosting, daily database backups, and monitoring. |
| **`day18_egg_tracker_fullstack.py`** | Kenyan Agribusinesses & SMEs | **KES 45,000 – 65,000** (one-off) | **KES 6,500 / month** | Full-stack operational dashboard. Ideal for commercial farms, posho mills, dairy coolers, and agro-vets. |
| **`day20_complaint_responder.py`** | Courier Services, Retail, Airbnbs | **KES 35,000** (branded build) | **KES 4,500 / month** | Custom-branded AI app with tailored guardrails. Retainer covers hosting and up to 2,500 AI generations per month. |
| **`day21_file_sorter.py`** | Law Firms, Accountants, Real Estate | **KES 12,000 – 15,000** (one-off) | N/A (local script) | Automates weekly digital filing. Saves a junior clerk or paralegal about 4 hours a week (200 hours a year), paying for itself in the first month. |