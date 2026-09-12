# flyrank scraper

## Target classification

- **Site:** https://books.toscrape.com/ (Books to Scrape, a website built specifically to practise scraping)
- **Why:** The site is explicitly designed as a sandbox for scraping exercises; it exists for this purpose and carries no paywall or login wall. There is no published scraping policy beyond what robots.txt says.
- **How much:** The first 3 catalogue pages only (`/catalogue/page-1.html`, `/page-2.html`, `/page-3.html`).
- **What data:** Book titles, prices, star ratings, availability, and catalogue URLs from those three pages.
- **Appropriateness:** Scraping a deliberately built "test shop" within a hard three-page limit keeps the load trivial and the practice legitimate.

## robots.txt result

`GET https://books.toscrape.com/robots.txt` returned **HTTP 404** — no robots file found.

I will not reuse this code on another site without checking its rules and terms first.