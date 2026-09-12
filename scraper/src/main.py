import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
CACHE_FILE = CACHE_DIR / "catalogue-page-1.html"

CATALOGUE_PAGE_1 = "https://books.toscrape.com/catalogue/page-1.html"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/Karksus/flyrank)"
TIMEOUT_SECONDS = 10


def fetch_catalogue_page() -> None:
    if CACHE_FILE.exists():
        print("CACHE")
        return

    print("FETCH")
    response = requests.get(
        CATALOGUE_PAGE_1,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
    )

    if response.status_code != 200:
        sys.exit(f"failed fetch: HTTP {response.status_code}")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(response.text, encoding="utf-8")


if __name__ == "__main__":
    fetch_catalogue_page()