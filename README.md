# Meta Job Scraper

A high-performance, asynchronous Python web scraper designed to extract comprehensive job listing data from [metacareers.com](https://www.metacareers.com/jobsearch).

## 🚀 Features

- **Parallel Execution**: Leverages `Playwright` and `asyncio` with configurable concurrency for rapid data extraction.
- **Smart Data Extraction**: Prioritizes embedded JSON metadata for precision, with robust DOM fallback mechanisms.
- **Rich Content Tracking**:
  - Captures split qualifications (Minimum vs. Preferred).
  - Formats salary ranges including bonus, equity, and benefits.
  - Extracts full compensation policy details.
  - Consolidates all supplementary links from About Meta, EEO, and Benefits sections.
- **Multiple Export Formats**: Automatically exports to `.xlsx`, `.ods`, and `.csv` with preserved formatting (bullet points).
- **Timestamped Outputs**: Every run generates a unique file to prevent data overwrites.

## 🛠️ Prerequisites

- Python 3.8 or higher
- [Playwright](https://playwright.dev/python/docs/intro)

## 📦 Setup

Follow these steps to set up the scraper from scratch:

1. **Clone the repository or navigate to the project folder:**
   ```bash
   cd meta-job-scrapper
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # OR
   .\venv\Scripts\activate   # On Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browser binaries:**
   ```bash
   playwright install chromium
   ```

## 🚀 Usage

Run the scraper with default settings (scrapes all pages, concurrency: 5):
```bash
python3 scraper.py
```

### Advanced Options

| Flag | Description | Example |
|------|-------------|---------|
| `--max_pages_to_scrap` | Limit the number of search result pages to process. | `python3 scraper.py --max_pages_to_scrap 10` |
| `--concurrency` | Number of parallel browser pages (default: 5). | `python3 scraper.py --concurrency 8` |

## 📊 Output

Results are saved in the project root with the format: `meta_jobs_HHMM_dd-MMM-YYYY`

### Supported Files
- **Excel (`.xlsx`)**: Best for viewing multi-line fields and bulleted lists.
- **OpenDocument (`.ods`)**: Open-source spreadsheet format compatible with LibreOffice/Excel.
- **CSV (`.csv`)**: Standard comma-separated values for data processing.

### Data Fields
- `job_name`: Official title of the role.
- `job_location`: Comma-separated list of all available locations.
- `job_department`: Combined list of internal/external departments.
- `job_description`: Full job description text.
- `job_responsibilities`: Bulleted list of daily tasks.
- `minimum_qualifications`: Specific requirements for the role.
- `preferred_qualifications`: Desired but not required attributes.
- `about_meta`: Meta's company culture and mission statement.
- `salary`: Annual pay range with bonus/equity indicators.
- `compensation_details`: Dynamic policy text regarding pay determination.
- `eeo`: Combined Equal Employment Opportunity and Accommodations disclosure.
- `additional_links`: A curated list of all relevant URLs found in the posting.
- `job_link`: Permanent URL to the specific job page.

## ⚠️ Notes
- The scraper includes a built-in semaphore to manage concurrency and avoid being flagged for excessive requests.
- Headless mode is enabled by default for performance.
