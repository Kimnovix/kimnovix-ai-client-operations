"""
Week 7 - Day 33: Weekly Livestock Digest (Email, Config, Scheduling & Tests)
----------------------------------------------------------------------------
Wraps `week7/weekly_livestock_core.py` without re-implementing CSV loading or
KPI calculations:
  1. Loads client settings and alert thresholds from `config.env` (UTF-8, BOM,
     UTF-16, or Windows-1252) with plain-English validation.
  2. Builds a multipart HTML + plain-text email strictly from `ReportResult.report`
     (numbers-only email when `ai_summary is None`; short notice on no-data weeks).
  3. Sends via Gmail SMTP (SSL on 465, STARTTLS on 587) with retries on
     transient errors, never retrying bad passwords, refused recipients or
     certificate failures, and saves a local HTML preview.
  4. Prevents overlapping runs (OS file lock) and duplicate weekly sends
     (`digest_state.json`), and installs a Monday 07:00 EAT scheduled task with
     power-cut catch-up. A no-data notice does not block the full digest: once
     the CSV arrives, the next scheduled retry sends the real report.

Run from the repository root (Python 3.13 venv):
    python week7\\weekly_livestock_digest.py --self-test
    python week7\\weekly_livestock_digest.py --check-config
    python week7\\weekly_livestock_digest.py --week-ending 2026-11-22 --dry-run
    python week7\\weekly_livestock_digest.py --week-ending 2026-11-22
    python week7\\weekly_livestock_digest.py --install-task
    python week7\\weekly_livestock_digest.py --status
"""

import argparse
import contextlib
import hashlib
import html
import io
import json
import os
import re
import shlex
import smtplib
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape as xml_escape

from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import weekly_livestock_core as core
from weekly_livestock_core import (
    AI_UNAVAILABLE_LINE,
    ReportResult,
    format_kpi_report,
    generate_weekly_report,
)

DEFAULT_CONFIG_PATH = BASE_DIR / "config.env"
DIGEST_LOG_PATH = BASE_DIR / "digest.log"
DIGEST_STATE_PATH = BASE_DIR / "digest_state.json"
DIGEST_LOCK_PATH = BASE_DIR / "digest.lock"
PREVIEW_HTML_PATH = BASE_DIR / "digest_preview.html"
LOG_MAX_BYTES = 1_000_000

WINDOWS_TASK_NAME = "Kimnovix_Weekly_Livestock_Digest"
TASK_RETRY_EVERY = "PT30M"
TASK_RETRY_FOR = "PT4H"
SMTP_TIMEOUT_SECONDS = 30.0
SMTP_BACKOFF_DELAYS: Tuple[float, ...] = (2.0, 4.0)
SMTP_SSL_PORT = 465
MAX_RECIPIENTS = 20

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
SECTION_CODE_PATTERN = re.compile(r"^[A-Z0-9_]{2,24}$")
RESERVED_SECTION_CODES = {"FARM"}  # the core engine uses FARM for the farm-wide total
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
PLACEHOLDER_VALUES = {
    "",
    "your_key_here",
    "sk-ant-paste-your-real-key-here",
    "paste-16-char-app-password",
    "abcd efgh ijkl mnop",
    "your.farm.reports@gmail.com",
}
# Reserved documentation domains used in config.env.example; never real inboxes.
PLACEHOLDER_EMAIL_DOMAINS = ("@example.com", "@example.org", "@example.net")
KNOWN_CONFIG_KEYS = frozenset(
    {
        "CLIENT_NAME", "DATA_PATH", "SECTIONS", "MORTALITY_ALERT_PCT",
        "FEED_USE_WATCH_PCT", "FEED_PRICE_WATCH_PCT", "FEED_PRICE_MIN_KES", "FEED_PRICE_MAX_KES",
        "ANTHROPIC_API_KEY", "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "SENDER_NAME",
        "REPORT_RECIPIENTS", "SCHEDULE_TIME", "SMTP_HOST", "SMTP_PORT",
    }
)

_LOG_LOCK = threading.Lock()


@dataclass(frozen=True)
class DigestConfig:
    client_name: str
    data_paths: Tuple[Path, ...]
    sections: Tuple[str, ...]
    mortality_alert_pct: Dict[str, Decimal]
    feed_use_watch_pct: Decimal
    feed_price_watch_pct: Decimal
    feed_price_min_kes: Decimal
    feed_price_max_kes: Decimal
    anthropic_api_key: str
    gmail_address: str
    gmail_app_password: str
    sender_name: str
    recipients: Tuple[str, ...]
    schedule_hour: int
    schedule_minute: int
    smtp_host: str
    smtp_port: int
    warnings: Tuple[str, ...] = ()  # non-fatal notes, e.g. a misspelt setting name

    @property
    def schedule_time_str(self) -> str:
        return f"{self.schedule_hour:02d}:{self.schedule_minute:02d}"


@dataclass(frozen=True)
class SmtpResult:
    attempts: int
    refused: int  # recipients Gmail refused while still delivering to the rest


@dataclass
class DigestRunOutcome:
    status: str  # "sent", "dry_run", "skipped_duplicate", "skipped_before_schedule", "skipped_locked", "error"
    exit_code: int
    iso_week: str = ""
    recipient_count: int = 0
    preview_path: Optional[Path] = None
    report_result: Optional[ReportResult] = None
    message: str = ""
    late_by: Optional[str] = None


class ConfigError(ValueError):
    """Plain-English configuration error listing every setting to fix."""


class EmailDeliveryError(RuntimeError):
    """Plain-English SMTP failure safe to show the farm admin."""


class OverlapLockError(RuntimeError):
    """Raised when another copy of the digest is already running."""


# --------------------------------------------------------------------------- #
# Logging, Atomic Writes & Process Lock
# --------------------------------------------------------------------------- #
def log_digest_event(level: str, message: str, log_path: Optional[Path] = None) -> None:
    """
    Thread-safe metadata logger rotated at ~1 MB.
    Never logs herd numbers, feed totals, notes, email addresses, or summary text.
    """
    target = log_path or DIGEST_LOG_PATH
    stamp = datetime.now(core.EAT).strftime("%Y-%m-%d %H:%M:%S")
    clean = " ".join(str(message).replace("\r", " ").replace("\n", " ").split())
    line = f"{stamp} | {level.upper()} | {clean}\n"
    with _LOG_LOCK:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_file() and target.stat().st_size > LOG_MAX_BYTES:
                target.replace(target.with_name(target.name + ".1"))
            with open(target, mode="a", encoding="utf-8", newline="") as handle:
                handle.write(line)
        except OSError as err:
            print(f"[WARN] Could not write log '{target}': {err}", file=sys.stderr)


def atomic_write_text(path: Path, content: str, allow_fallback: bool = True) -> Path:
    """Writes to a unique temp file in the target folder, then swaps with os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        last_err: Optional[OSError] = None
        for attempt in range(3):
            try:
                os.replace(tmp_path, path)
                return path
            except PermissionError as err:
                last_err = err
                time.sleep(0.05 * (attempt + 1))
        if allow_fallback:
            stamp = datetime.now(core.EAT).strftime("%Y%m%d_%H%M%S_%f")
            fallback = path.with_name(f"{path.stem}_{stamp}{path.suffix}")
            os.replace(tmp_path, fallback)
            return fallback
        assert last_err is not None
        raise last_err
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


@contextlib.contextmanager
def acquire_process_lock(lock_path: Path = DIGEST_LOCK_PATH) -> Iterator[None]:
    """Non-blocking OS file lock preventing overlapping manual/scheduled runs."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, mode="a+b")
    locked = False
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                locked = True
            except OSError as err:
                raise OverlapLockError("Another copy of the weekly digest is already running.") from err
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except BlockingIOError as err:
                raise OverlapLockError("Another copy of the weekly digest is already running.") from err
        yield
    finally:
        if locked:
            try:
                if os.name == "nt":
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


# --------------------------------------------------------------------------- #
# Config Loading & Validation (UTF-8 / BOM / UTF-16 / cp1252)
# --------------------------------------------------------------------------- #
def read_config_text(config_path: Path) -> str:
    try:
        raw = config_path.read_bytes()
    except OSError as err:
        raise ConfigError(
            f"Could not read '{config_path.name}' ({err.strerror or err}). "
            "Close any program that has it open and try again."
        ) from err
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return raw.decode("utf-16")
        except UnicodeDecodeError as err:
            raise ConfigError(
                f"'{config_path.name}' has broken UTF-16 text. Re-save it in Notepad as UTF-8."
            ) from err
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def parse_schedule_time(raw: str) -> Tuple[int, int]:
    text = raw.strip()
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text, re.IGNORECASE)
    if not match:
        raise ValueError(f"'{raw}' is not a valid time (use 07:00, 7am, or 7:30 AM)")
    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) is not None else 0
    meridiem = match.group(3).lower() if match.group(3) else None
    if meridiem is None and match.group(2) is None:
        raise ValueError(f"'{raw}' is ambiguous (use 07:00 or 7am)")
    if meridiem:
        if not (1 <= hour <= 12):
            raise ValueError(f"'{raw}' hour must be 1 to 12 with am/pm")
        if meridiem == "am":
            hour = 0 if hour == 12 else hour
        else:
            hour = 12 if hour == 12 else hour + 12
    elif not (0 <= hour <= 23):
        raise ValueError(f"'{raw}' hour must be 00 to 23")
    if not (0 <= minute <= 59):
        raise ValueError(f"'{raw}' minutes must be 00 to 59")
    return hour, minute


def _strip_header_breaks(text: str) -> str:
    """Removes CR/LF and every other control character so no value can add a header."""
    return " ".join(CONTROL_CHARS.sub(" ", text).split())


def parse_recipients(raw: str) -> Tuple[Tuple[str, ...], List[str]]:
    valid: List[str] = []
    invalid: List[str] = []
    seen = set()
    for part in raw.replace(";", ",").split(","):
        addr = part.strip()
        if not addr:
            continue
        if CONTROL_CHARS.search(addr) or not EMAIL_PATTERN.fullmatch(addr):
            invalid.append(addr)
            continue
        low = addr.lower()
        if low not in seen:
            seen.add(low)
            valid.append(addr)
    return tuple(valid), invalid


def load_and_validate_config(
    config_path: Path = DEFAULT_CONFIG_PATH,
    *,
    require_secrets: bool = True,
    to_override: Optional[str] = None,
    csv_override: Optional[Sequence[Path]] = None,
    time_override: Optional[str] = None,
) -> DigestConfig:
    """
    Loads `config.env` without mutating os.environ and reports all config issues
    together in plain English. Relative paths resolve from the config file folder.
    """
    if not config_path.is_file():
        hint = ""
        if config_path.with_name(config_path.name + ".txt").is_file():
            hint = (
                " Windows Notepad saved it as 'config.env.txt'. Turn on View > File name "
                "extensions in File Explorer and rename it to 'config.env'."
            )
        raise ConfigError(
            f"Could not find '{config_path.name}'. Copy 'config.env.example' to "
            f"'{config_path.name}' and fill in your farm settings.{hint}"
        )

    # interpolate=False: a '$' inside a password or key must stay a literal '$'.
    raw = dotenv_values(stream=io.StringIO(read_config_text(config_path)), interpolate=False)
    # The shipped config.env lives in week7/, so relative DATA_PATH values resolve
    # from week7/ (never from whatever folder the scheduler or terminal started in).
    config_dir = config_path.resolve().parent
    errors: List[str] = []
    warnings: List[str] = [
        f"Unknown setting '{key}' was ignored (check the spelling against config.env.example)."
        for key in raw
        if key not in KNOWN_CONFIG_KEYS
    ]

    def get_str(key: str, default: str = "") -> str:
        val = raw.get(key)
        val = val.strip() if isinstance(val, str) else ""
        return val or default

    client_name = _strip_header_breaks(get_str("CLIENT_NAME", core.CLIENT_NAME))

    # Data path(s)
    if csv_override:
        data_paths = tuple(p.expanduser().resolve() for p in csv_override)
    else:
        raw_paths = get_str("DATA_PATH", core.DEFAULT_CSV_PATH.name)
        resolved: List[Path] = []
        for token in raw_paths.split(","):
            item = token.strip()
            if not item:
                continue
            p = Path(item).expanduser()
            resolved.append(p if p.is_absolute() else (config_dir / p).resolve())
        data_paths = tuple(resolved) if resolved else (core.DEFAULT_CSV_PATH,)
    for p in data_paths:
        if not p.exists():
            errors.append(
                f"DATA_PATH '{p}' does not exist. Point it at the daily CSV file or the folder "
                "the farm clerk saves CSVs into."
            )

    # SECTIONS
    sections_raw = get_str("SECTIONS", ",".join(core.SECTIONS))
    parsed_sections: List[str] = []
    for tok in sections_raw.split(","):
        code = tok.strip().upper()
        if not code:
            continue
        if not SECTION_CODE_PATTERN.fullmatch(code):
            errors.append(
                f"SECTIONS contains invalid code '{tok.strip()}'. Use letters/numbers like WEANER."
            )
        elif code in RESERVED_SECTION_CODES:
            errors.append(
                f"SECTIONS cannot use '{code}'; that name is reserved for the farm-wide total."
            )
        elif code not in parsed_sections:
            parsed_sections.append(code)
    if not parsed_sections:
        errors.append("SECTIONS cannot be empty (example: BREEDING,FARROWING,WEANER,GROWER).")
        parsed_sections = list(core.SECTIONS)
    sections = tuple(parsed_sections)

    # MORTALITY_ALERT_PCT
    default_mort = ",".join(f"{k}:{v}" for k, v in core.MORTALITY_ALERT_PCT.items())
    mort_raw = get_str("MORTALITY_ALERT_PCT", default_mort)
    mort_map: Dict[str, Decimal] = {}
    for pair in mort_raw.split(","):
        item = pair.strip()
        if not item:
            continue
        if ":" not in item:
            errors.append(
                f"MORTALITY_ALERT_PCT entry '{item}' must use SECTION:PERCENT format (e.g. WEANER:1.00)."
            )
            continue
        sec_part, val_part = item.split(":", 1)
        sec_code = sec_part.strip().upper()
        try:
            pct = Decimal(val_part.strip())
            if not pct.is_finite() or pct < 0 or pct > 100:
                raise InvalidOperation("range")
        except InvalidOperation:
            errors.append(
                f"MORTALITY_ALERT_PCT for '{sec_code}' ('{val_part.strip()}') must be a number from 0 to 100."
            )
            continue
        if sec_code not in sections:
            errors.append(
                f"MORTALITY_ALERT_PCT lists unknown section '{sec_code}' (not in SECTIONS)."
            )
            continue
        if sec_code in mort_map:
            errors.append(
                f"MORTALITY_ALERT_PCT lists '{sec_code}' twice; keep one threshold per section."
            )
            continue
        mort_map[sec_code] = core.r2(pct)

    missing_mort = [s for s in sections if s not in mort_map]
    if missing_mort:
        errors.append(
            f"MORTALITY_ALERT_PCT is missing threshold(s) for: {', '.join(missing_mort)}."
        )

    def parse_pos_dec(key: str, default: Decimal) -> Decimal:
        text = get_str(key, str(default))
        try:
            val = Decimal(text)
            if not val.is_finite() or val <= 0:
                raise InvalidOperation("range")
            return core.r2(val)
        except InvalidOperation:
            errors.append(f"{key} ('{text}') must be a positive number (default: {default}).")
            return default

    feed_use_watch = parse_pos_dec("FEED_USE_WATCH_PCT", core.FEED_USE_WATCH_PCT)
    feed_price_watch = parse_pos_dec("FEED_PRICE_WATCH_PCT", core.FEED_PRICE_WATCH_PCT)
    feed_price_min = parse_pos_dec("FEED_PRICE_MIN_KES", core.FEED_PRICE_MIN_KES)
    feed_price_max = parse_pos_dec("FEED_PRICE_MAX_KES", core.FEED_PRICE_MAX_KES)
    if feed_price_min >= feed_price_max:
        errors.append(
            f"FEED_PRICE_MIN_KES ({feed_price_min}) must be lower than FEED_PRICE_MAX_KES ({feed_price_max})."
        )

    # Secrets & email settings
    api_key = get_str("ANTHROPIC_API_KEY")
    if require_secrets:
        if api_key.lower() in PLACEHOLDER_VALUES or "paste-your-real-key" in api_key.lower():
            errors.append(
                "ANTHROPIC_API_KEY is missing or still a placeholder. Paste your real key in config.env."
            )
        elif any(ch.isspace() for ch in api_key) or not api_key.isascii():
            errors.append("ANTHROPIC_API_KEY contains spaces or non-ASCII characters.")

    gmail_addr = get_str("GMAIL_ADDRESS")
    if require_secrets:
        if not gmail_addr or not EMAIL_PATTERN.fullmatch(gmail_addr):
            errors.append(
                f"GMAIL_ADDRESS ('{gmail_addr}') is not a valid email address. Update config.env."
            )
        elif gmail_addr.lower() in PLACEHOLDER_VALUES:
            errors.append("GMAIL_ADDRESS is still the example address. Use the farm's real Gmail account.")
    elif gmail_addr and not EMAIL_PATTERN.fullmatch(gmail_addr):
        errors.append(f"GMAIL_ADDRESS ('{gmail_addr}') is not a valid email address.")

    gmail_pw_raw = get_str("GMAIL_APP_PASSWORD")
    gmail_pw = gmail_pw_raw.replace(" ", "")
    if require_secrets:
        if gmail_pw_raw.lower() in PLACEHOLDER_VALUES or "paste-16-char" in gmail_pw_raw.lower():
            errors.append(
                "GMAIL_APP_PASSWORD is missing or still a placeholder. Create a 16-character "
                "Gmail App Password (with 2-Step Verification enabled) and paste it in config.env."
            )
        elif not gmail_pw.isascii() or len(gmail_pw) < 8:
            errors.append("GMAIL_APP_PASSWORD looks invalid. Paste your 16-character Gmail App Password.")

    sender_name = _strip_header_breaks(get_str("SENDER_NAME", f"{client_name} Reports"))

    rec_raw = to_override if to_override is not None else get_str("REPORT_RECIPIENTS")
    recipients, bad_recs = parse_recipients(rec_raw)
    if bad_recs:
        errors.append(
            f"REPORT_RECIPIENTS contains invalid email address(es): {', '.join(bad_recs)}. "
            "Check for typos and separate multiple emails with commas."
        )
    if require_secrets and not recipients:
        errors.append("REPORT_RECIPIENTS is blank. Add at least one manager email in config.env.")
    placeholder_recs = [r for r in recipients if r.lower().endswith(PLACEHOLDER_EMAIL_DOMAINS)]
    if require_secrets and placeholder_recs:
        errors.append(
            f"REPORT_RECIPIENTS still has example address(es): {', '.join(placeholder_recs)}. "
            "Replace them with the managers' real emails."
        )
    if len(recipients) > MAX_RECIPIENTS:
        errors.append(f"REPORT_RECIPIENTS has {len(recipients)} addresses; maximum is {MAX_RECIPIENTS}.")

    # Schedule & SMTP
    sched_raw = time_override if time_override is not None else get_str("SCHEDULE_TIME", "07:00")
    try:
        sched_hour, sched_minute = parse_schedule_time(sched_raw)
    except ValueError as err:
        errors.append(f"SCHEDULE_TIME: {err}.")
        sched_hour, sched_minute = 7, 0

    smtp_host = get_str("SMTP_HOST", "smtp.gmail.com")
    smtp_port_raw = get_str("SMTP_PORT", "465")
    try:
        smtp_port = int(smtp_port_raw)
        if not (1 <= smtp_port <= 65535):
            raise ValueError("range")
    except ValueError:
        errors.append(f"SMTP_PORT ('{smtp_port_raw}') must be a whole number between 1 and 65535.")
        smtp_port = 465

    if errors:
        bullets = "\n".join(f"  - {item}" for item in errors)
        raise ConfigError(f"Please fix the following setting(s) in {config_path.name}:\n{bullets}")

    return DigestConfig(
        client_name=client_name,
        data_paths=data_paths,
        sections=sections,
        mortality_alert_pct=mort_map,
        feed_use_watch_pct=feed_use_watch,
        feed_price_watch_pct=feed_price_watch,
        feed_price_min_kes=feed_price_min,
        feed_price_max_kes=feed_price_max,
        anthropic_api_key=api_key,
        gmail_address=gmail_addr or "preview@example.com",
        gmail_app_password=gmail_pw,
        sender_name=sender_name,
        recipients=recipients,
        schedule_hour=sched_hour,
        schedule_minute=sched_minute,
        smtp_host=_strip_header_breaks(smtp_host),
        smtp_port=smtp_port,
        warnings=tuple(warnings),
    )


@contextlib.contextmanager
def apply_core_config(cfg: DigestConfig) -> Iterator[None]:
    """Applies config.env thresholds/sections to `weekly_livestock_core` cleanly."""
    saved = {
        "CLIENT_NAME": core.CLIENT_NAME,
        "SECTIONS": core.SECTIONS,
        "MORTALITY_ALERT_PCT": core.MORTALITY_ALERT_PCT,
        "FEED_USE_WATCH_PCT": core.FEED_USE_WATCH_PCT,
        "FEED_PRICE_WATCH_PCT": core.FEED_PRICE_WATCH_PCT,
        "FEED_PRICE_MIN_KES": core.FEED_PRICE_MIN_KES,
        "FEED_PRICE_MAX_KES": core.FEED_PRICE_MAX_KES,
        "SYSTEM_PROMPT": core.SYSTEM_PROMPT,
    }
    try:
        core.SYSTEM_PROMPT = saved["SYSTEM_PROMPT"].replace(saved["CLIENT_NAME"], cfg.client_name)
        core.CLIENT_NAME = cfg.client_name
        core.SECTIONS = cfg.sections
        core.MORTALITY_ALERT_PCT = dict(cfg.mortality_alert_pct)
        core.FEED_USE_WATCH_PCT = cfg.feed_use_watch_pct
        core.FEED_PRICE_WATCH_PCT = cfg.feed_price_watch_pct
        core.FEED_PRICE_MIN_KES = cfg.feed_price_min_kes
        core.FEED_PRICE_MAX_KES = cfg.feed_price_max_kes
        yield
    finally:
        for attr, value in saved.items():
            setattr(core, attr, value)


# --------------------------------------------------------------------------- #
# Email Builder (HTML + Plain-Text Fallback, Strictly From ReportResult.report)
# --------------------------------------------------------------------------- #
def _build_subject(result: ReportResult, client_name: str) -> str:
    rep = result.report
    if not rep.has_data:
        raw = f"[NO DATA] {client_name} Weekly Digest {rep.iso_week} ({rep.week_end.isoformat()})"
    else:
        farm = rep.current["FARM"]
        spend = core.fmt_kes(core._rounded(farm, "feed_cost_kes"))
        flag_count = len(rep.flags)
        prefix = f"[{flag_count} ALERT{'S' if flag_count != 1 else ''}] " if flag_count else ""
        raw = f"{prefix}{client_name} Weekly Digest {rep.iso_week} - {spend}"
    return _strip_header_breaks(raw)


def _build_plain_body(result: ReportResult, client_name: str) -> str:
    rep = result.report
    if not rep.has_data:
        return (
            f"{client_name} - Weekly Production & Feed Cost Digest ({rep.iso_week})\n"
            f"Reporting Week: {rep.week_start.isoformat()} to {rep.week_end.isoformat()}\n\n"
            f"No daily operations records were found for week {rep.iso_week}.\n"
            "Action needed: confirm the farm clerk saved last week's daily CSV into the "
            "configured DATA_PATH folder. The scheduled task checks again every 30 minutes "
            "for 4 hours and at each login, and sends the full digest as soon as the rows arrive."
        )
    summary_block = result.ai_summary if result.ai_summary else AI_UNAVAILABLE_LINE
    return (
        f"{format_kpi_report(rep)}\n\n"
        + "=" * 78
        + "\nMANAGEMENT SUMMARY\n"
        + "-" * 78
        + f"\n{summary_block}\n"
    )


def _render_kpi_rows_html(rep: core.WeeklyReport, keys: Sequence[str]) -> str:
    rows_html: List[str] = []
    for key in keys:
        cur, prev = rep.current.get(key), rep.previous.get(key)
        label = html.escape(key)
        if cur is None:
            rows_html.append(
                f'<tr><td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600;">{label}</td>'
                '<td colspan="5" style="padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;">'
                "No rows received this week</td></tr>"
            )
            continue
        vals = [core._rounded(cur, m) for m, _lbl, _fmt in core.METRICS]
        chgs = [core.pct_change(core._rounded(cur, m), core._rounded(prev, m)) for m, _lbl, _fmt in core.METRICS]
        sub = (
            f"{cur.deaths} deaths / {cur.at_risk:,} at risk | "
            f"{cur.head_days:,} head-days | {core.r2(cur.feed_kg):,} kg | {cur.days}/7 days"
        )
        rows_html.append(
            "<tr>"
            f'<td style="padding:8px;border-bottom:1px solid #f3f4f6;font-weight:600;">{label}'
            f'<div style="font-size:11px;font-weight:400;color:#6b7280;">{html.escape(sub)}</div></td>'
            f'<td style="padding:8px;border-bottom:1px solid #f3f4f6;text-align:right;">{html.escape(core.fmt_pct(vals[0]))}'
            f'<div style="font-size:11px;color:#6b7280;">{html.escape(core.fmt_change(chgs[0]))}</div></td>'
            f'<td style="padding:8px;border-bottom:1px solid #f3f4f6;text-align:right;">{html.escape(core.fmt_num(vals[1]))}'
            f'<div style="font-size:11px;color:#6b7280;">{html.escape(core.fmt_change(chgs[1]))}</div></td>'
            f'<td style="padding:8px;border-bottom:1px solid #f3f4f6;text-align:right;font-weight:600;">{html.escape(core.fmt_kes(vals[2]))}'
            f'<div style="font-size:11px;font-weight:400;color:#6b7280;">{html.escape(core.fmt_change(chgs[2]))}</div></td>'
            f'<td style="padding:8px;border-bottom:1px solid #f3f4f6;text-align:right;">{html.escape(core.fmt_num(vals[3]))}'
            f'<div style="font-size:11px;color:#6b7280;">{html.escape(core.fmt_change(chgs[3]))}</div></td>'
            f'<td style="padding:8px;border-bottom:1px solid #f3f4f6;text-align:right;">{html.escape(core.fmt_num(vals[4]))}'
            f'<div style="font-size:11px;color:#6b7280;">{html.escape(core.fmt_change(chgs[4]))}</div></td>'
            "</tr>"
        )
    return "".join(rows_html)


def _build_html_body(result: ReportResult, client_name: str, sections: Sequence[str]) -> str:
    rep = result.report
    safe_client = html.escape(client_name)
    week_range = f"{rep.week_start.isoformat()} to {rep.week_end.isoformat()}"

    if not rep.has_data:
        return (
            "<!DOCTYPE html><html><body style=\"font-family:Arial,sans-serif;background:#f3f4f6;padding:20px;\">"
            "<div style=\"max-width:680px;margin:0 auto;background:#ffffff;border-radius:8px;overflow:hidden;border:1px solid #e5e7eb;\">"
            f"<div style=\"background:#92400e;color:#ffffff;padding:18px 22px;\">"
            f"<h2 style=\"margin:0;font-size:18px;\">{safe_client} - No Data Received</h2>"
            f"<p style=\"margin:4px 0 0;font-size:13px;\">Week {html.escape(rep.iso_week)} ({week_range})</p></div>"
            "<div style=\"padding:20px 22px;font-size:14px;line-height:1.5;color:#111827;\">"
            f"<p>No valid daily operations rows were found for week <strong>{html.escape(rep.iso_week)}</strong>.</p>"
            "<p>Please confirm the clerk saved last week's daily CSV in the configured folder. "
            "The scheduled task checks again every 30 minutes for 4 hours and at each login, and sends "
            "the full digest as soon as the rows arrive.</p>"
            "</div></div></body></html>"
        )

    # Flags block
    if rep.flags:
        flag_items = "".join(
            f'<li style="margin-bottom:6px;">{html.escape(f)}</li>' for f in rep.flags
        )
        flags_html = (
            '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:6px;padding:14px 16px;margin-bottom:18px;color:#991b1b;">'
            f'<div style="font-weight:700;margin-bottom:6px;">Alerts &amp; Watch Items ({len(rep.flags)})</div>'
            f'<ul style="margin:0;padding-left:18px;font-size:13px;line-height:1.45;">{flag_items}</ul></div>'
        )
    else:
        flags_html = (
            '<div style="background:#ecfdf5;border:1px solid #a7f3d0;border-radius:6px;padding:12px 16px;margin-bottom:18px;color:#065f46;font-size:13px;">'
            "<strong>All clear:</strong> No sections breached mortality, feed-use, feed-price, or data-quality thresholds.</div>"
        )

    # AI Summary block (falls back cleanly to numbers-only notice)
    if result.ai_summary:
        summary_escaped = html.escape(result.ai_summary).replace("\n", "<br>")
        summary_html = (
            '<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:14px 16px;margin-bottom:20px;">'
            '<div style="font-weight:700;color:#0f766e;margin-bottom:8px;font-size:14px;">Management Summary</div>'
            f'<div style="font-size:13px;line-height:1.55;color:#1f2937;">{summary_escaped}</div></div>'
        )
    else:
        summary_html = (
            '<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:12px 16px;margin-bottom:20px;color:#92400e;font-size:13px;">'
            f"<strong>{html.escape(AI_UNAVAILABLE_LINE)}</strong> Verified weekly KPI tables are shown below.</div>"
        )

    # Data quality block
    dq_lines: List[str] = []
    dq_lines.extend(f"Rejected - {i.label()}" for i in rep.rejected)
    dq_lines.extend(f"Duplicate - {i.label()}" for i in rep.duplicates)
    dq_lines.extend(f"Missing days - {s}: {n} of 7 days" for s, n in rep.missing_days.items())
    dq_lines.extend(f"Warning - {w}" for w in rep.warnings)
    if dq_lines:
        dq_items = "".join(f"<li>{html.escape(line)}</li>" for line in dq_lines)
        dq_html = f'<ul style="margin:6px 0 0;padding-left:18px;font-size:12px;color:#4b5563;">{dq_items}</ul>'
    else:
        dq_html = '<p style="margin:6px 0 0;font-size:12px;color:#065f46;">All rows accepted; headcounts reconcile; no missing days.</p>'

    table_head = (
        '<tr style="background:#f3f4f6;font-size:12px;color:#374151;">'
        '<th style="padding:8px;text-align:left;">Section</th>'
        '<th style="padding:8px;text-align:right;">Mort %</th>'
        '<th style="padding:8px;text-align:right;">kg/hd/d</th>'
        '<th style="padding:8px;text-align:right;">Feed Cost</th>'
        '<th style="padding:8px;text-align:right;">KES/hd/d</th>'
        '<th style="padding:8px;text-align:right;">KES/kg</th></tr>'
    )
    comp_note = "" if rep.has_comparison else " (first week: no comparison week)"

    return (
        '<!DOCTYPE html><html><body style="font-family:Arial,Helvetica,sans-serif;background:#f3f4f6;margin:0;padding:20px 12px;color:#111827;">'
        '<div style="max-width:740px;margin:0 auto;background:#ffffff;border-radius:8px;overflow:hidden;border:1px solid #e5e7eb;">'
        '<div style="background:#0f766e;color:#ffffff;padding:18px 22px;">'
        f'<h1 style="margin:0;font-size:19px;">{safe_client} - Weekly KPI Digest</h1>'
        f'<p style="margin:5px 0 0;font-size:13px;opacity:0.92;">Week {html.escape(rep.iso_week)} ({week_range}){html.escape(comp_note)}</p></div>'
        '<div style="padding:20px 22px;">'
        f"{flags_html}{summary_html}"
        '<h3 style="margin:0 0 8px;font-size:14px;color:#111827;">Farm-Wide Performance</h3>'
        f'<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:18px;">{table_head}{_render_kpi_rows_html(rep, ["FARM"])}</table>'
        '<h3 style="margin:0 0 8px;font-size:14px;color:#111827;">Section Breakdown</h3>'
        f'<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:18px;">{table_head}{_render_kpi_rows_html(rep, list(sections))}</table>'
        '<div style="border-top:1px solid #e5e7eb;padding-top:12px;">'
        '<div style="font-weight:700;font-size:13px;color:#374151;">Data Quality Notes</div>'
        f"{dq_html}</div>"
        '<p style="margin:16px 0 0;font-size:11px;color:#6b7280;">'
        "KPI tables are computed deterministically from daily farm CSV records. "
        "Any mortality alert requires immediate review by the farm veterinarian.</p>"
        "</div></div></body></html>"
    )


def build_email_message(
    result: ReportResult, cfg: DigestConfig
) -> Tuple[EmailMessage, str]:
    """Returns (multipart EmailMessage, html_body) with plain-text fallback."""
    subject = _build_subject(result, cfg.client_name)
    plain_body = _build_plain_body(result, cfg.client_name)
    html_body = _build_html_body(result, cfg.client_name, cfg.sections)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((_strip_header_breaks(cfg.sender_name), cfg.gmail_address))
    msg["To"] = ", ".join(cfg.recipients)
    # Date + Message-ID keep company spam filters happy. Passing the domain stops
    # make_msgid() from putting this PC's network name into every email.
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(
        idstring=f"digest-{result.report.iso_week}", domain=cfg.gmail_address.rsplit("@", 1)[-1]
    )
    msg.set_content(plain_body, subtype="plain", charset="utf-8")
    msg.add_alternative(html_body, subtype="html", charset="utf-8")
    return msg, html_body


# --------------------------------------------------------------------------- #
# SMTP Delivery (SSL + Transient Backoff + Plain-English Errors)
# --------------------------------------------------------------------------- #
def _open_smtp(cfg: DigestConfig, context: ssl.SSLContext, smtp_factory: Optional[Callable[..., object]]):
    """Port 465 = SSL from the first byte (Gmail default); any other port = plain SMTP + STARTTLS."""
    if cfg.smtp_port == SMTP_SSL_PORT:
        factory = smtp_factory or smtplib.SMTP_SSL
        return factory(cfg.smtp_host, cfg.smtp_port, timeout=SMTP_TIMEOUT_SECONDS, context=context), False
    factory = smtp_factory or smtplib.SMTP
    return factory(cfg.smtp_host, cfg.smtp_port, timeout=SMTP_TIMEOUT_SECONDS), True


def send_email_smtp(
    msg: EmailMessage,
    cfg: DigestConfig,
    *,
    smtp_factory: Optional[Callable[..., object]] = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> SmtpResult:
    """
    Sends the multipart email. Retries transient network drops and 4xx replies
    (2s, 4s); fails immediately on a wrong App Password, refused recipients,
    5xx replies or a failed certificate check. Once Gmail has accepted the
    message, a hiccup while hanging up never triggers a second (duplicate) send.
    """
    context = ssl.create_default_context()
    max_attempts = len(SMTP_BACKOFF_DELAYS) + 1

    for attempt in range(1, max_attempts + 1):
        delivered = False
        refused: Dict[str, object] = {}
        try:
            server_cm, needs_starttls = _open_smtp(cfg, context, smtp_factory)
            try:
                with server_cm as server:
                    if needs_starttls:
                        server.starttls(context=context)
                    server.login(cfg.gmail_address, cfg.gmail_app_password)
                    refused = server.send_message(
                        msg,
                        from_addr=cfg.gmail_address,
                        to_addrs=list(cfg.recipients),
                    ) or {}
                    delivered = True
            except (smtplib.SMTPException, OSError) as err:
                if not delivered:
                    raise
                # The message is already with Gmail; only the goodbye (QUIT) failed.
                log_digest_event("WARNING", f"smtp_quit_failed error={type(err).__name__} (message delivered)")
            if refused:
                log_digest_event("WARNING", f"smtp_partial_refused count={len(refused)}")
            return SmtpResult(attempts=attempt, refused=len(refused))
        except smtplib.SMTPAuthenticationError as err:
            log_digest_event("ERROR", f"smtp_auth_failed code={err.smtp_code}")
            raise EmailDeliveryError(
                "Email login failed. Double-check GMAIL_ADDRESS and your 16-character "
                "GMAIL_APP_PASSWORD in config.env (do not use your normal Gmail password)."
            ) from err
        except smtplib.SMTPRecipientsRefused as err:
            log_digest_event("ERROR", f"smtp_recipients_refused count={len(err.recipients)}")
            raise EmailDeliveryError(
                "Gmail rejected every address in REPORT_RECIPIENTS. "
                "Check config.env for typos and try again."
            ) from err
        except smtplib.SMTPResponseException as err:
            is_temp = 400 <= err.smtp_code < 500
            if not is_temp or attempt >= max_attempts:
                log_digest_event("ERROR", f"smtp_response_error code={err.smtp_code} attempts={attempt}")
                raise EmailDeliveryError(
                    f"Email server rejected the message (SMTP {err.smtp_code}). "
                    "Check digest.log and try again."
                ) from err
            delay = SMTP_BACKOFF_DELAYS[attempt - 1]
            log_digest_event(
                "WARNING",
                f"smtp_retry code={err.smtp_code} attempt={attempt}/{max_attempts} sleep={delay}s",
            )
            sleep_fn(delay)
        except ssl.SSLCertVerificationError as err:
            log_digest_event("ERROR", "smtp_certificate_failed")
            raise EmailDeliveryError(
                "The secure connection to the email server failed its certificate check. "
                "Check that this PC's date and time are correct, and turn off any antivirus "
                "'email scanning' or 'HTTPS scanning' feature, then try again."
            ) from err
        except ssl.SSLError as err:
            if "WRONG_VERSION_NUMBER" in str(err).upper():
                log_digest_event("ERROR", "smtp_tls_mismatch")
                raise EmailDeliveryError(
                    f"SMTP_PORT {cfg.smtp_port} does not match the server's security mode. "
                    "For Gmail use SMTP_PORT=465 (or 587)."
                ) from err
            if attempt >= max_attempts:
                log_digest_event("ERROR", f"smtp_network_failed error={type(err).__name__} attempts={attempt}")
                raise EmailDeliveryError(
                    f"Could not send email after {attempt} attempts ({type(err).__name__}). "
                    "Check your internet connection; the HTML preview was saved locally."
                ) from err
            delay = SMTP_BACKOFF_DELAYS[attempt - 1]
            log_digest_event(
                "WARNING", f"smtp_retry error={type(err).__name__} attempt={attempt}/{max_attempts} sleep={delay}s"
            )
            sleep_fn(delay)
        except (smtplib.SMTPException, OSError) as err:
            if attempt >= max_attempts:
                log_digest_event(
                    "ERROR",
                    f"smtp_network_failed error={type(err).__name__} attempts={attempt}",
                )
                raise EmailDeliveryError(
                    f"Could not send email after {attempt} attempts ({type(err).__name__}). "
                    "Check your internet connection; the HTML preview was saved locally."
                ) from err
            delay = SMTP_BACKOFF_DELAYS[attempt - 1]
            log_digest_event(
                "WARNING",
                f"smtp_retry error={type(err).__name__} attempt={attempt}/{max_attempts} sleep={delay}s",
            )
            sleep_fn(delay)

    raise EmailDeliveryError("Email delivery failed unexpectedly.")


# --------------------------------------------------------------------------- #
# Weekly Deduplication State & Schedule Timing
# --------------------------------------------------------------------------- #
def load_digest_state(state_path: Path = DIGEST_STATE_PATH) -> Dict[str, object]:
    if not state_path.is_file():
        return {"version": 1, "sent_weeks": {}}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("sent_weeks"), dict):
            return data
    except (OSError, ValueError):
        pass
    return {"version": 1, "sent_weeks": {}}


def save_digest_state(state: Dict[str, object], state_path: Path = DIGEST_STATE_PATH) -> bool:
    """Atomic save with no fallback file: a renamed copy would never be read back."""
    try:
        atomic_write_text(
            state_path,
            json.dumps(state, indent=2, sort_keys=True),
            allow_fallback=False,
        )
        return True
    except OSError as err:
        log_digest_event("ERROR", f"state_write_failed error={type(err).__name__}")
        return False


def _format_late_by(delta: timedelta) -> Optional[str]:
    total_min = int(delta.total_seconds() // 60)
    if total_min < 5:
        return None
    hours, mins = divmod(total_min, 60)
    return f"{hours}h{mins:02d}m"


def _scheduled_due_time(week_end: date, cfg: DigestConfig) -> datetime:
    monday = week_end + timedelta(days=1)
    return datetime.combine(monday, dt_time(cfg.schedule_hour, cfg.schedule_minute), tzinfo=core.EAT)


# --------------------------------------------------------------------------- #
# Main Digest Orchestrator
# --------------------------------------------------------------------------- #
def run_digest(
    cfg: DigestConfig,
    *,
    now: Optional[datetime] = None,
    week_ending: Optional[date] = None,
    dry_run: bool = False,
    scheduled: bool = False,
    force: bool = False,
    preview_path: Path = PREVIEW_HTML_PATH,
    state_path: Path = DIGEST_STATE_PATH,
    lock_path: Path = DIGEST_LOCK_PATH,
    claude_client: Optional[object] = None,
    claude_route: Optional[core.ModelRoute] = None,
    smtp_factory: Optional[Callable[..., object]] = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> DigestRunOutcome:
    run_now = now or datetime.now(core.EAT)
    today = run_now.date()
    target_week_end = week_ending or core.last_complete_week_end(today)
    target_week_start = target_week_end - timedelta(days=6)
    yr, wk, _ = target_week_start.isocalendar()
    iso_week = f"{yr}-W{wk:02d}"
    trigger = "scheduled" if scheduled else "manual"

    late_by: Optional[str] = None
    if scheduled and not dry_run:
        due_dt = _scheduled_due_time(target_week_end, cfg)
        if run_now < due_dt:
            log_digest_event(
                "INFO",
                f"SKIPPED before_schedule week={iso_week} due={due_dt.strftime('%Y-%m-%d_%H:%M')} trigger={trigger}",
            )
            return DigestRunOutcome(
                status="skipped_before_schedule",
                exit_code=0,
                iso_week=iso_week,
                message=f"Waiting until scheduled time {due_dt.strftime('%a %Y-%m-%d %H:%M EAT')}.",
            )
        late_by = _format_late_by(run_now - due_dt)

    try:
        with acquire_process_lock(lock_path):
            prior: Optional[object] = None
            if not dry_run and not force:
                state = load_digest_state(state_path)
                prior = state.get("sent_weeks", {}).get(iso_week)
                # A full digest blocks resends. A no-data notice does not: if the CSV
                # arrives later, the next retry must still send the real report.
                full_digest_sent = prior is not None and (
                    not isinstance(prior, dict) or bool(prior.get("has_data", True))
                )
                if full_digest_sent:
                    log_digest_event(
                        "INFO",
                        f"SKIPPED duplicate week={iso_week} trigger={trigger}",
                    )
                    return DigestRunOutcome(
                        status="skipped_duplicate",
                        exit_code=0,
                        iso_week=iso_week,
                        message=f"Weekly digest for {iso_week} was already sent. Pass --force to resend.",
                    )

            with apply_core_config(cfg):
                active_client = claude_client
                if active_client is None and not dry_run:
                    active_client = core.make_claude_client(cfg.anthropic_api_key)
                res = generate_weekly_report(
                    cfg.data_paths,
                    today=today,
                    week_ending=week_ending,
                    dry_run=dry_run,
                    client=active_client,
                    route=claude_route,
                    sleep_fn=sleep_fn,
                )

            if prior is not None and not res.report.has_data:
                log_digest_event("INFO", f"SKIPPED no_data_notice_already_sent week={iso_week} trigger={trigger}")
                return DigestRunOutcome(
                    status="skipped_duplicate",
                    exit_code=0,
                    iso_week=iso_week,
                    message=(
                        f"The no-data notice for {iso_week} was already sent and there are still no rows. "
                        "The full digest goes out on the next run after the CSV is saved."
                    ),
                )

            msg, html_body = build_email_message(res, cfg)
            written_preview = atomic_write_text(preview_path, html_body, allow_fallback=True)

            if dry_run:
                log_digest_event(
                    "INFO",
                    f"OK dry_run week={res.report.iso_week} has_data={res.report.has_data} "
                    f"flags={len(res.report.flags)} recipients={len(cfg.recipients)} trigger={trigger}",
                )
                return DigestRunOutcome(
                    status="dry_run",
                    exit_code=0,
                    iso_week=res.report.iso_week,
                    recipient_count=len(cfg.recipients),
                    preview_path=written_preview,
                    report_result=res,
                    message=f"Preview saved to '{written_preview}'. No email sent (--dry-run).",
                )

            try:
                smtp = send_email_smtp(msg, cfg, smtp_factory=smtp_factory, sleep_fn=sleep_fn)
            except EmailDeliveryError as err:
                return DigestRunOutcome(
                    status="error",
                    exit_code=2,
                    iso_week=res.report.iso_week,
                    recipient_count=len(cfg.recipients),
                    preview_path=written_preview,
                    report_result=res,
                    message=str(err),
                )

            state = load_digest_state(state_path)
            sent_weeks = state.setdefault("sent_weeks", {})
            if isinstance(sent_weeks, dict):
                sent_weeks[res.report.iso_week] = {
                    "sent_at": run_now.isoformat(timespec="seconds"),
                    "has_data": res.report.has_data,
                    "recipient_count": len(cfg.recipients),
                    "kpi_sha256_8": hashlib.sha256(res.kpi_json.encode("utf-8")).hexdigest()[:8],
                    "ai_used": bool(res.ai_summary),
                    "refused_count": smtp.refused,
                }
            state_saved = save_digest_state(state, state_path)

            late_tag = f" late_by={late_by}" if late_by else ""
            log_digest_event(
                "INFO",
                f"OK sent week={res.report.iso_week} has_data={res.report.has_data} "
                f"recipients={len(cfg.recipients)} flags={len(res.report.flags)} "
                f"rejected={len(res.report.rejected)} ai_status={res.ai_status.split(':')[0]} "
                f"model={res.model or 'none'} tokens={res.input_tokens}/{res.output_tokens} "
                f"cost_kes={res.cost_kes} smtp_attempts={smtp.attempts} refused={smtp.refused} "
                f"trigger={trigger}{late_tag}",
            )
            delivered = len(cfg.recipients) - smtp.refused
            message = f"Sent weekly digest for {res.report.iso_week} to {delivered} recipient(s)."
            if smtp.refused:
                message += f" Gmail refused {smtp.refused} address(es); check REPORT_RECIPIENTS."
            if not state_saved:
                message += (
                    f" WARNING: could not update '{state_path.name}' (is it open in another program?). "
                    "A later run may send this week again."
                )
            return DigestRunOutcome(
                status="sent",
                exit_code=0,
                iso_week=res.report.iso_week,
                recipient_count=delivered,
                preview_path=written_preview,
                report_result=res,
                message=message,
                late_by=late_by,
            )
    except OverlapLockError as err:
        log_digest_event("INFO", f"SKIPPED locked week={iso_week} trigger={trigger}")
        return DigestRunOutcome(
            status="skipped_locked",
            exit_code=0,
            iso_week=iso_week,
            message=str(err),
        )
    except core.InputError as err:
        log_digest_event("ERROR", f"input_error week={iso_week} detail={type(err).__name__}")
        return DigestRunOutcome(
            status="error",
            exit_code=1,
            iso_week=iso_week,
            message=str(err),
        )


# --------------------------------------------------------------------------- #
# Scheduling Installer (Windows Task Scheduler XML / Linux Crontab) & Status
# --------------------------------------------------------------------------- #
def task_python_exe() -> Path:
    """
    The interpreter the scheduled task should launch. `.absolute()`, never
    `.resolve()`: on Linux a venv's python is a symlink, and resolving it jumps to
    the system Python, which has no anthropic/dotenv packages installed.
    On Windows, pythonw.exe runs without a console window staff could close mid-run.
    """
    exe = Path(sys.executable).absolute()
    if os.name == "nt":
        pythonw = exe.with_name("pythonw.exe")
        if pythonw.is_file():
            return pythonw
    return exe


def current_windows_user() -> str:
    domain = os.environ.get("USERDOMAIN", "")
    user = os.environ.get("USERNAME", "")
    return f"{domain}\\{user}" if domain and user else user


def build_windows_task_xml(
    runner: Path, script_path: Path, config_path: Path, cfg: DigestConfig, user_id: str
) -> str:
    """
    Monday trigger at SCHEDULE_TIME pinned to +03:00, so it fires at 07:00 EAT even
    if the PC clock is set to another time zone. Retries every 30 min for 4 h,
    catches up 3 min after logon, runs on battery, and starts late if the PC was off.
    """
    e = xml_escape
    args_str = f'"{script_path}" --config "{config_path}" --scheduled'
    start_boundary = f"2026-11-23T{cfg.schedule_hour:02d}:{cfg.schedule_minute:02d}:00+03:00"
    return (
        '<?xml version="1.0" encoding="UTF-16"?>\n'
        '<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
        "  <RegistrationInfo>\n"
        f"    <Description>Weekly livestock KPI digest for {e(cfg.client_name)}. Mondays at "
        f"{cfg.schedule_time_str} EAT; retries every 30 min for 4 hours and catches up at logon. "
        "Sends at most one full digest per week.</Description>\n"
        "  </RegistrationInfo>\n"
        "  <Triggers>\n"
        "    <CalendarTrigger>\n"
        f"      <StartBoundary>{start_boundary}</StartBoundary>\n"
        "      <Enabled>true</Enabled>\n"
        "      <Repetition>\n"
        f"        <Interval>{TASK_RETRY_EVERY}</Interval>\n"
        f"        <Duration>{TASK_RETRY_FOR}</Duration>\n"
        "        <StopAtDurationEnd>false</StopAtDurationEnd>\n"
        "      </Repetition>\n"
        "      <ScheduleByWeek>\n"
        "        <DaysOfWeek><Monday /></DaysOfWeek>\n"
        "        <WeeksInterval>1</WeeksInterval>\n"
        "      </ScheduleByWeek>\n"
        "    </CalendarTrigger>\n"
        "    <LogonTrigger>\n"
        "      <Enabled>true</Enabled>\n"
        f"      <UserId>{e(user_id)}</UserId>\n"
        "      <Delay>PT3M</Delay>\n"
        "    </LogonTrigger>\n"
        "  </Triggers>\n"
        "  <Principals>\n"
        '    <Principal id="Author">\n'
        f"      <UserId>{e(user_id)}</UserId>\n"
        "      <LogonType>InteractiveToken</LogonType>\n"
        "      <RunLevel>LeastPrivilege</RunLevel>\n"
        "    </Principal>\n"
        "  </Principals>\n"
        "  <Settings>\n"
        "    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n"
        "    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n"
        "    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n"
        "    <AllowHardTerminate>true</AllowHardTerminate>\n"
        "    <StartWhenAvailable>true</StartWhenAvailable>\n"
        "    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>\n"
        "    <AllowStartOnDemand>true</AllowStartOnDemand>\n"
        "    <Enabled>true</Enabled>\n"
        "    <Hidden>false</Hidden>\n"
        "    <RunOnlyIfIdle>false</RunOnlyIfIdle>\n"
        "    <WakeToRun>false</WakeToRun>\n"
        "    <ExecutionTimeLimit>PT15M</ExecutionTimeLimit>\n"
        "  </Settings>\n"
        '  <Actions Context="Author">\n'
        "    <Exec>\n"
        f"      <Command>{e(str(runner))}</Command>\n"
        f"      <Arguments>{e(args_str)}</Arguments>\n"
        f"      <WorkingDirectory>{e(str(BASE_DIR))}</WorkingDirectory>\n"
        "    </Exec>\n"
        "  </Actions>\n"
        "</Task>\n"
    )


def _run_schtasks(cmd: List[str]) -> Tuple[int, str]:
    # errors="replace": schtasks prints in the console code page, which is not UTF-8.
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", check=False)
    return proc.returncode, (proc.stderr or proc.stdout or "").strip()


def build_cron_lines(config_path: Path, cfg: DigestConfig) -> List[str]:
    command = " ".join(
        shlex.quote(str(part))
        for part in (task_python_exe(), Path(__file__).absolute(), "--config", config_path, "--scheduled")
    )
    return [
        "CRON_TZ=Africa/Nairobi",
        f"{cfg.schedule_minute} {cfg.schedule_hour} * * 1 {command}",
        f"*/30 * * * 1-2 {command}",
        f"@reboot sleep 180 && {command}",
    ]


def install_schedule(config_path: Path, cfg: DigestConfig) -> int:
    script_path = Path(__file__).absolute()
    if os.name != "nt":
        print("[LINUX CRON] Run `crontab -e` and add these lines (the --scheduled flag waits for")
        print("             the Monday send time and skips weeks already sent):")
        for line in build_cron_lines(config_path, cfg):
            print(f"    {line}")
        print("             If your cron ignores CRON_TZ, set the server time zone to Africa/Nairobi.")
        return 0

    user_id = current_windows_user()
    if not user_id:
        print("[ERROR] Could not read the Windows user name (USERNAME is empty).")
        return 1
    xml_text = build_windows_task_xml(task_python_exe(), script_path, config_path, cfg, user_id)
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".xml", delete=False) as tmp:
        tmp.write(xml_text.encode("utf-16"))
        xml_path = Path(tmp.name)
    try:
        code, output = _run_schtasks(
            ["schtasks", "/Create", "/TN", WINDOWS_TASK_NAME, "/XML", str(xml_path), "/F"]
        )
    finally:
        xml_path.unlink(missing_ok=True)

    if code != 0:
        print(f"[ERROR] Could not install Windows task: {output}")
        return 1
    print(f"[INSTALLED] Windows task '{WINDOWS_TASK_NAME}' scheduled for Mondays at {cfg.schedule_time_str} EAT.")
    print("            Retries every 30 min for 4 hours and catches up 3 min after login.")
    print("            Changed SCHEDULE_TIME later? Run --install-task again to apply it.")
    log_digest_event("INFO", f"task_installed time={cfg.schedule_time_str}")
    return 0


def uninstall_schedule() -> int:
    if os.name != "nt":
        print("Linux/macOS: run `crontab -e` and delete the weekly_livestock_digest.py lines.")
        return 0
    code, _output = _run_schtasks(["schtasks", "/Delete", "/TN", WINDOWS_TASK_NAME, "/F"])
    if code != 0:
        print(f"[INFO] Task '{WINDOWS_TASK_NAME}' was not installed or could not be removed.")
        return 1
    print(f"[REMOVED] Windows task '{WINDOWS_TASK_NAME}' removed.")
    log_digest_event("INFO", "task_uninstalled")
    return 0


def print_status(
    state_path: Path = DIGEST_STATE_PATH, log_path: Path = DIGEST_LOG_PATH
) -> int:
    state = load_digest_state(state_path)
    sent_weeks = state.get("sent_weeks", {})
    now = datetime.now(core.EAT)
    healthy = False

    if isinstance(sent_weeks, dict) and sent_weeks:
        last_week = sorted(sent_weeks)[-1]
        info = sent_weeks[last_week]
        sent_at_str = str(info.get("sent_at", ""))
        print(f"Last weekly digest sent : {last_week} at {sent_at_str}")
        print(f"Recipients              : {info.get('recipient_count', 0)}")
        print(f"AI summary included     : {info.get('ai_used', False)}")
        try:
            sent_dt = datetime.fromisoformat(sent_at_str)
            age_days = (now - sent_dt).total_seconds() / 86400
            healthy = age_days <= 8.0
        except ValueError:
            healthy = False
    else:
        print("Last weekly digest sent : Never")

    if log_path.is_file():
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-5:]
        print("\nLast 5 log entries:")
        for ln in lines:
            print(f"  {ln}")
    else:
        print("\nLog file not created yet.")

    if healthy:
        print("\n[OK] Weekly digest is on schedule.")
        return 0
    print("\n[WARN] No weekly digest sent within the last 8 days.")
    return 1


# --------------------------------------------------------------------------- #
# Self-Test Suite (all Day 32 core checks + Day 33 digest checks, zero real calls)
# --------------------------------------------------------------------------- #
class _CountingStream(io.TextIOBase):
    """Passes core self-test output through while counting its [PASS]/[FAIL] lines."""

    def __init__(self, target) -> None:
        self.target = target
        self.passed = 0
        self.failed = 0
        self._partial = ""

    def write(self, text: str) -> int:
        if self.target is not None:
            self.target.write(text)
        self._partial += text
        *lines, self._partial = self._partial.split("\n")
        for line in lines:
            self.passed += line.startswith("[PASS]")
            self.failed += line.startswith("[FAIL]")
        return len(text)

    def flush(self) -> None:
        if self.target is not None:
            self.target.flush()


def run_self_test() -> int:
    import dataclasses
    import xml.etree.ElementTree as ET
    from types import SimpleNamespace
    from unittest import mock

    try:
        import httpx2 as _httpx
    except ImportError:
        import httpx as _httpx

    # Hard guards: any real SMTP connection or Anthropic client in this suite is a failure.
    no_network = mock.patch.multiple(
        smtplib,
        SMTP_SSL=mock.Mock(side_effect=AssertionError("real SMTP_SSL opened in self-test")),
        SMTP=mock.Mock(side_effect=AssertionError("real SMTP opened in self-test")),
    )
    no_anthropic = mock.patch.object(
        core.anthropic, "Anthropic", side_effect=AssertionError("real Anthropic client in self-test")
    )
    with no_network, no_anthropic:
        counter = _CountingStream(sys.stdout)
        with contextlib.redirect_stdout(counter):
            core_rc = core.run_self_test()
        core_total = counter.passed + counter.failed
        return _run_digest_checks(core_rc, core_total, counter.passed, dataclasses, ET, SimpleNamespace, mock, _httpx)


def _run_digest_checks(core_rc, core_total, core_passed, dataclasses, ET, SimpleNamespace, mock, _httpx) -> int:
    print("\n" + "=" * 72)
    print("   WEEK 7 DAY 33 DIGEST CHECKS (zero real API/SMTP calls)")
    print("=" * 72)
    results: List[bool] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append(bool(ok))
        print(f"[PASS] {name}" if ok else f"[FAIL] {name} :: {detail}")

    def api_error(cls, status: int):
        req = _httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        return cls(message=f"HTTP {status}", response=_httpx.Response(status, request=req), body=None)

    base_cfg_text = (
        "CLIENT_NAME=Nova Highlands Livestock Ltd\n"
        "DATA_PATH=sample.csv\n"
        "SECTIONS=BREEDING,FARROWING,WEANER,GROWER\n"
        "MORTALITY_ALERT_PCT=BREEDING:0.50,FARROWING:3.00,WEANER:1.00,GROWER:0.50\n"
        "FEED_USE_WATCH_PCT=10.00\n"
        "FEED_PRICE_WATCH_PCT=5.00\n"
        "FEED_PRICE_MIN_KES=20.00\n"
        "FEED_PRICE_MAX_KES=150.00\n"
        "ANTHROPIC_API_KEY=sk-ant-test-valid-key\n"
        "GMAIL_ADDRESS=reports@novahighlands.co.ke\n"
        "GMAIL_APP_PASSWORD=abcd efgh ijkl mnop\n"
        "SENDER_NAME=Nova Farm Reports\n"
        "REPORT_RECIPIENTS=m1@novahighlands.co.ke, m2@novahighlands.co.ke, "
        "m3@novahighlands.co.ke, m4@novahighlands.co.ke, m5@novahighlands.co.ke\n"
        "SCHEDULE_TIME=07:00\n"
    ).replace("abcd efgh ijkl mnop", "qrst uvwx yzab cdef")

    sample_text = core.DEFAULT_CSV_PATH.read_text(encoding="utf-8-sig")
    monday_after = datetime(2026, 11, 23, 7, 10, tzinfo=core.EAT)

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        (tmp / "sample.csv").write_text(sample_text, encoding="utf-8")
        tmp_log = tmp / "digest.log"
        tmp_core_log = tmp / "core.log"
        tmp_state = tmp / "digest_state.json"
        tmp_lock = tmp / "digest.lock"
        tmp_preview = tmp / "preview.html"
        mod = sys.modules[__name__]

        with mock.patch.object(mod, "DIGEST_LOG_PATH", tmp_log), \
             mock.patch.object(core, "CORE_LOG_PATH", tmp_core_log), \
             mock.patch.object(core, "SHARED_ROUTE", core.ModelRoute()), \
             mock.patch.object(core, "make_claude_client", side_effect=AssertionError("no real Claude client")):

            # Check 15: UTF-8 BOM, UTF-16, cp1252 config.env load cleanly; os.environ untouched
            env_before = dict(os.environ)
            enc_ok = True
            loaded_cfg: Optional[DigestConfig] = None
            for label, payload in (
                ("bom", b"\xef\xbb\xbf" + base_cfg_text.encode("utf-8")),
                ("utf16", base_cfg_text.encode("utf-16")),
                ("cp1252", base_cfg_text.encode("cp1252")),
            ):
                p = tmp / f"{label}.env"
                p.write_bytes(payload)
                c = load_and_validate_config(p)
                loaded_cfg = c
                enc_ok = enc_ok and len(c.recipients) == 5 and c.schedule_time_str == "07:00"
            check(
                "15 Config encodings (UTF-8 BOM, UTF-16, cp1252) & >3 recipients; os.environ untouched",
                enc_ok and dict(os.environ) == env_before and loaded_cfg is not None,
            )

            # Check 16: Missing file gives .txt hint; bad email typo & settings reported together
            (tmp / "missing.env.txt").write_text(base_cfg_text, encoding="utf-8")
            missing_msg = ""
            try:
                load_and_validate_config(tmp / "missing.env")
            except ConfigError as err:
                missing_msg = str(err)

            bad_env = tmp / "bad.env"
            bad_env.write_text(
                "ANTHROPIC_API_KEY=sk-ant-paste-your-real-key-here\n"
                "GMAIL_ADDRESS=not-an-email\n"
                "GMAIL_APP_PASSWORD=paste-16-char-app-password\n"
                "REPORT_RECIPIENTS=ok@farm.co.ke, typo-at-farm.co.ke\n"
                "MORTALITY_ALERT_PCT=BREEDING:0.50\n"
                "SCHEDULE_TIME=25:00\n",
                encoding="utf-8",
            )
            bad_msg = ""
            try:
                load_and_validate_config(bad_env)
            except ConfigError as err:
                bad_msg = str(err)
            check(
                "16 Config validation: .env.txt hint and all bad settings (incl. email typo) listed together",
                "config.env.txt" in missing_msg
                and all(k in bad_msg for k in ("ANTHROPIC_API_KEY", "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "typo-at-farm.co.ke", "MORTALITY_ALERT_PCT", "SCHEDULE_TIME")),
                f"missing={missing_msg} bad={bad_msg}",
            )

            # Check 17: Custom config thresholds apply to core KPI flags and restore afterwards
            assert loaded_cfg is not None
            custom_env = tmp / "custom.env"
            custom_env.write_text(
                base_cfg_text.replace("WEANER:1.00", "WEANER:5.00").replace(
                    "CLIENT_NAME=Nova Highlands Livestock Ltd", "CLIENT_NAME=Test <Farm> & Co"
                ),
                encoding="utf-8",
            )
            custom_cfg = load_and_validate_config(custom_env)
            with apply_core_config(custom_cfg):
                r_custom = generate_weekly_report(custom_cfg.data_paths, today=monday_after.date(), dry_run=True)
            check(
                "17 Custom thresholds from config.env apply cleanly and restore core defaults",
                not any("MORTALITY ALERT: WEANER" in f for f in r_custom.report.flags)
                and core.MORTALITY_ALERT_PCT["WEANER"] == Decimal("1.00")
                and core.CLIENT_NAME == "Nova Highlands Livestock Ltd",
                f"flags={r_custom.report.flags}",
            )

            # Check 18: Multipart email (plain + HTML), HTML-escaped name, KPI table from code
            msg_custom, html_custom = build_email_message(r_custom, custom_cfg)
            parts = {p.get_content_type(): p.get_content() for p in msg_custom.iter_parts()}
            check(
                "18 Multipart email has plain + HTML, escapes client name, shows code KPIs for 5 managers",
                "text/plain" in parts and "text/html" in parts
                and "Test &lt;Farm&gt; &amp; Co" in html_custom
                and "KES 1,432,656" in html_custom and "KES 1,432,656" in parts["text/plain"]
                and len(custom_cfg.recipients) == 5,
            )

            # Check 19: Numbers-only fallback when Claude fails (BadRequest 400 -> no summary, email still sent)
            sent_messages: List[EmailMessage] = []

            class FakeSMTP:
                def __init__(self, *args, **kwargs) -> None:
                    pass

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def login(self, user, pw):
                    return (235, b"OK")

                def send_message(self, msg, from_addr=None, to_addrs=None):
                    sent_messages.append(msg)
                    return {}

            class FailClaude:
                def create(self, **kwargs):
                    raise api_error(core.anthropic.BadRequestError, 400)

            out_num_only = run_digest(
                loaded_cfg,
                now=monday_after,
                preview_path=tmp_preview,
                state_path=tmp / "state_num.json",
                lock_path=tmp_lock,
                claude_client=SimpleNamespace(messages=FailClaude()),
                claude_route=core.ModelRoute(),
                smtp_factory=FakeSMTP,
            )
            num_html = tmp_preview.read_text(encoding="utf-8")
            check(
                "19 Numbers-only fallback: Claude failure still sends full KPI email with notice",
                out_num_only.status == "sent"
                and len(sent_messages) == 1
                and AI_UNAVAILABLE_LINE in num_html
                and "KES 1,432,656" in num_html,
                f"status={out_num_only.status} msg={out_num_only.message}",
            )

            # Check 20: No-data week sends short notice without calling Claude
            sent_nodata: List[EmailMessage] = []

            class NoDataSMTP(FakeSMTP):
                def send_message(self, msg, from_addr=None, to_addrs=None):
                    sent_nodata.append(msg)
                    return {}

            out_nodata = run_digest(
                loaded_cfg,
                now=datetime(2026, 12, 14, 7, 5, tzinfo=core.EAT),
                preview_path=tmp / "nodata.html",
                state_path=tmp / "state_nodata.json",
                lock_path=tmp_lock,
                claude_client=SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: (_ for _ in ()).throw(AssertionError("should not call Claude")))),
                smtp_factory=NoDataSMTP,
            )
            check(
                "20 No-data week sends '[NO DATA]' notice email without calling Claude",
                out_nodata.status == "sent"
                and len(sent_nodata) == 1
                and "[NO DATA]" in str(sent_nodata[0]["Subject"]),
                f"status={out_nodata.status}",
            )

            # Check 21: SMTP backoff retries transient drop; AuthError stops immediately
            smtp_slept: List[float] = []
            smtp_calls = {"n": 0}

            class FlakySMTP(FakeSMTP):
                def send_message(self, msg, from_addr=None, to_addrs=None):
                    smtp_calls["n"] += 1
                    if smtp_calls["n"] < 3:
                        raise smtplib.SMTPServerDisconnected("network drop")
                    return {}

            attempts_ok = send_email_smtp(msg_custom, loaded_cfg, smtp_factory=FlakySMTP, sleep_fn=smtp_slept.append).attempts

            auth_slept: List[float] = []
            auth_calls = {"n": 0}

            class AuthFailSMTP(FakeSMTP):
                def login(self, user, pw):
                    auth_calls["n"] += 1
                    raise smtplib.SMTPAuthenticationError(535, b"Username and Password not accepted")

            auth_err = ""
            try:
                send_email_smtp(msg_custom, loaded_cfg, smtp_factory=AuthFailSMTP, sleep_fn=auth_slept.append)
            except EmailDeliveryError as err:
                auth_err = str(err)
            check(
                "21 SMTP retry (2s, 4s) recovers on attempt 3; wrong App Password fails immediately",
                attempts_ok == 3 and smtp_slept == [2.0, 4.0]
                and auth_calls["n"] == 1 and not auth_slept and "GMAIL_APP_PASSWORD" in auth_err,
                f"ok={attempts_ok}/{smtp_slept} auth={auth_calls['n']}/{auth_err}",
            )

            # Check 22: Weekly dedup (3x runs -> 1 email), --force overrides, dry-run leaves no state
            dedup_sent: List[EmailMessage] = []

            class CountSMTP(FakeSMTP):
                def send_message(self, msg, from_addr=None, to_addrs=None):
                    dedup_sent.append(msg)
                    return {}

            dry_out = run_digest(
                loaded_cfg, now=monday_after, dry_run=True,
                preview_path=tmp / "dry.html", state_path=tmp_state, lock_path=tmp_lock,
                smtp_factory=CountSMTP,
            )
            dry_no_state = not tmp_state.exists()
            r1 = run_digest(
                loaded_cfg, now=monday_after, preview_path=tmp_preview, state_path=tmp_state,
                lock_path=tmp_lock, claude_client=SimpleNamespace(messages=FailClaude()),
                claude_route=core.ModelRoute(), smtp_factory=CountSMTP,
            )
            r2 = run_digest(
                loaded_cfg, now=monday_after, preview_path=tmp_preview, state_path=tmp_state,
                lock_path=tmp_lock, claude_client=SimpleNamespace(messages=FailClaude()),
                claude_route=core.ModelRoute(), smtp_factory=CountSMTP,
            )
            r3 = run_digest(
                loaded_cfg, now=monday_after, preview_path=tmp_preview, state_path=tmp_state,
                lock_path=tmp_lock, claude_client=SimpleNamespace(messages=FailClaude()),
                claude_route=core.ModelRoute(), smtp_factory=CountSMTP,
            )
            r_force = run_digest(
                loaded_cfg, now=monday_after, force=True, preview_path=tmp_preview, state_path=tmp_state,
                lock_path=tmp_lock, claude_client=SimpleNamespace(messages=FailClaude()),
                claude_route=core.ModelRoute(), smtp_factory=CountSMTP,
            )
            check(
                "22 Weekly dedup: dry-run leaves no state, 3 runs send 1 email, --force resends",
                dry_out.status == "dry_run" and dry_no_state
                and r1.status == "sent" and r2.status == "skipped_duplicate" and r3.status == "skipped_duplicate"
                and r_force.status == "sent" and len(dedup_sent) == 2,
                f"statuses={(r1.status, r2.status, r3.status, r_force.status)} sent={len(dedup_sent)}",
            )

            # Check 23: Scheduled window (waits before 07:00, catches up Tuesday) & OS overlap lock
            sched_state = tmp / "sched_state.json"
            early = run_digest(
                loaded_cfg, now=datetime(2026, 11, 23, 6, 30, tzinfo=core.EAT), scheduled=True,
                preview_path=tmp_preview, state_path=sched_state, lock_path=tmp_lock,
                claude_client=SimpleNamespace(messages=FailClaude()), smtp_factory=FakeSMTP,
            )
            catchup = run_digest(
                loaded_cfg, now=datetime(2026, 11, 24, 9, 15, tzinfo=core.EAT), scheduled=True,
                preview_path=tmp_preview, state_path=sched_state, lock_path=tmp_lock,
                claude_client=SimpleNamespace(messages=FailClaude()), claude_route=core.ModelRoute(),
                smtp_factory=FakeSMTP,
            )
            lock_blocked = False
            with acquire_process_lock(tmp_lock):
                try:
                    with acquire_process_lock(tmp_lock):
                        pass
                except OverlapLockError:
                    lock_blocked = True
                overlap = run_digest(
                    loaded_cfg, now=monday_after, preview_path=tmp_preview,
                    state_path=tmp / "overlap_state.json", lock_path=tmp_lock, smtp_factory=FakeSMTP,
                )
                lock_blocked = lock_blocked and overlap.status == "skipped_locked"
            with acquire_process_lock(tmp_lock):
                reacquired = True
            check(
                "23 Scheduled mode waits until Monday 07:00, catches up Tuesday, and OS lock stops overlaps",
                early.status == "skipped_before_schedule"
                and catchup.status == "sent" and catchup.late_by == "26h15m"
                and lock_blocked and reacquired,
                f"early={early.status} catchup={catchup.status}/{catchup.late_by} lock={lock_blocked}",
            )

            # Check 24: Atomic preview lock fallback & privacy check on log + state
            locked_html = tmp / "locked_preview.html"
            real_replace = os.replace

            def sim_lock(src, dst):
                if Path(dst) == locked_html:
                    raise PermissionError(13, "File in use", str(dst))
                return real_replace(src, dst)

            with mock.patch.object(os, "replace", side_effect=sim_lock), \
                 mock.patch.object(time, "sleep"):
                fallback_written = atomic_write_text(locked_html, "<html>ok</html>", allow_fallback=True)

            combined_private = (
                (tmp_log.read_text(encoding="utf-8") if tmp_log.is_file() else "")
                + (tmp_state.read_text(encoding="utf-8") if tmp_state.is_file() else "")
            )
            check(
                "24 Locked HTML preview uses timestamped copy (no .tmp left); log & state hide emails/figures",
                fallback_written != locked_html and fallback_written.is_file()
                and not list(tmp.glob("*.tmp"))
                and "novahighlands.co.ke" not in combined_private
                and "1432656" not in combined_private and "1,432,656" not in combined_private,
                f"written={fallback_written}",
            )

            # Check 25: Task Scheduler XML + cron lines
            xml_text = build_windows_task_xml(
                Path(r"C:\Users\farm\.venvs\kimnovix-env\Scripts\pythonw.exe"),
                Path(r"C:\Users\farm\Desktop\repo\week7\weekly_livestock_digest.py"),
                Path(r"C:\Users\farm\Desktop\repo\week7\config.env"),
                custom_cfg,
                "NOVA-PC\\farm",
            )
            ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
            root = ET.fromstring(xml_text.split("\n", 1)[1])

            def xml_val(path: str) -> str:
                node = root.find(path, ns)
                return (node.text or "").strip() if node is not None else ""

            cron = build_cron_lines(Path("/srv/nova/config.env"), loaded_cfg)
            check(
                "25 Task XML: Monday 07:00+03:00, pythonw, StartWhenAvailable, logon catch-up, "
                "battery-safe, 30-min retries; cron pinned to Nairobi",
                xml_val("t:Triggers/t:CalendarTrigger/t:StartBoundary").endswith("T07:00:00+03:00")
                and root.find("t:Triggers/t:CalendarTrigger/t:ScheduleByWeek/t:DaysOfWeek/t:Monday", ns) is not None
                and xml_val("t:Triggers/t:CalendarTrigger/t:Repetition/t:Interval") == "PT30M"
                and xml_val("t:Triggers/t:CalendarTrigger/t:Repetition/t:Duration") == "PT4H"
                and xml_val("t:Triggers/t:LogonTrigger/t:UserId") == "NOVA-PC\\farm"
                and xml_val("t:Principals/t:Principal/t:LogonType") == "InteractiveToken"
                and xml_val("t:Settings/t:StartWhenAvailable") == "true"
                and xml_val("t:Settings/t:DisallowStartIfOnBatteries") == "false"
                and xml_val("t:Settings/t:StopIfGoingOnBatteries") == "false"
                and xml_val("t:Settings/t:MultipleInstancesPolicy") == "IgnoreNew"
                and xml_val("t:Actions/t:Exec/t:Command").endswith("pythonw.exe")
                and "--scheduled" in xml_val("t:Actions/t:Exec/t:Arguments")
                and "Test &lt;Farm&gt; &amp; Co" in xml_text
                and cron[0] == "CRON_TZ=Africa/Nairobi" and cron[1].startswith("0 7 * * 1 ")
                and all("--scheduled" in line for line in cron[1:])
                and (os.name == "nt" or task_python_exe() == Path(sys.executable).absolute()),
                f"cron={cron}",
            )

            # Check 26: No-data notice once, then the full digest once the CSV arrives
            late_csv = tmp / "late" / "ops.csv"
            late_csv.parent.mkdir()
            early_lines = [
                ln for ln in sample_text.splitlines()
                if ln.startswith("date") or ln[:10] < "2026-11-16"
            ]
            late_csv.write_text("\n".join(early_lines) + "\n", encoding="utf-8")
            late_cfg = dataclasses.replace(loaded_cfg, data_paths=(late_csv,))
            late_sent: List[EmailMessage] = []

            class LateSMTP(FakeSMTP):
                def send_message(self, msg, from_addr=None, to_addrs=None):
                    late_sent.append(msg)
                    return {}

            late_kwargs = dict(
                now=datetime(2026, 11, 23, 7, 5, tzinfo=core.EAT), scheduled=True,
                preview_path=tmp / "late.html", state_path=tmp / "late_state.json", lock_path=tmp_lock,
                claude_client=SimpleNamespace(messages=FailClaude()), claude_route=core.ModelRoute(),
                smtp_factory=LateSMTP, sleep_fn=lambda _s: None,
            )
            n1 = run_digest(late_cfg, **late_kwargs)
            n2 = run_digest(late_cfg, **late_kwargs)
            late_csv.write_text(sample_text, encoding="utf-8")  # the clerk saves last week's rows
            n3 = run_digest(late_cfg, **{**late_kwargs, "now": datetime(2026, 11, 23, 8, 35, tzinfo=core.EAT)})
            n4 = run_digest(late_cfg, **{**late_kwargs, "now": datetime(2026, 11, 23, 9, 5, tzinfo=core.EAT)})
            subjects = [str(m["Subject"]) for m in late_sent]
            check(
                "26 No-data notice sent once; full digest still goes out when the CSV arrives, then dedups",
                (n1.status, n2.status, n3.status, n4.status) == ("sent", "skipped_duplicate", "sent", "skipped_duplicate")
                and len(late_sent) == 2 and "[NO DATA]" in subjects[0] and "[NO DATA]" not in subjects[1]
                and "KES 1,432,656" in subjects[1],
                f"statuses={(n1.status, n2.status, n3.status, n4.status)} subjects={subjects}",
            )

            # Check 27: SMTP edge cases
            partial = send_email_smtp(
                msg_custom, loaded_cfg,
                smtp_factory=type("PartialSMTP", (FakeSMTP,), {
                    "send_message": lambda self, m, from_addr=None, to_addrs=None: {"m5@novahighlands.co.ke": (550, b"no")}
                }),
                sleep_fn=lambda _s: None,
            )
            quit_sends = {"n": 0}

            class QuitFailSMTP(FakeSMTP):
                def send_message(self, msg, from_addr=None, to_addrs=None):
                    quit_sends["n"] += 1
                    return {}

                def __exit__(self, *args):
                    raise smtplib.SMTPServerDisconnected("dropped during QUIT")

            quit_res = send_email_smtp(msg_custom, loaded_cfg, smtp_factory=QuitFailSMTP, sleep_fn=lambda _s: None)
            tls_calls: List[str] = []

            class StartTlsSMTP(FakeSMTP):
                def __init__(self, host, port, **kwargs):
                    tls_calls.append("context" if "context" in kwargs else f"plain:{port}")

                def starttls(self, context=None):
                    tls_calls.append("starttls")

            send_email_smtp(
                msg_custom, dataclasses.replace(loaded_cfg, smtp_port=587),
                smtp_factory=StartTlsSMTP, sleep_fn=lambda _s: None,
            )
            cert_slept: List[float] = []
            cert_err = ""
            try:
                send_email_smtp(
                    msg_custom, loaded_cfg,
                    smtp_factory=mock.Mock(side_effect=ssl.SSLCertVerificationError("certificate verify failed")),
                    sleep_fn=cert_slept.append,
                )
            except EmailDeliveryError as err:
                cert_err = str(err)
            check(
                "27 SMTP: partial refusal reported, QUIT drop after delivery never resends, "
                "587 uses STARTTLS, certificate failure stops at once",
                partial.attempts == 1 and partial.refused == 1
                and quit_res.attempts == 1 and quit_sends["n"] == 1
                and tls_calls == ["plain:587", "starttls"]
                and not cert_slept and "date and time" in cert_err,
                f"partial={partial} quit={quit_res}/{quit_sends} tls={tls_calls} cert={cert_err!r}",
            )

            # Check 28: Header injection blocked; Date + Message-ID present without PC hostname
            evil_cfg = dataclasses.replace(
                loaded_cfg,
                client_name="Nova\r\nBcc: thief@evil.test",
                sender_name="Reports\nBcc: thief@evil.test",
            )
            evil_msg, _evil_html = build_email_message(r_custom, evil_cfg)
            header_values = [str(v) for _k, v in evil_msg.items()]
            injected_recs, injected_bad = parse_recipients("ok@farm.co.ke\nBcc: thief@evil.test, fine@farm.co.ke")
            check(
                "28 CR/LF in client name, sender name or recipients cannot add a Bcc header; "
                "Date and Message-ID set from the Gmail domain",
                "bcc" not in {k.lower() for k in evil_msg.keys()}
                and not any("\n" in v or "\r" in v for v in header_values)
                and injected_recs == ("fine@farm.co.ke",) and len(injected_bad) == 1
                and evil_msg["Date"] is not None
                and str(evil_msg["Message-ID"]).endswith("@novahighlands.co.ke>"),
                f"headers={list(evil_msg.items())[:4]} recs={injected_recs}",
            )

            # Check 29: config extras: typo warning, literal '$', DATA_PATH from config folder,
            # missing DATA_PATH / FARM / duplicate threshold / example.com addresses all reported
            extras_env = tmp / "extras.env"
            extras_env.write_text(
                base_cfg_text.replace("GMAIL_APP_PASSWORD=qrst uvwx yzab cdef", "GMAIL_APP_PASSWORD=qrst$uvwx${HOME}cd")
                + "MORTALITY_ALERT_PERCENT=WEANER:9\n",
                encoding="utf-8",
            )
            extras_cfg = load_and_validate_config(extras_env)
            broken_env = tmp / "broken.env"
            broken_env.write_text(
                base_cfg_text.replace("DATA_PATH=sample.csv", "DATA_PATH=no_such_folder")
                .replace("SECTIONS=BREEDING,", "SECTIONS=FARM,BREEDING,")
                .replace("GROWER:0.50", "GROWER:0.50,GROWER:0.80")
                .replace("m4@novahighlands.co.ke", "manager@example.com"),
                encoding="utf-8",
            )
            broken_msg = ""
            try:
                load_and_validate_config(broken_env)
            except ConfigError as err:
                broken_msg = str(err)
            check(
                "29 Config: misspelt key warned, '$' kept literal, DATA_PATH resolved from config folder; "
                "missing path, FARM, duplicate threshold and example.com listed together",
                any("MORTALITY_ALERT_PERCENT" in w for w in extras_cfg.warnings)
                and extras_cfg.gmail_app_password == "qrst$uvwx${HOME}cd"
                and extras_cfg.data_paths == ((tmp / "sample.csv").resolve(),)
                and all(k in broken_msg for k in ("no_such_folder", "'FARM'", "GROWER' twice", "manager@example.com")),
                f"warnings={extras_cfg.warnings} broken={broken_msg}",
            )

            # Check 30: privacy sweep over every log line and every state file this suite wrote
            private_text = tmp_log.read_text(encoding="utf-8") if tmp_log.is_file() else ""
            for state_file in tmp.glob("*state*.json"):
                private_text += state_file.read_text(encoding="utf-8")
            forbidden = ("@", "KES ", "1,432,656", "1432656", "WEEKLY PERFORMANCE", "Nova", "Eldoret")
            leaks = [word for word in forbidden if word in private_text]
            check(
                "30 Privacy sweep: digest.log + every digest_state.json hold no emails, figures, names or summary text",
                not leaks and "OK sent" in private_text and "sent_weeks" in private_text,
                f"leaks={leaks}",
            )

    total = len(results)
    passed = sum(results)
    grand_total, grand_passed = core_total + total, core_passed + passed
    print("=" * 72)
    if core_rc != 0 or core_total == 0 or total == 0 or passed != total:
        print(
            f"   FAILED: core {core_passed}/{core_total} (rc={core_rc}), digest {passed}/{total}, "
            f"total {grand_passed}/{grand_total}"
        )
        print("=" * 72)
        return 1
    print(f"   ALL {grand_total} CHECKS PASSED ({core_total} core + {total} digest = {grand_passed}/{grand_total})")
    print("=" * 72)
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _parse_sunday(text: str) -> date:
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError("use YYYY-MM-DD, for example 2026-11-22") from None


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Week 7 Day 33: Weekly Livestock Digest (email, config, scheduling)."
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG_PATH,
        help="Path to config.env (default: week7/config.env).",
    )
    parser.add_argument(
        "--csv", type=Path, nargs="+", default=None,
        help="Override DATA_PATH from config.env with one or more CSV files/folders.",
    )
    parser.add_argument(
        "--to", type=str, default=None,
        help="Override REPORT_RECIPIENTS (comma-separated emails).",
    )
    parser.add_argument(
        "--time", type=str, default=None,
        help="Override SCHEDULE_TIME (e.g. 07:00 or 8am).",
    )
    parser.add_argument(
        "--week-ending", type=_parse_sunday, default=None,
        help="Report the Mon-Sun week ending on this Sunday (default: last complete week, EAT).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Build preview HTML without calling Claude or SMTP.")
    parser.add_argument("--scheduled", action="store_true", help="Respect Monday schedule window and weekly dedup.")
    parser.add_argument("--force", action="store_true", help="Resend even if this ISO week was already sent.")
    parser.add_argument("--check-config", action="store_true", help="Validate config.env and exit.")
    parser.add_argument("--install-task", action="store_true", help="Install Monday scheduled task (Windows/Linux).")
    parser.add_argument("--uninstall-task", action="store_true", help="Remove Windows scheduled task.")
    parser.add_argument("--status", action="store_true", help="Show last send status and recent log lines.")
    parser.add_argument("--self-test", action="store_true", help="Run every offline check: Day 32 core + Day 33 digest (zero real API/SMTP calls).")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    core.make_console_unicode_safe()
    args = parse_args(argv)

    if args.self_test:
        return run_self_test()
    if args.uninstall_task:
        return uninstall_schedule()
    if args.status:
        return print_status()

    config_path = args.config.expanduser().resolve()
    try:
        cfg = load_and_validate_config(
            config_path,
            require_secrets=not args.dry_run,
            to_override=args.to,
            csv_override=args.csv,
            time_override=args.time,
        )
    except ConfigError as err:
        print(f"\n[CONFIGURATION ERROR]\n{err}")
        log_digest_event("ERROR", "config_validation_failed")
        return 1

    for note in cfg.warnings:
        print(f"[CONFIG WARNING] {note}")

    if args.check_config:
        print(f"[OK] Configuration valid for '{cfg.client_name}'.")
        print(f"     Sections   : {', '.join(cfg.sections)}")
        print(f"     Data Path  : {', '.join(str(p) for p in cfg.data_paths)}")
        print(f"     Recipients : {len(cfg.recipients)} manager(s)")
        print(f"     Schedule   : Mondays at {cfg.schedule_time_str} EAT")
        return 0

    if args.install_task:
        return install_schedule(config_path, cfg)

    try:
        outcome = run_digest(
            cfg,
            week_ending=args.week_ending,
            dry_run=args.dry_run,
            scheduled=args.scheduled,
            force=args.force,
        )
    except Exception as err:  # noqa: BLE001 - pythonw has no console, so the log is the only witness
        # Type name only: the message text could carry file contents or addresses.
        log_digest_event("ERROR", f"unexpected_error type={type(err).__name__} scheduled={args.scheduled}")
        print(f"[ERROR] Unexpected failure ({type(err).__name__}): {err}")
        return 3
    print(f"[{outcome.status.upper()}] {outcome.message}")
    if outcome.preview_path:
        print(f"[PREVIEW] {outcome.preview_path}")
    if outcome.report_result and outcome.report_result.api_calls:
        res = outcome.report_result
        print(
            f"[Telemetry] Model: {res.model} | Calls: {res.api_calls} | "
            f"Tokens: {res.input_tokens}/{res.output_tokens} | Cost: KES {res.cost_kes}"
        )
    return outcome.exit_code


if __name__ == "__main__":
    sys.exit(main())