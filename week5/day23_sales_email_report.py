"""
Day 23 - Nairobi Retail Daily Sales Email Report (Week 5: Email & Notification Automation)

Reads the day's sales CSV, calculates the 4 owner metrics (total revenue,
receipt count, top-selling item, low-stock restock flags), saves a local
HTML preview, and emails a plain-text + HTML report via Gmail SMTP_SSL.

Usage:
    python week5/day23_sales_email_report.py               # analyse + send
    python week5/day23_sales_email_report.py --dry-run     # analyse + preview only, no email
    python week5/day23_sales_email_report.py --csv path/to/sales.csv --to owner@shop.co.ke

.env (repo root):
    GMAIL_ADDRESS=yourshop@gmail.com
    GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
    REPORT_RECIPIENT_EMAIL=owner@gmail.com, manager@gmail.com   # optional, comma-separated
    SHOP_NAME=Nairobi Retail Shop                               # optional
"""

import argparse
import csv
import html
import os
import re
import smtplib
import ssl
import sys
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from email.message import EmailMessage
from email.utils import formataddr, getaddresses
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
load_dotenv(ROOT_DIR / ".env")

SALES_CSV_PATH = BASE_DIR / "nairobi_retail_sales.csv"
HTML_PREVIEW_PATH = BASE_DIR / "email_report_preview.html"
EMAIL_LOG_PATH = BASE_DIR / "email_log.txt"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_TIMEOUT_SECONDS = 20
SMTP_MAX_ATTEMPTS = 3  # Kenyan networks drop briefly; retry before giving up

REQUIRED_COLUMNS = (
    "transaction_id",
    "item_name",
    "quantity_sold",
    "unit_price_kes",
    "current_stock",
    "restock_level",
)

CENTS = Decimal("0.01")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

SAMPLE_SALES_ROWS = [
    {"transaction_id": "TXN-1001", "item_name": "Hostess Maize Meal 2kg", "quantity_sold": 14, "unit_price_kes": 210, "current_stock": 18, "restock_level": 25},
    {"transaction_id": "TXN-1002", "item_name": "Brookside Fresh Milk 500ml", "quantity_sold": 28, "unit_price_kes": 65, "current_stock": 42, "restock_level": 30},
    {"transaction_id": "TXN-1003", "item_name": "Kabras Sugar 2kg", "quantity_sold": 11, "unit_price_kes": 340, "current_stock": 9, "restock_level": 15},
    {"transaction_id": "TXN-1004", "item_name": "Elianto Corn Oil 2L", "quantity_sold": 6, "unit_price_kes": 780, "current_stock": 14, "restock_level": 10},
    {"transaction_id": "TXN-1005", "item_name": "Menengai Cream Bar Soap 800g", "quantity_sold": 19, "unit_price_kes": 175, "current_stock": 22, "restock_level": 15},
    {"transaction_id": "TXN-1006", "item_name": "Ketepa Pride Tea Leaves 500g", "quantity_sold": 9, "unit_price_kes": 290, "current_stock": 7, "restock_level": 12},
    {"transaction_id": "TXN-1007", "item_name": "Daawat Basmati Rice 2kg", "quantity_sold": 8, "unit_price_kes": 520, "current_stock": 16, "restock_level": 10},
    {"transaction_id": "TXN-1008", "item_name": "Hostess Maize Meal 2kg", "quantity_sold": 10, "unit_price_kes": 210, "current_stock": 18, "restock_level": 25},
    {"transaction_id": "TXN-1009", "item_name": "Broadways Sliced Bread 400g", "quantity_sold": 22, "unit_price_kes": 65, "current_stock": 5, "restock_level": 20},
    {"transaction_id": "TXN-1010", "item_name": "Royco Mchuzi Mix 200g", "quantity_sold": 15, "unit_price_kes": 145, "current_stock": 25, "restock_level": 15},
    {"transaction_id": "TXN-1011", "item_name": "Brookside Fresh Milk 500ml", "quantity_sold": 12, "unit_price_kes": 65, "current_stock": 42, "restock_level": 30},
    {"transaction_id": "TXN-1012", "item_name": "Kenyatta Charger Bulbs 9W", "quantity_sold": 7, "unit_price_kes": 250, "current_stock": 4, "restock_level": 10},
]


# ---------------------------------------------------------------------------
# Console / logging helpers
# ---------------------------------------------------------------------------
def make_console_unicode_safe() -> None:
    """Older Windows consoles use cp1252 and crash on characters it cannot show."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def log_email_event(status_line: str, log_path: Path = EMAIL_LOG_PATH) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean = status_line.replace("\r", " ").replace("\n", " ")
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, mode="a", encoding="utf-8", newline="") as log_f:
            log_f.write(f"{timestamp} | {clean}\n")
    except OSError as err:
        # A locked or read-only log file must never stop the report itself.
        print(f"[WARN] Could not write to log '{log_path}': {err}")


# ---------------------------------------------------------------------------
# CSV setup and parsing
# ---------------------------------------------------------------------------
def setup_sample_sales_csv(csv_path: Path) -> None:
    if csv_path.exists():
        return

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(REQUIRED_COLUMNS))
        writer.writeheader()
        writer.writerows(SAMPLE_SALES_ROWS)
    print(f"[SETUP] Generated {len(SAMPLE_SALES_ROWS)} sample retail transactions in '{csv_path}'")


def _read_csv_rows(csv_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """Read UTF-8 first; fall back to cp1252 for files re-saved by Excel on Windows."""
    last_error: Optional[Exception] = None
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            with open(csv_path, mode="r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                fieldnames = [(name or "").strip().lower() for name in (reader.fieldnames or [])]
                reader.fieldnames = fieldnames
                rows = list(reader)
            if encoding != "utf-8-sig":
                print(f"[INFO] CSV is not UTF-8; read it as {encoding} (typical of Excel on Windows).")
            return fieldnames, rows
        except UnicodeDecodeError as err:
            last_error = err
    raise ValueError(f"Could not decode CSV '{csv_path}': {last_error}")


def _to_decimal(raw: object) -> Decimal:
    text = str(raw if raw is not None else "").strip().replace(",", "")
    text = re.sub(r"^(KES|KSH|KSHS)\s*", "", text, flags=re.IGNORECASE)
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"{raw!r} is not a number") from None
    if not value.is_finite():
        raise ValueError(f"{raw!r} is not a usable number")
    return value


def _to_int(raw: object) -> int:
    value = _to_decimal(raw)
    if value != value.to_integral_value():
        raise ValueError(f"expected a whole number, got {raw!r}")
    return int(value)


def analyze_sales_csv(csv_path: Path) -> Dict[str, object]:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Sales CSV not found at: {csv_path}")

    fieldnames, rows = _read_csv_rows(csv_path)
    missing = [col for col in REQUIRED_COLUMNS if col not in fieldnames]
    if missing:
        raise ValueError(
            f"CSV is missing required column(s): {', '.join(missing)}. "
            f"Found: {', '.join(fieldnames) or '(no header row)'}"
        )

    total_revenue = Decimal("0")
    valid_lines = 0
    receipt_ids = set()
    lines_without_id = 0
    skipped_rows = 0
    item_totals: Dict[str, Dict[str, object]] = {}
    # item -> list of (row_num, stock, restock_level) so the closing rule is explicit
    stock_readings: Dict[str, List[Tuple[int, int, int]]] = {}
    display_names: Dict[str, str] = {}

    for row_num, row in enumerate(rows, start=2):
        try:
            item = " ".join(str(row.get("item_name") or "").split())
            qty = _to_int(row.get("quantity_sold"))
            price = _to_decimal(row.get("unit_price_kes"))
            stock = _to_int(row.get("current_stock"))
            restock_lvl = _to_int(row.get("restock_level"))
        except (ValueError, TypeError, InvalidOperation) as err:
            print(f"[WARN] Skipping malformed CSV row #{row_num}: {err}")
            skipped_rows += 1
            continue

        if not item or qty < 0 or price < 0 or stock < 0 or restock_lvl < 0:
            print(f"[WARN] Skipping invalid CSV row #{row_num}: blank item or negative value")
            skipped_rows += 1
            continue

        # "Maize Meal 2kg" and "maize meal 2KG" are the same product on the shelf.
        key = item.casefold()
        display_names.setdefault(key, item)

        line_revenue = (Decimal(qty) * price).quantize(CENTS, rounding=ROUND_HALF_UP)
        total_revenue += line_revenue
        valid_lines += 1

        txn_id = str(row.get("transaction_id") or "").strip()
        if txn_id:
            receipt_ids.add(txn_id)
        else:
            lines_without_id += 1

        stats = item_totals.setdefault(key, {"units": 0, "revenue": Decimal("0")})
        stats["units"] += qty
        stats["revenue"] += line_revenue

        stock_readings.setdefault(key, []).append((row_num, stock, restock_lvl))

    if valid_lines == 0:
        raise ValueError("No valid sales transactions found in CSV.")

    # Closing-stock rule: stock only goes DOWN during a trading day, so the lowest
    # reading across all receipts is the most recent (closing) figure. The original
    # "last row wins" rule silently trusted whichever row happened to be last.
    # Restock level: use the highest value seen, so we alert early rather than late.
    data_warnings: List[str] = []
    low_stock_alerts: List[Dict[str, object]] = []
    for key, readings in stock_readings.items():
        name = display_names[key]
        stocks = {r[1] for r in readings}
        levels = {r[2] for r in readings}
        closing_stock = min(stocks)
        threshold = max(levels)
        if len(stocks) > 1:
            data_warnings.append(
                f"'{name}' has conflicting stock counts {sorted(stocks)} across receipts; using lowest ({closing_stock})."
            )
        if len(levels) > 1:
            data_warnings.append(
                f"'{name}' has conflicting restock levels {sorted(levels)}; using highest ({threshold})."
            )
        if closing_stock <= threshold:
            low_stock_alerts.append(
                {
                    "item_name": name,
                    "current_stock": closing_stock,
                    "restock_level": threshold,
                    "deficit": threshold - closing_stock,
                }
            )

    low_stock_alerts.sort(key=lambda a: (-int(a["deficit"]), str(a["item_name"])))
    for warning in data_warnings:
        print(f"[DATA CHECK] {warning}")

    # Ties broken by units, then revenue, then alphabetical so the result never flips.
    top_key, top_stats = min(
        item_totals.items(),
        key=lambda kv: (-kv[1]["units"], -kv[1]["revenue"], kv[0]),
    )

    item_breakdown = {
        display_names[k]: {"units": v["units"], "revenue": v["revenue"]}
        for k, v in item_totals.items()
    }

    return {
        "report_date": datetime.now().strftime("%Y-%m-%d (%I:%M %p)"),
        "report_day": datetime.now().strftime("%a %d %b %Y"),
        "total_revenue_kes": total_revenue.quantize(CENTS, rounding=ROUND_HALF_UP),
        "transaction_count": len(receipt_ids) + lines_without_id,
        "line_count": valid_lines,
        "skipped_rows": skipped_rows,
        "top_selling_item": {
            "name": display_names[top_key],
            "units_sold": int(top_stats["units"]),
            "revenue_kes": top_stats["revenue"].quantize(CENTS, rounding=ROUND_HALF_UP),
        },
        "low_stock_alerts": low_stock_alerts,
        "item_breakdown": item_breakdown,
        "data_warnings": data_warnings,
    }


# ---------------------------------------------------------------------------
# Email body builders
# ---------------------------------------------------------------------------
def build_email_bodies(metrics: Dict[str, object], shop_name: str) -> Tuple[str, str]:
    top = metrics["top_selling_item"]
    alerts = metrics["low_stock_alerts"]
    warnings = metrics["data_warnings"]

    plain_lines = [
        f"{shop_name.upper()} - DAILY SALES SUMMARY ({metrics['report_date']})",
        "=" * 62,
        f"1. Total Revenue        : KES {metrics['total_revenue_kes']:,.2f}",
        f"2. Total Transactions   : {metrics['transaction_count']} receipt(s) ({metrics['line_count']} line items)",
        f"3. Top-Selling Item     : {top['name']} ({top['units_sold']} units | KES {top['revenue_kes']:,.2f})",
        f"4. Restock Alerts       : {len(alerts)} item(s) at or below restock level",
        "",
    ]
    if alerts:
        plain_lines.append("URGENT RESTOCK FLAGS:")
        for a in alerts:
            plain_lines.append(
                f"  - [LOW STOCK] {a['item_name']}: {a['current_stock']} left "
                f"(restock level {a['restock_level']}, short by {a['deficit']})"
            )
    else:
        plain_lines.append("All items are above minimum restock levels.")

    if warnings or metrics["skipped_rows"]:
        plain_lines.append("")
        plain_lines.append("DATA QUALITY NOTES:")
        if metrics["skipped_rows"]:
            plain_lines.append(f"  - {metrics['skipped_rows']} CSV row(s) skipped as unreadable.")
        for w in warnings:
            plain_lines.append(f"  - {w}")

    plain_text_body = "\n".join(plain_lines)

    alert_rows_html = ""
    for a in alerts:
        safe_name = html.escape(str(a["item_name"]))
        alert_rows_html += (
            "<tr>"
            f'<td style="padding:8px 12px; border:1px solid #fca5a5;">{safe_name}</td>'
            f'<td style="padding:8px 12px; border:1px solid #fca5a5; font-weight:bold; color:#b91c1c;">{a["current_stock"]}</td>'
            f'<td style="padding:8px 12px; border:1px solid #fca5a5;">{a["restock_level"]}</td>'
            f'<td style="padding:8px 12px; border:1px solid #fca5a5; color:#b91c1c; font-weight:bold;">RESTOCK NOW</td>'
            "</tr>"
        )
    if not alert_rows_html:
        alert_rows_html = (
            '<tr><td colspan="4" style="padding:10px; text-align:center; color:#166534;">'
            "All inventory items are safely above restock levels.</td></tr>"
        )

    item_rows_html = ""
    for item_name, stats in sorted(
        metrics["item_breakdown"].items(), key=lambda x: (-x[1]["revenue"], x[0])
    ):
        safe_item = html.escape(str(item_name))
        item_rows_html += (
            "<tr>"
            f'<td style="padding:8px 12px; border:1px solid #d1d5db;">{safe_item}</td>'
            f'<td style="padding:8px 12px; border:1px solid #d1d5db;">{int(stats["units"])}</td>'
            f'<td style="padding:8px 12px; border:1px solid #d1d5db;">KES {stats["revenue"]:,.2f}</td>'
            "</tr>"
        )

    notes_html = ""
    note_items = []
    if metrics["skipped_rows"]:
        note_items.append(f"{metrics['skipped_rows']} CSV row(s) skipped as unreadable.")
    note_items.extend(warnings)
    if note_items:
        lis = "".join(f"<li>{html.escape(n)}</li>" for n in note_items)
        notes_html = (
            '<h3 style="color:#92400e; margin-bottom:8px;">Data Quality Notes</h3>'
            f'<ul style="background:#fffbeb; border:1px solid #fcd34d; padding:12px 28px; font-size:13px;">{lis}</ul>'
        )

    safe_shop = html.escape(shop_name)
    safe_top_name = html.escape(str(top["name"]))
    safe_date = html.escape(str(metrics["report_date"]))

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_shop} - Daily Sales Summary</title>
</head>
<body style="font-family: Arial, sans-serif; color: #1f2937; line-height: 1.5; max-width: 680px; margin: 0 auto; padding: 16px;">
    <div style="background-color: #1F4E79; color: #ffffff; padding: 18px 22px; border-radius: 6px 6px 0 0;">
        <h2 style="margin: 0; font-size: 20px;">{safe_shop} &mdash; Daily Sales Summary</h2>
        <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.9;">Generated: {safe_date}</p>
    </div>

    <div style="border: 1px solid #d1d5db; border-top: none; padding: 20px; border-radius: 0 0 6px 6px;">
        <h3 style="margin-top: 0; color: #1F4E79;">Executive KPI Snapshot</h3>
        <table width="100%" cellpadding="10" style="border-collapse: collapse; margin-bottom: 22px; background: #f8fafc;">
            <tr>
                <td style="border: 1px solid #d1d5db;"><strong>Total Revenue</strong><br>
                    <span style="font-size: 20px; color: #166534; font-weight: bold;">KES {metrics['total_revenue_kes']:,.2f}</span>
                </td>
                <td style="border: 1px solid #d1d5db;"><strong>Transactions Logged</strong><br>
                    <span style="font-size: 20px; color: #1F4E79; font-weight: bold;">{metrics['transaction_count']} receipts</span>
                </td>
            </tr>
            <tr>
                <td style="border: 1px solid #d1d5db;"><strong>Top-Selling Item</strong><br>
                    <span style="font-size: 15px; font-weight: bold;">{safe_top_name}</span><br>
                    <span style="font-size: 13px; color: #4b5563;">{top['units_sold']} units sold (KES {top['revenue_kes']:,.2f})</span>
                </td>
                <td style="border: 1px solid #d1d5db;"><strong>Restock Flags</strong><br>
                    <span style="font-size: 20px; color: {'#b91c1c' if alerts else '#166534'}; font-weight: bold;">
                        {len(alerts)} item(s) low
                    </span>
                </td>
            </tr>
        </table>

        <h3 style="color: #b91c1c; margin-bottom: 8px;">Restock Alert Flags (At or Below Restock Level)</h3>
        <table width="100%" cellpadding="8" style="border-collapse: collapse; margin-bottom: 22px; font-size: 14px;">
            <tr style="background-color: #fee2e2; color: #991b1b; text-align: left;">
                <th style="padding:8px 12px; border:1px solid #fca5a5;">Item Name</th>
                <th style="padding:8px 12px; border:1px solid #fca5a5;">Closing Stock</th>
                <th style="padding:8px 12px; border:1px solid #fca5a5;">Restock Level</th>
                <th style="padding:8px 12px; border:1px solid #fca5a5;">Status</th>
            </tr>
            {alert_rows_html}
        </table>

        <h3 style="color: #1F4E79; margin-bottom: 8px;">Itemized Sales Breakdown</h3>
        <table width="100%" cellpadding="8" style="border-collapse: collapse; font-size: 14px; margin-bottom: 22px;">
            <tr style="background-color: #1F4E79; color: #ffffff; text-align: left;">
                <th style="padding:8px 12px; border:1px solid #1F4E79;">Item Name</th>
                <th style="padding:8px 12px; border:1px solid #1F4E79;">Units Sold</th>
                <th style="padding:8px 12px; border:1px solid #1F4E79;">Revenue (KES)</th>
            </tr>
            {item_rows_html}
        </table>
        {notes_html}
    </div>
</body>
</html>"""

    return plain_text_body, html_body


# ---------------------------------------------------------------------------
# Email address safety + sending
# ---------------------------------------------------------------------------
def strip_header_breaks(value: str) -> str:
    """CR/LF inside a header lets an attacker smuggle extra headers (e.g. a hidden Bcc)."""
    return " ".join(str(value).replace("\r", " ").replace("\n", " ").split())


def parse_recipients(raw: str) -> Tuple[List[str], List[str]]:
    """Split 'a@x.com, Name <b@y.com>; c@z.com' into (valid, rejected) address lists."""
    if "\r" in raw or "\n" in raw:
        return [], [raw.strip()]
    valid: List[str] = []
    rejected: List[str] = []
    for _, addr in getaddresses([raw.replace(";", ",")]):
        addr = addr.strip()
        if not addr:
            continue
        if EMAIL_PATTERN.match(addr):
            if addr.lower() not in {v.lower() for v in valid}:
                valid.append(addr)
        else:
            rejected.append(addr)
    return valid, rejected


def build_message(sender: str, sender_name: str, recipients: List[str], subject: str,
                  plain_body: str, html_body: str) -> EmailMessage:
    msg = EmailMessage()  # default policy: RFC-compliant encoding of non-ASCII headers
    msg["Subject"] = strip_header_breaks(subject)
    msg["From"] = formataddr((strip_header_breaks(sender_name), sender))
    msg["To"] = ", ".join(recipients)
    msg.set_content(plain_body, charset="utf-8")
    msg.add_alternative(html_body, subtype="html", charset="utf-8")
    return msg


def send_sales_email(recipients: List[str], subject: str, plain_body: str, html_body: str,
                     sender_name: str) -> bool:
    sender = os.getenv("GMAIL_ADDRESS", "").strip()
    app_password = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()

    if not sender or not app_password:
        msg_err = "Missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD in .env"
        print(f"[SKIPPED SMTP] {msg_err}. HTML preview is at '{HTML_PREVIEW_PATH}'.")
        log_email_event(f"SKIPPED - {msg_err}")
        return False
    if not EMAIL_PATTERN.match(sender):
        msg_err = f"GMAIL_ADDRESS '{strip_header_breaks(sender)}' is not a valid email address"
        print(f"[SKIPPED SMTP] {msg_err}.")
        log_email_event(f"SKIPPED - {msg_err}")
        return False
    if not recipients:
        msg_err = "No valid recipient address configured"
        print(f"[SKIPPED SMTP] {msg_err}.")
        log_email_event(f"SKIPPED - {msg_err}")
        return False

    msg = build_message(sender, sender_name, recipients, subject, plain_body, html_body)
    context = ssl.create_default_context()  # verifies Gmail's certificate + hostname
    to_list = ", ".join(recipients)

    for attempt in range(1, SMTP_MAX_ATTEMPTS + 1):
        try:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS,
                                  context=context) as server:
                server.login(sender, app_password)
                refused = server.send_message(msg)
            delivered = [r for r in recipients if r not in refused]
            if refused:
                log_email_event(f"PARTIAL - refused by server: {', '.join(refused)}")
                print(f"[WARN] Server refused: {', '.join(refused)}")
            log_email_event(f"OK - Daily sales report sent to {', '.join(delivered)}")
            print(f"[SUCCESS] Email sent to {', '.join(delivered)}")
            return True
        except smtplib.SMTPAuthenticationError:
            err_msg = "SMTP authentication failed. Check GMAIL_ADDRESS and the 16-character GMAIL_APP_PASSWORD."
            log_email_event(f"FAILED - {err_msg}")
            print(f"[ERROR] {err_msg}")
            return False  # wrong password will not fix itself; do not retry
        except smtplib.SMTPRecipientsRefused as err:
            err_msg = f"All recipients refused: {', '.join(err.recipients)}"
            log_email_event(f"FAILED - {err_msg}")
            print(f"[ERROR] {err_msg}")
            return False
        except (smtplib.SMTPException, OSError) as err:
            # OSError covers no internet, DNS failure, timeouts and SSL errors.
            log_email_event(f"RETRY {attempt}/{SMTP_MAX_ATTEMPTS} - {type(err).__name__}: {err}")
            print(f"[WARN] Attempt {attempt}/{SMTP_MAX_ATTEMPTS} to reach Gmail failed: {err}")
            if attempt < SMTP_MAX_ATTEMPTS:
                time.sleep(5 * attempt)

    log_email_event(f"FAILED - could not reach {SMTP_SERVER} after {SMTP_MAX_ATTEMPTS} attempts (to: {to_list})")
    print(f"[ERROR] Could not send email after {SMTP_MAX_ATTEMPTS} attempts. Preview saved at '{HTML_PREVIEW_PATH}'.")
    return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Email the day's sales summary to the shop owner.")
    parser.add_argument("--csv", type=Path, default=SALES_CSV_PATH, help="Path to the day's sales CSV.")
    parser.add_argument("--to", default=None,
                        help="Recipient(s), comma-separated. Overrides REPORT_RECIPIENT_EMAIL.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Build the report and HTML preview but do not send any email.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    make_console_unicode_safe()
    args = parse_args(argv)
    csv_path: Path = args.csv.expanduser().resolve()
    shop_name = strip_header_breaks(os.getenv("SHOP_NAME", "Nairobi Retail Shop")) or "Nairobi Retail Shop"

    print("======================================================")
    print("   NAIROBI RETAIL DAILY SALES EMAIL AUTOMATION        ")
    print("======================================================")

    try:
        if csv_path == SALES_CSV_PATH.resolve():
            setup_sample_sales_csv(csv_path)  # only auto-generate the demo file, never a user path
        metrics = analyze_sales_csv(csv_path)
    except (FileNotFoundError, ValueError, OSError) as err:
        print(f"[ERROR] {err}")
        log_email_event(f"ABORTED - {err}")
        return 1

    plain_body, html_body = build_email_bodies(metrics, shop_name)
    print(plain_body)
    print("------------------------------------------------------")

    try:
        HTML_PREVIEW_PATH.write_text(html_body, encoding="utf-8")
        print(f"[PREVIEW] Saved HTML email preview to: {HTML_PREVIEW_PATH}")
    except OSError as err:
        print(f"[WARN] Could not save HTML preview: {err}")

    raw_recipients = args.to or os.getenv("REPORT_RECIPIENT_EMAIL") or os.getenv("GMAIL_ADDRESS", "")
    recipients, rejected = parse_recipients(raw_recipients)
    for bad in rejected:
        print(f"[WARN] Ignoring invalid recipient address: {strip_header_breaks(bad)!r}")

    subject = (
        f"{shop_name} Daily Sales {metrics['report_day']} — KES {metrics['total_revenue_kes']:,.0f} "
        f"({len(metrics['low_stock_alerts'])} Restock Alerts)"
    )

    if args.dry_run:
        print(f"[DRY RUN] Would send to: {', '.join(recipients) or '(no valid recipient)'}")
        print(f"[DRY RUN] Subject: {subject}")
        log_email_event("DRY RUN - report built, no email sent")
        print("======================================================")
        return 0

    sent = send_sales_email(recipients, subject, plain_body, html_body, sender_name=f"{shop_name} Reports")
    print("======================================================")
    return 0 if sent else 2


if __name__ == "__main__":
    sys.exit(main())
