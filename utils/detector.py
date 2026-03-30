"""
utils/detector.py
-----------------
Automatically detects the source type of an input and validates / sanitizes it.
Supported types: url, pdf, csv, excel, database
"""

import re
from pathlib import Path
from urllib.parse import urlparse


# ── Allowed DB schemes ────────────────────────────────────────────────────────
ALLOWED_DB_SCHEMES = {"sqlite", "postgresql", "mysql", "mariadb", "mssql"}

# ── Allowed URL schemes ───────────────────────────────────────────────────────
ALLOWED_URL_SCHEMES = {"http", "https"}

# ── Max input length ──────────────────────────────────────────────────────────
MAX_INPUT_LENGTH = 2048


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_source_type(source: str) -> str:
    """
    Detect the source type from the input string.

    Returns one of: "url", "pdf", "csv", "excel", "database"

    Raises:
        ValueError: If the source is invalid, unsafe, or unrecognized
    """
    source = _sanitize_input(source)

    # 1. Database URI check
    if _is_database_uri(source):
        return "database"

    # 2. URL check
    if _is_url(source):
        return "url"

    # 3. File extension check
    path = Path(source)
    ext = path.suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext == ".csv":
        return "csv"
    if ext in {".xlsx", ".xls", ".xlsm", ".ods"}:
        return "excel"

    raise ValueError(
        f"Cannot detect source type for: '{source}'. "
        "Supported: HTTP/HTTPS URLs, .pdf, .csv, .xlsx, SQLAlchemy URIs."
    )


def validate_source(source: str, source_type: str) -> str:
    """
    Security-validate the source depending on its type.

    Returns the sanitized source string.
    Raises ValueError on unsafe inputs.
    """
    source = _sanitize_input(source)

    if source_type == "url":
        _validate_url(source)

    elif source_type in {"pdf", "csv", "excel"}:
        _validate_file_path(source)

    elif source_type == "database":
        _validate_db_uri(source)

    return source


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sanitize_input(source: str) -> str:
    """Strip whitespace, null bytes, and control characters."""
    if not isinstance(source, str):
        raise ValueError("Source must be a string.")
    if len(source) > MAX_INPUT_LENGTH:
        raise ValueError(
            f"Source string exceeds maximum length of {MAX_INPUT_LENGTH} characters."
        )
    # Remove null bytes and ASCII control characters (except tabs/newlines)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", source)
    return cleaned.strip()


def _is_url(source: str) -> bool:
    """Return True if source looks like an HTTP/HTTPS URL."""
    try:
        parsed = urlparse(source)
        return parsed.scheme in ALLOWED_URL_SCHEMES and bool(parsed.netloc)
    except Exception:
        return False


def _is_database_uri(source: str) -> bool:
    """Return True if source looks like a SQLAlchemy DB URI."""
    pattern = r"^(" + "|".join(ALLOWED_DB_SCHEMES) + r")[+a-z]*://"
    return bool(re.match(pattern, source, re.IGNORECASE))


def _validate_url(source: str) -> None:
    """Validate a URL for safety."""
    parsed = urlparse(source)
    if parsed.scheme not in ALLOWED_URL_SCHEMES:
        raise ValueError(
            f"Unsafe URL scheme '{parsed.scheme}'. Only http/https are allowed."
        )
    if not parsed.netloc:
        raise ValueError(f"Invalid URL (missing host): '{source}'")


def _validate_file_path(source: str) -> None:
    """Validate file path — prevent path traversal."""
    try:
        resolved = Path(source).resolve()
    except Exception as exc:
        raise ValueError(f"Invalid file path: {exc}")

    if not resolved.exists():
        raise FileNotFoundError(f"File not found: '{source}'")

    # Prevent traversal outside working dir (if relative path was given)
    if not source.startswith(("/", "\\")) and ".." in Path(source).parts:
        raise ValueError(f"Path traversal detected in: '{source}'")


def _validate_db_uri(source: str) -> None:
    """Validate DB URI against the allowed scheme allowlist."""
    pattern = r"^(" + "|".join(ALLOWED_DB_SCHEMES) + r")[+a-z]*://"
    if not re.match(pattern, source, re.IGNORECASE):
        allowed = ", ".join(ALLOWED_DB_SCHEMES)
        raise ValueError(
            f"Unsupported database URI scheme. Allowed: {allowed}. Got: '{source}'"
        )
