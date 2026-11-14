"""
Day 24 - Scheduled & Persistent Sales Report Runner (Week 5: Scheduling & Background Jobs)

Wraps week5/day23_sales_email_report.py so the 6:00 PM report runs by itself,
survives power cuts and dropped internet, and never emails the owner twice.

Usage:
    python week5/day24_scheduled_sales_runner.py                 # run the report now (manual)
    python week5/day24_scheduled_sales_runner.py --dry-run       # build report, no email
    python week5/day24_scheduled_sales_runner.py --catch-up      # run ONLY if the latest 6 PM report has not gone out yet
    python week5/day24_scheduled_sales_runner.py --status        # when did the last report go out?
    python week5/day24_scheduled_sales_runner.py --daemon        # keep running in the background (schedule library)
    python week5/day24_scheduled_sales_runner.py --install-task  # Windows: register the 6 PM task (Linux: prints crontab lines)
    python week5/day24_scheduled_sales_runner.py --uninstall-task
    Options: --time 18:00 | 6pm | "6:30 PM"   --csv PATH   --to a@b.com   --timeout 300

Every real run appends one line to week5/run_log.txt:
    YYYY-MM-DD HH:MM:SS | SUCCESS/ERROR/SKIPPED | rows_processed=<N> | <detail>

Day 23 exit codes this wrapper relies on:
    0 = report built and emailed (or --dry-run preview built)
    1 = report aborted (CSV missing, unreadable, or no valid rows)
    2 = report built but email NOT sent (no internet, bad app password, no recipient)
"""

import argparse
import contextlib
import importlib.util
import io
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as xml_escape

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DAY23_SCRIPT = BASE_DIR / "day23_sales_email_report.py"
DEFAULT_CSV_PATH = BASE_DIR / "nairobi_retail_sales.csv"
RUN_LOG_PATH = BASE_DIR / "run_log.txt"
STATE_PATH = BASE_DIR / "scheduler_state.json"
LOCK_PATH = BASE_DIR / "scheduler.lock"

WINDOWS_TASK_NAME = "Kimnovix_Daily_Sales_Report_6PM"
DEFAULT_RUN_TIME = "18:00"

# Day 23 can legitimately take ~2 minutes: 3 SMTP attempts x 20 s socket timeout
# per network step, plus 5 s + 10 s back-off. 60 s killed good retries mid-send.
DEFAULT_TIMEOUT_SECONDS = 300

SLOT_TOLERANCE = timedelta(minutes=2)      # a run at 17:58-18:02 counts as "the 6 PM report"
FIRST_RUN_GRACE = timedelta(minutes=35)    # on a fresh install, still send a report due up to 35 min ago
STALE_AFTER = timedelta(hours=26)          # --status warns if no report went out for this long
RETRY_EVERY = "PT30M"                      # Windows task: retry every 30 min ...
RETRY_FOR = "PT4H"                         # ... for 4 hours after 6 PM (power/internet back)
SCHTASKS_TR_LIMIT = 261                    # schtasks /TR refuses longer commands

DAY23_EXIT_MEANING = {
    1: "report_aborted",
    2: "email_not_sent",
}


# ---------------------------------------------------------------------------
# Console + time helpers
# ---------------------------------------------------------------------------
def make_console_unicode_safe() -> None:
    """Older Windows consoles use cp1252; under pythonw.exe there is no console at all."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


TIME_PATTERN = re.compile(r"^\s*(\d{1,2})(?::(\d{2}))?\s*(?:([ap])\.?\s*m?\.?)?\s*$", re.IGNORECASE)


def parse_run_time(text: str) -> str:
    """Accept 18:00, 6:00, 6pm, 6:30 PM; always return zero-padded 24-hour HH:MM.

    schedule, schtasks /ST and cron all need a valid HH:MM. "6:00" or "25:00"
    used to crash the daemon at start-up or produce a broken crontab line.
    """
    match = TIME_PATTERN.match(str(text))
    if not match:
        raise argparse.ArgumentTypeError(f"'{text}' is not a time. Use HH:MM, e.g. 18:00 or 6:00 PM.")
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = (match.group(3) or "").lower()
    if not meridiem and match.group(2) is None:
        raise argparse.ArgumentTypeError(f"'{text}' is ambiguous. Use 18:00 or 6pm.")
    if meridiem:
        if not 1 <= hour <= 12:
            raise argparse.ArgumentTypeError(f"'{text}': with AM/PM the hour must be 1-12.")
        hour = hour % 12 + (12 if meridiem == "p" else 0)
    if hour > 23 or minute > 59:
        raise argparse.ArgumentTypeError(f"'{text}' is not a real clock time (00:00-23:59).")
    return f"{hour:02d}:{minute:02d}"


def latest_due_slot(run_time: str, now: Optional[datetime] = None) -> datetime:
    """The most recent 'report time' that has arrived, e.g. today 18:00 or, before 6 PM, yesterday 18:00."""
    now = now or datetime.now()
    hour, minute = (int(part) for part in run_time.split(":"))
    slot = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if slot > now + SLOT_TOLERANCE:
        slot -= timedelta(days=1)
    return slot


def human_duration(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(max(minutes, 0), 60)
    return f"{hours}h{minutes:02d}m"


# ---------------------------------------------------------------------------
# Run log + state file
# ---------------------------------------------------------------------------
def write_run_log(status: str, rows_processed: int, detail: str, log_path: Path = RUN_LOG_PATH) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Pipes inside the detail would break anyone splitting the log on " | ".
    clean_detail = " ".join(str(detail).replace("|", "/").split())
    line = f"{timestamp} | {status.upper()} | rows_processed={rows_processed} | {clean_detail}"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, mode="a", encoding="utf-8", newline="") as log_file:
            log_file.write(line + "\n")
    except OSError as err:
        print(f"[WARN] Could not write to run log '{log_path}': {err}")
    print(line)
    return line


def load_state(path: Path = STATE_PATH) -> Dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(state: Dict[str, str], path: Path = STATE_PATH) -> None:
    """Write to a temp file then swap it in, so a power cut never leaves half a JSON file.

    The repo lives on a Google Drive-synced Desktop; Drive can hold a file for a
    moment while it uploads, so retry the swap a few times before giving up.
    """
    tmp_path = path.with_suffix(".json.tmp")
    try:
        tmp_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError as err:
        print(f"[WARN] Could not write state file: {err}")
        return
    for attempt in range(5):
        try:
            os.replace(tmp_path, path)
            return
        except OSError as err:
            if attempt == 4:
                print(f"[WARN] Could not update '{path.name}': {err}")
            time.sleep(0.5)


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def ensure_baseline(state: Dict[str, str]) -> Dict[str, str]:
    """Remember when scheduling started, so the first catch-up never emails a report from before install."""
    if not parse_iso(state.get("installed_at")):
        state["installed_at"] = (datetime.now() - FIRST_RUN_GRACE).isoformat(timespec="seconds")
        save_state(state)
    return state


def report_is_due(state: Dict[str, str], run_time: str, dry_run: bool,
                  now: Optional[datetime] = None) -> Tuple[bool, datetime, str]:
    slot = latest_due_slot(run_time, now)
    key = "last_dry_run_at" if dry_run else "last_success_at"
    last_ok = parse_iso(state.get(key))
    baseline = parse_iso(state.get("installed_at"))
    if baseline and slot < baseline:
        return False, slot, f"the {slot:%d %b %H:%M} slot is from before scheduling was set up"
    if last_ok and last_ok >= slot - SLOT_TOLERANCE:
        return False, slot, f"already done at {last_ok:%Y-%m-%d %H:%M}"
    return True, slot, "due"


# ---------------------------------------------------------------------------
# Overlap protection
# ---------------------------------------------------------------------------
class RunLock:
    """An OS-level file lock: if the PC crashes or the process is killed, Windows/Linux
    release it automatically, so there is never a stale lock to clean up by hand."""

    def __init__(self, path: Path = LOCK_PATH):
        self.path = path
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


# ---------------------------------------------------------------------------
# Row counting: reuse Day 23's own parser instead of a second copy of the rules
# ---------------------------------------------------------------------------
_day23_module = None


def _load_day23():
    global _day23_module
    if _day23_module is None:
        spec = importlib.util.spec_from_file_location("day23_sales_email_report", DAY23_SCRIPT)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load {DAY23_SCRIPT.name}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _day23_module = module
    return _day23_module


def count_rows_like_day23(csv_path: Path) -> Tuple[int, int, Optional[str]]:
    """Return (rows_processed, rows_skipped, error) using Day 23's analyze_sales_csv()."""
    try:
        day23 = _load_day23()
        with contextlib.redirect_stdout(io.StringIO()):  # silence Day 23's [WARN] lines
            metrics = day23.analyze_sales_csv(csv_path)
        return int(metrics["line_count"]), int(metrics["skipped_rows"]), None
    except Exception as err:  # noqa: BLE001 - counting must never crash the scheduler
        return 0, 0, f"{type(err).__name__}: {err}"


def summarize_failure(stdout: str, stderr: str) -> str:
    """Day 23 prints its errors to STDOUT and ends with a '=====' banner, so 'last line
    of output' was usually just the banner. Look for the real error line instead."""
    for line in reversed((stdout or "").splitlines()):
        text = line.strip()
        if text.startswith(("[ERROR]", "[SKIPPED SMTP]")):
            return text
    stderr_lines = [l.strip() for l in (stderr or "").splitlines() if l.strip()]
    if stderr_lines:
        return stderr_lines[-1]  # e.g. the last line of a Python traceback
    return "no error message captured"


# ---------------------------------------------------------------------------
# The job
# ---------------------------------------------------------------------------
def execute_sales_report_job(
    csv_path: Path = DEFAULT_CSV_PATH,
    dry_run: bool = False,
    recipient: Optional[str] = None,
    run_time: str = DEFAULT_RUN_TIME,
    catch_up: bool = False,
    trigger: str = "manual",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> int:
    lock = RunLock()
    if not lock.acquire():
        if catch_up:
            # A retry tick landed while the on-time run was busy: the busy run will finish the job.
            print("[CATCH-UP] Another report run is in progress; leaving it to finish.")
        else:
            write_run_log("SKIPPED", 0, f"trigger={trigger} another report run is still in progress")
        return 0
    try:
        state = load_state()
        slot = latest_due_slot(run_time)
        if catch_up:
            state = ensure_baseline(state)
            due, slot, reason = report_is_due(state, run_time, dry_run)
            if not due:
                # Quiet on purpose: retries fire every 30 min and would flood the log.
                print(f"[CATCH-UP] Nothing to do: {reason}.")
                return 0
        return _run_day23(csv_path, dry_run, recipient, slot, catch_up, trigger, timeout_seconds, state)
    finally:
        lock.release()


def _run_day23(csv_path: Path, dry_run: bool, recipient: Optional[str], slot: datetime,
               catch_up: bool, trigger: str, timeout_seconds: int, state: Dict[str, str]) -> int:
    if not DAY23_SCRIPT.is_file():
        write_run_log("ERROR", 0, f"trigger={trigger} missing script: {DAY23_SCRIPT.name}")
        return 1

    cmd: List[str] = [sys.executable, str(DAY23_SCRIPT), "--csv", str(csv_path)]
    if dry_run:
        cmd.append("--dry-run")
    if recipient:
        cmd.extend(["--to", recipient])

    late_note = ""
    started = datetime.now()
    if catch_up and started - slot > timedelta(minutes=10):
        late_note = f" late_by={human_duration(started - slot)}"

    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired:
        rows, _, _ = count_rows_like_day23(csv_path)
        write_run_log("ERROR", rows, f"trigger={trigger} timed out after {timeout_seconds}s "
                                     f"(email may or may not have gone out; check email_log.txt){late_note}")
        return 1
    except OSError as err:
        write_run_log("ERROR", 0, f"trigger={trigger} could not start Day 23: {err}")
        return 1

    duration = (datetime.now() - started).total_seconds()
    rows, skipped, count_err = count_rows_like_day23(csv_path)

    if proc.returncode == 0:
        mode = "dry_run_preview" if dry_run else "email_sent"
        partial = " partial_delivery=yes" if "Server refused" in (proc.stdout or "") else ""
        write_run_log(
            "SUCCESS", rows,
            f"mode={mode} trigger={trigger} exit_code=0 skipped_rows={skipped} "
            f"duration={duration:.1f}s{partial}{late_note}",
        )
        state["last_dry_run_at" if dry_run else "last_success_at"] = started.isoformat(timespec="seconds")
        if not dry_run:
            state["last_success_rows"] = str(rows)
        save_state(state)
        return 0

    meaning = DAY23_EXIT_MEANING.get(proc.returncode, "unexpected_failure")
    message = summarize_failure(proc.stdout, proc.stderr)
    if count_err and proc.returncode == 1:
        message = message if message != "no error message captured" else count_err
    write_run_log(
        "ERROR", rows,
        f"mode={meaning} trigger={trigger} exit_code={proc.returncode} msg={message[:160]}{late_note}",
    )
    return 1


# ---------------------------------------------------------------------------
# --status: the "is it actually working?" check
# ---------------------------------------------------------------------------
def show_status(run_time: str) -> int:
    state = load_state()
    now = datetime.now()
    last_ok = parse_iso(state.get("last_success_at"))
    print("======================================================")
    print("   DAILY SALES REPORT - SCHEDULER STATUS              ")
    print("======================================================")
    print(f"Report time        : {run_time} daily")
    print(f"Latest due report  : {latest_due_slot(run_time, now):%a %d %b %Y %H:%M}")
    if last_ok:
        print(f"Last email sent    : {last_ok:%a %d %b %Y %H:%M} ({human_duration(now - last_ok)} ago, "
              f"{state.get('last_success_rows', '?')} rows)")
    else:
        print("Last email sent    : never (no successful real send recorded yet)")
    last_dry = parse_iso(state.get("last_dry_run_at"))
    if last_dry:
        print(f"Last dry run       : {last_dry:%a %d %b %Y %H:%M}")

    try:
        tail = RUN_LOG_PATH.read_text(encoding="utf-8").splitlines()[-5:]
    except OSError:
        tail = []
    if tail:
        print("\nLast log lines:")
        for line in tail:
            print(f"  {line}")

    if not last_ok or now - last_ok > STALE_AFTER:
        print(f"\n[ALERT] No report has been emailed in the last {int(STALE_AFTER.total_seconds() // 3600)} hours.")
        return 1
    print("\n[OK] Reports are going out on schedule.")
    return 0


# ---------------------------------------------------------------------------
# --daemon: keep-alive loop
# ---------------------------------------------------------------------------
def run_persistent_schedule_loop(run_time: str, csv_path: Path, dry_run: bool,
                                 recipient: Optional[str], timeout_seconds: int) -> int:
    try:
        import schedule  # only the daemon needs it; the Task Scheduler path works without it
    except ImportError:
        print("[ERROR] --daemon needs the 'schedule' package: pip install schedule")
        return 1

    def job() -> None:
        try:
            execute_sales_report_job(csv_path, dry_run, recipient, run_time,
                                     catch_up=True, trigger="daemon", timeout_seconds=timeout_seconds)
        except Exception as err:  # noqa: BLE001 - one bad evening must not kill the loop
            write_run_log("ERROR", 0, f"trigger=daemon unexpected {type(err).__name__}: {err}")

    print("======================================================")
    print(f"   PERSISTENT SCHEDULER ACTIVE (Daily at {run_time})  ")
    print("   Retries every 30 min until the report goes out.    ")
    print("   Press Ctrl+C to stop cleanly.                      ")
    print("======================================================")

    schedule.clear()
    schedule.every().day.at(run_time).do(job)
    schedule.every(30).minutes.do(job)   # retries + covers sleep/hibernate; skips once sent
    job()                                # start-up catch-up: PC was off at 6 PM yesterday?

    try:
        while True:
            schedule.run_pending()
            time.sleep(20)
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Persistent scheduler stopped by user.")
        return 0


# ---------------------------------------------------------------------------
# --install-task / --uninstall-task
# ---------------------------------------------------------------------------
def build_task_arguments(run_time: str, csv_path: Path, dry_run: bool, recipient: Optional[str]) -> List[str]:
    args = [str(Path(__file__).resolve()), "--catch-up", "--time", run_time]
    if csv_path.resolve() != DEFAULT_CSV_PATH.resolve():
        args += ["--csv", str(csv_path.resolve())]
    if dry_run:
        args.append("--dry-run")
    if recipient:
        args += ["--to", recipient]
    return args


def windowless_python() -> Path:
    """pythonw.exe runs without a black console window that shop staff might close mid-run."""
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
    <Description>Kimnovix daily sales email. Runs at {run_time}, retries every 30 min for 4 hours, and catches up at logon if the PC was off. Sends at most once per day.</Description>
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
    print("[INFO] --install-task registers a Windows task. On Linux, run `crontab -e` and add BOTH lines:")
    print(f"{minute} {hour} * * * {command} >/dev/null 2>&1")
    print(f"*/30 * * * * {command} >/dev/null 2>&1")
    print("[INFO] Line 1 is the on-time run. Line 2 retries and catches up after the PC was off;")
    print("       --catch-up makes it send at most once per day, so it is safe to repeat.")
    return 0


def install_windows_scheduled_task(run_time: str, csv_path: Path, dry_run: bool,
                                   recipient: Optional[str]) -> int:
    task_args = build_task_arguments(run_time, csv_path, dry_run, recipient)
    if sys.platform != "win32":
        return print_crontab_lines(run_time, task_args)

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
        state = ensure_baseline(load_state())
        save_state(state)
        print(f"[INSTALLED] Task '{WINDOWS_TASK_NAME}': daily at {run_time}, retries every 30 min for 4 h,")
        print("            catch-up 3 min after logon, starts late if the PC was off. Sends once per day.")
        print(f"            Program  : {python_exe}")
        print(f"            Arguments: {arguments}")
        print("            Test it now: schtasks /Run /TN " + WINDOWS_TASK_NAME)
        return 0

    # Fallback: the classic one-line schtasks (no logon catch-up, no retries).
    print(f"[WARN] Full task setup was refused ({output}). Falling back to a basic daily task.")
    task_command = subprocess.list2cmdline([str(python_exe)] + task_args)
    if len(task_command) > SCHTASKS_TR_LIMIT:
        print(f"[ERROR] Command is {len(task_command)} characters; schtasks allows {SCHTASKS_TR_LIMIT}. "
              "Move the repo to a shorter folder (e.g. C:\\kimnovix) and try again.")
        return 1
    code, output = _run_schtasks(["schtasks", "/Create", "/SC", "DAILY", "/TN", WINDOWS_TASK_NAME,
                                  "/TR", task_command, "/ST", run_time, "/F"])
    if code == 0:
        ensure_baseline(load_state())
        print(f"[INSTALLED] Basic task '{WINDOWS_TASK_NAME}' at {run_time} daily (no automatic catch-up).")
        print("            Tip: open Task Scheduler > Properties > Settings and tick")
        print("            'Run task as soon as possible after a scheduled start is missed'.")
        return 0
    print(f"[ERROR] Failed to register task: {output}")
    return 1


def uninstall_windows_scheduled_task() -> int:
    if sys.platform != "win32":
        print("[INFO] On Linux, run `crontab -e` and delete the two day24 lines.")
        return 0
    try:
        code, output = _run_schtasks(["schtasks", "/Delete", "/TN", WINDOWS_TASK_NAME, "/F"])
    except OSError as err:
        code, output = 1, str(err)
    if code == 0:
        print(f"[REMOVED] Task '{WINDOWS_TASK_NAME}' deleted.")
        return 0
    print(f"[ERROR] Could not delete task: {output}")
    return 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or schedule the daily 6:00 PM Nairobi Retail Sales Report.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH, help="Path to the day's sales CSV.")
    parser.add_argument("--dry-run", action="store_true", help="Build the report but do not email it.")
    parser.add_argument("--to", type=str, default=None, help="Recipient(s), comma-separated.")
    parser.add_argument("--time", type=parse_run_time, default=DEFAULT_RUN_TIME,
                        help="Daily report time, e.g. 18:00 or '6:30 PM' (default 18:00).")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS,
                        help=f"Seconds before a stuck run is stopped (default {DEFAULT_TIMEOUT_SECONDS}).")
    parser.add_argument("--catch-up", action="store_true",
                        help="Run only if the latest scheduled report has not gone out yet.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--daemon", action="store_true", help="Stay running and send daily (schedule library).")
    mode.add_argument("--install-task", action="store_true", help="Register the Windows task (Linux: print crontab).")
    mode.add_argument("--uninstall-task", action="store_true", help="Remove the Windows task.")
    mode.add_argument("--status", action="store_true", help="Show when the last report went out.")
    args = parser.parse_args(argv)
    if args.timeout < 30:
        parser.error("--timeout must be at least 30 seconds (Day 23 retries Gmail for ~2 minutes).")
    return args


def main(argv: Optional[List[str]] = None) -> int:
    make_console_unicode_safe()
    args = parse_args(argv)
    csv_path = args.csv.expanduser().resolve()

    if args.status:
        return show_status(args.time)
    if args.uninstall_task:
        return uninstall_windows_scheduled_task()
    if args.install_task:
        return install_windows_scheduled_task(args.time, csv_path, args.dry_run, args.to)
    if args.daemon:
        return run_persistent_schedule_loop(args.time, csv_path, args.dry_run, args.to, args.timeout)

    return execute_sales_report_job(
        csv_path=csv_path,
        dry_run=args.dry_run,
        recipient=args.to,
        run_time=args.time,
        catch_up=args.catch_up,
        trigger="scheduled" if args.catch_up else "manual",
        timeout_seconds=args.timeout,
    )


if __name__ == "__main__":
    sys.exit(main())
