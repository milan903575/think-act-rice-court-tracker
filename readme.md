# Delhi High Court Case Tracker

A Streamlit-based web app that automates Delhi High Court case search and retrieves related orders/documents using Selenium, with robust parsing, error handling, and persistent logging to SQLite.

## Court Chosen

- Court: Delhi High Court
- Base Portal: delhihighcourt.nic.in
- Search Endpoint used by scraper: /app/get-case-type-status
- Why this court:
    - Stable public portal
    - Consistent HTML structures
    - Orders/status pages suitable for automated extraction


## Features

- Search by Case Type, Case Number, and Filing Year
- Automated form filling with resilient locators and fallbacks
- CAPTCHA detection and assistive handling (see CAPTCHA Strategy)
- Orders/documents extraction from the orders/status pages
- SQLite-backed search history, error logging, and basic stats
- Streamlit UI with sidebar history and CSV export (as supported by the provided code)


## Project Structure

- app.py — Streamlit app (UI, layout, sidebar, entry points)
- court_scraper.py — Scraper module with:
    - DatabaseManager — SQLite schema, inserts, history, stats
    - WebDriverManager — Chrome setup (headless toggle, stealth options)
    - FormHandler — Page readiness, field filling, CAPTCHA handling, submission
    - DataExtractor — Results table parsing, orders page crawling
    - CourtScraper — Orchestrates the whole flow and cleanup
- requirements.txt — Python dependencies
- court_data.db — SQLite database file (auto-created on first run)
- .env — Optional environment variables (see Sample Env Vars)


## Setup Steps

1) **Prerequisites**

- Python 3.10+
- Git installed on your system
- Google Chrome installed (webdriver-manager will fetch a matching driver)
- Internet access to delhihighcourt.nic.in

2) **Clone the repository**
```bash
git clone https://github.com/milan903575/think-act-rice-court-tracker.git
cd think-act-rice-court-tracker
```

3) **Create and activate a virtual environment**

- macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

- Windows:

```bash
py -m venv .venv
.venv\Scripts\activate
```

4) **Install dependencies**
```bash
pip install -r requirements.txt
```

5) **(Optional) Configure environment variables**

- Create a .env file at the project root (see Sample Env Vars below), or export them in your shell.

6) **Run the app (initializes DB on first launch)**
```bash
streamlit run app.py
```

7) **Verify database**

- court_data.db is created automatically with tables such as search_history and application_logs.


## Usage

- Open the Streamlit app in your browser (it prints a local URL on startup).
- Enter:
    - Case Type (e.g., "W.P.(C)", "FAO", "CRL.M.C.")
    - Case Number (numeric)
    - Filing Year (YYYY)
- Submit the form.
- If a portal verification appears, follow the CAPTCHA Strategy guidelines.
- Review parsed case details and any available orders. Use the sidebar for history/stats and export if supported.


## CAPTCHA Strategy

This project follows a compliant, "assistive automation" approach:

- Detection:
    - The scraper checks for common CAPTCHA indicators (IDs like captcha-code or captchaInput, text containing "CAPTCHA", and XPath fallbacks).
- Entry:
    - If a visible alphanumeric code is rendered in the DOM (plain text), the app attempts to read and fill it automatically.
    - If the CAPTCHA is image-based/obfuscated or cannot be read, the app will not bypass it. The UI should prompt the user to complete verification manually and retry the search.
- Compliance stance:
    - No breaking or solving of image CAPTCHAs.
    - Supports manual completion by running the browser in non-headless mode when needed.
- Tips:
    - Toggle headless off for local manual verification.
    - If rate-limited or repeatedly challenged, slow down and retry after a brief wait.


## Sample Env Vars

Create a .env file (optional):

- SCRAPER_HEADLESS=true
- SCRAPER_PAGELOAD_TIMEOUT=30
- SCRAPER_WAIT_TIMEOUT=20
- BASE_URL=https://delhihighcourt.nic.in/
- SEARCH_URL=https://delhihighcourt.nic.in/app/get-case-type-status
- DB_NAME=court_data.db
- LOG_LEVEL=INFO

If not supplied, the code defaults in court_scraper.py are used.

## How It Works (Technical Overview)

- WebDriverManager
    - Configures Chrome (headless toggle, sandbox/GPU off, reduced automation fingerprints) and fetches a matching ChromeDriver via webdriver-manager.
- FormHandler
    - Waits for DOM readiness; fills case_type, case_no, and filing_year via multiple selectors; attempts CAPTCHA handling; submits and waits for results.
- DataExtractor
    - Parses results table via id/class fallbacks to extract metadata such as status, parties, dates, and court number; follows orders link to collect order date/title/PDF link.
- DatabaseManager
    - Persists search outcomes (success/failure), timestamps, raw payloads, and error messages for auditability and analytics.


## Common Issues

- No results:
    - Match the portal's exact Case Type label; verify number and year.
- CAPTCHA failure:
    - Retry after waiting; consider non-headless mode to solve manually.
- Driver/version errors:
    - Update Chrome; reinstall dependencies; clear webdriver cache.
- HTML changes:
    - Update selectors in FormHandler and DataExtractor.


## Security and Compliance

- Does not bypass or break CAPTCHAs.
- Respect the portal's terms and rate limits.
- Stores only publicly available case metadata.


## Commands

- Run app: `streamlit run app.py`
- Reset DB (optional):
    - macOS/Linux: `rm court_data.db`
    - Windows: `del court_data.db`


## Acknowledgments

- Streamlit, Selenium, webdriver-manager, and SQLite.


