"""
Week 5 Capstone (Day 25) Option 2: Automated Daily Stock Alert - Nairobi Pet Clinic
----------------------------------------------------------------------------
Client: Kilimani Vet & Pet Care Clinic (Nairobi)

Reads the clinic dispensary CSV ('item name', 'current stock', 'minimum stock'),
finds every vaccine, drug and surgical consumable that is BELOW its minimum,
works out how many units to order, and emails a prioritised HTML + plain-text
reorder list via Gmail SMTP_SSL every morning.

Rules in one place:
  * Flagged for reorder : current stock <  minimum stock
  * "Watch" list         : current stock == minimum stock (shown, never triggers an email)
  * Deficit to minimum  : minimum - current
  * Recommended order   : top up to minimum + 25% buffer (at least +2 units), rounded UP
  * CRITICAL            : out of stock, 2 units or fewer left, or at/below one third of minimum

Common commands (Windows PowerShell or Linux):
  python week5/day25_pet_clinic_stock_alert.py --self-test       # 10 automated checks, touches no real files
  python week5/day25_pet_clinic_stock_alert.py --dry-run         # preview only, creates the sample CSV if missing
  python week5/day25_pet_clinic_stock_alert.py                   # real run: send the alert if anything is low
  python week5/day25_pet_clinic_stock_alert.py --install-task --time 07:00
  python week5/day25_pet_clinic_stock_alert.py --uninstall-task
"""

import argparse
import contextlib
import csv
import hashlib
import html
import io
import json
import math
import os
import re
import shlex
import smtplib
import ssl
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, getaddresses
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Tuple
from xml.sax.saxutils import escape as xml_escape

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
load_dotenv(ROOT_DIR / ".env")

# Runtime paths. Functions look these up when they run (not when Python loads the
# file), so the self-test can point them at a throw-away temp folder.
DEFAULT_CSV_PATH = BASE_DIR / "pet_clinic_inventory.csv"
HTML_PREVIEW_PATH = BASE_DIR / "pet_clinic_stock_preview.html"
AUTOMATION_LOG_PATH = BASE_DIR / "pet_clinic_automation.log"
STATE_FILE_PATH = BASE_DIR / "pet_clinic_state.json"
LOCK_FILE_PATH = BASE_DIR / "pet_clinic_scheduler.lock"

CLINIC_NAME = "Kilimani Vet & Pet Care Clinic"
# The run time can be changed with --time, so the task name no longer says "7AM".
WINDOWS_TASK_NAME = "Kimnovix_PetClinic_Stock_Alert"
LEGACY_TASK_NAMES = ("Kimnovix_PetClinic_Stock_Alert_7AM",)
DEFAULT_RUN_TIME = "07:00"
RETRY_EVERY = "PT30M"   # Task Scheduler re-runs every 30 minutes...
RETRY_FOR = "PT4H"      # ...for 4 hours after the start time (sends at most once a day)
SCHTASKS_TR_LIMIT = 261

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_TIMEOUT_SECONDS = 20
SMTP_MAX_ATTEMPTS = 3

BUFFER_RATE = 0.25        # 25% clinical safety buffer on top of the minimum
MIN_BUFFER_UNITS = 2      # never a buffer smaller than 2 units
CRITICAL_UNITS_LEFT = 2   # 2 or fewer units left is always CRITICAL

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
TIME_PATTERN = re.compile(r"^\s*(\d{1,2})(?::(\d{2}))?\s*(?:([ap])\.?\s*m?\.?)?\s*$", re.IGNORECASE)
REQUIRED_COLUMNS = ("item name", "current stock", "minimum stock")

# Realistic Nairobi Small-Animal Veterinary Clinic Dispensary Inventory (12 items)
SAMPLE_CLINIC_INVENTORY = [
    {"item name": "Nobivac DHPPi Canine Vaccine (Doses)", "current stock": 6, "minimum stock": 15},
    {"item name": "Nobivac Rabies Vaccine (Vials)", "current stock": 18, "minimum stock": 10},
    {"item name": "Amoxicillin-Clavulanate 250mg (Tablets)", "current stock": 45, "minimum stock": 100},
    {"item name": "Meloxicam Oral Suspension 15ml (Bottles)", "current stock": 3, "minimum stock": 8},
    {"item name": "Bravecto Chewable Medium Dog (Packs)", "current stock": 12, "minimum stock": 10},
    {"item name": "NexGard Spectra Small Dog (Packs)", "current stock": 4, "minimum stock": 10},
    {"item name": "Ketamine HCl 100mg/ml Injectable (Vials)", "current stock": 2, "minimum stock": 6},
    {"item name": "Propofol 10mg/ml Anesthetic (Ampoules)", "current stock": 9, "minimum stock": 8},
    {"item name": "Vicryl 2-0 Absorbable Sutures (Packs)", "current stock": 5, "minimum stock": 12},
    {"item name": "IV Catheters 22G Blue (Units)", "current stock": 14, "minimum stock": 30},
    {"item name": "Lactated Ringer's Solution 500ml (Bags)", "current stock": 25, "minimum stock": 20},
    {"item name": "Canine Parvovirus Rapid Ag Test Kits", "current stock": 3, "minimum stock": 10},
]

SendFunc = Callable[[List[str], str, str, str], bool]


# ---------------------------------------------------------------------------
# Console, time and logging helpers
# ---------------------------------------------------------------------------
def make_console_unicode_safe() -> None:
    """Older Windows consoles use cp1252; under pythonw.exe there is no console at all."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def parse_run_time(text: str) -> str:
    """Accept 07:00, 7:00, 7am, 7:30 AM; always return zero-padded 24-hour HH:MM.

    `schedule`, `schtasks /ST` and cron all need a valid HH:MM. "7:00" used to crash
    the daemon at start-up and "25:00" produced a broken crontab line.
    """
    match = TIME_PATTERN.match(str(text))
    if not match:
        raise argparse.ArgumentTypeError(f"'{text}' is not a time. Use HH:MM, e.g. 07:00 or 7:00 AM.")
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = (match.group(3) or "").lower()
    if not meridiem and match.group(2) is None:
        raise argparse.ArgumentTypeError(f"'{text}' is ambiguous. Use 07:00 or 7am.")
    if meridiem:
        if not 1 <= hour <= 12:
            raise argparse.ArgumentTypeError(f"'{text}': with AM/PM the hour must be 1-12.")
        hour = hour % 12 + (12 if meridiem == "p" else 0)
    if hour > 23 or minute > 59:
        raise argparse.ArgumentTypeError(f"'{text}' is not a real clock time (00:00-23:59).")
    return f"{hour:02d}:{minute:02d}"


def log_automation_event(level: str, message: str, log_path: Optional[Path] = None) -> str:
    """Writes one timestamped audit line to pet_clinic_automation.log and closes the handle."""
    path = log_path or AUTOMATION_LOG_PATH
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_msg = " ".join(str(message).replace("|", "/").split())
    line = f"{timestamp} | {level.upper()} | {clean_msg}"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # If someone hand-edited the log and the editor dropped the final newline,
        # start on a fresh line instead of gluing two entries together.
        needs_break = False
        if path.is_file() and path.stat().st_size > 0:
            with open(path, "rb") as existing:
                existing.seek(-1, os.SEEK_END)
                needs_break = existing.read(1) not in (b"\n", b"\r")
        with open(path, mode="a", encoding="utf-8", newline="") as f:
            f.write(("\n" if needs_break else "") + line + "\n")
    except OSError as err:
        print(f"[WARN] Could not write to log '{path}': {err}")
    return line


# ---------------------------------------------------------------------------
# CSV reading and stock analysis
# ---------------------------------------------------------------------------
def setup_sample_inventory_csv(csv_path: Path) -> bool:
    """Creates the 12-item Nairobi Pet Clinic sample CSV if missing. Returns True if created."""
    if csv_path.exists():
        return False
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(REQUIRED_COLUMNS))
        writer.writeheader()
        writer.writerows(SAMPLE_CLINIC_INVENTORY)
    print(f"[SETUP] Created 12-item sample Nairobi Pet Clinic inventory at '{csv_path}'")
    return True


def _normalize_header(header: str) -> str:
    """Normalizes 'Item Name', 'item_name' or ' ITEM  NAME ' to 'item name'."""
    return " ".join(str(header).strip().lower().replace("_", " ").split())


def _detect_delimiter(text: str) -> str:
    """Excel on some regional settings saves CSVs with ';' instead of ','."""
    first_line = text.split("\n", 1)[0]
    counts = {d: first_line.count(d) for d in (",", ";", "\t")}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] > 0 else ","


def _read_csv_with_fallback(csv_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """Reads UTF-8 (with or without BOM) first, then cp1252 (Windows Excel), then latin-1.

    latin-1 can decode any byte, so a CSV with one odd character never stops the alert.
    """
    if not csv_path.is_file():
        raise FileNotFoundError(f"Inventory CSV not found: {csv_path}")

    raw = csv_path.read_bytes()
    text = ""
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if not text.strip():
        return [], []

    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=_detect_delimiter(text))
    if not reader.fieldnames:
        return [], []
    normalized_fields = [_normalize_header(h or "") for h in reader.fieldnames]
    reader.fieldnames = normalized_fields
    rows = []
    for row in reader:
        # Excel often leaves rows like ",," at the bottom: ignore them silently.
        if all(not str(v or "").strip() for k, v in row.items() if k is not None):
            continue
        rows.append(row)
    return normalized_fields, rows


def _parse_int(raw: object, field_label: str) -> int:
    text = str(raw if raw is not None else "").strip().replace(",", "")
    if not text:
        raise ValueError(f"blank {field_label}")
    try:
        val = float(text)
    except ValueError:
        raise ValueError(f"{field_label} must be a number, got {raw!r}") from None
    if not val.is_integer() or val < 0:
        raise ValueError(f"{field_label} must be a non-negative whole number, got {raw!r}")
    return int(val)


def calculate_recommended_order(current: int, minimum: int) -> Tuple[int, int]:
    """Returns (target_level, units_to_order).

    Target = minimum + 25% buffer, rounded UP, never less than +2 units.
    The old code used round(), which rounds 12.5 down to 12, so a minimum of 10
    really only got a 20% buffer. math.ceil always rounds up: 10 -> 13.
    """
    buffer_units = max(MIN_BUFFER_UNITS, math.ceil(minimum * BUFFER_RATE))
    target = minimum + buffer_units
    return target, max(0, target - current)


def classify_severity(current: int, minimum: int) -> str:
    """CRITICAL = out of stock, 2 or fewer left, or at/below one third of the minimum."""
    if current <= CRITICAL_UNITS_LEFT or current * 3 <= minimum:
        return "CRITICAL"
    return "LOW"


def analyze_clinic_stock(csv_path: Path, now: Optional[datetime] = None) -> Dict[str, object]:
    """Reads the clinic CSV and evaluates stock levels against minimum thresholds.

    A header-only or blank CSV returns empty_dataset=True instead of crashing.
    A CSV with the wrong columns raises ValueError (that is a setup mistake, not "no stock").
    """
    now = now or datetime.now()
    headers, rows = _read_csv_with_fallback(csv_path)

    if headers:
        missing = set(REQUIRED_COLUMNS) - set(headers)
        if missing:
            raise ValueError(
                f"CSV is missing required column(s): {sorted(missing)}. Found: {headers}"
            )

    merged_items: Dict[str, Dict[str, object]] = {}
    skipped_rows = 0

    for row_num, row in enumerate(rows, start=2):
        item_name = " ".join(str(row.get("item name") or "").split())
        if not item_name:
            print(f"[WARN] Skipping row #{row_num}: blank item name")
            skipped_rows += 1
            continue
        try:
            curr_stock = _parse_int(row.get("current stock"), "current stock")
            min_stock = _parse_int(row.get("minimum stock"), "minimum stock")
        except ValueError as err:
            print(f"[WARN] Skipping invalid row #{row_num} ({item_name}): {err}")
            skipped_rows += 1
            continue

        key = item_name.casefold()
        if key not in merged_items:
            merged_items[key] = {
                "item_name": item_name,
                "current_stock": curr_stock,
                "minimum_stock": min_stock,
            }
        else:
            # Same item listed twice: be conservative (lowest stock, highest minimum).
            merged_items[key]["current_stock"] = min(int(merged_items[key]["current_stock"]), curr_stock)
            merged_items[key]["minimum_stock"] = max(int(merged_items[key]["minimum_stock"]), min_stock)

    below_min_list: List[Dict[str, object]] = []
    at_min_list: List[Dict[str, object]] = []
    healthy_count = 0

    for item in merged_items.values():
        curr = int(item["current_stock"])
        minimum = int(item["minimum_stock"])
        if curr < minimum:
            _, recommended_order = calculate_recommended_order(curr, minimum)
            below_min_list.append(
                {
                    "item_name": item["item_name"],
                    "current_stock": curr,
                    "minimum_stock": minimum,
                    "restock_needed": minimum - curr,
                    "recommended_order": recommended_order,
                    "severity": classify_severity(curr, minimum),
                }
            )
        else:
            healthy_count += 1
            if curr == minimum and minimum > 0:
                # Exactly at minimum is NOT below minimum, so it never triggers an email
                # on its own. It is listed as "watch" so procurement sees it coming.
                at_min_list.append({"item_name": item["item_name"], "current_stock": curr})

    # Most urgent first: CRITICAL, then the biggest deficit, then A-Z.
    below_min_list.sort(
        key=lambda x: (
            0 if x["severity"] == "CRITICAL" else 1,
            -int(x["restock_needed"]),
            str(x["item_name"]).casefold(),
        )
    )
    at_min_list.sort(key=lambda x: str(x["item_name"]).casefold())

    return {
        "report_date": now.strftime("%Y-%m-%d (%I:%M %p)"),
        "total_items_checked": len(merged_items),
        "skipped_rows": skipped_rows,
        "below_minimum_items": below_min_list,
        "at_minimum_items": at_min_list,
        "healthy_items_count": healthy_count,
        "empty_dataset": len(merged_items) == 0,
    }


# ---------------------------------------------------------------------------
# Duplicate prevention (state file)
# ---------------------------------------------------------------------------
def compute_alert_fingerprint(report: Dict[str, object], now: Optional[datetime] = None) -> str:
    """SHA-256 of today's date + the exact low-stock list.

    Same day + same shortages = same fingerprint = no second email.
    A new shortage later in the day changes the fingerprint, so it IS sent.
    """
    today_str = (now or datetime.now()).strftime("%Y-%m-%d")
    payload = json.dumps(
        {"date": today_str, "below_minimum": report.get("below_minimum_items", [])},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_state(state_path: Optional[Path] = None) -> Dict[str, object]:
    path = state_path or STATE_FILE_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def is_duplicate_run(fingerprint: str, state_path: Optional[Path] = None) -> bool:
    return load_state(state_path).get("last_sent_fingerprint") == fingerprint


def already_alerted_today(state_path: Optional[Path] = None, now: Optional[datetime] = None) -> bool:
    today = (now or datetime.now()).strftime("%Y-%m-%d")
    return load_state(state_path).get("last_sent_date") == today


def record_successful_run(
    fingerprint: str,
    items_flagged: int,
    state_path: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> None:
    path = state_path or STATE_FILE_PATH
    now = now or datetime.now()
    payload = {
        "last_sent_at": now.isoformat(timespec="seconds"),
        "last_sent_date": now.strftime("%Y-%m-%d"),
        "last_sent_fingerprint": fingerprint,
        "items_below_minimum": items_flagged,
    }
    tmp_path = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp_path, path)  # atomic: a power cut never leaves half a JSON file
    except OSError as err:
        print(f"[WARN] Could not update state file: {err}")


# ---------------------------------------------------------------------------
# Overlap protection
# ---------------------------------------------------------------------------
class RunLock:
    """OS-level file lock (msvcrt on Windows, fcntl on Linux).

    Stops the 7:00 task, a retry and a manual run from both passing the
    "already sent?" check at the same moment and emailing twice. If the PC crashes
    or the process is killed, the OS frees the lock, so there is nothing to clean up.
    """

    def __init__(self, path: Optional[Path] = None):
        self.path = path or LOCK_FILE_PATH
        self._fh = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT, 0o644)
        fh = os.fdopen(fd, "r+", encoding="utf-8")
        try:
            if os.name == "nt":
                import msvcrt
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fh.close()
            return False
        self._fh = fh
        try:
            fh.seek(0)
            fh.truncate()
            fh.write(f"pid={os.getpid()} started={datetime.now():%Y-%m-%d %H:%M:%S}\n")
            fh.flush()
        except OSError:
            pass  # the lock itself is what matters, not the note inside it
        return True

    def release(self) -> None:
        if not self._fh:
            return
        try:
            if os.name == "nt":
                import msvcrt
                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            self._fh.close()
            self._fh = None

    def __enter__(self) -> bool:
        return self.acquire()

    def __exit__(self, *exc) -> None:
        self.release()


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
def build_stock_alert_bodies(report: Dict[str, object], clinic_name: str = CLINIC_NAME) -> Tuple[str, str]:
    """Builds both plain-text and inline-CSS HTML email bodies."""
    below = report["below_minimum_items"]
    at_min = report.get("at_minimum_items", [])
    total = report["total_items_checked"]
    healthy = report["healthy_items_count"]
    critical_count = sum(1 for item in below if item["severity"] == "CRITICAL")
    buffer_pct = int(BUFFER_RATE * 100)

    plain_lines = [
        f"{clinic_name.upper()} - DAILY DISPENSARY STOCK ALERT",
        f"Generated: {report['report_date']}",
        "=" * 68,
        f"Total Items Audited    : {total}",
        f"Items Below Minimum    : {len(below)} ({critical_count} CRITICAL)",
        f"Items At/Above Minimum : {healthy}",
    ]
    if report.get("skipped_rows"):
        plain_lines.append(f"Rows Skipped (bad data): {report['skipped_rows']} - please check the stock sheet")
    plain_lines.append("")

    if below:
        plain_lines.append("ITEMS BELOW MINIMUM STOCK (PROCUREMENT ACTION REQUIRED):")
        plain_lines.append("-" * 68)
        for idx, item in enumerate(below, start=1):
            plain_lines.append(
                f"{idx:2d}. [{item['severity']}] {item['item_name']}\n"
                f"    Current Stock: {item['current_stock']} | Minimum: {item['minimum_stock']} "
                f"| Deficit to Min: +{item['restock_needed']} "
                f"| Recommended Order: +{item['recommended_order']}"
            )
    else:
        plain_lines.append("All clinic vaccines, drugs, and consumables are at or above minimum stock.")

    if at_min:
        plain_lines.append("")
        plain_lines.append("WATCH LIST (exactly at minimum - next use puts these below minimum):")
        for item in at_min:
            plain_lines.append(f"  - {item['item_name']} ({item['current_stock']} left)")

    plain_lines.append("")
    plain_lines.append(
        f"Deficit to Min = units needed to reach the minimum. Recommended Order adds a "
        f"{buffer_pct}% clinical safety buffer (at least +{MIN_BUFFER_UNITS} units)."
    )
    plain_text = "\n".join(plain_lines)

    cell = "padding:9px 12px; border:1px solid #e5e7eb;"
    rows_html = ""
    for item in below:
        safe_name = html.escape(str(item["item_name"]))
        badge_bg = "#b91c1c" if item["severity"] == "CRITICAL" else "#b45309"
        rows_html += (
            "<tr>"
            f'<td style="{cell}">{safe_name}</td>'
            f'<td style="{cell} text-align:center; font-weight:bold; color:#b91c1c;">{item["current_stock"]}</td>'
            f'<td style="{cell} text-align:center;">{item["minimum_stock"]}</td>'
            f'<td style="{cell} text-align:center; font-weight:bold; color:#1f2937;">+{item["restock_needed"]}</td>'
            f'<td style="{cell} text-align:center; font-weight:bold; color:#0f766e;">+{item["recommended_order"]}</td>'
            f'<td style="{cell} text-align:center;">'
            f'<span style="background:{badge_bg}; color:#ffffff; padding:3px 8px; border-radius:4px; '
            f'font-size:11px; font-weight:bold;">{item["severity"]}</span>'
            "</td></tr>"
        )

    if not rows_html:
        rows_html = (
            '<tr><td colspan="6" style="padding:14px; text-align:center; color:#166534; font-weight:bold;">'
            "All veterinary items are stocked at or above minimum levels.</td></tr>"
        )

    watch_html = ""
    if at_min:
        watch_items = "".join(
            f"<li>{html.escape(str(item['item_name']))} ({item['current_stock']} left)</li>" for item in at_min
        )
        watch_html = (
            '<h3 style="color:#b45309; margin:20px 0 6px 0; font-size:15px;">Watch List (exactly at minimum)</h3>'
            '<p style="margin:0 0 6px 0; font-size:13px; color:#4b5563;">Not yet below minimum, '
            "but the next dispense will put these on tomorrow's reorder list.</p>"
            f'<ul style="margin:0; font-size:13px;">{watch_items}</ul>'
        )

    skipped_html = ""
    if report.get("skipped_rows"):
        skipped_html = (
            '<p style="font-size:13px; color:#b91c1c; margin:12px 0 0 0;">'
            f"{report['skipped_rows']} row(s) in the stock sheet had missing or invalid numbers and "
            "were skipped. Please check the sheet.</p>"
        )

    safe_clinic = html.escape(clinic_name)
    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family: Arial, sans-serif; color: #1f2937; max-width: 720px; margin: 0 auto; padding: 16px;">
    <div style="background-color: #0f766e; color: #ffffff; padding: 18px 22px; border-radius: 6px 6px 0 0;">
        <h2 style="margin: 0; font-size: 20px;">{safe_clinic} &mdash; Daily Dispensary Stock Alert</h2>
        <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.9;">Generated: {html.escape(str(report['report_date']))}</p>
    </div>
    <div style="border: 1px solid #d1d5db; border-top: none; padding: 20px; border-radius: 0 0 6px 6px;">
        <table width="100%" cellpadding="10" style="border-collapse: collapse; margin-bottom: 20px; background: #f8fafc;">
            <tr>
                <td style="border: 1px solid #d1d5db;"><strong>Items Audited</strong><br>
                    <span style="font-size: 20px; font-weight: bold; color: #0f766e;">{total} SKUs</span>
                </td>
                <td style="border: 1px solid #d1d5db;"><strong>Below Minimum</strong><br>
                    <span style="font-size: 20px; font-weight: bold; color: #b91c1c;">{len(below)} items</span>
                    <span style="font-size: 12px; color: #b91c1c;">({critical_count} critical)</span>
                </td>
                <td style="border: 1px solid #d1d5db;"><strong>At/Above Minimum</strong><br>
                    <span style="font-size: 20px; font-weight: bold; color: #166534;">{healthy} items</span>
                </td>
            </tr>
        </table>

        <h3 style="color: #b91c1c; margin-bottom: 8px;">Dispensary Reorder List (Items Below Minimum)</h3>
        <table width="100%" cellpadding="8" style="border-collapse: collapse; font-size: 13px;">
            <tr style="background-color: #1f2937; color: #ffffff; text-align: left;">
                <th style="padding:9px 12px;">Item Name</th>
                <th style="padding:9px 12px; text-align:center;">Current</th>
                <th style="padding:9px 12px; text-align:center;">Minimum</th>
                <th style="padding:9px 12px; text-align:center;">Deficit to Min</th>
                <th style="padding:9px 12px; text-align:center;">Rec. Order (+Buffer)</th>
                <th style="padding:9px 12px; text-align:center;">Priority</th>
            </tr>
            {rows_html}
        </table>
        {watch_html}
        {skipped_html}
        <p style="font-size: 12px; color: #6b7280; margin-top: 16px;">
            * <strong>Deficit to Min</strong> is the exact quantity required to reach minimum stock.
            <strong>Rec. Order (+Buffer)</strong> adds a {buffer_pct}% clinical safety buffer
            (at least +{MIN_BUFFER_UNITS} units) for emergency cases.
            <strong>CRITICAL</strong> = out of stock, {CRITICAL_UNITS_LEFT} or fewer left, or at/below one third of minimum.
        </p>
    </div>
</body>
</html>"""

    return plain_text, html_body


def _strip_header_breaks(val: str) -> str:
    return " ".join(str(val).replace("\r", " ").replace("\n", " ").split())


def _parse_recipients(raw: str) -> List[str]:
    if "\r" in raw or "\n" in raw:
        return []
    valid: List[str] = []
    for _, addr in getaddresses([raw.replace(";", ",")]):
        addr = addr.strip()
        if EMAIL_PATTERN.match(addr) and addr.lower() not in {v.lower() for v in valid}:
            valid.append(addr)
    return valid


def send_stock_alert_email(
    recipients: List[str],
    subject: str,
    plain_body: str,
    html_body: str,
    sender_name: str = "Kilimani Vet Inventory Watch",
) -> bool:
    """Dispatches the multipart alert email over verified TLS with a 3-attempt retry."""
    sender = os.getenv("GMAIL_ADDRESS", "").strip()
    app_password = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()

    if not sender or not app_password:
        log_automation_event("ERROR", "FAILED - Missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD in .env")
        print("[ERROR] Missing Gmail credentials in .env.")
        return False

    msg = EmailMessage()
    msg["Subject"] = _strip_header_breaks(subject)
    msg["From"] = formataddr((_strip_header_breaks(sender_name), sender))
    msg["To"] = ", ".join(recipients)
    msg.set_content(plain_body, charset="utf-8")
    msg.add_alternative(html_body, subtype="html", charset="utf-8")

    context = ssl.create_default_context()

    for attempt in range(1, SMTP_MAX_ATTEMPTS + 1):
        try:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS, context=context) as server:
                server.login(sender, app_password)
                server.send_message(msg)
            log_automation_event("INFO", f"OK - Sent stock alert to {len(recipients)} recipient(s)")
            print(f"[SUCCESS] Stock alert emailed to {', '.join(recipients)}")
            return True
        except smtplib.SMTPAuthenticationError:
            log_automation_event("ERROR", "FAILED - Gmail SMTP Authentication error (check App Password)")
            print("[ERROR] SMTP Authentication failed.")
            return False
        except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused) as err:
            # Retrying will not fix a rejected address, so stop straight away.
            log_automation_event("ERROR", f"FAILED - Address rejected by Gmail: {err}")
            print(f"[ERROR] Gmail rejected an address: {err}")
            return False
        except (smtplib.SMTPException, OSError) as err:
            log_automation_event("WARNING", f"RETRY {attempt}/{SMTP_MAX_ATTEMPTS} - Network/SMTP error: {err}")
            print(f"[WARN] Send attempt {attempt}/{SMTP_MAX_ATTEMPTS} failed: {err}")
            if attempt < SMTP_MAX_ATTEMPTS:
                time.sleep(3 * attempt)

    log_automation_event("ERROR", "FAILED - All SMTP retry attempts exhausted (internet down?)")
    return False


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def run_stock_alert_pipeline(
    csv_path: Optional[Path] = None,
    dry_run: bool = False,
    force: bool = False,
    recipient_override: Optional[str] = None,
    scheduled: bool = False,
    run_time: str = DEFAULT_RUN_TIME,
    sender: Optional[SendFunc] = None,
    now: Optional[datetime] = None,
) -> int:
    """Fetch CSV -> find shortages -> email -> log. Holds a lock for the whole run.

    Returns 0 on success/skip, 1 on data error, 2 on email delivery failure.
    `scheduled=True` (used by the Windows task / cron) sends at most ONE alert per day
    and never before `run_time`, so the 30-minute retries are always safe.
    """
    lock = RunLock()
    if not lock.acquire():
        log_automation_event("INFO", "SKIPPED - Another stock-alert run is already in progress")
        print("[SKIPPED] Another run is already in progress.")
        return 0
    try:
        return _run_pipeline_locked(
            csv_path or DEFAULT_CSV_PATH, dry_run, force, recipient_override,
            scheduled, run_time, sender or send_stock_alert_email, now or datetime.now(),
        )
    finally:
        lock.release()


def _run_pipeline_locked(
    csv_path: Path,
    dry_run: bool,
    force: bool,
    recipient_override: Optional[str],
    scheduled: bool,
    run_time: str,
    sender: SendFunc,
    now: datetime,
) -> int:
    if scheduled and not force:
        hour, minute = (int(p) for p in run_time.split(":"))
        if now < now.replace(hour=hour, minute=minute, second=0, microsecond=0):
            print(f"[SKIPPED] Scheduled run before {run_time}; waiting for the {run_time} run.")
            return 0
        if not dry_run and already_alerted_today(now=now):
            print("[SKIPPED] Today's scheduled alert has already been sent.")
            return 0

    try:
        if dry_run and csv_path.resolve() == DEFAULT_CSV_PATH.resolve():
            # Sample data is only ever created in a preview. A real run with a missing
            # sheet must fail loudly, never email made-up shortages to the clinic.
            setup_sample_inventory_csv(csv_path)
        report = analyze_clinic_stock(csv_path, now=now)
    except FileNotFoundError as err:
        log_automation_event("ERROR", f"FAILED - {err}")
        print(f"[ERROR] {err}")
        print("        Save the clinic's stock sheet there, or run once with --dry-run to create the sample.")
        return 1
    except (ValueError, OSError) as err:
        log_automation_event("ERROR", f"FAILED - Data error: {err}")
        print(f"[ERROR] {err}")
        return 1

    if report["empty_dataset"]:
        # Exit 0 (no crash), but logged as a WARNING: an empty stock sheet means no
        # alerts at all, which is a smoke alarm with the battery out.
        log_automation_event(
            "WARNING",
            f"EMPTY - Inventory CSV '{csv_path.name}' has 0 valid items "
            f"(skipped_rows={report['skipped_rows']}); no alert sent",
        )
        print(f"[WARN] Inventory file '{csv_path.name}' has 0 valid items. Handled gracefully; nothing sent.")
        return 0

    below_items = report["below_minimum_items"]
    total_checked = report["total_items_checked"]

    if not below_items:
        log_automation_event(
            "INFO",
            f"OK - All {total_checked} clinic items at or above minimum stock "
            f"({len(report['at_minimum_items'])} exactly at minimum); no alert needed",
        )
        print(f"[OK] All {total_checked} items are adequately stocked.")
        return 0

    fingerprint = compute_alert_fingerprint(report, now=now)
    if not force and not dry_run and is_duplicate_run(fingerprint):
        log_automation_event(
            "INFO",
            f"SKIPPED - Duplicate prevented (alert already sent today for the same {len(below_items)} low-stock items)",
        )
        print("[SKIPPED] Alert already sent today for this exact stock state (use --force to resend).")
        return 0

    plain_body, html_body = build_stock_alert_bodies(report)
    print(plain_body)
    print("-" * 68)

    try:
        HTML_PREVIEW_PATH.write_text(html_body, encoding="utf-8")
        print(f"[PREVIEW] Saved HTML preview to: {HTML_PREVIEW_PATH}")
    except OSError as err:
        print(f"[WARN] Could not save HTML preview: {err}")

    if dry_run:
        log_automation_event(
            "INFO", f"OK - Dry run processed {total_checked} items ({len(below_items)} below minimum)"
        )
        print("[DRY RUN] Email dispatch skipped.")
        return 0

    raw_to = recipient_override or os.getenv("REPORT_RECIPIENT_EMAIL") or os.getenv("GMAIL_ADDRESS", "")
    recipients = _parse_recipients(raw_to)
    if not recipients:
        log_automation_event("ERROR", "FAILED - No valid recipient email configured")
        print("[ERROR] No valid recipient email configured (REPORT_RECIPIENT_EMAIL in .env or --to).")
        return 2

    critical_count = sum(1 for item in below_items if item["severity"] == "CRITICAL")
    tag = "[URGENT RESTOCK]" if critical_count else "[RESTOCK]"
    subject = (
        f"{tag} Kilimani Vet Clinic - {len(below_items)} Item(s) Below Minimum"
        + (f" ({critical_count} Critical)" if critical_count else "")
    )
    if sender(recipients, subject, plain_body, html_body):
        record_successful_run(fingerprint, len(below_items), now=now)
        log_automation_event(
            "INFO",
            f"OK - Processed {total_checked} items ({len(below_items)} flagged, {critical_count} critical, "
            f"skipped_rows={report['skipped_rows']}, trigger={'scheduled' if scheduled else 'manual'})",
        )
        return 0
    return 2


# ---------------------------------------------------------------------------
# Step 3 verification suite (runs in a temp folder; never touches real files)
# ---------------------------------------------------------------------------
@contextlib.contextmanager
def _isolated_runtime(folder: Path) -> Iterator[None]:
    """Points every runtime path at a temp folder for the duration of a test."""
    global DEFAULT_CSV_PATH, HTML_PREVIEW_PATH, AUTOMATION_LOG_PATH, STATE_FILE_PATH, LOCK_FILE_PATH
    saved = (DEFAULT_CSV_PATH, HTML_PREVIEW_PATH, AUTOMATION_LOG_PATH, STATE_FILE_PATH, LOCK_FILE_PATH)
    DEFAULT_CSV_PATH = folder / "pet_clinic_inventory.csv"
    HTML_PREVIEW_PATH = folder / "pet_clinic_stock_preview.html"
    AUTOMATION_LOG_PATH = folder / "pet_clinic_automation.log"
    STATE_FILE_PATH = folder / "pet_clinic_state.json"
    LOCK_FILE_PATH = folder / "pet_clinic_scheduler.lock"
    try:
        yield
    finally:
        DEFAULT_CSV_PATH, HTML_PREVIEW_PATH, AUTOMATION_LOG_PATH, STATE_FILE_PATH, LOCK_FILE_PATH = saved


class _FakeSender:
    """Stands in for Gmail during tests: counts emails instead of sending them."""

    def __init__(self, succeed: bool = True):
        self.succeed = succeed
        self.calls: List[Tuple[List[str], str]] = []

    def __call__(self, recipients: List[str], subject: str, plain: str, html_body: str) -> bool:
        self.calls.append((recipients, subject))
        return self.succeed


def _check(condition: bool, message: str) -> None:
    # Explicit check instead of `assert`, which `python -O` silently removes.
    if not condition:
        raise AssertionError(message)


def _write_csv(path: Path, rows: List[Tuple[str, object, object]], encoding: str = "utf-8",
               header: str = "item name,current stock,minimum stock", delimiter: str = ",") -> Path:
    lines = [header] + [delimiter.join(str(v) for v in row) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding=encoding)
    return path


def _test_client_data(tmp: Path) -> str:
    setup_sample_inventory_csv(DEFAULT_CSV_PATH)
    rep = analyze_clinic_stock(DEFAULT_CSV_PATH)
    below = {i["item_name"]: i for i in rep["below_minimum_items"]}
    _check(rep["total_items_checked"] == 12, f"expected 12 items, got {rep['total_items_checked']}")
    _check(len(below) == 8, f"expected 8 below minimum, got {len(below)}")
    crit = sorted(n for n, i in below.items() if i["severity"] == "CRITICAL")
    _check(crit == ["Canine Parvovirus Rapid Ag Test Kits", "Ketamine HCl 100mg/ml Injectable (Vials)"],
           f"unexpected CRITICAL items {crit}")
    amox = below["Amoxicillin-Clavulanate 250mg (Tablets)"]
    _check(amox["restock_needed"] == 55 and amox["recommended_order"] == 80, "Amoxicillin maths wrong")
    dhppi = below["Nobivac DHPPi Canine Vaccine (Doses)"]
    _check(dhppi["recommended_order"] == 13, "DHPPi: 15 + 25% rounded up = 19, so order 13")
    _check(rep["below_minimum_items"][0]["severity"] == "CRITICAL", "CRITICAL items must be listed first")
    return "12 items checked, 8 low-stock (2 CRITICAL), deficit and +25% order maths correct"


def _test_empty_data(tmp: Path) -> str:
    sender = _FakeSender()
    header_only = _write_csv(tmp / "header_only.csv", [])
    blank = tmp / "blank.csv"
    blank.write_bytes(b"")
    excel_blank_rows = _write_csv(tmp / "excel_blank.csv", [("", "", ""), ("", "", "")])
    for path in (header_only, blank, excel_blank_rows):
        code = run_stock_alert_pipeline(csv_path=path, recipient_override="vet@example.com", sender=sender)
        _check(code == 0, f"{path.name}: expected exit 0, got {code}")
    _check(not sender.calls, "an empty sheet must never send an email")
    _check("EMPTY" in AUTOMATION_LOG_PATH.read_text(encoding="utf-8"), "empty sheet must be logged as WARNING")
    return "header-only, 0-byte and blank-rows CSVs exit 0, no email, WARNING logged"


def _test_three_consecutive_runs(tmp: Path) -> str:
    setup_sample_inventory_csv(DEFAULT_CSV_PATH)
    sender = _FakeSender()
    codes = [run_stock_alert_pipeline(recipient_override="vet@example.com", sender=sender) for _ in range(3)]
    _check(codes == [0, 0, 0], f"exit codes {codes}")
    _check(len(sender.calls) == 1, f"expected exactly 1 email from 3 runs, got {len(sender.calls)}")
    skipped = AUTOMATION_LOG_PATH.read_text(encoding="utf-8").count("SKIPPED - Duplicate")
    _check(skipped == 2, f"expected 2 duplicate skips in the log, got {skipped}")
    _check(load_state().get("items_below_minimum") == 8, "state file not written")
    return "real pipeline run 3x: 1 email sent, 2 duplicates blocked and logged"


def _test_boundaries(tmp: Path) -> str:
    path = _write_csv(tmp / "edges.csv", [
        ("Exactly At Minimum", 10, 10),
        ("One Below Minimum", 9, 10),
        ("Zero Minimum Item", 0, 0),
        ("Out Of Stock", 0, 4),
        ("Duplicate Row", 8, 10),
        ("duplicate row", 6, 12),
        ("Negative Stock", -1, 5),
        ("Text Stock", "five", 5),
        ("Half Unit", 2.5, 5),
        ("", 1, 5),
        ('"1,200 Syringes"', '"1,000"', '"1,200"'),
    ])
    rep = analyze_clinic_stock(path)
    below = {i["item_name"]: i for i in rep["below_minimum_items"]}
    _check("Exactly At Minimum" not in below, "current == minimum must NOT be flagged")
    _check([i["item_name"] for i in rep["at_minimum_items"]] == ["Exactly At Minimum"], "watch list wrong")
    _check(below["One Below Minimum"]["restock_needed"] == 1, "current = minimum - 1 must be flagged")
    _check("Zero Minimum Item" not in below, "minimum 0 must never be flagged")
    _check(below["Out Of Stock"]["severity"] == "CRITICAL", "0 units must be CRITICAL")
    dup = below["Duplicate Row"]
    _check((dup["current_stock"], dup["minimum_stock"]) == (6, 12), "duplicates must merge conservatively")
    _check(rep["skipped_rows"] == 4, f"expected 4 skipped rows, got {rep['skipped_rows']}")
    _check(below["1,200 Syringes"]["restock_needed"] == 200, "thousands separators must parse")
    _check(calculate_recommended_order(9, 10) == (13, 4), "10 + 25% must round UP to 13")
    _check(calculate_recommended_order(0, 1) == (3, 3), "small minimums get at least +2 buffer")
    return "== minimum not flagged (watch list), minimum 0, out of stock, duplicates, bad rows, 1,200 parsing"


def _test_windows_excel_files(tmp: Path) -> str:
    cp = _write_csv(tmp / "cp1252.csv", [("Vacuna Antirrábica (Vials)", 1, 5)], encoding="cp1252",
                    header="Item_Name,Current Stock,MINIMUM STOCK")
    rep = analyze_clinic_stock(cp)
    _check(rep["below_minimum_items"][0]["item_name"] == "Vacuna Antirrábica (Vials)", "cp1252 decode failed")
    semi = _write_csv(tmp / "semicolon.csv", [("Gauze Swabs", 3, 9)],
                      header="item name;current stock;minimum stock", delimiter=";")
    _check(len(analyze_clinic_stock(semi)["below_minimum_items"]) == 1, "semicolon CSV failed")
    bad = _write_csv(tmp / "bad_cols.csv", [], header="product,qty")
    try:
        analyze_clinic_stock(bad)
        _check(False, "wrong columns must raise ValueError")
    except ValueError:
        pass
    xss = _write_csv(tmp / "xss.csv", [("<script>alert(1)</script> & Co", 0, 5)])
    _, body = build_stock_alert_bodies(analyze_clinic_stock(xss))
    _check("<script>" not in body and "&lt;script&gt;" in body, "item names must be HTML-escaped")
    return "cp1252 accents, Item_Name headers, ';' delimiter, wrong columns, HTML escaping"


def _test_new_shortage_and_force(tmp: Path) -> str:
    path = _write_csv(tmp / "changing.csv", [("Rabies Vaccine", 2, 10)])
    sender = _FakeSender()
    run_stock_alert_pipeline(csv_path=path, recipient_override="vet@example.com", sender=sender)
    _write_csv(path, [("Rabies Vaccine", 2, 10), ("Ketamine", 1, 6)])
    run_stock_alert_pipeline(csv_path=path, recipient_override="vet@example.com", sender=sender)
    _check(len(sender.calls) == 2, "a NEW shortage the same day must send a fresh alert")
    run_stock_alert_pipeline(csv_path=path, recipient_override="vet@example.com", sender=sender)
    _check(len(sender.calls) == 2, "identical state must not resend")
    run_stock_alert_pipeline(csv_path=path, recipient_override="vet@example.com", sender=sender, force=True)
    _check(len(sender.calls) == 3, "--force must resend")
    return "new shortage resends, identical state does not, --force overrides"


def _test_scheduled_mode(tmp: Path) -> str:
    setup_sample_inventory_csv(DEFAULT_CSV_PATH)
    sender = _FakeSender()
    day = datetime(2026, 11, 16)
    kwargs = dict(recipient_override="vet@example.com", sender=sender, scheduled=True, run_time="07:00")
    run_stock_alert_pipeline(now=day.replace(hour=6, minute=40), **kwargs)
    _check(not sender.calls, "a scheduled run before 07:00 must wait")
    run_stock_alert_pipeline(now=day.replace(hour=8, minute=5), **kwargs)  # PC switched on late
    _check(len(sender.calls) == 1, "a late (catch-up) scheduled run must send")
    _write_csv(DEFAULT_CSV_PATH, [("Ketamine", 0, 6)])
    run_stock_alert_pipeline(now=day.replace(hour=8, minute=35), **kwargs)  # 30-min retry
    _check(len(sender.calls) == 1, "scheduled retries must send at most once per day")
    run_stock_alert_pipeline(now=day.replace(day=17, hour=7, minute=0), **kwargs)
    _check(len(sender.calls) == 2, "the next morning must send again")
    return "waits until 07:00, catches up if PC was off, once per day, next day sends"


def _test_overlap_lock(tmp: Path) -> str:
    setup_sample_inventory_csv(DEFAULT_CSV_PATH)
    sender = _FakeSender()
    holder = RunLock()
    _check(holder.acquire(), "could not take the test lock")
    try:
        code = run_stock_alert_pipeline(recipient_override="vet@example.com", sender=sender)
    finally:
        holder.release()
    _check(code == 0 and not sender.calls, "a second run must step aside while one is running")
    run_stock_alert_pipeline(recipient_override="vet@example.com", sender=sender)
    _check(len(sender.calls) == 1, "lock must be released after the run")
    return "second run steps aside while one holds the lock; lock released afterwards"


def _test_failures(tmp: Path) -> str:
    sender = _FakeSender()
    code = run_stock_alert_pipeline(recipient_override="vet@example.com", sender=sender)
    _check(code == 1 and not DEFAULT_CSV_PATH.exists(), "missing CSV on a real run: exit 1, no fake sample")
    setup_sample_inventory_csv(DEFAULT_CSV_PATH)
    failing = _FakeSender(succeed=False)
    code = run_stock_alert_pipeline(recipient_override="vet@example.com", sender=failing)
    _check(code == 2 and not STATE_FILE_PATH.exists(), "failed send: exit 2 and nothing recorded")
    code = run_stock_alert_pipeline(recipient_override="vet@example.com", sender=sender)
    _check(code == 0 and len(sender.calls) == 1, "after a failed send the next run must retry")
    code = run_stock_alert_pipeline(recipient_override="not-an-email", sender=_FakeSender(), force=True)
    _check(code == 2, "invalid recipient must exit 2")
    return "missing sheet exits 1 without fake data; failed send exits 2 and is retried"


def _test_time_parsing(tmp: Path) -> str:
    good = {"07:00": "07:00", "7:00": "07:00", "7am": "07:00", "6:30 PM": "18:30", "12am": "00:00"}
    for raw, expected in good.items():
        _check(parse_run_time(raw) == expected, f"{raw!r} should parse to {expected}")
    for raw in ("25:00", "7", "13pm", "seven"):
        try:
            parse_run_time(raw)
            _check(False, f"{raw!r} should be rejected")
        except argparse.ArgumentTypeError:
            pass
    return "7:00 / 7am / 6:30 PM accepted, 25:00 and '7' rejected"


def run_step3_verification_suite() -> int:
    """Step 3 checks plus edge cases. Each test gets its own temp folder."""
    tests = [
        ("Test 1 (Client Data)", _test_client_data),
        ("Test 2 (Empty Data)", _test_empty_data),
        ("Test 3 (3x Consecutive Runs)", _test_three_consecutive_runs),
        ("Test 4 (Min-Stock Boundaries)", _test_boundaries),
        ("Test 5 (Windows/Excel CSVs)", _test_windows_excel_files),
        ("Test 6 (New Shortage + --force)", _test_new_shortage_and_force),
        ("Test 7 (Scheduled Once-a-Day)", _test_scheduled_mode),
        ("Test 8 (Overlap Lock)", _test_overlap_lock),
        ("Test 9 (Failure Handling)", _test_failures),
        ("Test 10 (--time Parsing)", _test_time_parsing),
    ]
    print("=" * 68)
    print("   STEP 3 AUTOMATED VERIFICATION SUITE (NAIROBI PET CLINIC)")
    print("   Runs in a temp folder: your real CSV, log and state are untouched.")
    print("=" * 68)
    failures = 0
    for label, func in tests:
        with tempfile.TemporaryDirectory(prefix="petclinic_test_") as tmp_name:
            tmp = Path(tmp_name)
            with _isolated_runtime(tmp), contextlib.redirect_stdout(io.StringIO()):
                try:
                    detail, error = func(tmp), None
                except Exception as err:  # report every failure, keep going
                    detail, error = None, f"{type(err).__name__}: {err}"
        if error:
            failures += 1
            print(f"[FAIL] {label}: {error}")
        else:
            print(f"[PASS] {label}: {detail}")
    print("=" * 68)
    if failures:
        print(f"   {failures} CHECK(S) FAILED")
    else:
        print(f"   ALL {len(tests)} CHECKS PASSED (including the 3 Step 3 mandatory checks)")
    print("=" * 68)
    return 1 if failures else 0


# ---------------------------------------------------------------------------
# Scheduling (Windows Task Scheduler / Linux cron)
# ---------------------------------------------------------------------------
def build_task_arguments(run_time: str, csv_path: Path, recipient: Optional[str]) -> List[str]:
    args = [str(Path(__file__).resolve()), "--scheduled", "--time", run_time]
    if csv_path.resolve() != DEFAULT_CSV_PATH.resolve():
        args += ["--csv", str(csv_path.resolve())]
    if recipient:
        args += ["--to", recipient]
    return args


def windowless_python() -> Path:
    """pythonw.exe runs without a black console window that clinic staff might close mid-run."""
    exe = Path(sys.executable).absolute()  # NOT .resolve(): that can escape a virtualenv
    candidate = exe.with_name("pythonw.exe")
    return candidate if candidate.is_file() else exe


def current_windows_user() -> str:
    domain = os.environ.get("USERDOMAIN", "")
    user = os.environ.get("USERNAME", "")
    return f"{domain}\\{user}" if domain and user else user


def build_task_xml(run_time: str, command: Path, arguments: str, user_id: str) -> str:
    start = f"{datetime.now():%Y-%m-%d}T{run_time}:00"
    e = xml_escape
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Kimnovix pet clinic stock alert. Runs at {run_time}, retries every 30 min for 4 hours, and catches up at logon if the PC was off. Sends at most once per day.</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <Repetition>
        <Interval>{RETRY_EVERY}</Interval>
        <Duration>{RETRY_FOR}</Duration>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>{start}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>{e(user_id)}</UserId>
      <Delay>PT3M</Delay>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{e(user_id)}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{e(str(command))}</Command>
      <Arguments>{e(arguments)}</Arguments>
      <WorkingDirectory>{e(str(ROOT_DIR))}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def _run_schtasks(cmd: List[str]) -> Tuple[int, str]:
    res = subprocess.run(cmd, capture_output=True, text=True, errors="replace", check=False)
    return res.returncode, (res.stderr or res.stdout or "").strip()


def print_crontab_lines(run_time: str, task_args: List[str]) -> int:
    hour, minute = (int(part) for part in run_time.split(":"))
    command = (f"cd {shlex.quote(str(ROOT_DIR))} && {shlex.quote(str(Path(sys.executable).absolute()))} "
               + " ".join(shlex.quote(a) for a in task_args))
    print("[LINUX CRON] Run `crontab -e` and add BOTH lines:")
    print(f"{minute} {hour} * * * {command} >/dev/null 2>&1")
    print(f"*/30 * * * * {command} >/dev/null 2>&1")
    print("[INFO] Line 1 is the on-time run. Line 2 retries and catches up after the PC was off;")
    print("       --scheduled makes it send at most once per day and never before the set time.")
    print("       Results go to week5/pet_clinic_automation.log, so cron output is discarded.")
    return 0


def install_windows_task(run_time: str = DEFAULT_RUN_TIME, csv_path: Optional[Path] = None,
                         recipient: Optional[str] = None) -> int:
    """Registers the daily stock alert in Windows Task Scheduler (or prints cron lines on Linux)."""
    csv_path = csv_path or DEFAULT_CSV_PATH
    task_args = build_task_arguments(run_time, csv_path, recipient)
    if sys.platform != "win32":
        return print_crontab_lines(run_time, task_args)

    for legacy in LEGACY_TASK_NAMES:  # an older "_7AM" task would send a second copy
        _run_schtasks(["schtasks", "/Delete", "/TN", legacy, "/F"])

    python_exe = windowless_python()
    arguments = subprocess.list2cmdline(task_args)  # Windows-correct quoting for spaces/quotes
    xml_text = build_task_xml(run_time, python_exe, arguments, current_windows_user())
    xml_file = Path(tempfile.gettempdir()) / f"{WINDOWS_TASK_NAME}.xml"
    try:
        xml_file.write_text(xml_text, encoding="utf-16")  # schtasks /XML insists on UTF-16
        code, output = _run_schtasks(["schtasks", "/Create", "/TN", WINDOWS_TASK_NAME,
                                      "/XML", str(xml_file), "/F"])
    except OSError as err:
        code, output = 1, str(err)
    finally:
        with contextlib.suppress(OSError):
            xml_file.unlink()

    if code == 0:
        print(f"[INSTALLED] Task '{WINDOWS_TASK_NAME}': daily at {run_time}, retries every 30 min for 4 h,")
        print("            catch-up 3 min after logon, starts late if the PC was off. Sends once per day.")
        print(f"            Program  : {python_exe}")
        print(f"            Arguments: {arguments}")
        print(f"            Test it now: schtasks /Run /TN {WINDOWS_TASK_NAME}")
        return 0

    print(f"[WARN] Full task setup was refused ({output}). Falling back to a basic daily task.")
    task_command = subprocess.list2cmdline([str(python_exe)] + task_args)
    if len(task_command) > SCHTASKS_TR_LIMIT:
        print(f"[ERROR] Command is {len(task_command)} characters; schtasks allows {SCHTASKS_TR_LIMIT}. "
              "Move the repo to a shorter folder (e.g. C:\\kimnovix) and try again.")
        return 1
    code, output = _run_schtasks(["schtasks", "/Create", "/SC", "DAILY", "/TN", WINDOWS_TASK_NAME,
                                  "/TR", task_command, "/ST", run_time, "/F"])
    if code == 0:
        print(f"[INSTALLED] Basic task '{WINDOWS_TASK_NAME}' at {run_time} daily (no automatic catch-up).")
        print("            Tip: Task Scheduler > Properties > Settings > tick")
        print("            'Run task as soon as possible after a scheduled start is missed'.")
        return 0
    print(f"[ERROR] Failed to register task: {output}")
    return 1


def uninstall_windows_task() -> int:
    if sys.platform != "win32":
        print("[INFO] On Linux, run `crontab -e` and delete the two day25 lines.")
        return 0
    removed = False
    for name in (WINDOWS_TASK_NAME,) + LEGACY_TASK_NAMES:
        code, _ = _run_schtasks(["schtasks", "/Delete", "/TN", name, "/F"])
        if code == 0:
            print(f"[REMOVED] Task '{name}' deleted.")
            removed = True
    if not removed:
        print("[INFO] No pet clinic stock-alert task was registered.")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automated Daily Dispensary Stock Alert for a Nairobi Pet Clinic."
    )
    parser.add_argument("--csv", type=Path, default=None, help="Path to inventory CSV.")
    parser.add_argument("--dry-run", action="store_true", help="Preview alert without sending email.")
    parser.add_argument("--force", action="store_true", help="Send even if already alerted today.")
    parser.add_argument("--to", type=str, default=None, help="Override recipient email address(es).")
    parser.add_argument("--time", type=parse_run_time, default=DEFAULT_RUN_TIME,
                        help="Daily run time, e.g. 07:00 or 7am (default 07:00).")
    parser.add_argument("--scheduled", action="store_true",
                        help="Used by the scheduled task: send at most once per day, never before --time.")
    parser.add_argument("--daemon", action="store_true", help="Run continuously using `schedule` (keep window open).")
    parser.add_argument("--install-task", action="store_true", help="Register in Windows Task Scheduler / print cron.")
    parser.add_argument("--uninstall-task", action="store_true", help="Remove the Windows scheduled task.")
    parser.add_argument("--self-test", action="store_true", help="Run the Step 3 verification suite.")
    return parser.parse_args(argv)


def run_daemon(args: argparse.Namespace, csv_path: Path) -> int:
    import schedule  # only needed here; the scheduled task does not use it

    if args.force:
        print("[INFO] --force is ignored in --daemon mode, or it would resend every morning regardless.")
    print(f"[DAEMON] Pet Clinic Stock Alert active (daily at {args.time}). Press Ctrl+C to stop.")
    print("         Tip: --install-task is more reliable; it survives restarts and closed windows.")

    def job() -> None:
        try:
            run_stock_alert_pipeline(csv_path=csv_path, dry_run=args.dry_run, recipient_override=args.to)
        except Exception as err:  # one bad morning must not kill the daemon
            log_automation_event("ERROR", f"FAILED - Unexpected daemon error: {type(err).__name__}: {err}")
            print(f"[ERROR] {err}")

    schedule.clear()
    schedule.every().day.at(args.time).do(job)
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        print("[DAEMON] Stopped.")
        return 0


def main(argv: Optional[List[str]] = None) -> int:
    make_console_unicode_safe()
    args = parse_args(argv)
    csv_path = (args.csv or DEFAULT_CSV_PATH).expanduser().resolve()

    if args.self_test:
        return run_step3_verification_suite()
    if args.uninstall_task:
        return uninstall_windows_task()
    if args.install_task:
        return install_windows_task(run_time=args.time, csv_path=csv_path, recipient=args.to)
    if args.daemon:
        return run_daemon(args, csv_path)

    return run_stock_alert_pipeline(
        csv_path=csv_path,
        dry_run=args.dry_run,
        force=args.force,
        recipient_override=args.to,
        scheduled=args.scheduled,
        run_time=args.time,
    )


if __name__ == "__main__":
    sys.exit(main())
