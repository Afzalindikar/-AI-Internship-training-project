# Quick Reference Guide

## What This Project Does

**Multi-Source Data Extraction Engine** — Transforms messy data from URLs, PDFs, CSV files, Excel sheets, and databases into **clean, normalized, LLM-ready datasets**.

## Entry Points

| Interface  | Location                   | Command                                          |
| ---------- | -------------------------- | ------------------------------------------------ |
| **CLI**    | `main.py`                  | `python main.py --sources "file.csv"`            |
| **API**    | `api/main.py`              | `python main.py --api` (starts FastAPI on :8000) |
| **Python** | `pipeline/orchestrator.py` | `from pipeline.orchestrator import DataPipeline` |

---

## The 6-Step Pipeline

```
Source Input
    ↓
[1] DETECT      ← What is this? (URL? PDF? CSV?)
    ↓
[2] EXTRACT     ← Get the data out
    ↓
[3] CLEAN       ← Remove junk, fix encoding
    ↓
[4] NORMALIZE   ← Fit to standard schema
    ↓
[5] MAP         ← Smart field name matching
    ↓
[6] SAVE        ← Write JSON/CSV/LLM format
    ↓
Output Files
```

---

## What Each Module Does

### **Extractors** (`extractors/`)

- **web_extractor.py** → Scrapes URLs (BeautifulSoup + Playwright)
- **pdf_extractor.py** → Reads PDFs (pdfplumber + OCR)
- **csv_extractor.py** → Parses CSV/Excel (pandas)
- **db_extractor.py** → Queries databases (SQLAlchemy)

### **Utils** (`utils/`)

- **logger.py** → Structured logging (colorful console + file log)
- **detector.py** → Identifies source type + validates input
- **cleaner.py** → Strips HTML, fixes unicode, deduplicates
- **mapper.py** → Maps messy field names to standard ones
- **schema.py** → Enforces data structure (dataclass validation)
- **saver.py** → Writes JSON/CSV/LLM/text outputs
- **job_store.py** → Keeps record of all jobs (persistent)

### **Pipeline** (`pipeline/`)

- **orchestrator.py** → Runs the 6 steps end-to-end

### **API** (`api/`)

- **main.py** → FastAPI endpoints: POST /extract, GET /status, GET /download

---

## Configuration

Edit `config.json`:

- `enable_ocr`: true/false — Enable PDF OCR
- `max_retries`: 3 — How many times to retry on error
- `parallel`: false → true — Process multiple sources at once
- `dedup`: true/false — Remove duplicate records
- `fuzzy_dedup`: true/false — Remove similar records
- `output_format`: "json" or "csv"
- `llm_format`: "instruction" or "text"

---

## Unified Data Schema (Every Record)

```json
{
  "id": "uuid4-string",                    ← Unique ID
  "source": "csv | pdf | web | database",  ← Where it came from
  "content": {                             ← Structured data
    "field1": "value1",
    "field2": "value2"
  },
  "metadata": {                            ← Info about the record
    "title": null,
    "author": null,
    "file_name": "sample.csv",
    "extracted_at": "2026-03-28T...",
    "source_type": "csv"
  },
  "raw": "flat text representation",       ← For LLM training
  "failed": false,                         ← Did extraction fail?
  "error": null                            ← Error message if failed
}
```

---

## Output Files (in `output/`)

For each job, you get:

| File                    | Contains                                |
| ----------------------- | --------------------------------------- |
| `<job_id>_output.json`  | Full records (with all metadata)        |
| `<job_id>_output.csv`   | Flattened table format                  |
| `<job_id>_llm.json`     | LLM-ready instruction pairs             |
| `<job_id>_summary.json` | Execution stats (count, timing, errors) |
| `jobs.json`             | Registry of all jobs ever run           |
| `pipeline.log`          | Timestamped execution log               |

---

## CLI Examples

### Single Source

```bash
python main.py --sources "data/input/sample.csv"
```

### Multiple Sources

```bash
python main.py --sources "https://example.com" "file.pdf" "data.xlsx"
```

### Batch File

```bash
python main.py --batch data/input/batch.json
```

### Change Output Format

```bash
python main.py --sources "file.csv" --output-format csv --llm-format text
```

### Enable Debug Logging

```bash
python main.py --sources "file.csv" --verbose
```

### Launch API Server

```bash
python main.py --api
# Then: curl -X POST http://localhost:8000/extract ...
```

---

## API Endpoints

### Extract Job

```bash
POST /extract
Content-Type: application/json

{
  "sources": ["data/input/sample.csv", "https://example.com"],
  "output_format": "json",
  "llm_format": "instruction"
}

Response:
{
  "job_id": "abc-123-def",
  "status": "RUNNING"
}
```

### Check Status

```bash
GET /status/{job_id}

Response:
{
  "job_id": "abc-123-def",
  "status": "SUCCESS",
  "total_records": 150,
  "output_files": {...}
}
```

### Download Output

```bash
GET /download/{job_id}?format=json

Returns: <job_id>_output.json file
```

---

## Key Features

✅ **Auto-detect source type** (URL? PDF? CSV?)  
✅ **Retry with backoff** (handles transient failures)  
✅ **Exact + Fuzzy deduplication**  
✅ **Intelligent field mapping** (messy names → canonical)  
✅ **Multiple output formats** (JSON, CSV, LLM, text)  
✅ **Persistent job tracking** (survives restarts)  
✅ **Security validation** (prevent path traversal, SQL injection)  
✅ **Structured logging** (colorful + file log)  
✅ **Configurable timeouts** (don't hang forever)  
✅ **Unicode safety** (Windows UTF-8 handling)

---

## Dependencies

Install via:

```bash
pip install -r requirements.txt
```

Key packages:

- `beautifulsoup4`, `playwright` — Web scraping
- `pdfplumber`, `pytesseract` — PDF reading
- `pandas`, `openpyxl` — CSV/Excel
- `sqlalchemy` — Database access
- `fastapi`, `uvicorn` — API server
- `rapidfuzz` — Fuzzy field matching
- `colorlog` — Colored console output

---

## Project Status

✅ **COMPLETE** — All planned features implemented:

- [x] All 5 extractors
- [x] All 7 utils modules
- [x] Pipeline orchestrator (6-step flow)
- [x] FastAPI backend
- [x] CLI interface
- [x] Configuration system
- [x] Logging system
- [x] Error handling + retry logic
- [x] Documentation

📊 **Sample Data**: 12 successful extraction jobs stored in `output/`

---

## Next Steps (Ideas)

1. Deploy API to cloud (Azure App Service / AWS Lambda)
2. Add more extractors (APIs, S3, Kafka, etc.)
3. Set up database backend for job store (vs. JSON file)
4. Add monitoring/metrics (Prometheus)
5. Implement distributed processing (Celery)
6. Add user authentication + API keys

---

## File Locations Quick Map

```
main.py                    ← Start here (CLI entry)
config.json               ← Change settings
README.md                 ← Full documentation
ANALYSIS.md               ← Deep dive (this analysis)

api/main.py              ← FastAPI server code
pipeline/orchestrator.py ← Pipeline logic
extractors/              ← Source-specific logic
utils/                   ← Data transformation utilities

data/input/              ← Sample data + seeding scripts
output/                  ← All generated files land here
```
