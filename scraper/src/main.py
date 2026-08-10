import os
from pathlib import Path
import requests

# Define base paths
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PAGE_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_FILE = CACHE_DIR / "catalogue-page-1.html"

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/shahrukhfu/task-crud-fastapi)"
}
TIMEOUT = 5

def get_page_html(url: str, cache_path: Path) -> str:
    """
    Returns HTML for a given URL. Loads from cache if present,
    otherwise fetches via HTTP request and caches to disk.
    """
    if cache_path.exists():
        html_content = cache_path.read_text(encoding="utf-8")
        file_size = os.path.getsize(cache_path)
        print(f"CACHE HIT: {cache_path.name} - {file_size} bytes")
        return html_content

    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    if response.status_code != 200:
        raise RuntimeError(f"HTTP fetch failed for {url} with status code {response.status_code}")

    html_content = response.text
    cache_path.write_text(html_content, encoding="utf-8")
    response_size = len(response.content)
    print(f"FETCH: {url} - {response_size} bytes")
    return html_content

def main():
    html = get_page_html(PAGE_URL, CACHE_FILE)
    print(f"Page 1 HTML ready (length: {len(html)} characters)")

if __name__ == "__main__":
    main()
