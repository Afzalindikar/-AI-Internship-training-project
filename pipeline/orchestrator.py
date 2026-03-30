"""
pipeline/orchestrator.py
------------------------
Pipeline orchestrator: enforces the strict flow
    Detect → Extract → Clean → Normalize → Map → Save

Enhancements:
    - Per-step execution timing with duration logs
    - Total pipeline execution time
    - Summary report saved to output/<job_id>_summary.json
    - Persistent job tracking via PersistentJobStore (output/jobs.json)
    - Batch processing (sequential + optional ThreadPoolExecutor parallel)
    - Partial failure handling with failed_jobs.json
    - Retry with exponential backoff
"""

import gc
import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from utils.detector import detect_source_type, validate_source
from utils.cleaner import clean_records
from utils.schema import validate_and_normalize
from utils.mapper import map_records
from utils.saver import save_json, save_csv, save_llm_dataset, save_failed_jobs
from utils.logger import get_logger, step_log
from utils.job_store import PersistentJobStore

from extractors.web_extractor import WebExtractor
from extractors.pdf_extractor import PDFExtractor
from extractors.csv_extractor import CSVExtractor
from extractors.db_extractor import DBExtractor

# ── Extractor registry (plug-and-play) ───────────────────────────────────────
EXTRACTOR_REGISTRY: dict = {
    "url": WebExtractor(),
    "web": WebExtractor(),
    "pdf": PDFExtractor(),
    "csv": CSVExtractor(),
    "excel": CSVExtractor(),
    "database": DBExtractor(),
}


# ---------------------------------------------------------------------------
# Timing context manager
# ---------------------------------------------------------------------------

@contextmanager
def _timed_step(logger, step_name: str, job_id: str = ""):
    """Context manager that logs a step's duration on exit."""
    t0 = time.perf_counter()
    step_log(logger, step_name, "Starting...", job_id)
    try:
        yield
    finally:
        elapsed = time.perf_counter() - t0
        step_log(logger, step_name, f"Completed in {elapsed:.2f}s", job_id)


# ---------------------------------------------------------------------------
# DataPipeline
# ---------------------------------------------------------------------------

class DataPipeline:
    """
    Main pipeline orchestrator.

    Usage:
        pipeline = DataPipeline(config)
        result = pipeline.run("data/input/sample.csv")
        results = pipeline.run_batch(["url1", "file.pdf", "db.sqlite"])
    """

    def __init__(self, config: dict):
        self.config = config
        self.output_dir = config.get("output_dir", "output")
        self.max_retries = config.get("max_retries", 3)
        self.dedup = config.get("dedup", True)
        self.fuzzy_dedup = config.get("fuzzy_dedup", False)
        self.output_format = config.get("output_format", "json")
        self.llm_format = config.get("llm_format", "instruction")
        self.parallel = config.get("parallel", False)
        self.batch_size = config.get("batch_size", 10)

        log_level = config.get("logging_level", "INFO")
        self.logger = get_logger("pipeline", level=log_level, log_dir=self.output_dir)

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        # Persistent job store (survives restarts)
        self.job_store = PersistentJobStore(
            path=str(Path(self.output_dir) / "jobs.json")
        )

    # ── Single source ─────────────────────────────────────────────────────────

    def run(self, source: str, job_id: Optional[str] = None) -> dict:
        """
        Run the full pipeline on a single source.

        Returns:
            Result dict with job_id, status, output_paths, records, error
        """
        job_id = job_id or str(uuid.uuid4())
        pipeline_start = time.perf_counter()

        self.job_store.create(job_id, source=source)
        self.job_store.update(job_id, status="RUNNING")
        self.logger.info(f"[JOB START] job_id={job_id} source={source}")

        records: list[dict] = []
        source_type: Optional[str] = None
        error_msg: Optional[str] = None
        step_timings: dict[str, float] = {}

        try:
            # ── STEP 1: DETECT ────────────────────────────────────────────────
            t0 = time.perf_counter()
            step_log(self.logger, "DETECT", f"Detecting source type for: {source}", job_id)
            source_type = detect_source_type(source)
            validated_source = validate_source(source, source_type)
            step_timings["detect"] = round(time.perf_counter() - t0, 3)
            step_log(
                self.logger, "DETECT",
                f"Source type -> {source_type} (in {step_timings['detect']:.2f}s)", job_id
            )

            # ── STEP 2: EXTRACT ───────────────────────────────────────────────
            t0 = time.perf_counter()
            step_log(self.logger, "EXTRACT", f"Extracting from {source_type}: {source}", job_id)
            raw_output = self._extract_with_retry(validated_source, source_type, job_id)

            # Fix 6: Defensive checks on extractor output
            if not isinstance(raw_output, list):
                self.logger.warning(
                    f"[EXTRACT] Extractor returned unexpected type "
                    f"{type(raw_output).__name__} for '{source}' — wrapping in list"
                )
                raw_output = [raw_output] if raw_output else []

            # Filter out non-dict items defensively
            raw_records = [
                r for r in raw_output if isinstance(r, dict)
            ]
            if len(raw_records) != len(raw_output):
                dropped = len(raw_output) - len(raw_records)
                self.logger.warning(
                    f"[EXTRACT] Dropped {dropped} non-dict item(s) from extractor output"
                )

            if not raw_records:
                self.logger.warning(
                    f"[EXTRACT] No records extracted from '{source}'. "
                    f"Source may be empty or unsupported."
                )

            step_timings["extract"] = round(time.perf_counter() - t0, 3)
            step_log(
                self.logger, "EXTRACT",
                f"Extracted {len(raw_records)} raw records (in {step_timings['extract']:.2f}s)",
                job_id
            )

            # ── STEP 3: CLEAN ─────────────────────────────────────────────────
            t0 = time.perf_counter()
            step_log(self.logger, "CLEAN", "Cleaning and deduplicating records", job_id)
            cleaned = clean_records(
                raw_records,
                dedup=self.dedup,
                fuzzy_dedup=self.fuzzy_dedup,
            )
            step_timings["clean"] = round(time.perf_counter() - t0, 3)
            step_log(
                self.logger, "CLEAN",
                f"{len(cleaned)} records after cleaning (in {step_timings['clean']:.2f}s)",
                job_id
            )

            # ── STEP 4: NORMALIZE ─────────────────────────────────────────────
            t0 = time.perf_counter()
            step_log(self.logger, "NORMALIZE", "Normalizing to unified schema", job_id)
            normalized = [validate_and_normalize(r) for r in cleaned]
            step_timings["normalize"] = round(time.perf_counter() - t0, 3)
            step_log(
                self.logger, "NORMALIZE",
                f"{len(normalized)} records normalized (in {step_timings['normalize']:.2f}s)",
                job_id
            )

            # ── STEP 5: MAP ───────────────────────────────────────────────────
            t0 = time.perf_counter()
            step_log(self.logger, "MAP", "Applying Smart Field Mapper", job_id)
            mapped = map_records(normalized)
            step_timings["map"] = round(time.perf_counter() - t0, 3)
            step_log(
                self.logger, "MAP",
                f"Field mapping complete (in {step_timings['map']:.2f}s)", job_id
            )

            # ── STEP 6: SAVE ──────────────────────────────────────────────────
            t0 = time.perf_counter()
            step_log(self.logger, "SAVE", "Saving outputs", job_id)
            output_paths = self._save_outputs(mapped, job_id)
            step_timings["save"] = round(time.perf_counter() - t0, 3)
            step_log(
                self.logger, "SAVE",
                f"Saved {len(output_paths)} files (in {step_timings['save']:.2f}s)", job_id
            )

            records = mapped
            total_time = round(time.perf_counter() - pipeline_start, 3)
            self.logger.info(
                f"[PIPELINE] Total execution time: {total_time:.2f}s | "
                f"job_id={job_id} | records={len(records)}"
            )

            # ── SUMMARY REPORT ────────────────────────────────────────────────
            summary = self._build_summary(
                job_id=job_id,
                sources=[source],
                successful=1,
                failed=0,
                total_records=len(records),
                total_time=total_time,
                step_timings=step_timings,
            )
            summary_path = self._save_summary(summary, job_id)
            output_paths["summary"] = summary_path

            self.job_store.update(
                job_id, status="SUCCESS",
                record_count=len(records),
                output_paths=output_paths,
                step_timings=step_timings,
                total_time_seconds=total_time,
            )
            self.logger.info(f"[JOB DONE] job_id={job_id}")

            return {
                "job_id": job_id,
                "status": "SUCCESS",
                "source": source,
                "source_type": source_type,
                "record_count": len(records),
                "output_paths": output_paths,
                "records": records,
                "step_timings": step_timings,
                "total_time_seconds": total_time,
                "summary": summary,
                "error": None,
            }

        except Exception as exc:
            import traceback
            error_msg = str(exc)
            tb = traceback.format_exc()
            total_time = round(time.perf_counter() - pipeline_start, 3)
            self.logger.error(
                f"[JOB FAILED] job_id={job_id} source={source} "
                f"error={error_msg} (after {total_time:.2f}s)\n{tb}"
            )

            failed_entry = {
                "job_id": job_id,
                "source": source,
                "error": error_msg,
                "traceback": tb,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_time_seconds": total_time,
            }
            save_failed_jobs([failed_entry], self.output_dir)

            self.job_store.update(
                job_id, status="FAILED",
                error=error_msg,
                total_time_seconds=total_time,
                errors=[error_msg],
            )

            return {
                "job_id": job_id,
                "status": "FAILED",
                "source": source,
                "source_type": source_type,
                "record_count": 0,
                "output_paths": {},
                "records": records,
                "step_timings": step_timings,
                "total_time_seconds": total_time,
                "summary": None,
                "error": error_msg,
            }

    # ── Batch processing ──────────────────────────────────────────────────────

    def run_batch(self, sources: list[str]) -> list[dict]:
        """
        Process multiple sources, sequentially or in parallel.

        Args:
            sources: List of file paths, URLs, or DB URIs

        Returns:
            List of result dicts (one per source)
        """
        batch_start = time.perf_counter()
        self.logger.info(
            f"[BATCH] Starting batch of {len(sources)} sources "
            f"(parallel={self.parallel})"
        )

        # Pre-assign job IDs and register as PENDING
        job_map = {source: str(uuid.uuid4()) for source in sources}
        for src, jid in job_map.items():
            self.job_store.create(jid, source=src)

        results: list[dict] = []

        if self.parallel:
            workers = min(self.batch_size, len(sources))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(self.run, src, jid): src
                    for src, jid in job_map.items()
                }
                for future in as_completed(futures):
                    src = futures[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        result = {
                            "job_id": job_map[src],
                            "status": "FAILED",
                            "source": src,
                            "error": str(exc),
                            "records": [],
                            "record_count": 0,
                            "output_paths": {},
                            "summary": None,
                        }
                    results.append(result)
        else:
            for source, job_id in job_map.items():
                result = self.run(source, job_id=job_id)
                results.append(result)

        # Batch-level summary
        total_time = round(time.perf_counter() - batch_start, 3)
        gc.collect()

        success = sum(1 for r in results if r["status"] == "SUCCESS")
        failed = len(results) - success
        total_records = sum(r.get("record_count", 0) for r in results)

        self.logger.info(
            f"[BATCH DONE] total={len(results)} success={success} "
            f"failed={failed} records={total_records} time={total_time:.2f}s"
        )
        return results

    # ── Job status ────────────────────────────────────────────────────────────

    def get_job_status(self, job_id: str) -> dict:
        """Return current status of a job from persistent store."""
        job = self.job_store.get(job_id)
        return job or {"error": "Job not found", "job_id": job_id}

    # ── Internals ─────────────────────────────────────────────────────────────

    def _extract_with_retry(
        self, source: str, source_type: str, job_id: str
    ) -> list[dict]:
        """Wrap extractor call with retry + exponential backoff."""
        extractor = EXTRACTOR_REGISTRY.get(source_type)
        if extractor is None:
            raise ValueError(f"No extractor registered for source type: {source_type}")

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return extractor.extract(source, self.config)
            except Exception as exc:
                last_exc = exc
                wait = 2 ** attempt
                self.logger.warning(
                    f"[EXTRACT] Attempt {attempt}/{self.max_retries} failed "
                    f"for {source}: {exc}. Retrying in {wait}s..."
                )
                time.sleep(wait)

        raise RuntimeError(
            f"All {self.max_retries} extraction attempts failed for '{source}': {last_exc}"
        )

    def _save_outputs(self, records: list[dict], job_id: str) -> dict:
        """Save JSON, CSV, and LLM-format outputs. Returns dict of paths."""
        short_id = job_id[:8]
        paths = {}

        json_path = os.path.join(self.output_dir, f"{short_id}_output.json")
        paths["json"] = save_json(records, json_path)

        csv_path = os.path.join(self.output_dir, f"{short_id}_output.csv")
        paths["csv"] = save_csv(records, csv_path)

        llm_path = os.path.join(self.output_dir, f"{short_id}_llm.json")
        paths["llm"] = save_llm_dataset(records, llm_path, fmt=self.llm_format)

        return paths

    @staticmethod
    def _build_summary(
        job_id: str,
        sources: list,
        successful: int,
        failed: int,
        total_records: int,
        total_time: float,
        step_timings: dict,
    ) -> dict:
        """Build a structured summary report dict."""
        return {
            "job_id": job_id,
            "total_sources": len(sources),
            "successful_sources": successful,
            "failed_sources": failed,
            "total_records": total_records,
            "execution_time_seconds": total_time,
            "step_timings_seconds": step_timings,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _save_summary(self, summary: dict, job_id: str) -> str:
        """Save summary report to output/<short_id>_summary.json."""
        short_id = job_id[:8]
        path = os.path.join(self.output_dir, f"{short_id}_summary.json")
        return save_json(summary, path)
