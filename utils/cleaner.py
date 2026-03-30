"""
utils/cleaner.py
----------------
Data cleaning utilities: HTML stripping, text normalisation,
null handling, deduplication (exact + optional fuzzy).
"""

import re
import unicodedata
from typing import Optional

import pandas as pd

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def clean_records(
    records: list[dict],
    dedup: bool = True,
    fuzzy_dedup: bool = False,
    fuzzy_threshold: int = 90,
) -> list[dict]:
    """
    Clean and deduplicate a list of extracted records.

    Steps:
        1. Clean each record's `content` field
        2. Fill null/missing values
        3. Exact deduplication on `content` (pandas)
        4. Optional fuzzy deduplication

    Args:
        records         : List of raw record dicts
        dedup           : Enable exact deduplication
        fuzzy_dedup     : Enable near-duplicate removal via rapidfuzz
        fuzzy_threshold : Similarity score threshold (0-100)

    Returns:
        List of cleaned, deduplicated record dicts
    """
    if not records:
        return []

    cleaned = [_clean_record(r) for r in records]

    if dedup:
        cleaned = _exact_dedup(cleaned)

    if fuzzy_dedup and HAS_RAPIDFUZZ:
        cleaned = _fuzzy_dedup(cleaned, fuzzy_threshold)

    return cleaned


def clean_text(text: str) -> str:
    """
    Clean a raw text string:
        - Strip HTML/XML tags
        - Remove special characters and extra whitespace
        - Normalize unicode
        - Lowercase and trim
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""

    # Strip HTML tags
    if HAS_BS4:
        try:
            text = BeautifulSoup(text, "lxml").get_text(separator=" ")
        except Exception:
            text = re.sub(r"<[^>]+>", " ", text)
    else:
        text = re.sub(r"<[^>]+>", " ", text)

    # Normalize unicode (NFKC: compatibility + canonical composition)
    # This preserves international characters while normalizing ligatures etc.
    text = unicodedata.normalize("NFKC", text)

    # Remove null bytes and control characters only (keep international chars)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Replace multiple whitespace (spaces, tabs, newlines) with single space
    text = re.sub(r"\s+", " ", text)

    # Strip leading/trailing whitespace and lowercase
    return text.strip().lower()


def sanitize_metadata(meta: dict) -> dict:
    """
    Sanitize metadata fields: strip HTML, truncate overly long strings.
    """
    if not isinstance(meta, dict):
        return {}
    cleaned = {}
    for k, v in meta.items():
        if isinstance(v, str):
            v = re.sub(r"<[^>]+>", "", v).strip()
            v = v[:512]  # cap metadata field lengths
        cleaned[k] = v
    return cleaned


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_record(record: dict) -> dict:
    """Apply cleaning to the content and metadata fields of a single record."""
    record = dict(record)  # shallow copy

    content = record.get("content", {})

    # Store raw content if not already stored
    if record.get("raw") is None:
        if isinstance(content, str):
            record["raw"] = content
        elif isinstance(content, dict):
            record["raw"] = " | ".join(
                f"{k}: {v}" for k, v in content.items() if v is not None
            )
        else:
            record["raw"] = str(content)

    # Clean content depending on type
    if isinstance(content, dict):
        # Clean each string value in the structured dict
        record["content"] = {
            k: clean_text(v) if isinstance(v, str) else v
            for k, v in content.items()
        }
    elif isinstance(content, str):
        record["content"] = clean_text(content)
    else:
        record["content"] = content

    # Fill null metadata values
    meta = record.get("metadata", {}) or {}
    for key in ("title", "author", "date", "url", "file_name"):
        if meta.get(key) is None:
            meta[key] = None
        elif isinstance(meta[key], str):
            meta[key] = meta[key].strip() or None

    record["metadata"] = sanitize_metadata(meta)
    return record


def _exact_dedup(records: list[dict]) -> list[dict]:
    """Remove exact duplicates based on the `content` field using pandas."""
    if not records:
        return records
    import json as _json

    def _content_key(r):
        c = r.get("content", "")
        if isinstance(c, dict):
            return _json.dumps(c, sort_keys=True, ensure_ascii=False, default=str)
        return str(c)

    df = pd.DataFrame(records)
    df["_content_key"] = [_content_key(r) for r in records]
    df = df.drop_duplicates(subset=["_content_key"], keep="first")
    df = df.drop(columns=["_content_key"])
    return df.to_dict(orient="records")


def _fuzzy_dedup(
    records: list[dict], threshold: int = 90
) -> list[dict]:
    """
    Remove near-duplicate records using rapidfuzz similarity.
    For structured dict content, compares serialized JSON strings.
    O(n^2) — suitable for moderate dataset sizes.
    """
    if not records or not HAS_RAPIDFUZZ:
        return records

    import json as _json

    def _to_text(r):
        c = r.get("content", "")
        if isinstance(c, dict):
            return _json.dumps(c, sort_keys=True, ensure_ascii=False, default=str)
        return str(c)

    keep_indices: list[int] = []
    contents = [_to_text(r) for r in records]

    for i, content in enumerate(contents):
        is_dup = False
        for kept_idx in keep_indices:
            score = fuzz.ratio(content, contents[kept_idx])
            if score >= threshold:
                is_dup = True
                break
        if not is_dup:
            keep_indices.append(i)

    return [records[i] for i in keep_indices]
