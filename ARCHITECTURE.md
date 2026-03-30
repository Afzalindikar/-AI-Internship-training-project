# System Architecture Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         INPUT SOURCES                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  File System      Web                Database         File Formats     │
│  │                │                  │                │                │
│  ├─ /path/file    ├─ http://         ├─ sqlite://     ├─ .csv          │
│  │   .csv/.xlsx   │   https://       │   postgres://  ├─ .xlsx         │
│  │   (local)      │   (URLs)         │   mysql://     └─ .pdf          │
│  │                │                  │   (SQLAlchemy) │                │
│  └────────────────┴──────────────────┴────────────────┴────────────────┘
│                                 │
│                                 │ sources (list)
│                                 ▼
│                         ┌──────────────────┐
│                         │   CLI / API      │
│                         │   (main.py)      │
│                         │   (api/main.py)  │
│                         └────────┬─────────┘
│                                 │
│                                 ▼
│                      ┌──────────────────────┐
│                      │  DataPipeline        │
│                      │  (orchestrator.py)   │
│                      └────────┬─────────────┘
│                               │
└───────────────────────────────┼───────────────────────────────────────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │ Configuration
                    │           │           │ (config.json)
                    ▼           ▼           ▼
                ┌─ config via .env ────────┐
                │                         │
                │ (Applied in sequence:   │
                │  config.json            │
                │  → .env overrides)      │
                └─────────────────────────┘
                    │
                    ▼
         ┌──────────────────────────────────┐
         │  PIPELINE: 6-STEP PROCESSING     │
         └──────────────────────────────────┘
                    │
            ┌───────┴───────┬────────┬────────┬─────┐
            │               │        │        │     │
            ▼  [1]          ▼        ▼        ▼     ▼
         DETECT         EXTRACT   CLEAN   NORMALIZE MAP
            │               │        │        │     │
            │   Detector    │     Cleaner    Schema Mapper
            │   ├─ type     │     ├─ HTML   │      ├─ alias
            │   ├─ validate │     ├─ unicode├─ valid├─ rapidfuzz
            │   └─ security │     ├─ dedup  │      └─ content-
            │               │     └─ fuzzy  │         scoped
            │               │               │
            │ ┌─ Registry ──┤               │
            │ │ ├─Web       │               │
            │ │ ├─PDF       └───────────────┼──────┐
            │ │ ├─CSV                       │      │
            │ │ └─DB                        │      │
            │ └───────────────────────────┬─┘      │
            │                             │        │
            │ Extractor runs:             │        │
            │ ├─ retry (exponential)      │        │
            │ ├─ timeout                  │        │
            │ └─ returns raw records      │        │
            │                             ▼        │
            │                         [Records]    │
            │                         Normalized   │
            │                         to Schema    │
            │                             │        │
            │             ┌───────────────┘        │
            │             │                        │
            └─────────────┼────────────────────────┘
                          │
                          ▼
                   ┌─────────────────┐
                 [6] SAVE            │
                   │                 │
                   ├─ JSON           │
                   ├─ CSV            │
                   ├─ LLM format     │
                   └─ Plain text     │
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │  OUTPUT FILES (in output/)          │
        ├─────────────────────────────────────┤
        │                                     │
        │  <job_id>_output.json               │
        │  <job_id>_output.csv                │
        │  <job_id>_llm.json                  │
        │  <job_id>_summary.json              │
        │  jobs.json (persistent registry)    │
        │  pipeline.log (execution log)       │
        │                                     │
        └─────────────────────────────────────┘
```

---

## Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌──────────────────────┐          ENTRY POINTS                        │
│  │  CLI (main.py)       │                                              │
│  │  ├─ --sources        │                                              │
│  │  ├─ --batch          │                                              │
│  │  ├─ --output-format  │ ◄──────────────┐                             │
│  │  ├─ --llm-format     │                │                             │
│  │  ├─ --verbose        │                │                             │
│  │  └─ --api            │ ──────┐        │                             │
│  └──────────────────────┘       │        │                             │
│                                 │        │                             │
│  ┌──────────────────────┐       │        │                             │
│  │  FastAPI (api/main.py)       │        │                             │
│  │  ├─ POST /extract   │       │        │                             │
│  │  ├─ GET /status     │ ◄─────┤────────┤                             │
│  │  └─ GET /download   │       │        │                             │
│  └──────────────────────┘       │        │                             │
│                                 │        │                             │
│  ┌──────────────────────────┐   │        │                             │
│  │  Python API              │   │        │                             │
│  │  (programmatic use)      │ ◄─┤────────┤                             │
│  │                          │   │        │                             │
│  │  from pipeline.          │   │        │                             │
│  │  orchestrator import     │   │        │                             │
│  │  DataPipeline            │   │        │                             │
│  └──────────────────────────┘   │        │                             │
│         │                        │        │                             │
│         └────────┬───────────────┴────────┘                             │
│                  ▼                                                      │
│         ┌─────────────────────────────────────┐                        │
│         │  DataPipeline (orchestrator.py)     │                        │
│         │                                     │                        │
│         │  Methods:                           │                        │
│         │  • run(source)                      │                        │
│         │  • run_batch(sources)               │                        │
│         │  • _run_pipeline(source, config)    │                        │
│         │  • _run_batch_parallel()            │                        │
│         │                                     │                        │
│         └─────────────────┬───────────────────┘                        │
│                           │                                            │
│         ┌─────────────────┼─────────────────┬──────────────┐           │
│         │                 │                 │              │           │
│         ▼                 ▼                 ▼              ▼           │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────┐ ┌──────────┐      │
│  │  Detector      │  │ Extractor    │  │ Cleaner  │ │ Normalizer
│  │ (detector.py)  │  │ Registry     │  │(cleaner) │ │(schema.py) │
│  │                │  │ (base.py)    │  │          │ │           │
│  │ detect_source  │  │              │  │ strip    │ │ validate  │
│  │ _type()        │  │ WebExtractor │  │ HTML     │ │ _record() │
│  │                │  │ PDFExtractor │  │ dedup    │ │ generate  │
│  │ validate_      │  │ CSVExtractor │  │ fuzzy    │ │ uuid4     │
│  │ source()       │  │ DBExtractor  │  │ dedupe   │ │ timestamps│
│  │                │  │              │  │ normalize│ │           │
│  │ security       │  │ all inherit  │  │ unicode  │ │           │
│  │ checks         │  │ BaseExtractor│  │ (NFKC)   │ │           │
│  │                │  │              │  │          │ │           │
│  └────────────────┘  └──────────────┘  └─────────┘ └──────────┘
│         │                 │                 │              │
│         └─────────────────┼─────────────────┼──────────────┘
│                           │                 │              ▼
│                           │                 │        ┌──────────────┐
│                           │                 │        │  Mapper      │
│                           │                 │        │ (mapper.py)  │
│                           │                 │        │              │
│                           │                 │        │ SmartField   │
│                           │                 │        │ Mapper       │
│                           │                 │        │              │
│                           │                 │        │ rapidfuzz    │
│                           │                 │        │ alias match  │
│                           │                 │        │ content-     │
│                           │                 │        │ scoped       │
│                           │                 │        └──────────────┘
│                           │                 │              │
│         ┌─────────────────┼─────────────────┼──────────────┘
│         │                 │                 │
│         ▼                 ▼                 ▼
│  ┌────────────────────────────────────────────────────────┐
│  │  Saver (saver.py)                                      │
│  │                                                        │
│  │  save_json(records, path)                              │
│  │  save_csv(records, path)                               │
│  │  save_llm_dataset(records, path, format)               │
│  │  save_failed_jobs(failed, path)                        │
│  └────────────────────┬─────────────────────────────────┘
│                       │
│         ┌─────────────┼─────────────┬──────────┐
│         │             │             │          │
│         ▼             ▼             ▼          ▼
│  JSON Output    CSV Output    LLM Output   Summary
│  Records        Flattened     Instruction   Report
│                 Rows          Format
│         │             │             │          │
│         │             │             │          │
│         └─────────────┼─────────────┼──────────┘
│                       │
│                       ▼
│      ┌────────────────────────────────┐
│      │  Job Store (job_store.py)      │
│      │                                │
│      │  PersistentJobStore            │
│      │  └─ output/jobs.json           │
│      │     (persistent registry)      │
│      └────────────────────────────────┘
│                       │
│         ┌─────────────┼─────────────┐
│         │             │             │
│         ▼             ▼             ▼
│  Logger Info    Job Tracking  Execution
│  (logger.py)    Updates       State
│  colorlog       (status,      Persistence
│  file handler   counts)
│
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Through Pipeline

```
Raw Data
   │
   ├─ CSV row:     "Alice,alice@ex.com,95000"
   ├─ PDF text:    "Name: Alice\nEmail: alice@ex.com"
   ├─ Web HTML:    "<td>Alice</td><td>alice@ex.com</td>"
   └─ DB record:   Row(name='Alice', email='alice@ex.com')
   │
   ▼
[DETECT] Auto-detect source type
   │
   ├─ → "csv"
   ├─ → "pdf"
   ├─ → "web"
   └─ → "database"
   │
   ▼
[EXTRACT] Get data from source
   │
   ├─ CSVExtractor.extract()     → pandas read_csv()
   ├─ PDFExtractor.extract()     → pdfplumber.open()
   ├─ WebExtractor.extract()     → requests + BeautifulSoup
   └─ DBExtractor.extract()      → SQLAlchemy reflect()
   │
   Produces: List[dict] with raw content
   │
   ├─ {"source": "csv", "content": "Alice,alice@ex.com,95000", "metadata": {...}}
   ├─ {"source": "pdf", "content": "Name: Alice\nEmail: alice@ex.com", "metadata": {...}}
   └─ ...
   │
   ▼
[CLEAN] Normalize & deduplicate
   │
   Cleaner processes each record:
   ├─ Strip HTML tags
   ├─ Normalize unicode (NFKC)
   ├─ Lowercase
   ├─ Trim whitespace
   ├─ Exact dedup (byte compare)
   └─ Fuzzy dedup (rapidfuzz ≥ 0.85)
   │
   ├─ Removed: 3 duplicates
   └─ Remaining: 147 records
   │
   ▼
[NORMALIZE] Validate & standardize
   │
   Schema validation:
   ├─ Ensure all required fields exist
   ├─ Generate UUID4 if missing
   ├─ Add timestamp (ISO 8601)
   ├─ Type cast values
   └─ Create structured "content" dict
   │
   │ All records now conform to:
   │ {
   │   "id": "550e8400-...",
   │   "source": "csv|pdf|web|database",
   │   "content": {key: value, ...},
   │   "metadata": {...},
   │   "raw": "flat text",
   │   "failed": false,
   │   "error": null
   │ }
   │
   ▼
[MAP] Intelligent field mapping
   │
   SmartFieldMapper (rapidfuzz):
   │
   Input: {"first_name": "Alice", "e-mail": "alice@ex.com"}
   │
   ├─ "first_name" ~matches~ "name" (similarity > 0.85)
   ├─ "e-mail" ~matches~ "email" (exact match)
   │
   Output: {"name": "Alice", "email": "alice@ex.com"}
   │
   ▼
[SAVE] Write outputs
   │
   ├─ JSON: Full record with all fields
   │   {
   │     "id": "...",
   │     "source": "csv",
   │     "content": {...},
   │     "metadata": {...},
   │     "raw": "...",
   │     "failed": false
   │   }
   │
   ├─ CSV: Flattened rows
   │   id,source,name,email,salary,file_name,extracted_at,...
   │
   ├─ LLM: Instruction format
   │   {
   │     "instruction": "Extract data",
   │     "input": "Alice alice@ex.com 95000",
   │     "output": "{\"name\":\"Alice\",\"email\":\"alice@ex.com\"}"
   │   }
   │
   └─ Text: Raw concatenated
   │   "alice. alice@ex.com. 95000."
   │
   ▼
Output Files (in output/)
   │
   ├─ abc123_output.json
   ├─ abc123_output.csv
   ├─ abc123_llm.json
   ├─ abc123_summary.json
   ├─ jobs.json (updated)
   └─ pipeline.log (appended)
```

---

## Extractor Plugin Architecture

```
┌─────────────────────────────────────────────────┐
│  BaseExtractor (ABC)                            │
│  abstract class                                 │
│                                                 │
│  Methods:                                       │
│  • extract(source, config) → List[dict]         │
│  • supports(source_type) → bool                 │
└────────┬────────────────────────────────────────┘
         │
         │     Inheritance
         │
    ┌────┴────────┬───────────────┬─────────────┐
    │             │               │             │
    ▼             ▼               ▼             ▼
WebExtractor  PDFExtractor  CSVExtractor  DBExtractor
(web_extractor.py) (pdf_extractor.py) (csv_extractor.py) (db_extractor.py)
    │             │               │             │
    │ implements: │               │             │
    │ extract()   │               │             │
    │ supports()  │               │             │
    │             │               │             │
    ├─ Uses:      ├─ Uses:        ├─ Uses:      ├─ Uses:
    │ BeautifulSoup │ pdfplumber  │ pandas     │ SQLAlchemy
    │ Playwright    │ pytesseract │ openpyxl   │
    │ requests      │ Pillow      │            │
    │              │             │             │
    │ Features:    │ Features:   │ Features:  │ Features:
    │ -timeout     │ -OCR        │ -chunked   │ -reflection
    │ -retry       │ -per page   │ -large CSV │ -configurable
    │ -fallback    │ -DPI config │ -encoding  │ -all dialects
    │              │             │             │
    └──────────────┴─────────────┴─────────────┘
                    │
                    │ All return:
                    │
         List[dict] with keys:
         {
           "source": "csv|pdf|web|database",
           "content": "extracted text or dict",
           "metadata": {
             "title", "author", "date", "url",
             "file_name", "extracted_at", "source_type"
           }
         }
                    │
                    ▼
        Pipeline continues (Clean → Normalize → Map → Save)
```

---

## Job Lifecycle

```
┌─────────────────────────────────────────────────┐
│  JOB CREATION                                   │
│  • User submits sources via CLI / API           │
│  • job_id = UUID4 generated                     │
│  • Status set to PENDING                        │
│  • Record stored in jobs.json                   │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────────────┐
        │  JOB EXECUTION               │
        │  Status → RUNNING            │
        │                              │
        │  For each source:            │
        │  1. Run pipeline (6 steps)   │
        │  2. Log per-step timing      │
        │  3. Count records            │
        │  4. Handle errors            │
        │                              │
        │  Outcomes:                   │
        │  ✅ SUCCESS                   │
        │  ❌ PARTIAL_SUCCESS (some failed)
        │  ❌ FAILED (all failed)      │
        │                              │
        └──────────────┬───────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
    SUCCESS              FAILED / PARTIAL
    │                           │
    ├─ Save outputs            ├─ Save partial results
    │ ├─ json                  ├─ Store failed records
    │ ├─ csv                   │  in failed_jobs.json
    │ ├─ llm                   │
    │ └─ summary               ├─ Log error details
    │                          │
    ├─ Generate summary        ├─ Status → FAILED or
    │ ├─ total count           │  PARTIAL_SUCCESS
    │ ├─ timing                │
    │ ├─ output files          └─ User can retry
    │ └─ no errors
    │
    ├─ Update jobs.json
    │ └─ Status → SUCCESS
    │    Add paths to outputs
    │
    ▼
┌─────────────────────────────────────────────────┐
│  JOB COMPLETION                                 │
│  • Status stored in jobs.json                   │
│  • Output files available in output/            │
│  • User can download via API or CLI             │
│  • Job history persists (survives restart)      │
└─────────────────────────────────────────────────┘
```

---

## Configuration Override Chain

```
Default values
   │
   ├─ Hard-coded defaults in code
   │  (e.g., max_retries=3, batch_size=10)
   │
   ▼
config.json
   │
   ├─ Loads defaults from JSON
   │ {
   │   "enable_ocr": true,
   │   "max_retries": 3,
   │   ...
   │ }
   │
   ▼
.env file overrides
   │
   ├─ Loads environment variables
   │ ENABLE_OCR=false
   │ MAX_RETRIES=5
   │ ...
   │
   ├─ Mapping:
   │ ENABLE_OCR     → enable_ocr
   │ MAX_RETRIES    → max_retries
   │ LOG_LEVEL      → logging_level
   │ OUTPUT_FORMAT  → output_format
   │ PARALLEL       → parallel
   │ BATCH_SIZE     → batch_size
   │ LLM_FORMAT     → llm_format
   │
   ▼
Final Configuration
   │
   ├─ Used by DataPipeline
   ├─ Used by each extractor
   ├─ Used by logger
   └─ Used by all utils
```

---

## Batch Processing Modes

```
Sequential (parallel=false)
│
├─ Source 1
│  └─ Detect → Extract → Clean → Normalize → Map → Save
│     └─ Wait for completion
│
├─ Source 2
│  └─ Same steps
│     └─ Wait for completion
│
└─ Source N
   └─ Complete before continuing

Total time = sum of all sources
(Good for I/O bound, lower resource use)


Parallel (parallel=true, ThreadPoolExecutor)
│
├─ Source 1 ─────────┐
│  └─ Pipeline   ├─ Concurrent
├─ Source 2 ─────┤  Execution
│  └─ Pipeline   │  (4-16 threads
├─ Source 3 ─────┤   configurable)
│  └─ Pipeline   │
└─ Source N ─────┘

Total time ≈ max(individual times)
(Good for multi-source, higher resource use,
 requires careful memory management)

Note: Respects batch_size limit per iteration
```
