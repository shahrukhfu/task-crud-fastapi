import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, ValidationError

# Define base paths
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DETAIL_DIR = CACHE_DIR / "detail"
OUTPUT_DIR = BASE_DIR / "output"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DETAIL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BOOKS_JSON = OUTPUT_DIR / "books.json"
ERRORS_JSON = OUTPUT_DIR / "errors.json"
RUN_REPORT_JSON = OUTPUT_DIR / "run-report.json"

START_URL = "https://books.toscrape.com/catalogue/page-1.html"
HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/shahrukhfu/task-crud-fastapi)"
}
TIMEOUT = 5
REQUEST_DELAY = 0.5
MAX_PAGES = 3

# Execution metrics counters
metrics = {
    "pages_fetched": 0,
    "cache_hits": 0
}

class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_gbp: float
    price_text: str
    availability_text: str
    rating_text: str
    description: Optional[str] = None
    source_page: HttpUrl
    fetched_at: str

def parse_price(price_text: str) -> float:
    """
    Normalizes a price text string (e.g., '£51.77') to a numeric float (51.77).
    """
    if not price_text:
        return 0.0
    match = re.search(r"[\d.]+", price_text)
    if match:
        return float(match.group(0))
    return 0.0

def fetch_page_with_retry(url: str, cache_path: Path) -> str:
    """
    Returns HTML for a given URL. Loads from cache if present (no delay).
    Otherwise, attempts HTTP fetch with 1 retry attempt for timeouts/5xx errors.
    Skips retries on 404/403 errors.
    """
    if cache_path.exists():
        metrics["cache_hits"] += 1
        html_content = cache_path.read_text(encoding="utf-8")
        file_size = os.path.getsize(cache_path)
        print(f"CACHE HIT: {cache_path.name} - {file_size} bytes")
        return html_content

    max_attempts = 2
    attempts = 0

    while attempts < max_attempts:
        attempts += 1
        time.sleep(REQUEST_DELAY)
        try:
            metrics["pages_fetched"] += 1
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            
            if response.status_code == 200:
                html_content = response.text
                cache_path.write_text(html_content, encoding="utf-8")
                response_size = len(response.content)
                print(f"FETCH: {url} - {response_size} bytes")
                return html_content

            if response.status_code in (404, 403):
                raise RuntimeError(f"HTTP {response.status_code} client error for {url}")

            if response.status_code >= 500 and attempts < max_attempts:
                print(f"Retry attempt {attempts} for {url} due to HTTP {response.status_code}")
                continue
            
            raise RuntimeError(f"HTTP {response.status_code} server error for {url}")

        except requests.exceptions.Timeout as e:
            if attempts < max_attempts:
                print(f"Retry attempt {attempts} for {url} due to Timeout")
                continue
            raise RuntimeError(f"Timeout fetching {url}") from e
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error fetching {url}: {e}") from e

    raise RuntimeError(f"Failed to fetch {url} after {max_attempts} attempts")

def crawl_catalogue_pages(start_url: str, max_pages: int = 3):
    """
    Crawls max_pages catalogue pages, returning a list of dicts containing
    product_url and source_page. Appends one fake invalid URL to test resilience.
    """
    current_url = start_url
    pages_crawled = 0
    items = []

    while current_url and pages_crawled < max_pages:
        page_num = pages_crawled + 1
        cache_file = CACHE_DIR / f"catalogue-page-{page_num}.html"

        try:
            html_content = fetch_page_with_retry(current_url, cache_file)
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract book relative links and convert to absolute URLs
            book_links = soup.select("article.product_pod h3 a")
            for link in book_links:
                href = link.get("href")
                if href:
                    abs_url = urljoin(current_url, href)
                    items.append({
                        "product_url": abs_url,
                        "source_page": current_url
                    })

            pages_crawled += 1

            # Follow next page link if available and within max_pages limit
            next_el = soup.select_one("li.next a")
            if next_el and pages_crawled < max_pages:
                current_url = urljoin(current_url, next_el.get("href"))
            else:
                current_url = None
        except Exception as e:
            print(f"Catalogue page error on {current_url}: {e}")
            break

    # Deduplicate items by product_url while preserving insertion order
    seen = set()
    unique_items = []
    for item in items:
        if item["product_url"] not in seen:
            seen.add(item["product_url"])
            unique_items.append(item)

    # Append one fake invalid URL for local resilience testing
    fake_invalid_url = "https://books.toscrape.com/catalogue/invalid-book-404-test_9999/index.html"
    unique_items.append({
        "product_url": fake_invalid_url,
        "source_page": start_url
    })

    print(f"catalogue_pages = {pages_crawled}, discovered = {len(items)}, unique_urls = {len(unique_items)}")
    return unique_items

def url_to_cache_filename(url: str) -> str:
    """
    Generates a unique, Windows MAX_PATH safe filename for caching a detail page HTML.
    """
    parts = [p for p in url.split("/") if p and p != "index.html"]
    slug = parts[-1] if parts else "item"
    if len(slug) > 50:
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
        slug = f"{slug[:40]}_{url_hash}"
    return f"{slug}.html"

def extract_book_detail(item: dict) -> dict:
    """
    Fetches (or loads from cache) and extracts raw fields for a single book detail page.
    """
    product_url = item["product_url"]
    source_page = item["source_page"]
    filename = url_to_cache_filename(product_url)
    cache_path = CACHE_DETAIL_DIR / filename

    html_content = fetch_page_with_retry(product_url, cache_path)
    soup = BeautifulSoup(html_content, "html.parser")

    # Title
    title_el = soup.select_one(".product_main h1")
    title = title_el.text.strip() if title_el else ""

    # Price
    price_el = soup.select_one(".product_main .price_color")
    price_text = price_el.text.strip() if price_el else ""

    # Availability
    avail_el = soup.select_one(".product_main .availability")
    availability_text = avail_el.text.strip() if avail_el else ""

    # Rating
    rating_el = soup.select_one(".product_main .star-rating")
    rating_text = ""
    if rating_el:
        rating_classes = [c for c in rating_el.get("class", []) if c != "star-rating"]
        if rating_classes:
            rating_text = rating_classes[0]

    # Description (store None if missing)
    desc_header = soup.find("div", id="product_description")
    description = None
    if desc_header:
        desc_p = desc_header.find_next_sibling("p")
        if desc_p:
            description = desc_p.text.strip()

    fetched_at = datetime.now(timezone.utc).isoformat()
    price_gbp = parse_price(price_text)

    return {
        "title": title,
        "product_url": product_url,
        "price_gbp": price_gbp,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at
    }

def main():
    start_dt = datetime.now(timezone.utc)
    start_time = start_dt.isoformat()
    start_ticks = time.time()

    # Reset execution metrics
    metrics["pages_fetched"] = 0
    metrics["cache_hits"] = 0

    items = crawl_catalogue_pages(START_URL, max_pages=MAX_PAGES)
    valid_records = []
    invalid_records = []
    failed_pages = []

    for item in items:
        try:
            raw_record = extract_book_detail(item)
            try:
                validated = BookRecord(**raw_record)
                valid_records.append(validated.model_dump(mode="json"))
            except ValidationError as err:
                invalid_records.append({
                    "record": raw_record,
                    "error": err.errors()
                })
        except Exception as e:
            print(f"Failed to process book {item['product_url']}: {e}")
            failed_pages.append(item["product_url"])

    duration_seconds = round(time.time() - start_ticks, 2)

    # Save output files
    with open(BOOKS_JSON, "w", encoding="utf-8") as f:
        json.dump(valid_records, f, indent=2, ensure_ascii=False)

    with open(ERRORS_JSON, "w", encoding="utf-8") as f:
        json.dump(invalid_records, f, indent=2, ensure_ascii=False)

    report = {
        "start_time": start_time,
        "duration_seconds": duration_seconds,
        "pages_fetched": metrics["pages_fetched"],
        "cache_hits": metrics["cache_hits"],
        "valid_records": len(valid_records),
        "invalid_records": len(invalid_records),
        "failed_pages": failed_pages
    }

    with open(RUN_REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Validated records saved to {BOOKS_JSON.name}: {len(valid_records)}")
    print(f"Invalid records saved to {ERRORS_JSON.name}: {len(invalid_records)}")
    print(f"Failed pages count: {len(failed_pages)}")
    print(f"Run report saved to {RUN_REPORT_JSON.name}:")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
