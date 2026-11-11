from datetime import datetime
from pathlib import Path
import shutil

BASE_DIR = Path(__file__).resolve().parent
TARGET_DIR = BASE_DIR / "moi_avenue_downloads"
LOG_FILE = TARGET_DIR / "sort_log.txt"

CATEGORIES = {
    "Contracts": {".docx", ".doc"},
    "Evidence": {".jpg", ".jpeg", ".png"},
    "Filings": {".pdf"},
    "Correspondence": {".txt", ".eml"},
}
SKIP_SUFFIXES = {".crdownload", ".tmp", ".part"}

DUMMY_FILES = [
    "scan001.pdf", "scan002.pdf", "IMG_4827.jpg", "IMG_4828.png",
    "Contract_FINAL_v3.docx", "Lease_Agreement.doc",
    "client_email.eml", "meeting_notes.txt",
    "unknown_software.exe", "budget_draft.xlsx",
]


def setup_dummy_files():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    created = 0
    for name in DUMMY_FILES:
        path = TARGET_DIR / name
        if not path.exists():
            path.write_text("Dummy content", encoding="utf-8")
            created += 1
    print(f"[SETUP] Created {created} dummy files in '{TARGET_DIR}'\n")


def log_line(message):
    """Open, write, close each time so no handle stays locked."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"[{now}] {message}\n")


def unique_destination(dest_dir, name):
    """Return a path that does not exist yet: name, name (1), name (2)..."""
    candidate = dest_dir / name
    stem, suffix = Path(name).stem, Path(name).suffix
    counter = 1
    while candidate.exists():
        candidate = dest_dir / f"{stem} ({counter}){suffix}"
        counter += 1
    return candidate


def category_for(path):
    ext = path.suffix.lower()
    for category, extensions in CATEGORIES.items():
        if ext in extensions:
            return category
    return "Other"


def sort_files(dry_run=False):
    if not TARGET_DIR.is_dir():
        print(f"Error: Target directory '{TARGET_DIR}' does not exist.")
        return

    print("--- DRY RUN (no files will be moved) ---" if dry_run
          else "--- SORTING INITIATED ---")

    moved = failed = 0
    for item in sorted(TARGET_DIR.iterdir()):
        if (not item.is_file() or item.is_symlink()
                or item.name == LOG_FILE.name
                or item.name.startswith("~$")
                or item.suffix.lower() in SKIP_SUFFIXES):
            continue

        folder = category_for(item)
        dest_dir = TARGET_DIR / folder
        dest = unique_destination(dest_dir, item.name)

        if dry_run:
            print(f"Would move: {item.name} -> {folder}/{dest.name}")
            continue

        try:
            dest_dir.mkdir(exist_ok=True)
            shutil.move(str(item), str(dest))
        except OSError as err:  # includes PermissionError (file open elsewhere)
            failed += 1
            log_line(f"FAILED: {item} ({err})")
            print(f"Skipped (in use or unreadable): {item.name}")
            continue

        moved += 1
        log_line(f"MOVED: {item} -> {dest}")
        print(f"Moved: {item.name} -> {folder}/{dest.name}")

    if not dry_run:
        print(f"\n[COMPLETE] Moved {moved}, failed {failed}. See {LOG_FILE}")


if __name__ == "__main__":
    setup_dummy_files()
    sort_files(dry_run=True)   # preview first, as a careful clerk would
    sort_files(dry_run=False)