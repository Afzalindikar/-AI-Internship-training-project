# Multi-Source Data Extraction Engine — Comprehensive Analysis

**Project**: Multi-Source Data Extraction Engine  
**Status**: Active Development  
**Language**: Python 3.10+  
**Architecture**: Modular, Plug-and-Play Pipeline  
**Date Analyzed**: 2026-03-28

---

## 1. Project Purpose

A **production-ready, modular Python pipeline** that extracts, cleans, validates, and structures data from heterogeneous sources into **LLM-ready datasets**.

### Core Goals:

- ✅ Extract from **multiple sources** (URLs, PDFs, CSV/Excel, SQL databases)
- ✅ **Normalize** all data to a unified schema
- ✅ **Clean & deduplicate** intelligently (exact + fuzzy matching)
- ✅ **Map** fields to canonical names using AI-fuzzy matching
- ✅ **Output** in multiple formats (JSON, CSV, LLM instruction, plain text)
- ✅ **Persistent job tracking** with summary reports
- ✅ **FastAPI backend** + CLI interface
- ✅ **Enterprise features**: retry logic, error handling, logging, security validation

---

## 2. Architecture & Data Flow

### Pipeline Flow (Strict Sequential)

```
INPUT SOURCE (URL / PDF / CSV / Excel / Database)
    ↓
[1] DETECT
    • Auto-detect source type (url | web | pdf | csv | excel | database)
    • Security validation (URL scheme check, path traversal prevention)
    • Input sanitization
    ↓
[2] EXTRACT (Plug-and-Play Extractors)
    • WebExtractor: BeautifulSoup + Playwright fallback
    • PDFExtractor: pdfplumber + pytesseract OCR
    • CSVExtractor: pandas (chunked for large files)
    • DBExtractor: SQLAlchemy with auto table reflection
    • Includes: Retry with exponential backoff, timeout handling
    ↓
[3] CLEAN
    • Strip HTML tags & special characters
    • Unicode normalization (NFKC)
    • Trim whitespace, lowercase, null removal
    • Exact deduplication
    • Fuzzy deduplication (rapidfuzz, configurable)
    ↓
[4] NORMALIZE
    • Validate against unified schema
    • Auto-correct missing/invalid fields
    • Generate UUID4 IDs
    • Timestamp all records
    ↓
[5] MAP
    • SmartFieldMapper using rapidfuzz
    • Content-scoped alias matching
    • Map arbitrary field names → canonical names
    ↓
[6] SAVE
    • JSON output (full record structure)
    • CSV output (flattened with metadata columns)
    • LLM instruction format (specially formatted for LLM training)
    • Plain text format (raw concatenated text)
    ↓
OUTPUT
    • output/<job_id>_output.json (full structured records)
    • output/<job_id>_output.csv (flattened CSV)
    • output/<job_id>_llm.json (LLM-ready format)
    • output/<job_id>_summary.json (execution report)
    • output/jobs.json (persistent job registry)
    • output/pipeline.log (timestamped execution log)
```

### Unified Data Schema

Every record (regardless of source) normalizes to:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "csv | excel | database | web | pdf | unknown",
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

**Key Design Decisions**:

- `content` is **structured dict** (key-value), not flat string → enables field mapping & normalization
- `raw` stores flat text representation → enables LLM training
- Schema validation is **strict** → all records must conform
- UUID4 auto-generation → ensures uniqueness

---

## 3. Project Structure & Components

### Directory Layout

```
afzal/
├── main.py                           # CLI entry point
├── config.json                       # Central configuration
├── .env.example                      # Environment override reference
├── requirements.txt                  # Python dependencies
├── README.md                         # User documentation
├── task.md                           # Task checklist
├── implementation_plan.md            # Requirements + enhancements
├── walkthrough.md                    # [Additional docs]
│
├── extractors/                       # Plug-and-play extractor modules
│   ├── __init__.py
│   ├── base.py                       # Abstract BaseExtractor (ABC)
│   ├── web_extractor.py              # BeautifulSoup + Playwright
│   ├── pdf_extractor.py              # pdfplumber + pytesseract
│   ├── csv_extractor.py              # pandas (chunked, column normalization)
│   ├── db_extractor.py               # SQLAlchemy (auto table reflection)
│   └── __pycache__/
│
├── utils/                            # Core utilities
│   ├── __init__.py
│   ├── logger.py                     # Structured logging (colorlog + file)
│   ├── detector.py                   # Source type detection + security validation
│   ├── cleaner.py                    # HTML strip, Unicode norm, dedup, fuzzy dedup
│   ├── mapper.py                     # SmartFieldMapper (rapidfuzz)
│   ├── saver.py                      # JSON/CSV/LLM/text output formats
│   ├── schema.py                     # Unified schema + validate_record()
│   ├── job_store.py                  # Persistent job tracking (jobs.json)
│   └── __pycache__/
│
├── pipeline/                         # Orchestration
│   ├── __init__.py
│   ├── orchestrator.py               # Main pipeline: Detect→Extract→Clean→Norm→Map→Save
│   └── __pycache__/
│
├── api/                              # FastAPI backend
│   ├── __init__.py
│   └── main.py                       # POST /extract, GET /status, GET /download
│
├── data/                             # Sample data & seeding scripts
│   └── input/
│       ├── sample.csv                # Sample customer records (1 duplicate for testing)
│       ├── batch.json                # Batch input example
│       ├── create_sample_db.py       # Seeds SQLite DB (customers + products)
│       └── create_sample_xlsx.py     # Creates sample.xlsx from CSV
│
└── output/                           # All generated files (job outputs, logs, registry)
    ├── job_id_1_output.json          # Full structured records
    ├── job_id_1_output.csv           # Flattened CSV
    ├── job_id_1_llm.json             # LLM-ready format
    ├── job_id_1_summary.json         # Execution report
    ├── jobs.json                     # Persistent job registry
    └── pipeline.log                  # Timestamped execution log
```

---

## 4. Core Components Detailed

### 4.1 Extractors (Plug-and-Play)

| Extractor        | Source Type | Implementation                      | Key Features                                                                          |
| ---------------- | ----------- | ----------------------------------- | ------------------------------------------------------------------------------------- |
| **WebExtractor** | URL/Web     | BeautifulSoup + Playwright fallback | Timeout handling, JS rendering fallback, metadata extraction                          |
| **PDFExtractor** | PDF         | pdfplumber + pytesseract OCR        | Stream per page, OCR fallback for scanned PDFs, DPI configurable                      |
| **CSVExtractor** | CSV/Excel   | pandas                              | Chunked reading for large files, column normalization, header detection               |
| **DBExtractor**  | Database    | SQLAlchemy                          | Auto table reflection, configurable table selection, supports all SQLAlchemy dialects |

**All extractors**:

- Inherit from `BaseExtractor` (abstract interface)
- Implement `extract()` and `supports()` methods
- Return list of raw records with metadata
- Registered in `EXTRACTOR_REGISTRY` for auto-dispatch

### 4.2 Utils Layer

| Module           | Purpose            | Key Functions                                                                |
| ---------------- | ------------------ | ---------------------------------------------------------------------------- |
| **logger.py**    | Structured logging | `get_logger()`, `step_log()` — colorlog + file handlers, per-step labels     |
| **detector.py**  | Source detection   | `detect_source_type()`, `validate_source()` — auto-detect + security checks  |
| **cleaner.py**   | Data cleaning      | `clean_records()` — HTML strip, Unicode norm, dedup (exact + fuzzy)          |
| **mapper.py**    | Field mapping      | `SmartFieldMapper` — rapidfuzz-based alias matching, content-scoped          |
| **saver.py**     | Output formats     | Save JSON, CSV, LLM instruction, plain text formats                          |
| **schema.py**    | Data schema        | `validate_record()`, `normalize_record()` — strict unified schema validation |
| **job_store.py** | Job tracking       | `PersistentJobStore` — persistent registry in `output/jobs.json`             |

### 4.3 Pipeline Orchestrator

**File**: [pipeline/orchestrator.py](pipeline/orchestrator.py)

**Main Class**: `DataPipeline`

**Key Methods**:

- `run(source: str)` → Process single source
- `run_batch(sources: list)` → Process multiple sources (sequential or parallel via ThreadPoolExecutor)
- Retry logic with exponential backoff (configurable max_retries)
- Partial failure handling → continues batch, stores failed jobs in `failed_jobs.json`
- Per-step timing → logs duration of each stage
- Summary report generation → `<job_id>_summary.json`

**Features**:

- ✅ Strict sequential pipeline flow
- ✅ Configurable parallel batch processing (ThreadPoolExecutor)
- ✅ Automatic job ID generation (UUID4)
- ✅ Status tracking (PENDING/RUNNING/SUCCESS/FAILED)
- ✅ Persistent job store (survives restarts)
- ✅ Memory-efficient garbage collection between batches

### 4.4 FastAPI Backend

**File**: [api/main.py](api/main.py)

**Endpoints**:

| Method | Endpoint             | Purpose                                    |
| ------ | -------------------- | ------------------------------------------ |
| POST   | `/extract`           | Submit extraction job(s), returns `job_id` |
| GET    | `/status/{job_id}`   | Check job status, progress, errors         |
| GET    | `/download/{job_id}` | Stream output file (JSON/CSV)              |

**Features**:

- ✅ CORS enabled (all origins)
- ✅ Background task processing
- ✅ In-memory job store per session
- ✅ Configurable via `config.json` (host, port, etc.)

### 4.5 CLI Entry Point

**File**: [main.py](main.py)

**Usage**:

```bash
python main.py --sources "data/input/sample.csv"
python main.py --sources "https://example.com" --llm-format text
python main.py --batch data/input/batch.json --output-format csv --verbose
python main.py --api                          # Launch FastAPI server
```

**Supported Flags**:

- `--sources` : Single or multiple file paths / URLs / DB URIs
- `--batch` : Path to JSON file with list of sources
- `--output-format` : `json` or `csv` (default from config)
- `--llm-format` : `instruction` or `text` (default from config)
- `--verbose` : Enable DEBUG-level logging
- `--api` : Launch FastAPI backend
- `--config` : Custom config.json path

---

## 5. Configuration

**File**: [config.json](config.json)

```json
{
  "enable_ocr": true,
  "max_retries": 3,
  "output_format": "json",
  "batch_size": 10,
  "logging_level": "INFO",
  "output_dir": "output",
  "dedup": true,
  "fuzzy_dedup": false,
  "parallel": false,
  "llm_format": "instruction",
  "web": {
    "timeout": 15,
    "use_playwright": false,
    "user_agent": "Mozilla/5.0 (compatible; DataExtractionEngine/1.0)"
  },
  "pdf": {
    "language": "eng",
    "dpi": 300
  },
  "db": {
    "tables": []
  },
  "api": {
    "host": "0.0.0.0",
    "port": 8000
  }
}
```

**Environment Overrides** (via `.env`):

- `ENABLE_OCR` → enables PDF OCR
- `MAX_RETRIES` → retry attempts
- `LOG_LEVEL` → logging level
- `OUTPUT_FORMAT` → default output format
- `PARALLEL` → enable ThreadPoolExecutor
- `BATCH_SIZE` → batch processing size
- `LLM_FORMAT` → LLM output format

---

## 6. Dependencies

**Key Libraries** (see [requirements.txt](requirements.txt)):

| Category               | Libraries                                    |
| ---------------------- | -------------------------------------------- |
| **Web Scraping**       | requests, beautifulsoup4, lxml, playwright   |
| **PDF Processing**     | pdfplumber, pdf2image, pytesseract, Pillow   |
| **Data Processing**    | pandas, openpyxl, numpy                      |
| **Database**           | SQLAlchemy                                   |
| **NLP/Fuzzy Matching** | rapidfuzz                                    |
| **API Backend**        | fastapi, uvicorn, python-multipart, aiofiles |
| **Logging**            | colorlog                                     |
| **Config**             | python-dotenv                                |

---

## 7. Special Features

### 7.1 Retry & Backoff Logic

- Exponential backoff for transient failures
- Configurable max retries in `config.json`
- Per-source retry tracking in job store

### 7.2 Deduplication

- **Exact dedup**: Byte-for-byte comparison
- **Fuzzy dedup**: rapidfuzz-based similarity (configurable threshold)
- Configurable via `config.json` (dedup, fuzzy_dedup flags)

### 7.3 Field Mapping

- **SmartFieldMapper** uses rapidfuzz for intelligent alias matching
- Content-scoped: considers actual data values when determining field similarity
- Supports custom alias mappings

### 7.4 Output Formats

| Format              | Use Case                          | Structure                                       |
| ------------------- | --------------------------------- | ----------------------------------------------- |
| **JSON**            | Full structured records           | Array of record objects with all metadata       |
| **CSV**             | Data analysis, spreadsheet import | Flattened, one row per record, metadata columns |
| **LLM Instruction** | LLM training/fine-tuning          | Specially formatted instruction-response pairs  |
| **Plain Text**      | Direct LLM ingestion              | Raw concatenated text, line-per-record          |

### 7.5 Security Features

- URL validation (scheme check, domain sanitization)
- File path validation (prevent path traversal)
- DB URI sanitization (allowlist schemes)
- Content sanitization before processing

### 7.6 Logging

- **Colorlog** console output (color-coded by level)
- **File handler** → `output/pipeline.log`
- Per-step labels → [DETECT] [EXTRACT] [CLEAN] etc.
- Timestamps for all events
- UTF-8 safe on Windows

---

## 8. Progress & Implementation Status

### ✅ Completed Items

**Utils Layer** (100%):

- [x] logger.py — structured logging with colorlog + file
- [x] detector.py — source detection + security validation
- [x] cleaner.py — HTML strip, Unicode norm, dedup (exact + fuzzy)
- [x] mapper.py — SmartFieldMapper with rapidfuzz
- [x] saver.py — JSON, CSV, LLM, text output formats
- [x] schema.py — unified schema validation
- [x] job_store.py — persistent job registry

**Extractors** (100%):

- [x] base.py — abstract BaseExtractor
- [x] web_extractor.py — BeautifulSoup + Playwright
- [x] pdf_extractor.py — pdfplumber + pytesseract
- [x] csv_extractor.py — pandas with chunking
- [x] db_extractor.py — SQLAlchemy auto-reflection

**Pipeline** (100%):

- [x] orchestrator.py — full pipeline with retry + timing
- [x] Batch processing (sequential + parallel)
- [x] Job tracking + summary reports
- [x] Error handling + failed_jobs.json

**API** (100%):

- [x] POST /extract endpoint
- [x] GET /status endpoint
- [x] GET /download endpoint
- [x] CORS + background tasks

**CLI** (100%):

- [x] --sources, --batch, --output-format, --llm-format
- [x] --verbose, --api mode
- [x] Config loading + .env overrides

**Documentation** (100%):

- [x] README.md — setup, usage, config reference

### 📊 Sample Data & Outputs

**Input Data**:

- [x] sample.csv — customer records with varied field names (includes 1 duplicate)
- [x] batch.json — batch input example
- [x] create_sample_db.py — SQLite seeding script
- [x] create_sample_xlsx.py — Excel generation script

**Output Artifacts** (in `output/`):

- ✅ Job output files (JSON, CSV, LLM, summaries)
- ✅ Persistent job registry (`jobs.json`)
- ✅ Pipeline execution log (`pipeline.log`)

---

## 9. Output Examples

### Example: Single Record (Full Schema)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "csv",
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

### Example: Summary Report

```json
{
  "job_id": "abc123def456",
  "source": "data/input/sample.csv",
  "status": "SUCCESS",
  "total_records": 150,
  "successful_records": 148,
  "failed_records": 2,
  "dedup_removed": 3,
  "output_files": {
    "json": "output/abc123def456_output.json",
    "csv": "output/abc123def456_output.csv",
    "llm": "output/abc123def456_llm.json"
  },
  "timing": {
    "detect": 0.001,
    "extract": 0.234,
    "clean": 0.045,
    "normalize": 0.089,
    "map": 0.042,
    "save": 0.12,
    "total": 0.531
  },
  "generated_at": "2026-03-28T02:30:00Z"
}
```

---

## 10. Known Outputs (in `output/`)

The workspace shows these completed job outputs:

| Job ID   | Type | Status                       |
| -------- | ---- | ---------------------------- |
| 1d412776 | CSV  | ✅ (JSON, CSV, LLM, summary) |
| 1e2df454 | CSV  | ✅ (JSON, CSV, LLM)          |
| 35a1f220 | CSV  | ✅ (JSON, CSV, LLM, summary) |
| 3a973fb5 | CSV  | ✅ (JSON, CSV, LLM, summary) |
| 458ae016 | CSV  | ✅ (JSON, CSV, LLM)          |
| 6b108550 | CSV  | ✅ (JSON, CSV, LLM, summary) |
| 7198882a | CSV  | ✅ (JSON, CSV, LLM, summary) |
| 996a9655 | CSV  | ✅ (JSON, CSV, LLM)          |
| b40b2f6d | CSV  | ✅ (JSON, CSV, LLM)          |
| bb1c3567 | CSV  | ✅ (JSON, CSV, LLM)          |
| bf2a14a7 | CSV  | ✅ (JSON, CSV, LLM)          |
| c61c475f | CSV  | ✅ (JSON, CSV, LLM, summary) |

**Note**: All outputs appear to be from CSV extractions; diverse source types (Web, PDF, DB) can also be processed.

---

## 11. Key Design Patterns

### 11.1 Plug-and-Play Extensibility

```
New Extractor:
1. Create extractor class inheriting BaseExtractor
2. Implement extract() and supports() methods
3. Register in EXTRACTOR_REGISTRY
4. Zero changes to pipeline required
```

### 11.2 Strict Schema Enforcement

- All records normalized to unified schema before output
- Validation at every step
- Ensures LLM datasets have consistent structure

### 11.3 Separation of Concerns

- **Extractors**: Data source interaction
- **Utils**: Data transformation (clean, map, validate)
- **Pipeline**: Orchestration + flow control
- **API**: HTTP interface
- **CLI**: Command-line interface

### 11.4 Persistent State

- Job registry survives application restarts
- Failed jobs tracked separately
- Full execution logs for debugging

---

## 12. Performance Considerations

### Optimizations Implemented

- ✅ ThreadPoolExecutor for parallel batch processing (configurable)
- ✅ Chunked/streaming reads for large CSV/PDF files
- ✅ Memory-efficient pandas operations
- ✅ Garbage collection between batches
- ✅ Timeout handling for web requests (configurable)

### Scalability

- **Batch sizes** configurable (default: 10)
- **Parallel processing** toggle in config
- **Retry logic** prevents unnecessary external calls
- **Persistent job store** enables resumable processing

---

## 13. Security Considerations

### Input Validation

- URL scheme validation (http/https/file only)
- Path traversal prevention (no `../` allowed)
- DB URI sanitization

### Data Sanitization

- HTML entity decoding
- Special character handling
- Unicode normalization (NFKC)

### Logging

- No sensitive data logged (no passwords, tokens, etc.)
- File paths sanitized in logs
- Configurable log levels

---

## 14. Future Enhancement Opportunities

Based on analysis, potential improvements:

1. **Additional Extractors**:
   - JSON/XML endpoints
   - AWS S3 / Azure Blob Storage
   - Message queues (Kafka, RabbitMQ)
   - REST API generic handlers

2. **Advanced Features**:
   - Incremental extraction (track last extracted timestamp)
   - Change data capture (CDC) for databases
   - Custom transformations (user-defined functions)
   - Webhook callbacks on job completion

3. **Monitoring & Observability**:
   - Metrics export (Prometheus format)
   - Structured tracing (OpenTelemetry)
   - Dashboard for job history

4. **Production Hardening**:
   - Database backend for job store (instead of JSON file)
   - Distributed queue (Celery + Redis)
   - Rate limiting + authentication
   - Health check endpoints

---

## 15. Summary

This is a **well-architected, production-ready data extraction engine** with:

✅ **Modular design** → Easy to extend with new extractors  
✅ **Strict pipeline** → Predictable, debuggable flow  
✅ **Unified schema** → Consistent output across sources  
✅ **Enterprise features** → Retry logic, error handling, logging, security  
✅ **Multiple interfaces** → CLI + FastAPI + Python API  
✅ **LLM-ready outputs** → Specialized formats for training  
✅ **Persistent state** → Job tracking survives restarts  
✅ **Well-documented** → Clear code, comprehensive README

The project demonstrates strong software engineering practices: abstraction, separation of concerns, configuration management, error handling, and logging. It's ready for production deployment with appropriate monitoring/observability layers added.
