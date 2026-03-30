"""
utils/schema.py
---------------
Strict unified data schema with strong validation.
All extractors must return records conforming to this schema.

Schema:
    {
        "id":       str (UUID4),
        "source":   "web|pdf|csv|excel|database",
        "content":  dict  (structured key-value pairs),
        "metadata": {
            "title", "author", "date", "url",
            "file_name", "extracted_at", "source_type"
        },
        "raw":      str | None,
        "failed":   bool,
        "error":    str | None
    }
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from utils.logger import get_logger
    _logger = get_logger("schema")
except Exception:
    import logging
    _logger = logging.getLogger("schema")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_SOURCES = {"web", "pdf", "csv", "excel", "database", "unknown"}

REQUIRED_FIELDS = {"id", "source", "content", "metadata"}

REQUIRED_METADATA_FIELDS = {
    "title", "author", "date", "url",
    "file_name", "extracted_at", "source_type",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Metadata:
    """Metadata block attached to every extracted record."""
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    url: Optional[str] = None
    file_name: Optional[str] = None
    extracted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source_type: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "author": self.author,
            "date": self.date,
            "url": self.url,
            "file_name": self.file_name,
            "extracted_at": self.extracted_at,
            "source_type": self.source_type,
        }


@dataclass
class SchemaRecord:
    """
    Unified schema record.

    `content` is now a structured dict (key-value pairs) instead of a flat string.
    `raw` preserves the original pre-cleaning text for LLM formatting.
    """
    source: str
    content: dict          # ← structured dict
    metadata: Metadata
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    raw: Optional[str] = None
    failed: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "content": self.content,
            "metadata": self.metadata.to_dict(),
            "raw": self.raw,
            "failed": self.failed,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_record(record: dict) -> bool:
    """
    Validate a record dict against the unified schema.

    Checks:
        - Required top-level fields exist
        - 'source' is in VALID_SOURCES
        - 'content' is a dict
        - 'metadata' is a dict with all required sub-fields

    Args:
        record: Dict to validate

    Returns:
        True if valid, False otherwise (errors are logged)
    """
    valid = True

    # 1. Required top-level fields
    for f in REQUIRED_FIELDS:
        if f not in record:
            _logger.warning(f"[SCHEMA] Missing required field: '{f}'")
            valid = False

    # 2. Source value
    source = record.get("source", "")
    if source not in VALID_SOURCES:
        _logger.warning(f"[SCHEMA] Invalid source value: '{source}'")
        valid = False

    # 3. Content must be a non-empty dict
    content = record.get("content")
    if content is None:
        _logger.warning("[SCHEMA] 'content' field is None")
        valid = False
    elif not isinstance(content, dict):
        _logger.warning(
            f"[SCHEMA] 'content' must be a dict, got {type(content).__name__}"
        )
        valid = False
    elif len(content) == 0:
        _logger.warning("[SCHEMA] 'content' dict is empty — record may have no data")
        # Not fatal — empty content is allowed (e.g. blank pages in PDFs)

    # 4. Metadata must be a non-None dict with all required sub-fields
    meta = record.get("metadata")
    if meta is None or not isinstance(meta, dict):
        _logger.warning("[SCHEMA] 'metadata' must be a dict — found None or wrong type")
        valid = False
    else:
        for mf in REQUIRED_METADATA_FIELDS:
            if mf not in meta:
                _logger.warning(f"[SCHEMA] Missing metadata field: '{mf}'")
                valid = False

    return valid


def validate_and_normalize(record: dict) -> dict:
    """
    Validate and auto-correct a record to conform to the unified schema.

    Missing fields are filled with safe defaults instead of raising errors.
    Logs a warning for every corrected field.

    Args:
        record: Raw dict from extractor / cleaner

    Returns:
        Normalised dict conforming to schema
    """
    record = dict(record)  # shallow copy

    # ── id ────────────────────────────────────────────────────────────────────
    if not record.get("id"):
        record["id"] = str(uuid.uuid4())

    # ── source ────────────────────────────────────────────────────────────────
    source = str(record.get("source", "unknown")).lower().strip()
    if source not in VALID_SOURCES:
        _logger.warning(f"[SCHEMA] Unknown source '{source}', defaulting to 'unknown'")
        source = "unknown"
    record["source"] = source

    # ── content → must be dict ────────────────────────────────────────────────
    content = record.get("content")
    if content is None:
        record["content"] = {}
    elif isinstance(content, str):
        # Legacy string content → wrap in dict for backward compat
        record["content"] = {"text": content}
    elif not isinstance(content, dict):
        record["content"] = {"text": str(content)}

    # ── raw ───────────────────────────────────────────────────────────────────
    if record.get("raw") is None:
        # Build raw string from content dict for LLM formatting
        record["raw"] = _dict_to_text(record["content"])

    # ── metadata ──────────────────────────────────────────────────────────────
    meta = record.get("metadata")
    if not isinstance(meta, dict):
        _logger.warning("[SCHEMA] 'metadata' missing or not a dict — using defaults")
        meta = {}

    for mf in REQUIRED_METADATA_FIELDS:
        if mf not in meta:
            meta[mf] = None

    if not meta.get("extracted_at"):
        meta["extracted_at"] = datetime.now(timezone.utc).isoformat()

    if not meta.get("source_type"):
        meta["source_type"] = source

    record["metadata"] = meta

    # ── flags ─────────────────────────────────────────────────────────────────
    record.setdefault("failed", False)
    record.setdefault("error", None)

    # Final validation check (log only, don't raise)
    if not validate_record(record):
        _logger.warning(f"[SCHEMA] Record {record['id'][:8]} failed validation after normalization")

    return record


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dict_to_text(d: dict) -> str:
    """Convert a content dict to a flat key: value string for raw/LLM fields."""
    if not d:
        return ""
    return " | ".join(f"{k}: {v}" for k, v in d.items() if v is not None)
