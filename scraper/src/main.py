import hashlib
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# Define base paths
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DETAIL_DIR = CACHE_DIR / "detail"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DETAIL_DIR.mkdir(parents=True, exist_ok=True)

START_URL = "https://books.toscrape.com/catalogue/page-1.html"
HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/shahrukhfu/task-crud-fastapi)"
}
TIMEOUT = 5
REQUEST_DELAY = 0.5
MAX_PAGES = 3

def get_page_html(url: str, cache_path: Path) -> str:
    """
    Returns HTML for a given URL. Loads from cache if present (no delay),
    otherwise waits for 0.5s request delay, fetches via HTTP, and caches to disk.
    """
    if cache_path.exists():
        html_content = cache_path.read_text(encoding="utf-8")
        file_size = os.path.getsize(cache_path)
        print(f"CACHE HIT: {cache_path.name} - {file_size} bytes")
        return html_content

    time.sleep(REQUEST_DELAY)
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    if response.status_code != 200:
        raise RuntimeError(f"HTTP fetch failed for {url} with status code {response.status_code}")

    html_content = response.text
    cache_path.write_text(html_content, encoding="utf-8")
    response_size = len(response.content)
    print(f"FETCH: {url} - {response_size} bytes")
    return html_content

def crawl_catalogue_pages(start_url: str, max_pages: int = 3):
    """
    Crawls max_pages catalogue pages, returning a list of dicts containing
    product_url and source_page.
    """
    current_url = start_url
    pages_crawled = 0
    items = []

    while current_url and pages_crawled < max_pages:
        page_num = pages_crawled + 1
        cache_file = CACHE_DIR / f"catalogue-page-{page_num}.html"

        html_content = get_page_html(current_url, cache_file)
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

    # Deduplicate items by product_url while preserving insertion order
    seen = set()
    unique_items = []
    for item in items:
        if item["product_url"] not in seen:
            seen.add(item["product_url"])
            unique_items.append(item)

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

    html_content = get_page_html(product_url, cache_path)
    soup = BeautifulSoup(html_content, "html.parser")

    # Title
    title_el = soup.select_one(".product_main h1")
    title = title_el.text.strip() if title_el else None

    # Price
    price_el = soup.select_one(".product_main .price_color")
    price_text = price_el.text.strip() if price_el else None

    # Availability
    avail_el = soup.select_one(".product_main .availability")
    availability_text = avail_el.text.strip() if avail_el else None

    # Rating
    rating_el = soup.select_one(".product_main .star-rating")
    rating_text = None
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

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at
    }

def main():
    items = crawl_catalogue_pages(START_URL, max_pages=MAX_PAGES)
    raw_records = []

    for item in items:
        record = extract_book_detail(item)
        raw_records.append(record)

    print(f"detail_pages = {len(raw_records)}")
    if raw_records:
        print("Sample raw record:")
        print(raw_records[0])

if __name__ == "__main__":
    main()
