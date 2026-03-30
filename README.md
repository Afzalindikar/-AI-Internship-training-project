# Multi-Source Data Extraction Engine

A production-ready, modular Python pipeline that extracts, cleans, validates, and structures data from heterogeneous sources into **LLM-ready datasets**.

---

## Architecture Overview

```
INPUT (URL / PDF / CSV / Excel / Database)
         │
    [1] DETECT          ← Auto-detect source type + security validation
         │
    [2] EXTRACT         ← Plug-and-play extractors (retry + backoff)
         │
    [3] CLEAN           ← HTML strip, NFKC unicode, normalize, dedup
         │
    [4] NORMALIZE       ← Validate + auto-correct against unified schema
         │
    [5] MAP             ← SmartFieldMapper → canonical field names
         │
    [6] SAVE            ← JSON / CSV / LLM outputs + summary report
         │
OUTPUT: output/<job_id>_{output.json, output.csv, llm.json, summary.json}
        output/jobs.json        ← persistent job registry
        output/pipeline.log     ← full timestamped execution log
```

---

## Project Structure

```
afzal/
├── extractors/
│   ├── base.py              # Abstract BaseExtractor (plug-and-play)
│   ├── web_extractor.py     # BeautifulSoup + Playwright fallback
│   ├── pdf_extractor.py     # pdfplumber + pytesseract OCR fallback
│   ├── csv_extractor.py     # pandas (chunked) + regex column normalizer
│   └── db_extractor.py      # SQLAlchemy (auto table reflection)
├── utils/
│   ├── schema.py            # Strict unified schema + validate_record()
│   ├── logger.py            # colorlog + file handler (per-step labels)
│   ├── detector.py          # Source type detection + security checks
│   ├── cleaner.py           # NFKC unicode, HTML strip, exact + fuzzy dedup
│   ├── mapper.py            # SmartFieldMapper (content-scoped, rapidfuzz)
│   ├── saver.py             # JSON / CSV / LLM instruction + text outputs
│   └── job_store.py         # Persistent job tracking (output/jobs.json)
├── pipeline/
│   └── orchestrator.py      # Full pipeline, step timing, summary report
├── api/
│   └── main.py              # FastAPI: POST /extract, GET /status, /download
├── ui/
│   └── app.py               # Modern Dark-Themed Streamlit Dashboard UI
├── data/input/
│   ├── sample.csv           # Sample CSV (with 1 duplicate for dedup test)
│   ├── batch.json           # Batch input list
│   ├── create_sample_db.py  # Seeds SQLite DB (customers + products)
│   └── create_sample_xlsx.py# Seeds sample.xlsx
├── output/                  # All generated files land here
├── config.json              # Central configuration
├── .env.example             # Environment override reference
├── requirements.txt
├── main.py                  # CLI entry point
└── README.md
```

---

## Unified Data Schema

Every record from every source is normalized to this structure:

```json
{
  "id": "uuid4-string",
  "source": "csv | excel | database | web | pdf",
  "content": {
    "name": "alice johnson",
    "email": "alice@example.com",
    "salary": 95000
  },
  "metadata": {
    "title": null,
    "author": null,
    "date": null,
    "url": null,
    "file_name": "sample.csv",
    "extracted_at": "2026-03-28T02:30:00Z",
    "source_type": "csv"
  },
  "raw": "name: alice johnson | email: alice@example.com | ...",
  "failed": false,
  "error": null
}
```

> **`content` is a structured dict** (key-value pairs), not a flat string.  
> `raw` stores the flat text representation for LLM input.

---

## LLM Dataset Formats

### Instruction Format (`--llm-format instruction`)
```json
{
  "instruction": "Extract and summarise the key information from the following text.",
  "input": "name: alice johnson | email: alice@example.com | salary: 95000",
  "output": "{\"source\": \"csv\", \"content\": {...}, \"metadata\": {...}}"
}
```

### Plain Text Format (`--llm-format text`)
```json
{ "text": "name: alice johnson | email: alice@example.com | salary: 95000" }
```

---

## Installation

```bash
cd "C:\Users\priya\OneDrive\Desktop\afzal"

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

# Optional: JavaScript-heavy pages
playwright install chromium

# Optional: Scanned PDF OCR
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# macOS:   brew install tesseract
# Linux:   sudo apt install tesseract-ocr

# Seed sample data
python data/input/create_sample_db.py
python data/input/create_sample_xlsx.py
```

---

## Configuration (`config.json`)

| Key | Type | Default | Description |
|---|---|---|---|
| `enable_ocr` | bool | `true` | Enable OCR for scanned PDFs |
| `max_retries` | int | `3` | Retry attempts per source (exponential backoff) |
| `output_format` | string | `"json"` | `json` or `csv` |
| `llm_format` | string | `"instruction"` | `instruction` or `text` |
| `batch_size` | int | `10` | Max parallel workers |
| `parallel` | bool | `false` | Parallel batch processing |
| `dedup` | bool | `true` | Exact deduplication |
| `fuzzy_dedup` | bool | `false` | Near-duplicate removal (rapidfuzz) |
| `logging_level` | string | `"INFO"` | `DEBUG`, `INFO`, `ERROR` |

Override any key with `.env` file (see `.env.example`).

---

## CLI Usage

```bash
# Single CSV file
python main.py --sources "data/input/sample.csv"

# Excel file with CSV output
python main.py --sources "data/input/sample.xlsx" --output-format csv

# Web scraping
python main.py --sources "https://books.toscrape.com"

# SQLite database
python main.py --sources "sqlite:///data/input/sample.db"

# Batch (multiple sources from JSON list)
python main.py --batch data/input/batch.json --verbose

# Parallel batch + LLM plain text format
python main.py --batch data/input/batch.json --llm-format text --parallel

# Launch REST API server
python main.py --api
```

### CLI Arguments

| Argument | Description |
|---|---|
| `--sources` | One or more file paths, URLs, or DB URIs |
| `--batch` | JSON file with list of sources |
| `--output-format` | `json` (default) or `csv` |
| `--llm-format` | `instruction` (default) or `text` |
| `--verbose` | Enable DEBUG-level logging |
| `--parallel` | Parallel batch processing |
| `--config` | Custom config.json path |
| `--api` | Launch FastAPI server |

---

## FastAPI Usage

```bash
python main.py --api
# Server: http://localhost:8000
# Docs:   http://localhost:8000/docs
```

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/extract` | Submit an extraction job (async) |
| `GET` | `/status/{job_id}` | Poll job status + output paths |
| `GET` | `/download/{job_id}?format=json` | Download output (`json`/`csv`/`llm`) |

```bash
# Submit
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"sources": ["data/input/sample.csv"]}'
# → {"job_id": "abc123...", "status": "PENDING"}

# Poll
curl http://localhost:8000/status/abc123...

# Download
curl "http://localhost:8000/download/abc123...?format=llm" -o llm.json
```

---

## Streamlit Dashboard UI

A beautifully designed, fully responsive dark-theme Streamlit application is available for an interactive zero-code pipeline management experience. 

**Features:**
- **Modern UI Design:** Deep dark aesthetic (`#080b12`), sophisticated cyan & violet gradients, interactive hover-lift buttons, and responsive metric grids.
- **Visual Progress Stepper:** Live animated HTML stepper tracking extraction stages (Detect → Extract → Clean → Normalize → Map → Save) with pulsing and completion states.
- **Execution History:** Robust historical job table with pill-status badges, monospace identifiers, and interactive one-click export buttons natively rendered via custom HTML.
- **Dynamic Configuration:** Tweak outputs (`json` or `csv`), LLM syntax formats, chunking parallelisation, and deduplication modes directly inside the interactive sidebar.

### Running the Dashboard

Ensure all requirements (including `streamlit`) are installed, then launch the app:

```bash
streamlit run ui/app.py
# Dashboard will be available at: http://localhost:8501
```

---

## Output Files (per job)

| File | Description |
|---|---|
| `<id>_output.json` | All records in unified schema format |
| `<id>_output.csv` | Flat CSV (nested dicts serialized as JSON columns) |
| `<id>_llm.json` | LLM-ready dataset (instruction or text format) |
| `<id>_summary.json` | Execution summary with step timings |
| `jobs.json` | Persistent registry of all jobs (survives restarts) |
| `failed_jobs.json` | Details of any failed sources |
| `pipeline.log` | Timestamped per-step execution log |

### Summary Report (`<id>_summary.json`)

```json
{
  "job_id": "abc123...",
  "total_sources": 1,
  "successful_sources": 1,
  "failed_sources": 0,
  "total_records": 10,
  "execution_time_seconds": 0.18,
  "step_timings_seconds": {
    "detect": 0.001, "extract": 0.05,
    "clean": 0.01,   "normalize": 0.01,
    "map": 0.01,     "save": 0.02
  }
}
```

---

## SmartFieldMapper

Automatically maps varied field names to canonical keys using exact lookup + fuzzy matching (rapidfuzz):

| Input Field | Canonical Key |
|---|---|
| `Full Name`, `Customer Name` | `name` |
| `Email Address`, `E-Mail` | `email` |
| `Telephone`, `Mobile` | `phone` |
| `Organisation`, `Employer` | `company` |
| `Designation`, `Role` | `job_title` |
| `Annual Income`, `Wage` | `salary` |

**Scope**: Only `content` dict keys are remapped. Schema keys (`id`, `source`, `metadata`, `raw`, `failed`, `error`) are never touched.

---

## Security Features

- URL scheme allowlist (`http`, `https` only)
- File path traversal prevention
- DB URI scheme allowlist (`sqlite`, `postgresql`, `mysql`, `mssql`)
- Input length limiting and sanitization

---

## Extensibility: Adding a New Extractor

1. Create `extractors/my_extractor.py`:
```python
from extractors.base import BaseExtractor

class MyExtractor(BaseExtractor):
    def supports(self, source_type: str) -> bool:
        return source_type == "json"

    def extract(self, source: str, config: dict) -> list[dict]:
        # Return list of records with 'content' as dict
        ...
```

2. Register in `pipeline/orchestrator.py`:
```python
EXTRACTOR_REGISTRY["json"] = MyExtractor()
```

That's all — no other changes needed.

---

## License

MIT License — open for use, modification, and distribution.
