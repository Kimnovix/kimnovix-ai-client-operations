# Kimnovix AI & Client Operations Portfolio

API-powered Python command-line tools, AI automated workflows, full-stack web applications, web scrapers, local file automation scripts, and automated email reporting built for field operations and enterprise integration in Kenya.

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

A progressive suite of practical software tools demonstrating API integrations, prompt engineering, stateful memory, autonomous tool-calling agents, production CLI utilities, cloud-deployed RESTful web applications, local file automation, ethical web scraping, and automated email notifications.

Domains covered:
- **Agriculture & Logistics:** client trackers, real-time weather monitoring (OpenWeatherMap API), an autonomous tea harvest advisory agent, and a cloud-deployed poultry production tracker.
- **Financial & Legal Operations:** dairy co-op payment calculators and an automated file sorter for law firms.
- **Customer Service, Healthcare & Productivity:** Matatu SACCO assistant, Kisumu Pharmacy stateful chatbot, real estate JSON extractor, AI meeting notes summarizer, and the AI complaint responder.
- **Retail & Inventory Reporting:** an automated evening sales email that summarises revenue, receipts, top sellers, and restock alerts for shop owners.
- **Market Intelligence & HR:** a polite, robots.txt-aware web scraper that produces Excel-safe competitive listing reports.
- **Web Applications & Cloud Deployment:** Flask servers under Gunicorn on Render, CORS-enabled JSON endpoints, and asynchronous JavaScript (`fetch`) dashboards.

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

## Week 5: Automation & Productivity Tools

- **`week5/day21_file_sorter.py`:** Local productivity script for a busy Nairobi law firm.
  - Sorts a messy downloads folder by extension (`.pdf` to Filings, images to Evidence, `.docx`/`.doc` to Contracts, `.txt`/`.eml` to Correspondence, everything else to Other) and creates missing folders on the fly.
  - Previews every move with a **dry run** before touching a file.
  - **Never overwrites:** name collisions become `scan001 (1).pdf`, `scan001 (2).pdf`, and so on.
  - Skips files locked by other programs (for example a PDF open in Acrobat), skips temporary and partial-download files, logs the failure, and continues.
  - Resolves paths from the script's own location using `pathlib`, so it behaves the same on Windows and Linux regardless of where you launch it.
  - Writes a permanent UTF-8 timestamped audit trail to `sort_log.txt`.
- **`week5/day22_job_market_scraper.py`:** Competitive job-listing scraper for a Nairobi HR consultancy. The demo targets `quotes.toscrape.com`, a public practice site built for scraping, standing in for a job board.
  - Walks up to 3 pages, extracting author/company, skill tags, tag count, summary, detail URL, source page, and a run timestamp.
  - **Polite by design:** reads `robots.txt` and skips disallowed pages, identifies itself with a descriptive User-Agent, pauses between pages, and never follows links off the target site.
  - **Resilient:** one reusable session with automatic retries on temporary errors only (429/5xx/dropped connections), respecting the site's `Retry-After`; duplicate and blank listings are dropped.
  - **Excel-safe:** exports UTF-8 with BOM so Excel shows characters correctly, and neutralises CSV formula injection (cells beginning with `=`, `+`, `-`, `@`).
  - **Windows-safe:** writes via a temp file and, if the report is open in Excel, saves a timestamped copy instead of crashing.
  - Returns a non-zero exit code on failure, so it can run unattended from Windows Task Scheduler or cron.

- **`week5/day23_sales_email_report.py`:** Evening sales email report for a Nairobi retail shop (also fits agro-vets, hardware shops, and wholesale depots). It reads the day's sales CSV (`week5/nairobi_retail_sales.csv`, auto-generated with 12 sample receipts on first run) and emails the owner a branded summary of the four numbers that matter: **total revenue**, **number of receipts**, **top-selling item** (summed across every receipt it appears on), and **low-stock restock flags**.
  - **Two-format email:** a plain-text version for basic phones and a styled HTML version (inline CSS, works in Gmail and Outlook), plus a local `week5/email_report_preview.html` copy you can open in any browser.
  - **Accurate money:** amounts are calculated with `Decimal` (exact shillings and cents), never floating-point, so totals always reconcile with the till.
  - **Clear closing-stock rule:** when an item appears on several receipts, the lowest stock reading of the day is taken as the closing figure (stock only goes down while trading), and the highest restock level is used so alerts fire early. Any conflicting values are listed under **Data Quality Notes** in the email instead of being silently overwritten.
  - **Safe email headers:** recipient addresses are validated, line breaks are stripped from the subject and sender name (blocking header injection), the sender is formatted with `formataddr`, and non-ASCII subjects (for example the em dash) are encoded correctly by `EmailMessage`.
  - **Secure connection:** `smtplib.SMTP_SSL` with `ssl.create_default_context()`, so Gmail's certificate and hostname are verified.
  - **Multiple recipients:** `REPORT_RECIPIENT_EMAIL` accepts a comma-separated list (owner, manager, accountant), or override with `--to`.
  - **Resilient on Kenyan networks:** up to 3 send attempts with a growing pause on timeouts or dropped connections; wrong passwords are not retried. Every attempt is written to `week5/email_log.txt`.
  - **Robust CSV handling:** checks for missing columns up front, tolerates `1,200` or `KES 1200` style numbers, treats differently-cased item names as one product, counts unique receipt IDs (a multi-item receipt counts once), and falls back to `cp1252` for CSVs re-saved by Excel on Windows.
  - **Safe to schedule:** `--dry-run` builds the report without sending, `--csv` points at any day's file, and the script returns exit code `0` (sent), `1` (bad/missing CSV), or `2` (email not sent), which Windows Task Scheduler and cron can act on.

### Legal & Ethical Notes for Scraping

*This is practical guidance, not legal advice. Have a lawyer review any commercial engagement.*
- **Practice target only:** the demo site exists for learning. Before pointing the scraper at a real job board, read its Terms of Service and `robots.txt`. If scraping is prohibited, don't scrape it. Prefer an official API, data feed, or written permission.
- **Public data only:** no logging in, no bypassing paywalls, CAPTCHAs, or rate limits.
- **Be a good guest:** keep the delay between requests, keep volumes small, and run weekly rather than continuously.
- **Personal data:** job ads can contain names, phone numbers, and emails. Under Kenya's **Data Protection Act, 2019**, collecting and processing personal data carries obligations. Collect company-level and role-level information only, and strip or avoid personal contact details.
- **Unauthorised access:** circumventing technical access controls can fall under Kenya's **Computer Misuse and Cybercrimes Act, 2018**. Stay within what a normal visitor can see.
- **Contract it:** each client engagement should name the approved data sources in writing.

### Email Automation Notes (Day 23)

- **Use a Gmail App Password, never your normal password.** Turn on 2-Step Verification on the sending Google account, then create a 16-character App Password and put it in `.env` as `GMAIL_APP_PASSWORD`.
- **Use a dedicated sending account** (for example `shopname.reports@gmail.com`) so a leaked password never exposes the owner's personal inbox. Gmail allows roughly 500 messages a day from a personal account, far more than a daily report needs.
- **Keep reports out of Git:** `week5/email_log.txt` and `week5/email_report_preview.html` contain the shop's sales figures; add both to `.gitignore`.
- **Schedule it:** run at 6:00 PM daily with Windows Task Scheduler (`python week5\day23_sales_email_report.py`) or a Linux cron entry (`0 18 * * * /path/to/venv/bin/python week5/day23_sales_email_report.py`).
- **Customer data:** the report contains sales totals only. If you later add customer names or phone numbers (for example M-Pesa payers), Kenya's **Data Protection Act, 2019** applies; send only to people the owner has authorised.

---

## Setup & Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Kimnovix/kimnovix-ai-client-operations.git
   cd kimnovix-ai-client-operations
   ```
2. Create a virtual environment and install dependencies (includes `requests` and `beautifulsoup4` for the scraper):
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

   # Day 23 sales email report
   GMAIL_ADDRESS=yourshop.reports@gmail.com
   GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
   REPORT_RECIPIENT_EMAIL=owner@example.com, manager@example.com
   SHOP_NAME=Nairobi Retail Shop
   ```
4. Run any script, for example:
   ```bash
   python week5/day21_file_sorter.py
   python week5/day22_job_market_scraper.py
   python week5/day23_sales_email_report.py --dry-run
   ```

---

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

### Running Week 5 Automation Tools
```bash
python week5/day21_file_sorter.py
python week5/day22_job_market_scraper.py

# Day 23: preview first, then send for real
python week5/day23_sales_email_report.py --dry-run
python week5/day23_sales_email_report.py
python week5/day23_sales_email_report.py --csv week5/nairobi_retail_sales.csv --to "owner@example.com, manager@example.com"
```

**Day 23 Sales Email Report Example Output (`--dry-run`, 12 sample receipts):**
```text
======================================================
   NAIROBI RETAIL DAILY SALES EMAIL AUTOMATION        
======================================================
NAIROBI RETAIL SHOP - DAILY SALES SUMMARY (2026-11-12 (06:00 PM))
==============================================================
1. Total Revenue        : KES 31,510.00
2. Total Transactions   : 12 receipt(s) (12 line items)
3. Top-Selling Item     : Brookside Fresh Milk 500ml (40 units | KES 2,600.00)
4. Restock Alerts       : 5 item(s) at or below restock level

URGENT RESTOCK FLAGS:
  - [LOW STOCK] Broadways Sliced Bread 400g: 5 left (restock level 20, short by 15)
  - [LOW STOCK] Hostess Maize Meal 2kg: 18 left (restock level 25, short by 7)
  - [LOW STOCK] Kabras Sugar 2kg: 9 left (restock level 15, short by 6)
  - [LOW STOCK] Kenyatta Charger Bulbs 9W: 4 left (restock level 10, short by 6)
  - [LOW STOCK] Ketepa Pride Tea Leaves 500g: 7 left (restock level 12, short by 5)
------------------------------------------------------
[PREVIEW] Saved HTML email preview to: week5/email_report_preview.html
[DRY RUN] Would send to: owner@example.com, manager@example.com
[DRY RUN] Subject: Nairobi Retail Shop Daily Sales Thu 12 Nov 2026 — KES 31,510 (5 Restock Alerts)
======================================================
```

---

## Commercial Pricing & Kenyan SME Market Valuation

| Module | Target Client / Sector | Build & Deployment Fee | Monthly Retainer | Valuation & Kenyan SME Fit |
| :--- | :--- | :--- | :--- | :--- |
| **`day16_hardware_balances.py`** | Eldoret Hardware Shop | **KES 15,000** (One-off) | N/A (Local LAN execution) | Priced on the business value of recovering unpaid credit accounts and preventing counter revenue leakage. |
| **`day17_egg_tracker_api.py`** | Kiambu Multi-Shed Poultry Farm | **KES 30,000** (One-off) | **KES 5,000 / month** | Build fee covers API setup and shed telemetry validation; monthly retainer covers cloud hosting, automated daily ledger backups, and uptime monitoring. |
| **`day18_egg_tracker_fullstack.py` (Live on Render)** | Kenyan Agribusinesses & High-Frequency SMEs | **KES 45,000 – 65,000** (One-off) | **KES 6,500 / month** | Cloud-deployed full-stack single-page operational dashboard + REST API. Ideal for: **(1) Commercial Poultry & Dairy Farms**, **(2) Posho Mills & Cereal Depots**, **(3) Dairy Collection Coolers & Co-ops**, and **(4) Agro-Vet & Wholesale Distributors**. |
| **`day20_complaint_responder.py` (Branded AI Web App — Live on Render)** | Nairobi & Eldoret Courier Services, E-Commerce Shops, Airbnbs & Restaurants | **KES 35,000** (One-off Branded Build) | **KES 4,500 / month** | Custom-branded version includes company logo, custom domain setup, and a tailored system prompt trained on the client's specific refund, delivery, and escalation policies. Monthly retainer covers cloud hosting and up to 2,500 AI-generated responses per month (actual Claude Haiku token cost is ~KES 0.12 per reply, yielding a >90% gross margin on the retainer). |
| **`day21_file_sorter.py`** | Law Firms, Accountants, Real Estate | **KES 12,000 – 15,000** (one-off) | N/A (local script) | Automates weekly digital filing. Saves a junior clerk or paralegal about 4 hours a week (200 hours a year), paying for itself in the first month. |
| **`day22_job_market_scraper.py`** | Nairobi HR Consultancies & Recruiters | **KES 25,000** (one-off) | **KES 8,000 / month** | Replaces manual weekly copy-paste research of competitor job boards (an estimated 4 to 6 analyst hours a week). Retainer covers the scheduled weekly run, fixing the scraper when a board changes its layout, and delivery of the Excel-ready report. Only for sources the client is permitted to collect from (see Legal & Ethical Notes). |
| **`day23_sales_email_report.py`** | Nairobi Retail Shops, Agro-Vets, Hardware Stores & Wholesale Depots | **KES 18,000** (one-off) | **KES 3,500 / month** | Build fee covers adapting the script to the client's POS or M-Pesa till export, branding the email, Gmail App Password setup, and scheduling the 6:00 PM run on the shop PC. Retainer covers monitoring the daily send log, fixing breakages when the POS export format changes, adding recipients, and tuning restock levels each season. Replaces the owner's nightly phone call or WhatsApp to the shop attendant and catches stock-outs before customers walk to the competitor; one saved stock-out of a fast mover like maize meal or milk covers the monthly retainer. Running cost is near zero (Gmail SMTP is free). |
