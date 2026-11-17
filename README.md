# Kimnovix AI & Client Operations Portfolio

API-powered Python command-line tools, AI automated workflows, full-stack web applications, web scrapers, local file automation scripts, automated email reporting, self-healing scheduled jobs, daily stock alerts, and AI document Q&A for contracts built for field operations, veterinary clinics, agribusiness procurement, and enterprise integration in Kenya.

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

A progressive suite of practical software tools demonstrating API integrations, prompt engineering, stateful memory, autonomous tool-calling agents, production CLI utilities, cloud-deployed RESTful web applications, local file automation, ethical web scraping, automated email notifications, and scheduled inventory alerts.

Domains covered:
- **Agriculture & Logistics:** client trackers, real-time weather monitoring (OpenWeatherMap API), an autonomous tea harvest advisory agent, and a cloud-deployed poultry production tracker.
- **Financial & Legal Operations:** dairy co-op payment calculators (`day10_project/`) and an automated file sorter for law firms.
- **Veterinary & Clinical Inventory:** a 7:00 AM dispensary stock alert for a Nairobi pet clinic that flags vaccines, anaesthetics, antibiotics, and surgical consumables below minimum stock and says exactly how many to order.
- **Customer Service, Healthcare & Productivity:** Matatu SACCO assistant, Kisumu Pharmacy stateful chatbot, real estate JSON extractor, AI meeting notes summarizer, and the AI complaint responder.
- **Retail & Inventory Reporting:** an automated evening sales email that summarises revenue, receipts, top sellers, and restock alerts for shop owners.
- **Scheduling & Unattended Automation:** a 6:00 PM job runner for Windows Task Scheduler, cron, or a background loop that retries through power cuts and dropped internet, catches up after the shop PC was off, and never emails the owner twice.
- **Market Intelligence & HR:** a polite, robots.txt-aware web scraper that produces Excel-safe competitive listing reports.
- **Legal, Procurement & Contract Intelligence:** a PDF and Word document Q&A tool that answers questions about supply contracts with page citations, exports a Word Q&A report, and indexes whole folders of PDFs.
- **Web Applications & Cloud Deployment:** Flask servers under Gunicorn on Render, CORS-enabled JSON endpoints, and asynchronous JavaScript (`fetch`) dashboards.

## Week 1: API Integrations & Automation

- **`week1/day5_client_tool.py` (Week 1 Capstone Project — Client Action & Dispatch Logger):** An interactive command-line tool that logs client follow-up tasks in a continuous loop, enriches each entry with live location weather from the OpenWeatherMap API, prints a formatted action summary, and archives all records to `week1/tasks.txt`.
- **`week1/day4_fetch.html` (Browser Telemetry Dashboard):** A single-page web application using JavaScript `fetch()` and `async/await` to geocode cities and display live temperature, humidity, pressure, wind speed, elevation, and precipitation outlooks.
- **`week1/day3_travel_info.py` (Chained API CLI Tool):** Chains OpenWeatherMap GPS coordinates (`lat`/`lon`) into the Open-Meteo Forecast API and caches the combined response to a local `.json` file.
- **`week1/day2_weather.py` (Authenticated Weather Script):** Loads API credentials securely from `.env` using `python-dotenv` and handles HTTP `400`, `401`, `404`, `429`, and `500+` errors explicitly.
- **`week1/weather_digest.py` (Public API Baseline):** Fetches and formats real-time Eldoret atmospheric metrics from Open-Meteo.

## Week 2: Python Foundations Capstone

- **`day10_project/` (Kiambu Dairy Co-op Payment Calculator):** Calculates farmer milk payouts in KES using an externalised rate file (`price.txt`) and defensive input validation. (Week 2's daily practice files in `week2/` are kept local and are not pushed to GitHub.)

## Week 3: AI API Integrations (Anthropic Claude SDK, tagged `v1.0`)

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

- **`week5/day24_scheduled_sales_runner.py`:** Turns the Day 23 report into a hands-off daily job for a shop computer. It runs Day 23 for you and writes one line per run to `week5/run_log.txt`: `YYYY-MM-DD HH:MM:SS | SUCCESS/ERROR/SKIPPED | rows_processed=<N> | <detail>`.
  - **Three ways to run:** a single run (for Windows Task Scheduler or cron), `--daemon` (stays open and uses the `schedule` library), and `--install-task` (registers the Windows task in one command; on Linux it prints the two crontab lines to paste).
  - **Catches up after power cuts:** with `--catch-up`, the job asks "has the latest 6:00 PM report gone out yet?" and only sends if it has not. The Windows task fires at 6:00 PM, retries every 30 minutes for 4 hours, starts late if the PC was off at 6:00 PM (`StartWhenAvailable`), and runs again 3 minutes after the attendant logs in the next morning. However many triggers fire, the owner gets **one** email per day. Late reports are tagged `late_by=14h05m` in the log.
  - **No double runs:** an operating-system file lock (`week5/scheduler.lock`) stops two copies running at once (for example the daemon and the task both firing at 6:00 PM). The lock frees itself if the PC crashes, so there is never a stale lock to delete by hand.
  - **Honest results:** reads Day 23's exit codes (`0` sent, `1` CSV problem, `2` email not sent) and logs the real error line Day 23 printed, not the closing `=====` banner. `rows_processed` comes from Day 23's own CSV parser, so the log count always matches the email.
  - **Patient with slow networks:** a 5-minute default timeout (`--timeout`) leaves room for Day 23's three Gmail attempts, instead of killing a good retry halfway through a send.
  - **Friendly time input:** `--time` accepts `18:00`, `6pm` or `"6:30 PM"` and rejects `25:00` or a bare `6` before anything is scheduled.
  - **Windows-proof task:** registered from an XML definition, so paths with spaces, the working folder, the 261-character `schtasks /TR` limit, and laptop battery rules (it still runs on battery during a KPLC outage) are all handled. It uses `pythonw.exe`, so no black console window pops up for staff to close mid-run.
  - **`--status` health check:** shows when the last email actually went out, how many rows it covered, and the last 5 log lines; returns exit code `1` if nothing has been sent for 26 hours, so it can feed a monitoring alert.

- **`week5/day25_pet_clinic_stock_alert.py` (Week 5 Capstone — Nairobi Pet Clinic Daily Stock Alert):** An automated dispensary watchdog for **Kilimani Vet & Pet Care Clinic (Nairobi)**. Every morning it reads `week5/pet_clinic_inventory.csv` (columns `item name`, `current stock`, `minimum stock`; 12 sample vaccines, anaesthetics, antibiotics, parasite treatments and surgical consumables) and emails a prioritised reorder list.
  - **Clear rules:** an item is flagged only when `current < minimum`. Items exactly **at** minimum are not flagged but appear on a **Watch List** in the email, so procurement sees them coming. A minimum of `0` is never flagged.
  - **Two numbers per item:** **Deficit to Min** (`minimum - current`, the units needed just to reach the minimum) and **Recommended Order**, which tops up to the minimum plus a **25% clinical safety buffer** (rounded up, at least +2 units). Example: minimum 15, current 6 gives a deficit of 9 and an order of 13.
  - **Priority:** `CRITICAL` when an item is out of stock, has 2 or fewer units left, or is at or below one third of its minimum; otherwise `LOW`. CRITICAL items are listed first and the subject line reads `[URGENT RESTOCK]`.
  - **No duplicate emails:** a SHA-256 fingerprint of today's date plus the exact shortage list is saved in `week5/pet_clinic_state.json`. Running it three times in a row sends one email. A *new* shortage later the same day changes the fingerprint and is sent; `--force` resends on purpose.
  - **Once-a-day scheduled task:** `--install-task` registers a Windows task (from XML, using `pythonw.exe`, no console window) that runs at 7:00 AM, retries every 30 minutes for 4 hours, starts late if the PC was off, and runs 3 minutes after login. The task uses `--scheduled`, which sends at most one alert per day and never before the set time. On Linux it prints two crontab lines. `--uninstall-task` removes it (including the older `_7AM` task name).
  - **No overlapping runs:** an operating-system file lock (`week5/pet_clinic_scheduler.lock`, `msvcrt` on Windows, `fcntl` on Linux) stops a manual run and the task from both emailing at the same moment. The lock frees itself if the PC crashes.
  - **Never invents data:** the 12-item sample CSV is only created during `--dry-run`. A real run with a missing stock sheet stops with exit code `1` and a logged error instead of emailing made-up shortages.
  - **Excel-proof CSV reading:** UTF-8 (with or without BOM), then `cp1252`, then `latin-1`; headers like `Item_Name` or `MINIMUM STOCK`; `;` delimiters from regional Excel settings; `1,200`-style numbers; blank `,,` rows ignored; duplicate item names merged conservatively (lowest stock, highest minimum); negative, decimal and text quantities skipped and counted in the email.
  - **Graceful on empty data:** a header-only, blank or 0-byte CSV exits `0` without crashing and without sending, but is logged as a `WARNING`, because an empty stock sheet means the clinic gets no alerts at all.
  - **Audit log:** every run writes one line to `week5/pet_clinic_automation.log` (`YYYY-MM-DD HH:MM:SS | LEVEL | message`). Exit codes: `0` sent/skipped/nothing low, `1` CSV problem, `2` email not sent.
  - **`--self-test`:** 10 automated checks (the 3 mandatory Step 3 checks plus boundaries, Excel files, scheduling, locking and failures). It runs in a temporary folder with a fake mail sender, so it never touches the clinic's real CSV, log or state and never sends an email.

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
- **Schedule it:** run at 6:00 PM daily with Windows Task Scheduler (`python week5\day23_sales_email_report.py`) or a Linux cron entry (`0 18 * * * /path/to/venv/bin/python week5/day23_sales_email_report.py`). For retries, power-cut catch-up and a once-per-day guarantee, schedule the Day 24 runner instead (see below).
- **Customer data:** the report contains sales totals only. If you later add customer names or phone numbers (for example M-Pesa payers), Kenya's **Data Protection Act, 2019** applies; send only to people the owner has authorised.

### Scheduling & Reliability Notes (Day 24)

**3-Step Client Setup Guide (shop computer, Windows 10/11)**

Do this once, signed in as the Windows user the shop attendant normally uses.

1. **Test it by hand.** Open PowerShell in the project folder, activate the environment, and run a preview:
   ```powershell
   .\venv\Scripts\Activate.ps1
   python week5\day24_scheduled_sales_runner.py --dry-run
   ```
   You should see a line ending in `SUCCESS | rows_processed=12 | mode=dry_run_preview ...`. If you see `ERROR`, the message after `msg=` says what to fix (usually a missing `.env` value or CSV column).
2. **Install the 6:00 PM task.**
   ```powershell
   python week5\day24_scheduled_sales_runner.py --install-task
   # different time:  --time "6:30 PM"     different owner email:  --to "owner@shop.co.ke"
   ```
   It prints `[INSTALLED]` with the program and arguments it registered.
3. **Prove it works today.** Fire the task once and check the result:
   ```powershell
   schtasks /Run /TN Kimnovix_Daily_Sales_Report_6PM
   python week5\day24_scheduled_sales_runner.py --status
   ```
   The owner receives the email and `--status` ends with `[OK] Reports are going out on schedule.` To remove it later: `--uninstall-task`.

**What happens on a bad day**

| Situation | What the runner does |
| :--- | :--- |
| Internet down at 6:00 PM | Day 23 tries Gmail 3 times; the task retries every 30 min until 10:00 PM. First success wins, later retries do nothing. |
| PC switched off (or power cut) at 6:00 PM, on again at 8:00 AM | Windows starts the missed run as soon as it can, and the logon trigger runs `--catch-up` 3 minutes after the attendant signs in. Yesterday's report goes out once, tagged `late_by=` in the log. |
| PC asleep at 6:00 PM | Same as above when it wakes (`StartWhenAvailable`). The task never wakes the PC on purpose. |
| Daemon and task both running | The file lock lets one run; the other stops quietly. |
| Run stuck for 5 minutes | Stopped and logged as `ERROR ... timed out`. Check `email_log.txt` to see whether Gmail accepted it. |

**Good to know**
- **Catch-up sends the CSV that is there when it runs.** If the till export overwrites `nairobi_retail_sales.csv` each morning, run catch-up before opening sales, or have the POS export one file per day.
- **Check the PC clock.** Old shop PCs with a flat CMOS battery reset their clock after a power cut, and every schedule then fires at the wrong time. If the date on the taskbar is wrong after an outage, replace the coin battery (about KES 150).
- **Linux:** `--install-task` prints two crontab lines: the on-time run and a `*/30` catch-up line. Paste both with `crontab -e`.
- **Keep runtime files out of Git:** add `week5/run_log.txt`, `week5/scheduler_state.json` and `week5/scheduler.lock` to `.gitignore`.
- **Google Drive-synced Desktop:** the state file is written to a temp file and swapped in with retries, so Drive briefly holding the file does not lose the "last sent" record.
- **Keep the synced folder "Available offline":** in Google Drive for Desktop, never set the project folder to "Online only" (streamed), or a scheduled run on a PC without internet may find placeholder files instead of the real scripts.
- **The task waits for a login:** the task runs as the signed-in shop user and stores no Windows password. If Windows Update restarts the PC overnight, the missed report goes out about 3 minutes after the next login.

**Day 24 Proof of Run (verified 13–14 Nov 2026, Windows 11)**

These are the exact lines from `week5/run_log.txt`, copied verbatim. The log file itself stays out of Git (it is in `.gitignore`), so this block is the public record. The lines contain no sales figures or email addresses.

```text
2026-11-13 19:39:11 | SUCCESS | rows_processed=12 | mode=email_sent trigger=manual exit_code=0 skipped_rows=0 duration=5.7s
2026-11-13 19:40:03 | SUCCESS | rows_processed=12 | mode=email_sent trigger=manual exit_code=0 skipped_rows=0 duration=7.1s
2026-11-13 20:32:42 | SUCCESS | rows_processed=12 | mode=email_sent trigger=scheduled exit_code=0 skipped_rows=0 duration=12.5s
2026-11-13 20:49:07 | SUCCESS | rows_processed=12 | mode=email_sent trigger=scheduled exit_code=0 skipped_rows=0 duration=6.6s
2026-11-14 09:30:09 | SUCCESS | rows_processed=12 | mode=email_sent trigger=scheduled exit_code=0 skipped_rows=0 duration=7.0s
2026-11-14 18:00:09 | SUCCESS | rows_processed=12 | mode=email_sent trigger=scheduled exit_code=0 skipped_rows=0 duration=7.9s
```

What it shows: 6 runs, **6 `SUCCESS`, 0 `ERROR`, 0 `SKIPPED`**. Two manual runs and four scheduled `--catch-up` runs from the Windows task, each processing all 12 receipts with none rejected (`skipped_rows=0`) and each finishing in 6 to 13 seconds. Every line has a matching "sent" entry in the private `email_log.txt`. The first three scheduled runs used test times; the task was then reset to the production time with `--install-task --time 18:00`, and the last line (14 Nov, 6:00 PM) is the first run at that production time.

### Daily Stock Alert Notes (Day 25)

**Week 5 Capstone: One-Page Client Guide (Kilimani Vet & Pet Care Clinic, Nairobi)**

*Written for the Head Veterinarian, Practice Manager and Procurement Officer. No technical knowledge needed.*

**What it does**

Every morning at **7:00 AM**, before the clinic opens, the reception computer checks your dispensary stock sheet (`pet_clinic_inventory.csv`). If any vaccine (DHPPi, Rabies), anaesthetic (Ketamine, Propofol), antibiotic, parasite treatment (Bravecto, NexGard) or surgical consumable (Vicryl sutures, IV catheters, Parvo test kits) has fallen **below** its minimum, the Head Vet and Procurement Officer receive one colour-coded email, the **Dispensary Reorder List**, showing for each item:

1. **Current** stock on the shelf or in the fridge.
2. **Minimum** stock the clinic has agreed to keep.
3. **Deficit to Min:** how many units just to get back to the minimum.
4. **Recommended Order:** how many to actually order, with a 25% safety buffer for emergency cases.
5. **Priority:** red **CRITICAL** (out of stock, 2 or fewer left, or at a third of the minimum or less) or amber **LOW**. Critical items are always at the top.

Items sitting exactly **at** their minimum are listed at the bottom as a **Watch List**: nothing to order yet, but they will be on tomorrow's list after the next use.

**What the clinic does each day (2 minutes)**

- Update the **current stock** column in the stock sheet at closing time, after the day's dispensing. The alert is only as accurate as the sheet: a smoke alarm only works if it has a battery.
- Keep the file name and the three column headings exactly as they are. Save as **CSV**, not as an Excel workbook.
- When a new item is stocked, add a row with its name, current stock and minimum stock.
- Leave the reception PC switched on, or switch it on and log in as usual in the morning.

**What happens on a bad day**

| Situation | What the alert does |
| :--- | :--- |
| Internet or Safaricom data down at 7:00 AM | Tries Gmail 3 times, then the task tries again every 30 minutes until 11:00 AM. You get one email, as soon as the line is back. |
| PC off or a KPLC power cut at 7:00 AM | Runs about 3 minutes after the first person logs in. Still one email that day. |
| Someone also runs it by hand | Only one copy runs at a time, and the same list is never emailed twice in a day. |
| A new shortage appears later the same day and someone runs it again | A fresh email is sent, because the list has changed. |
| Stock sheet missing, empty, or a row has a typo | No made-up alerts. The problem is written to the log; rows with bad numbers are skipped and the email says how many, so they can be fixed. |
| Nothing is below minimum | No email. Silence means all stock is at or above minimum. |

**One-time setup (done by Kimnovix on the reception PC)**

1. Install Python and the tool, and add the clinic's sending Gmail account (with an App Password) and the recipients' addresses to the private `.env` file.
2. Load the clinic's real item list and agreed minimums into `pet_clinic_inventory.csv`, then send a preview (`--dry-run`) and one real test email together with the Head Vet.
3. Switch on the 7:00 AM schedule (`--install-task --time 07:00`) and fire it once (`schtasks /Run /TN Kimnovix_PetClinic_Stock_Alert`) to prove it works.

**What it replaces and why it pays for itself**

- **Replaces** 30 to 45 minutes of manual fridge and shelf counting and reorder list writing every morning, about **15 hours a month** of a veterinary technician's time (roughly **KES 7,500 a month** at KES 500 an hour).
- **Prevents** the costly moments: no rabies vaccine for a walk-in, no ketamine for an emergency spay, no Parvo test kit for a vomiting puppy. Avoiding just two lost vaccination or emergency cases a month covers the **KES 12,000** setup fee within the first month, and the **KES 2,000 a month** support fee is far below the technician time it saves.

**Technical notes**

- **Use a Gmail App Password**, exactly as for Day 23 (see Email Automation Notes). `REPORT_RECIPIENT_EMAIL` takes a comma-separated list, for example `headvet@clinic.co.ke, procurement@clinic.co.ke`.
- **Keep runtime files out of Git:** `week5/pet_clinic_automation.log`, `week5/pet_clinic_stock_preview.html`, `week5/pet_clinic_state.json` (and its `.tmp` swap file) and `week5/pet_clinic_scheduler.lock` are in `.gitignore`. The sample `week5/pet_clinic_inventory.csv` and the script are tracked. For a real client, keep their actual stock sheet out of the public repository.
- **If you change the time,** run `--install-task --time 06:30` again; it replaces the existing task. The task name no longer contains "7AM", because the time can change; `--install-task` and `--uninstall-task` also remove the old `Kimnovix_PetClinic_Stock_Alert_7AM` task if it exists, so the clinic never receives two copies.
- **Controlled drugs:** ketamine is a controlled drug. The tool only reports stock levels; ordering, storage and record-keeping still follow the clinic's controlled-drug register and the regulator's rules.
- **Google Drive-synced Desktop and PC clock:** the same advice as Day 24 applies (keep the folder "Available offline"; replace a flat CMOS battery if the clock resets after power cuts).

**Day 25 Verification (`--self-test`, 14 Nov 2026, Python 3.13)**

```text
====================================================================
   STEP 3 AUTOMATED VERIFICATION SUITE (NAIROBI PET CLINIC)
   Runs in a temp folder: your real CSV, log and state are untouched.
====================================================================
[PASS] Test 1 (Client Data): 12 items checked, 8 low-stock (2 CRITICAL), deficit and +25% order maths correct
[PASS] Test 2 (Empty Data): header-only, 0-byte and blank-rows CSVs exit 0, no email, WARNING logged
[PASS] Test 3 (3x Consecutive Runs): real pipeline run 3x: 1 email sent, 2 duplicates blocked and logged
[PASS] Test 4 (Min-Stock Boundaries): == minimum not flagged (watch list), minimum 0, out of stock, duplicates, bad rows, 1,200 parsing
[PASS] Test 5 (Windows/Excel CSVs): cp1252 accents, Item_Name headers, ';' delimiter, wrong columns, HTML escaping
[PASS] Test 6 (New Shortage + --force): new shortage resends, identical state does not, --force overrides
[PASS] Test 7 (Scheduled Once-a-Day): waits until 07:00, catches up if PC was off, once per day, next day sends
[PASS] Test 8 (Overlap Lock): second run steps aside while one holds the lock; lock released afterwards
[PASS] Test 9 (Failure Handling): missing sheet exits 1 without fake data; failed send exits 2 and is retried
[PASS] Test 10 (--time Parsing): 7:00 / 7am / 6:30 PM accepted, 25:00 and '7' rejected
====================================================================
   ALL 10 CHECKS PASSED (including the 3 Step 3 mandatory checks)
====================================================================
```

What it shows: the three mandatory Step 3 checks pass against the **real** pipeline, not just helper functions. Test 1 is the client data (12 items, 8 below minimum). Test 2 is empty data (no crash, no email). Test 3 runs the full pipeline three times in a row and proves exactly one email goes out, with the two repeats logged as `SKIPPED - Duplicate`.

**Day 25 Live Proof of Run (verified 14–15 Nov 2026, Windows 11)**

These are the exact lines from `week5/pet_clinic_automation.log`, copied verbatim. The log itself stays out of Git (it is in `.gitignore`), so this block is the public record. The lines contain no stock figures or email addresses.

```text
2026-11-14 21:31:40 | INFO | OK - Dry run processed 12 items (8 below minimum)
2026-11-14 21:33:03 | INFO | OK - Sent stock alert to 1 recipient(s)
2026-11-14 21:33:03 | INFO | OK - Processed 12 items (8 flagged, 2 critical, skipped_rows=0, trigger=manual)
2026-11-15 09:20:02 | INFO | OK - Sent stock alert to 1 recipient(s)
2026-11-15 09:20:02 | INFO | OK - Processed 12 items (8 flagged, 2 critical, skipped_rows=0, trigger=scheduled)
```

What it shows: a dry run, then a manual live send on 14 Nov. The last two lines are the real-world **power-off catch-up test**: the laptop was switched off at the 7:00 AM scheduled time on Sunday 15 Nov. When Windows was booted at about 9:20 AM, the `Kimnovix_PetClinic_Stock_Alert` task started by itself with nobody clicking anything (`trigger=scheduled`) and delivered the morning's alert: 12 items checked, 8 below minimum, 2 CRITICAL, no rows rejected. That proves unattended recovery from a missed 7:00 AM run, which is exactly what happens when a clinic PC is switched on late or after a KPLC outage. `week5/pet_clinic_state.json` recorded the send for 15 Nov, so any later scheduled retry that day sends nothing.

## Week 6: Advanced AI Applications

- **`week6/day26_document_qa.py` (Day 26: Working with Documents, Document Q&A & Contract Intelligence Tool):** Ask plain-English questions about a PDF or Word contract and get answers from Claude (`claude-haiku-4-5-20251001`) with a page citation for every fact, date, party and KES amount.
  - **Step 1 & 2, extraction (`pypdf`, `python-docx`):** reads text page by page from `.pdf` files and in reading order (paragraphs and tables) from `.docx` files. Detects password-protected PDFs (with a clear "ask the client for an unlocked copy" message), damaged files, and scanned image pages that have no text and need OCR; a partly scanned contract still loads and the tool lists which pages it cannot see.
  - **Self-contained sample:** `generate_sample_contract_pdf()` builds a realistic 2-page Kenyan agribusiness contract in pure Python, `week6/sample_feed_supply_contract.pdf` (Rift Valley Livestock Feeds Ltd supplying Nova Swine Breeding & Production Unit, Eldoret: sow, weaner and boar feed at KES 1,428,000 a month, KEBS aflatoxin limits, Tuesday deliveries with wheel-dip biosecurity, Net 30 payment, KES 15,000/day late-delivery penalty, arbitration in Eldoret). The file is byte-for-byte identical every time it is generated, so it never shows up as a change in Git.
  - **Chunking and retrieval:** splits long documents into overlapping, page-tagged chunks that end on a line or sentence and never start mid-word, then sends Claude only the best-matching chunks for a specific question. **Broad questions** ("Summarize this contract", "What are the key terms / risks?") get the **whole document** when it fits (up to about 60,000 characters, roughly 40 pages), or an even spread from first to last page when it does not, and Claude is told when it is reading a sample.
  - **Step 3, grounded answers:** strict rules: cite `[Page X]` for every fact (`[Section X]` for Word files, which have no fixed pages), say "Not stated in the provided document" instead of guessing, and treat the document's text as data, never as instructions. Answers that hit the length limit are marked as cut short. Every answer prints live token and KES cost telemetry.
  - **Reliable API handling:** the Claude client retries rate limits, overloads and dropped connections automatically; if one question still fails, it is recorded as "Not answered" and the remaining questions carry on. A bad API key or wrong model id stops the run with a clear message, and the answers already paid for are still exported.
  - **Step 4, Word report (`--export-docx`):** writes `week6/contract_qa_report.docx` with a summary table, the full transcript, the estimated AI cost and a "not legal advice" note. If the previous report is still open in Word (Windows locks it), the new one is saved as `contract_qa_report_YYYYMMDD_HHMMSS.docx` instead of crashing and losing the answers.
  - **Step 5, batch folder index (`--batch-index <folder>`):** indexes every PDF in a folder (`.pdf` and `.PDF`, on Windows and Linux) into `week6/document_index.csv` with `file`, `pages`, `chars`, `preview`. Damaged or locked PDFs get an `ERROR:` row instead of stopping the batch, scanned files are flagged "need OCR", and cells starting with `=`, `+`, `-` or `@` are neutralised so a malicious file name cannot run an Excel formula. If the CSV is open in Excel, a timestamped copy is written.
  - **Modes:** `-q "..."` (repeatable), interactive `Ask Document >` loop (Ctrl+C keeps the answers so far), offline `--dry-run` (keyword extract or section outline, no API cost), and an **11-check** `--self-test` that runs in a temporary folder.

### Document Q&A Notes (Day 26)

**Who it is for:** agribusiness procurement officers, farm managers, SACCO and co-op boards, small law firms and county tender committees who receive 10 to 60-page supply contracts, tenders and lease agreements and need answers like "What is the late-delivery penalty?" or "When can we terminate?" in seconds, with the page to check.

**What it costs to run:** about **KES 0.30 to 0.60 per question** on a 2 to 5-page contract, and about **KES 2 to 3** for a "Summarize this contract" on a 40-page contract (Claude Haiku 4.5 at $1 / $5 per million input / output tokens, KES 129.50 to the dollar). The exact cost of every answer is printed and written to the log.

**Technical notes**

- **Requirements:** `pypdf` and `python-docx` (both in `requirements.txt`). Some bank and government PDFs use AES encryption; if the tool asks for it, run `pip install cryptography`.
- **No `temperature` setting:** the current Anthropic SDK and API version no longer accept `temperature`, so the tool does not send it. Consistent, repeatable answers come from the strict rules instead: answer only from the document excerpts, cite every fact, and say "Not stated in the provided document" rather than guess.
- **Keep runtime outputs out of Git:** `week6/document_qa.log`, `week6/contract_qa_report*.docx`, `week6/document_index*.csv`, `week6/*.tmp` and Word/Excel `~$` lock files are in `.gitignore`. The script and the sample contract PDF are tracked. Real client contracts must never go into the public repository; keep them in a separate folder outside the repo and pass them with `--file`.
- **Scanned contracts:** a photocopied contract has no text layer. The tool says so instead of answering from nothing. OCR it first (for example with Microsoft Lens or Adobe Scan on a phone, saved as a searchable PDF), then run it again.
- **Not legal advice:** the answers summarise what the document says. For disputed or high-value terms, the client confirms against the signed original with their advocate. The Word report carries this note.

**Day 26 Verification (`--self-test`, 17 Nov 2026, Python 3.13)**

```text
====================================================================
   DAY 26 DOCUMENT Q&A - AUTOMATED SELF-TEST SUITE
====================================================================
[PASS] Check 1 (PDF Extraction): Extracted 2 pages cleanly via pypdf.
[PASS] Check 2 (Chunking): Split 2 pages into 8 page-tagged chunks.
[PASS] Check 3 (Chunk Retrieval & Q&A): Retrieved payment & penalty clauses.
[PASS] Check 4 (Word .docx Report): Created & verified .docx Q&A report.
[PASS] Check 5 (Batch PDF Indexer): 3 files indexed (incl. .PDF and a broken file) to UTF-8-SIG CSV.
[PASS] Check 6 (Broad Questions): 'Summarize' covers both pages (whole doc, or even sample if too long).
[PASS] Check 7 (Excel Safety): '=' '+' '-' '@' cells are prefixed with an apostrophe.
[PASS] Check 8 (Chunk Boundaries): no-space text, oversized overlap and blank pages all terminate.
[PASS] Check 9 (Windows File Lock): report open in Word -> saved as a timestamped copy.
[PASS] Check 10 (Encrypted PDF): password-protected PDF gives a clear message.
[PASS] Check 11 (API Errors): failed question recorded, next one answered, KES 0.2590 costed.
====================================================================
   ALL 11 DAY 26 CHECKS PASSED (11/11)
====================================================================
```

What it shows: the five core checks (extraction, chunking, retrieval, Word report, batch index) plus six edge-case checks: broad "Summarize" questions read the whole contract, Excel formula injection is blocked, the chunker cannot loop forever, a report left open in Word is saved under a new name, a password-protected PDF gives a clear message, and one failed API call does not lose the other answers.

---

## Setup & Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Kimnovix/kimnovix-ai-client-operations.git
   cd kimnovix-ai-client-operations
   ```
2. Create a virtual environment and install dependencies (includes `requests` and `beautifulsoup4` for the scraper, and `pypdf` and `python-docx` for the Day 26 document tool):
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

   # Day 23 sales email report (Day 24 and Day 25 use the same Gmail settings)
   GMAIL_ADDRESS=yourshop.reports@gmail.com
   GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
   REPORT_RECIPIENT_EMAIL=owner@example.com, manager@example.com
   SHOP_NAME=Nairobi Retail Shop
   ```
   For a client install of Day 25, `REPORT_RECIPIENT_EMAIL` is the clinic's Head Vet and Procurement Officer (or pass `--to`).
4. Run any script, for example:
   ```bash
   python week5/day21_file_sorter.py
   python week5/day22_job_market_scraper.py
   python week5/day23_sales_email_report.py --dry-run
   python week5/day24_scheduled_sales_runner.py --dry-run
   python week5/day25_pet_clinic_stock_alert.py --self-test
   python week5/day25_pet_clinic_stock_alert.py --dry-run
   python week6/day26_document_qa.py --self-test
   python week6/day26_document_qa.py --dry-run
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

```bash
# Day 24: run once, check health, or keep it scheduled
python week5/day24_scheduled_sales_runner.py --dry-run
python week5/day24_scheduled_sales_runner.py --catch-up          # sends only if today's report has not gone out
python week5/day24_scheduled_sales_runner.py --status
python week5/day24_scheduled_sales_runner.py --daemon --time 6pm
python week5/day24_scheduled_sales_runner.py --install-task      # Windows task / Linux crontab lines
```

```bash
# Day 25: test, preview, send, then schedule
python week5/day25_pet_clinic_stock_alert.py --self-test         # 10 checks in a temp folder, sends nothing
python week5/day25_pet_clinic_stock_alert.py --dry-run           # preview; creates the 12-item sample CSV if missing
python week5/day25_pet_clinic_stock_alert.py                     # real run: emails only if something is below minimum
python week5/day25_pet_clinic_stock_alert.py --to "headvet@example.com, procurement@example.com"
python week5/day25_pet_clinic_stock_alert.py --force             # resend today's alert on purpose
python week5/day25_pet_clinic_stock_alert.py --install-task --time 07:00
python week5/day25_pet_clinic_stock_alert.py --uninstall-task
python week5/day25_pet_clinic_stock_alert.py --daemon --time 7am # alternative: keep a window open
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


**Day 24 Scheduled Runner Example `week5/run_log.txt`:**
```text
2026-11-12 18:00:04 | ERROR | rows_processed=12 | mode=email_not_sent trigger=scheduled exit_code=2 msg=[ERROR] Could not send email after 3 attempts. Preview saved at 'week5\email_report_preview.html'.
2026-11-12 18:30:03 | SUCCESS | rows_processed=12 | mode=email_sent trigger=scheduled exit_code=0 skipped_rows=0 duration=3.4s late_by=0h30m
2026-11-14 08:03:12 | SUCCESS | rows_processed=12 | mode=email_sent trigger=scheduled exit_code=0 skipped_rows=0 duration=2.9s late_by=14h03m
```
*(Line 1: Safaricom data was down at 6 PM. Line 2: the 6:30 PM retry delivered it. Line 3: the PC was off on the 13th at 6 PM; the report went out once when the attendant logged in next morning.)*

**Day 25 Pet Clinic Stock Alert Example Output (`--dry-run`, 12 sample items):**
```text
KILIMANI VET & PET CARE CLINIC - DAILY DISPENSARY STOCK ALERT
Generated: 2026-11-14 (06:07 PM)
====================================================================
Total Items Audited    : 12
Items Below Minimum    : 8 (2 CRITICAL)
Items At/Above Minimum : 4

ITEMS BELOW MINIMUM STOCK (PROCUREMENT ACTION REQUIRED):
--------------------------------------------------------------------
 1. [CRITICAL] Canine Parvovirus Rapid Ag Test Kits
    Current Stock: 3 | Minimum: 10 | Deficit to Min: +7 | Recommended Order: +10
 2. [CRITICAL] Ketamine HCl 100mg/ml Injectable (Vials)
    Current Stock: 2 | Minimum: 6 | Deficit to Min: +4 | Recommended Order: +6
 3. [LOW] Amoxicillin-Clavulanate 250mg (Tablets)
    Current Stock: 45 | Minimum: 100 | Deficit to Min: +55 | Recommended Order: +80
 4. [LOW] IV Catheters 22G Blue (Units)
    Current Stock: 14 | Minimum: 30 | Deficit to Min: +16 | Recommended Order: +24
 5. [LOW] Nobivac DHPPi Canine Vaccine (Doses)
    Current Stock: 6 | Minimum: 15 | Deficit to Min: +9 | Recommended Order: +13
 6. [LOW] Vicryl 2-0 Absorbable Sutures (Packs)
    Current Stock: 5 | Minimum: 12 | Deficit to Min: +7 | Recommended Order: +10
 7. [LOW] NexGard Spectra Small Dog (Packs)
    Current Stock: 4 | Minimum: 10 | Deficit to Min: +6 | Recommended Order: +9
 8. [LOW] Meloxicam Oral Suspension 15ml (Bottles)
    Current Stock: 3 | Minimum: 8 | Deficit to Min: +5 | Recommended Order: +7

Deficit to Min = units needed to reach the minimum. Recommended Order adds a 25% clinical safety buffer (at least +2 units).
--------------------------------------------------------------------
[PREVIEW] Saved HTML preview to: week5/pet_clinic_stock_preview.html
[DRY RUN] Email dispatch skipped.
```

**Day 25 Example `week5/pet_clinic_automation.log` (3 runs in a row, then a new shortage):**
```text
2026-11-16 07:00:05 | INFO | OK - Sent stock alert to 2 recipient(s)
2026-11-16 07:00:05 | INFO | OK - Processed 12 items (8 flagged, 2 critical, skipped_rows=0, trigger=scheduled)
2026-11-16 07:02:11 | INFO | SKIPPED - Duplicate prevented (alert already sent today for the same 8 low-stock items)
2026-11-16 07:02:40 | INFO | SKIPPED - Duplicate prevented (alert already sent today for the same 8 low-stock items)
2026-11-16 14:15:22 | INFO | OK - Sent stock alert to 2 recipient(s)
2026-11-16 14:15:22 | INFO | OK - Processed 12 items (9 flagged, 2 critical, skipped_rows=0, trigger=manual)
```
*(Lines 3 and 4: two manual re-runs with the same stock, blocked. Lines 5 and 6: an afternoon manual run after Propofol dropped below minimum, so the list changed and a fresh alert went out.)*

### Running Week 6 Document Q&A
```bash
# Day 26: test, preview offline, then ask Claude
python week6/day26_document_qa.py --self-test                     # 11 checks in a temp folder, no API cost
python week6/day26_document_qa.py --dry-run                       # creates the sample contract PDF if missing
python week6/day26_document_qa.py -q "What are the payment terms and the late delivery penalty?"
python week6/day26_document_qa.py -q "Summarize this contract" -q "When can either party terminate?" --export-docx
python week6/day26_document_qa.py --file "C:/Clients/Tenders/county_feed_tender.pdf"   # interactive: type 'exit' to finish
python week6/day26_document_qa.py --file contract.docx -q "Who signs for the buyer?"     # Word files cite [Section X]
python week6/day26_document_qa.py --batch-index week6             # every PDF in the folder -> week6/document_index.csv
```

**Day 26 Document Q&A Example Output (`--dry-run`, sample feed supply contract):**
```text
====================================================================
DOCUMENT LOADED : sample_feed_supply_contract.pdf
Pages Extracted : 2 | Total Characters: 2,686 | Chunks: 4
====================================================================

Q: Who are the contracting parties, what products are supplied, and what is the monthly KES value?
--------------------------------------------------------------------
Offline Dry-Run Extractive Match:
- [Page 1] COMMERCIAL LIVESTOCK FEED SUPPLY AGREEMENT (REF: RVF-2026-089)
- [Page 1] 1. CONTRACTING PARTIES
- [Page 1] 2. PRODUCT SPECIFICATIONS & MONTHLY VOLUMES
- [Page 1] at KES 3,450 per bag (Total: KES 621,000 / month).
- [Page 1] month at KES 4,100 per bag (Total: KES 492,000 / month).
- [Page 1] month at KES 3,150 per bag (Total: KES 315,000 / month).
- [Page 1] Total Contract Monthly Value: KES 1,428,000 (Inclusive of transport).
- [Page 2] 1.5% per month (simple interest) on the overdue KES balance.

[Dry-run] Chunks used: 4/4 (whole document)
--------------------------------------------------------------------

Q: What are the payment terms, delivery schedule, biosecurity rules, and penalties?
--------------------------------------------------------------------
Offline Dry-Run Extractive Match:
- [Page 2] 4. DELIVERY SCHEDULE & BIOSECURITY PROTOCOL
- [Page 2] Deliveries shall occur every Tuesday by 09:00 AM EAT at the Buyer’s
- [Page 2] designated perimeter feed store. Delivery trucks must undergo wheel-dip
- [Page 2] 5. PAYMENT TERMS & BANKING DETAILS
- [Page 2] Payment Terms: Net 30 days from the date of signed Goods Received Note (GRN).
- [Page 2] Late Payment Penalty: Unpaid invoices past 30 days attract a late fee of
- [Page 2] 6. LATE DELIVERY PENALTIES & EMERGENCY SUBSTITUTION
- [Page 2] If the Supplier fails to deliver within 24 hours of the scheduled Tuesday

[Dry-run] Chunks used: 4/4 (whole document)
--------------------------------------------------------------------

Q: Summarize this contract
--------------------------------------------------------------------
Offline Dry-Run Outline (section headings):
- [Page 1] 1. CONTRACTING PARTIES
- [Page 1] 2. PRODUCT SPECIFICATIONS & MONTHLY VOLUMES
- [Page 1] 3. QUALITY ASSURANCE & AFLATOXIN LIMITS
- [Page 2] 4. DELIVERY SCHEDULE & BIOSECURITY PROTOCOL
- [Page 2] 5. PAYMENT TERMS & BANKING DETAILS
- [Page 2] 6. LATE DELIVERY PENALTIES & EMERGENCY SUBSTITUTION
- [Page 2] 7. TERMINATION & DISPUTE RESOLUTION

[Dry-run] Chunks used: 4/4 (whole document)
--------------------------------------------------------------------
```
*(Dry-run answers are a simple offline keyword extract so the pipeline can be checked for free. A live run sends the same chunks to Claude and returns a written answer with `[Page X]` citations plus a `[Telemetry]` line with tokens and KES cost.)*

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
| **`day24_scheduled_sales_runner.py`** | Any Day 23 client: Retail Shops, Agro-Vets, Hardware Stores, Wholesale Depots | **KES 8,000** (add-on to Day 23) or **KES 24,000** bundled with Day 23 | **+KES 1,500 / month** on the Day 23 retainer | The difference between a script and a service. Covers installing the self-healing 6:00 PM task on the shop PC, a test send with the owner, and monthly `--status` checks so a silent failure is caught within a day, not a week. The catch-up and retry logic protects the report on days with KPLC outages or dropped data bundles, which is exactly when the owner most wants the numbers. |
| **`day25_pet_clinic_stock_alert.py` (Week 5 Capstone)** | Nairobi Veterinary Clinics, Pet Hospitals, Agro-Vets & Pharmacies | **KES 12,000** (one-off setup) or **KES 18,000** (setup + 3 months' support) | **KES 2,000 / month** | 7:00 AM dispensary low-stock alert for vaccines, anaesthetics, antibiotics and surgical consumables. Setup covers loading the clinic's real item list and agreed minimums, Gmail App Password and recipients, the scheduled task with catch-up, and a live test with the Head Vet. Retainer covers checking the log weekly, adjusting minimums as caseload changes (for example rabies campaigns), adding new items and recipients, and fixing the sheet when someone breaks a column. Saves about 15 hours a month of manual stock-taking (roughly KES 7,500 of technician time) and prevents clinical stock-outs; running cost is near zero (Gmail SMTP is free). |
| **`day26_document_qa.py` (Week 6, Day 26)** | Agribusiness Procurement Teams, Feed Millers & Large Farms, SACCOs & Co-ops, Small Law Firms, County Tender Committees | **KES 30,000 – 45,000** (one-off setup) | **KES 5,000 / month** | Contract and tender Q&A with page citations, a Word Q&A report for the board file, and a searchable index of the client's PDF folder. Setup covers installing on the client PC, loading and testing 5 to 10 of their real contracts (scanned ones OCR'd first), tuning the questions they ask most, and training one staff member; the upper end covers Word contracts, large archives or a custom report template. Retainer covers the Claude API cost (about KES 0.30 to 3 per question, so even 500 questions a month stay under KES 1,500), checking the log, adding new document types and fixing problem files. Replaces 1 to 2 hours of reading per contract and catches the clause that costs money: one missed KES 15,000-a-day late-delivery penalty or a 60-day termination notice pays for the year. |
