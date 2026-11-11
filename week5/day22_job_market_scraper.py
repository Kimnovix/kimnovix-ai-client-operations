import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_CSV = BASE_DIR / "scraped_listings.csv"

BASE_URL = "https://quotes.toscrape.com"
MAX_PAGES = 3
POLITE_DELAY_SECONDS = 1.0
TIMEOUT = (5, 15)  # (connect, read) seconds

USER_AGENT = (
    "KimnovixMarketResearchBot/1.0 "
    "(+https://github.com/Kimnovix/kimnovix-ai-client-operations)"
)

FIELDNAMES = [
    "author_or_company", "skill_tags", "tag_count",
    "listing_summary", "detail_url", "source_page", "scraped_at",
]


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    retry = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def load_robots(session: requests.Session) -> RobotFileParser:
    parser = RobotFileParser()
    try:
        resp = session.get(urljoin(BASE_URL, "/robots.txt"), timeout=TIMEOUT)
        if resp.status_code == 200:
            parser.parse(resp.text.splitlines())
        elif resp.status_code in (401, 403):
            parser.disallow_all = True
        else:
            parser.allow_all = True
    except requests.RequestException as err:
        print(f"[WARN] Could not read robots.txt ({err}); proceeding cautiously.")
        parser.allow_all = True
    return parser


def sanitize_cell(value: object) -> object:
    """Neutralise Excel formula injection in text cells."""
    if isinstance(value, str):
        stripped = value.lstrip()
        if value[:1] in ("\t", "\r", "\n") or (stripped and stripped[0] in "=+-@"):
            return "'" + value
    return value


def fetch_soup(session: requests.Session, url: str) -> Optional[BeautifulSoup]:
    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as err:
        print(f"[WARN] Failed to fetch {url}: {err}")
        return None
    # Pass bytes so BeautifulSoup detects the encoding itself.
    return BeautifulSoup(response.content, "html.parser")


def parse_listings(
    soup: BeautifulSoup, page_num: int, scraped_at: str
) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    for card in soup.find_all("div", class_="quote"):
        text_el = card.find("span", class_="text")
        summary = text_el.get_text(strip=True).strip("“”\"") if text_el else ""
        if not summary:
            continue  # skip empty or malformed cards

        author_el = card.find("small", class_="author")
        author = author_el.get_text(strip=True) if author_el else "Unknown"

        link_el = card.select_one('a[href*="/author/"]')
        detail_url = urljoin(BASE_URL, link_el["href"]) if link_el else ""

        tags = [t.get_text(strip=True) for t in card.find_all("a", class_="tag")]

        records.append({
            "author_or_company": author,
            "skill_tags": ", ".join(tags),
            "tag_count": len(tags),
            "listing_summary": summary,
            "detail_url": detail_url,
            "source_page": page_num,
            "scraped_at": scraped_at,
        })
    return records


def find_next_page_url(soup: BeautifulSoup, current_url: str) -> Optional[str]:
    next_li = soup.find("li", class_="next")
    link = next_li.find("a", href=True) if next_li else None
    if not link:
        return None
    next_url = urljoin(current_url, link["href"])
    if urlparse(next_url).netloc != urlparse(BASE_URL).netloc:
        return None  # never follow links off the target site
    return next_url


def save_to_csv(records: List[Dict[str, object]], output_path: Path) -> Optional[Path]:
    if not records:
        print("[ERROR] No records collected; skipping CSV export.")
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(".csv.tmp")
    with open(tmp_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in records:
            writer.writerow({k: sanitize_cell(v) for k, v in row.items()})

    try:
        os.replace(tmp_path, output_path)
        return output_path
    except PermissionError:  # e.g. file open in Excel on Windows
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback = output_path.with_name(f"{output_path.stem}_{stamp}{output_path.suffix}")
        os.replace(tmp_path, fallback)
        print(f"[WARN] '{output_path.name}' is locked (open in Excel?). Saved to {fallback.name}")
        return fallback


def run_scraper(max_pages: int = MAX_PAGES) -> int:
    print("======================================================")
    print("   KIMNOVIX COMPETITIVE LISTINGS SCRAPER (v1.1)       ")
    print("======================================================")

    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    all_records: List[Dict[str, object]] = []
    seen = set()
    current_url: Optional[str] = BASE_URL

    with build_session() as session:
        robots = load_robots(session)
        for page_num in range(1, max_pages + 1):
            if not current_url:
                break
            if not robots.can_fetch(USER_AGENT, current_url):
                print(f"[SKIP] robots.txt disallows {current_url}")
                break

            print(f"[FETCH] Page {page_num}: {current_url}")
            soup = fetch_soup(session, current_url)
            if soup is None:
                print(f"[ABORT] Could not retrieve page {page_num}. Stopping.")
                break

            new = 0
            for rec in parse_listings(soup, page_num, scraped_at):
                key = (rec["author_or_company"], rec["listing_summary"])
                if key not in seen:
                    seen.add(key)
                    all_records.append(rec)
                    new += 1
            print(f"        -> Extracted {new} new listings.")

            current_url = find_next_page_url(soup, current_url)
            if current_url and page_num < max_pages:
                time.sleep(POLITE_DELAY_SECONDS)

    saved = save_to_csv(all_records, OUTPUT_CSV)
    print("------------------------------------------------------")
    print(f"[COMPLETE] Total listings scraped : {len(all_records)}")
    print(f"[SAVED]    CSV report path        : {saved}")
    print("======================================================")
    return 0 if saved else 1


if __name__ == "__main__":
    sys.exit(run_scraper())