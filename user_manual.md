# Multi-Source Data Extraction Engine: User Manual

## What is this project?
At its core, this project is an automated pipeline that takes messy data from almost any source (PDFs, Web Pages, Excel files, CSVs, or SQL databases), extracts the text, cleans it up, standardizes the column/field names, and exports pristine, ready-to-use structured datasets.

---

## 1. How to Give Inputs (The Entry Points)

There are three main ways you can feed data into the system:

### A. Single Source (via Command Line)
If you just want to process one file or URL, you pass it using the `--sources` flag. 
*   **Web Page:** `python main.py --sources "https://example.com/article"`
*   **PDF Document:** `python main.py --sources "data/input/annual_report.pdf"`
*   **CSV or Excel:** `python main.py --sources "data/customers.xlsx"`
*   **Database:** `python main.py --sources "sqlite:///data/my_database.db"`

### B. Batch Processing (via JSON File)
If you have hundreds of files or URLs, you can put them all into a batch JSON list (`batch_inputs.json`):
```json
[
  "https://news.ycombinator.com",
  "data/invoice.pdf",
  "data/employee_data.csv"
]
```
You then trigger the batch process using the `--batch` flag. You can also add `--parallel` to process them simultaneously to save time:
*   `python main.py --batch batch_inputs.json --parallel`

### C. The User Interface (Streamlit)
The project also comes with a web dashboard (typically located in the `ui` folder).
*   Start it via: `python -m streamlit run app.py`
*   Open your browser to the local Streamlit port (usually `http://localhost:8501`).
*   Upload your PDFs, CSVs, or enter URLs directly into the upload boxes.
*   Click **"Start Processing"**. 

---

## 2. How to Control the Output (Configuration)

Before hitting run, you can tune how the engine behaves by editing `config.json` or by passing command-line arguments:
*   `--output-format csv`: Requesting the engine to heavily prioritize saving CSV data.
*   `--llm-format text`: Instructing the engine to format data straight into full plain text blocks instead of fine-tuning QA JSON formats.
*   In `config.json`, you can toggle settings like `"enable_ocr": true` (to force image-based PDFs to be read) or `"dedup": true` (to automatically delete duplicate rows).

---

## 3. What to Expect as Outputs (The Results)

Whenever a job finishes successfully, the engine automatically generates several files inside the `output/` directory. Each file is prefixed with a unique 8-character ID for that specific job (e.g., `a1b2c3d4_output.json`).

Here is exactly what the engine produces:

### A. `*_output.json` (The Core Database)
This is the holy grail of the output. It is a highly structured, perfectly clean JSON file containing all data normalized across every source. Every record will look exactly like this:
```json
{
  "id": "e44d5g...",
  "source": "excel",
  "content": {
    "name": "John Doe",
    "phone": "555-0100"
  },
  "metadata": {
    "file_name": "customers.xlsx",
    "extracted_at": "2026-03-29T12:00:00.000Z",
    "source_type": "excel"
  },
  "raw": "Customer Name: John Doe | Mobile Num: 555-0100" 
}
```

### B. `*_output.csv` (For Data Analysts)
It flattens the nested JSON shown above into a standard, spreadsheet-ready CSV file. All nested metadata values get their own columns (e.g., `metadata_file_name`). This is perfect for importing into Excel, Tableau, or feeding into Pandas.

### C. `*_llm.json` (For AI Training)
If you are building an AI/LLM, this file is specifically formatted for Supervised Fine-Tuning. It structures the data into exact "Prompt" and "Completion" pairs:
```json
{
  "instruction": "Extract and summarise the key information from the following text.",
  "input": "Customer Name: John Doe | Mobile Num: 555-0100",
  "output": "{\"content\": {\"name\": \"John Doe\", \"phone\": \"555-0100\"}}"
}
```

### D. Tracking and Summaries
*   **`*_summary.json`**: A health report for your batch. It tells you exactly how long the extraction took (down to the millisecond), how many sources succeeded, and how many records were parsed.
*   **`jobs.json`**: Acts as the project's memory. It remembers every job you've ever run, meaning the Streamlit UI can retrieve past extractions.
*   **`failed_jobs.json`**: If an extraction crashed (e.g., a PDF was heavily corrupted or a URL went offline), the exact Python Exception log is saved here so developers can debug it later without having to dig through terminal logs.

---

## Summary
*   **Input**: Provide a file path, a URL, or a DB connection string via CLI, JSON Array, or the Web Dashboard.
*   **Output**: Navigate to your `output/` folder and receive perfectly mapped, clean JSON data, flattened CSVs, AI-training files, and a performance report.
