# Polite Book Scraper & Pipeline (Assignment A9)

A resilient, polite Python web scraper built with `requests`, `BeautifulSoup`, and `Pydantic` to discover, fetch, extract, normalize, and validate product details from [Books to Scrape](https://books.toscrape.com/).

---

## Target Classification & Compliance

- **Target Site:** [https://books.toscrape.com/](https://books.toscrape.com/) (Books to Scrape sandbox)
- **Target Scope:** First 3 catalogue pages (60 books total) plus detail pages
- **robots.txt Check Result:** Checked [https://books.toscrape.com/robots.txt](https://books.toscrape.com/robots.txt) (Note: No `robots.txt` file found - returns HTTP 404)
- **Data Fields Collected:** Book title, product URL, numeric price (`price_gbp`), raw price text (`price_text`), availability text, star rating text, book description, source catalogue page URL, and ISO fetch timestamp
- **Ethics Statement:** *"I will not reuse this code on another site without checking its rules and terms first."*

---

## Politeness Rules & Architecture

The scraper follows strict web scraping politeness and efficiency guidelines:

1. **Custom User-Agent:**  
   Identifies requests transparently using:  
   `FlyRankInternship-A9/1.0 (+https://github.com/shahrukhfu/task-crud-fastapi)`
2. **Rate Limiting / Request Delay:**  
   Enforces a mandatory `0.5s` delay (`time.sleep(0.5)`) between real network HTTP GET requests.
3. **Timeout Protection:**  
   Implements a strict `5-second` timeout (`timeout=5`) per HTTP request.
4. **Local Disk Caching:**  
   Persists all retrieved HTML locally in `cache/` (for catalogue pages) and `cache/detail/` (for detail pages). Subsequent runs skip network fetches and delays for cached pages.
5. **Fault Tolerance & Retries:**  
   Includes a 1-retry mechanism for timeouts and `5xx` server errors, while immediately skipping retries for `404`/`403` errors.

---

## Technical Stack & Schema

- **Fetching & Parsing:** `requests`, `beautifulsoup4`
- **Data Normalization & Validation:** `pydantic` v2

### Pydantic Data Model (`BookRecord`)

```python
from typing import Optional
from pydantic import BaseModel, HttpUrl

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
```

---

## Installation & Run Instructions

### 1. Install Dependencies

Ensure Python 3.10+ is installed, then install required packages:

```bash
pip install requests beautifulsoup4 pydantic
```

### 2. Run the Scraper

Run the main scraper script from the repository root:

```bash
python scraper/src/main.py
```

Outputs will be saved in:
- `output/books.json` — Deduplicated, validated book records (60 total)
- `output/errors.json` — Validation error records (if any)
- `output/run-report.json` — Execution metrics and failure summary

---

## Sample Run Report (`output/run-report.json`)

```json
{
  "start_time": "2026-08-10T12:06:05.041992+00:00",
  "duration_seconds": 2.61,
  "pages_fetched": 1,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": [
    "https://books.toscrape.com/catalogue/invalid-book-404-test_9999/index.html"
  ]
}
```

---

## Why No Browser Automation Was Needed

Browser automation frameworks (such as Playwright or Selenium) were **not required** for this target site. The target website ([Books to Scrape](https://books.toscrape.com/)) serves complete, pre-rendered HTML directly from the server. There are no client-side JavaScript frameworks (e.g. React/Vue), dynamic API calls, or hydration steps required to view book content. Consequently, fetching static HTML via standard HTTP GET requests using `requests` and parsing the DOM with `BeautifulSoup` is vastly faster, lightweight, and more resource-efficient than launching a headless browser instance.
