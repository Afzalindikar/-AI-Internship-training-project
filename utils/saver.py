"""
utils/saver.py
--------------
Save pipeline outputs to JSON, CSV, and LLM-ready dataset formats.
"""

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------


def save_json(data: list[dict], path: str) -> str:
    """
    Save a list of records as pretty-printed JSON.

    Args:
        data : List of record dicts
        path : Output file path

    Returns:
        Absolute path of saved file
    """
    _ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    return str(Path(path).resolve())


def save_csv(data: list[dict], path: str) -> str:
    """
    Save a list of records as a flat CSV.
    Nested dicts (e.g., metadata) are JSON-serialised into a single column.

    Args:
        data : List of record dicts
        path : Output file path

    Returns:
        Absolute path of saved file
    """
    if not data:
        return ""

    _ensure_dir(path)
    flat_data = [_flatten_record(r) for r in data]
    fieldnames = list({k for row in flat_data for k in row.keys()})

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sorted(fieldnames),
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(flat_data)

    return str(Path(path).resolve())


# ---------------------------------------------------------------------------
# LLM dataset formatting
# ---------------------------------------------------------------------------

def format_llm_dataset(
    records: list[dict],
    fmt: Literal["instruction", "text"] = "instruction",
    instruction_text: str = "Extract and summarise the key information from the following text.",
) -> list[dict]:
    """
    Convert cleaned records into LLM-ready dataset format.

    Args:
        records          : List of schema-conforming record dicts
        fmt              : "instruction" | "text"
        instruction_text : Custom instruction string for instruction format

    Returns:
        List of LLM-format dicts
    """
    result = []
    for record in records:
        raw = record.get("raw") or ""
        content = record.get("content", {}) or {}
        source = record.get("source", "unknown")
        meta = record.get("metadata", {}) or {}

        # Build input text: prefer raw, fall back to content string
        if not raw and isinstance(content, dict):
            raw = " | ".join(
                f"{k}: {v}" for k, v in content.items() if v is not None
            )
        elif not raw and isinstance(content, str):
            raw = content

        # Fix 5: Skip records where input text is empty/None
        input_text = raw.strip() if isinstance(raw, str) else ""
        if not input_text:
            continue  # do not add blank inputs to LLM dataset

        if fmt == "instruction":
            output_obj = {
                "source": source,
                "content": content,
                "metadata": meta,
            }
            result.append({
                "instruction": instruction_text,
                "input": input_text[:4096],  # cap to avoid huge LLM inputs
                "output": json.dumps(output_obj, ensure_ascii=False, default=str),
            })
        else:  # "text" format
            result.append({
                "text": input_text[:4096],
            })

    return result


def save_llm_dataset(
    records: list[dict],
    path: str,
    fmt: Literal["instruction", "text"] = "instruction",
) -> str:
    """
    Format and save the LLM dataset as JSON.

    Returns:
        Absolute path of saved file
    """
    llm_data = format_llm_dataset(records, fmt=fmt)
    return save_json(llm_data, path)


# ---------------------------------------------------------------------------
# Job manifest
# ---------------------------------------------------------------------------

def save_failed_jobs(failed_jobs: list[dict], output_dir: str) -> str:
    """
    Append failed job records to output/failed_jobs.json.

    Args:
        failed_jobs : List of failure dicts
        output_dir  : Directory to write to

    Returns:
        Absolute path of the failed jobs file
    """
    path = os.path.join(output_dir, "failed_jobs.json")
    existing: list[dict] = []

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    existing.extend(failed_jobs)
    return save_json(existing, path)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _ensure_dir(path: str) -> None:
    """Create parent directories if they don't exist."""
    parent = Path(path).parent
    parent.mkdir(parents=True, exist_ok=True)


def _flatten_record(record: dict) -> dict:
    """
    Flatten nested dicts into the top level.
    Metadata fields are prefixed with 'meta_'.
    """
    flat = {}
    for k, v in record.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                flat[f"{k}_{sub_k}"] = (
                    json.dumps(sub_v, ensure_ascii=False)
                    if isinstance(sub_v, (dict, list))
                    else sub_v
                )
        elif isinstance(v, list):
            flat[k] = json.dumps(v, ensure_ascii=False)
        else:
            flat[k] = v
    return flat
