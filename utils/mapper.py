"""
utils/mapper.py
---------------
SmartFieldMapper: maps heterogeneous field names to canonical unified keys
using a pre-defined alias dictionary and rapidfuzz fuzzy matching.

Key design decisions:
    - Mapping is applied ONLY to the "content" dict inside a record.
    - Critical schema keys (id, source, metadata, raw, failed, error)
      are NEVER remapped.
    - If two content keys map to the same canonical name, the first wins.
"""

import re
from typing import Optional

try:
    from rapidfuzz import process, fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False


# ---------------------------------------------------------------------------
# Protected schema keys — these must never be remapped
# ---------------------------------------------------------------------------

_PROTECTED_KEYS = frozenset({
    "id", "source", "metadata", "raw", "failed", "error",
    "content",  # the container key itself is not remapped
})


# ---------------------------------------------------------------------------
# Canonical field alias registry
# ---------------------------------------------------------------------------

FIELD_ALIASES: dict[str, list[str]] = {
    "name": [
        "full name", "fullname", "customer name", "client name",
        "username", "user name", "first name", "display name",
        "contact name", "person name", "fname", "given name",
    ],
    "last_name": [
        "last name", "lastname", "surname", "family name", "lname",
    ],
    "email": [
        "email address", "e-mail", "emailaddress", "mail",
        "contact email", "user email",
    ],
    "phone": [
        "telephone", "phone number", "mobile", "mobile number",
        "cell", "contact number", "tel",
    ],
    "address": [
        "street address", "mailing address", "home address",
        "shipping address", "billing address", "location",
    ],
    "city": ["town", "municipality", "locality"],
    "state": ["province", "region", "state/province"],
    "country": ["nation", "country name", "country code"],
    "zip_code": ["postal code", "postcode", "zip", "pincode", "pin"],
    "age": ["years old", "age group"],
    "gender": ["sex"],
    "dob": ["date of birth", "birth date", "birthday", "born on"],
    "company": [
        "organization", "organisation", "employer", "company name",
        "firm", "business", "enterprise",
    ],
    "job_title": [
        "title", "designation", "role", "position", "occupation",
        "profession",
    ],
    "salary": ["income", "pay", "wage", "compensation", "earnings", "annual income"],
    "price": ["cost", "amount", "fee", "rate", "charge"],
    "quantity": ["qty", "number of", "units"],
    "date": ["timestamp", "created at", "updated at", "record date", "entry date"],
    "description": ["details", "notes", "remarks", "comments", "info"],
    "record_id": ["identifier", "record id", "row id", "uid", "uuid", "no."],
    "url": ["link", "website", "web address", "href", "uri"],
}

# Build reverse lookup: alias → canonical
_REVERSE_MAP: dict[str, str] = {}
for _canonical, _aliases in FIELD_ALIASES.items():
    _REVERSE_MAP[_canonical] = _canonical
    for _alias in _aliases:
        _REVERSE_MAP[_alias.lower()] = _canonical


# ---------------------------------------------------------------------------
# SmartFieldMapper
# ---------------------------------------------------------------------------

class SmartFieldMapper:
    """
    Maps field names in a record's `content` dict to canonical unified keys.

    SCOPE: Only operates on record["content"]. Never touches top-level
    schema keys (id, source, metadata, raw, failed, error).
    """

    def __init__(self, fuzzy_threshold: int = 80):
        self.fuzzy_threshold = fuzzy_threshold
        self._all_aliases = list(_REVERSE_MAP.keys())

    def map_key(self, key: str) -> str:
        """
        Map a single content field name to its canonical form.
        Returns the original key if no mapping found.
        """
        normalized = key.lower().strip().replace("-", " ").replace("_", " ")

        # 1. Exact match
        if normalized in _REVERSE_MAP:
            return _REVERSE_MAP[normalized]

        # 2. Fuzzy match (if rapidfuzz available)
        if HAS_RAPIDFUZZ:
            result = process.extractOne(
                normalized,
                self._all_aliases,
                scorer=fuzz.ratio,
                score_cutoff=self.fuzzy_threshold,
            )
            if result:
                return _REVERSE_MAP[result[0]]

        return key  # No mapping found — keep original

    def map_content(self, content: dict) -> dict:
        """
        Remap keys inside a content dict to canonical forms.
        If two keys map to the same canonical name, the first wins.

        Args:
            content: The record's content dict (data fields only)

        Returns:
            New dict with canonicalised keys
        """
        if not isinstance(content, dict):
            return content  # non-dict content (e.g. string) passed through

        mapped: dict = {}
        for key, value in content.items():
            canonical = self.map_key(str(key))
            if canonical not in mapped:
                mapped[canonical] = value
        return mapped

    def map_record(self, record: dict) -> dict:
        """
        Apply field mapping ONLY to record["content"].
        All other top-level keys (id, source, metadata, raw, etc.) are
        passed through unchanged.

        Args:
            record: Full schema record dict

        Returns:
            Record with mapped content, unchanged schema keys
        """
        record = dict(record)  # shallow copy — never mutate in place
        content = record.get("content")
        if isinstance(content, dict):
            record["content"] = self.map_content(content)
        return record

    def map_records(self, records: list[dict]) -> list[dict]:
        """Apply map_record to a list of records."""
        return [self.map_record(r) for r in records]

    # ── Legacy compatibility ───────────────────────────────────────────────────
    def map_fields(self, record: dict) -> dict:
        """Alias for map_record (backward compatibility)."""
        return self.map_record(record)


# Module-level default instance
_DEFAULT_MAPPER = SmartFieldMapper()


def map_fields(record: dict) -> dict:
    """
    Map field names in record["content"] to canonical keys.
    Top-level schema keys are never touched.
    """
    return _DEFAULT_MAPPER.map_record(record)


def map_records(records: list[dict]) -> list[dict]:
    """Apply map_fields to a list of records."""
    return _DEFAULT_MAPPER.map_records(records)
