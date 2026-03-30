# ⚡ Multi-Source Data Extraction Engine
 
<div align="center">
 
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)
 
**A production-ready, modular Python pipeline that extracts, cleans, validates, and structures data from heterogeneous sources into LLM-ready datasets.**
 
[Features](#-features) • [Architecture](#-architecture) • [Installation](#-installation) • [Usage](#-usage) • [API](#-api-reference) • [Contributing](#-contributing)
 
</div>
 
---
 
## 📌 Overview
 
The **Multi-Source Data Extraction Engine** is a plug-and-play data pipeline designed to ingest raw data from multiple source types — URLs, PDFs, CSVs, Excel files, and databases — and output clean, validated, schema-normalized records ready for LLM fine-tuning or downstream processing.
 
It ships with a **Streamlit dashboard** for interactive use and a **FastAPI backend** for programmatic/async access, making it suitable for both data teams and production deployments.
 
---
 
## ✨ Features
 
- 🌐 **Multi-Source Ingestion** — Web scraping, PDF extraction (with OCR fallback), CSV/Excel parsing, and SQL database support
- 🧹 **Automated Cleaning** — HTML stripping, NFKC unicode normalization, exact and fuzzy deduplication
- 🗂️ **Unified Schema** — Every record from every source is normalized to a single consistent structure
- 🤖 **LLM-Ready Output** — Exports in instruction-tuning format or plain text format
- 🔁 **Retry & Backoff** — Configurable retry logic with exponential backoff per source
- ⚡ **Parallel Processing** — Optional concurrent batch extraction
- 📊 **Streamlit Dashboard** — Interactive UI for job submission, live progress, and result download
- 🚀 **FastAPI REST API** — Async job submission, status polling, and file download endpoints
- 🔒 **Security Validated** — URL allowlisting, path traversal prevention, DB URI scheme validation
- 📋 **Job Registry** — Persistent job tracking that survives restarts
 
---
 
## 🏗️ Architecture
 
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
```
 
---
 
## 📁 Project Structure
 
```
├── extractors/
│   ├── base.py                 # Abstract BaseExtractor (plug-and-play interface)
│   ├── web_extractor.py        # BeautifulSoup + Playwright fallback
│   ├── pdf_extractor.py        # pdfplumber + pytesseract OCR fallback
│   ├── csv_extractor.py        # pandas (chunked) + regex column normalizer
│   └── db_extractor.py         # SQLAlchemy (auto table reflection)
├── utils/
│   ├── schema.py               # Strict unified schema + validate_record()
│   ├── logger.py               # colorlog + file handler (per-step labels)
│   ├── detector.py             # Source type detection + security checks
│   ├── cleaner.py              # NFKC unicode, HTML strip, exact + fuzzy dedup
│   ├── mapper.py               # SmartFieldMapper (content-scoped, rapidfuzz)
│   ├── saver.py                # JSON / CSV / LLM instruction + text outputs
│   └── job_store.py            # Persistent job tracking (output/jobs.json)
├── pipeline/
│   └── orchestrator.py         # Full pipeline, step timing, summary report
├── api/
│   └── main.py                 # FastAPI: POST /extract, GET /status, /download
├── data/input/
│   ├── sample.csv
│   ├── batch.json
│   ├── create_sample_db.py
│   └── create_sample_xlsx.py
├── output/                     # All generated files land here
├── app.py                      # Streamlit frontend entry point
├── config.json                 # Central configuration
├── requirements.txt
└── main.py                     # CLI entry point
```
 
---
 
## 📦 Installation
 
### Prerequisites
 
- Python 3.9+
- pip
 
### Steps
 
```bash
# 1. Clone the repository
git clone https://github.com/Afzalindikar/-AI-Internship-training-project.git
cd multi-source-extraction-engine
 
# 2. Create and activate virtual environment
python -m venv venv
 
# Windows
venv\Scripts\activate
 
# macOS / Linux
source venv/bin/activate
 
# 3. Install dependencies
pip install -r requirements.txt
 
# 4. (Optional) JavaScript-heavy page scraping
playwright install chromium
 
# 5. (Optional) Scanned PDF OCR support
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# macOS:   brew install tesseract
# Linux:   sudo apt install tesseract-ocr
 
# 6. Seed sample data
python data/input/create_sample_db.py
python data/input/create_sample_xlsx.py
```
 
---
 
## 🚀 Usage
 
### Streamlit Dashboard
 
```bash
streamlit run app.py
```
 
Open `http://localhost:8501` in your browser to access the interactive dashboard.
 
### CLI
 
```bash
# Single CSV file
python main.py --sources "data/input/sample.csv"
 
# Excel file with CSV output
python main.py --sources "data/input/sample.xlsx" --output-format csv
 
# Web scraping
python main.py --sources "https://books.toscrape.com"
 
# SQLite database
python main.py --sources "sqlite:///data/input/sample.db"
 
# Batch processing from JSON list
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
| `--parallel` | Enable parallel batch processing |
| `--config` | Path to custom config file |
| `--api` | Launch the FastAPI server |
 
---
 
## ⚙️ Configuration
 
Edit `config.json` to customize pipeline behavior:
 
| Key | Type | Default | Description |
|---|---|---|---|
| `enable_ocr` | bool | `true` | Enable OCR for scanned PDFs |
| `max_retries` | int | `3` | Retry attempts per source |
| `output_format` | string | `"json"` | `json` or `csv` |
| `llm_format` | string | `"instruction"` | `instruction` or `text` |
| `batch_size` | int | `10` | Max parallel workers |
| `parallel` | bool | `false` | Enable parallel batch processing |
| `dedup` | bool | `true` | Exact deduplication |
| `fuzzy_dedup` | bool | `false` | Near-duplicate removal via rapidfuzz |
| `logging_level` | string | `"INFO"` | `DEBUG`, `INFO`, or `ERROR` |
 
> You can also override any config key using a `.env` file. See `.env.example` for reference.
 
---
 
## 📤 Output Files
 
Each job produces the following files under `output/`:
 
| File | Description |
|---|---|
| `<id>_output.json` | All records in unified schema format |
| `<id>_output.csv` | Flat CSV (nested dicts serialized as JSON columns) |
| `<id>_llm.json` | LLM-ready dataset (instruction or text format) |
| `<id>_summary.json` | Execution summary with per-step timings |
| `jobs.json` | Persistent registry of all jobs |
| `failed_jobs.json` | Details of any failed sources |
| `pipeline.log` | Timestamped full execution log |
 
### Unified Record Schema
 
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
  "raw": "name: alice johnson | email: alice@example.com | salary: 95000",
  "failed": false,
  "error": null
}
```
 
### LLM Output Formats
 
**Instruction Format**
```json
{
  "instruction": "Extract and summarise the key information from the following text.",
  "input": "name: alice johnson | email: alice@example.com | salary: 95000",
  "output": "{\"source\": \"csv\", \"content\": {...}, \"metadata\": {...}}"
}
```
 
**Plain Text Format**
```json
{ "text": "name: alice johnson | email: alice@example.com | salary: 95000" }
```
 
---
 

 
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/extract` | Submit an extraction job |
| `GET` | `/status/{job_id}` | Poll job status and output paths |
| `GET` | `/download/{job_id}?format=json` | Download output (`json` / `csv` / `llm`) |
 
**Example — Submit a job:**
```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"sources": ["data/input/sample.csv"]}'
```
 
**Example — Poll status:**
```bash
curl http://localhost:8000/status/<job_id>
```
 
**Example — Download LLM output:**
```bash
curl "http://localhost:8000/download/<job_id>?format=llm" -o llm.json
```
 
---
 
## 🧠 SmartFieldMapper
 
Automatically maps varied field names to canonical keys using exact lookup and fuzzy matching via `rapidfuzz`:
 
| Input Variants | Canonical Key |
|---|---|
| `Full Name`, `Customer Name` | `name` |
| `Email Address`, `E-Mail` | `email` |
| `Telephone`, `Mobile` | `phone` |
| `Organisation`, `Employer` | `company` |
| `Designation`, `Role` | `job_title` |
| `Annual Income`, `Wage` | `salary` |
 
> Only `content` dict keys are remapped. Schema-level keys (`id`, `source`, `metadata`, `raw`, `failed`, `error`) are never modified.
 
---
 
## 🔒 Security
 
- HTTP/HTTPS URL scheme allowlist
- File path traversal prevention
- Database URI scheme allowlist (`sqlite`, `postgresql`, `mysql`, `mssql`)
- Input length limiting and sanitization
 
---
 
## 🔌 Extending the Pipeline
 
Adding a new source type takes only two steps:
 
**Step 1 — Create your extractor:**
```python
# extractors/my_extractor.py
from extractors.base import BaseExtractor
 
class MyExtractor(BaseExtractor):
    def supports(self, source_type: str) -> bool:
        return source_type == "json"
 
    def extract(self, source: str, config: dict) -> list[dict]:
        # Return list of records with 'content' as a dict
        ...
```
 
**Step 2 — Register it:**
```python
# pipeline/orchestrator.py
EXTRACTOR_REGISTRY["json"] = MyExtractor()
```
 
No other changes required.
 
---
 
## 🤝 Contributing
 
Contributions are welcome! To get started:
 
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request
 
Please make sure your code follows the existing structure and includes appropriate logging.

---
 
<div align="center">
 
Made with ❤️ | Open for contributions
 
</div>
 
