import os
import time
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# Define base paths
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

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
    Crawls max_pages catalogue pages, extracting absolute book URLs and following pagination links.
    """
    current_url = start_url
    pages_crawled = 0
    discovered_urls = []

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
                discovered_urls.append(abs_url)

        pages_crawled += 1

        # Follow next page link if available and within max_pages limit
        next_el = soup.select_one("li.next a")
        if next_el and pages_crawled < max_pages:
            current_url = urljoin(current_url, next_el.get("href"))
        else:
            current_url = None

    unique_urls = list(dict.fromkeys(discovered_urls))
    print(f"catalogue_pages = {pages_crawled}, discovered = {len(discovered_urls)}, unique_urls = {len(unique_urls)}")
    return unique_urls

def main():
    crawl_catalogue_pages(START_URL, max_pages=MAX_PAGES)

if __name__ == "__main__":
    main()
