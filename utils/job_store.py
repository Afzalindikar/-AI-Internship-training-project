"""
utils/job_store.py
------------------
Persistent job tracking backed by a JSON file (output/jobs.json).
Job data survives application restarts.

Each job record:
    {
        "job_id":     str,
        "status":     "PENDING|RUNNING|SUCCESS|FAILED",
        "source":     str | list,
        "created_at": ISO 8601,
        "updated_at": ISO 8601,
        "record_count": int,
        "output_paths": dict,
        "errors":     list[str]
    }
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class PersistentJobStore:
    """
    Thread-safe persistent job store backed by a JSON file.

    Usage:
        store = PersistentJobStore("output/jobs.json")
        store.create(job_id, source)
        store.update(job_id, status="RUNNING")
        job = store.get(job_id)
        all_jobs = store.all()
    """

    def __init__(self, path: str = "output/jobs.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._cache: dict[str, dict] = self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def create(self, job_id: str, source: Any = None) -> dict:
        """Create a new PENDING job record."""
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "job_id": job_id,
            "status": "PENDING",
            "source": source,
            "created_at": now,
            "updated_at": now,
            "record_count": 0,
            "output_paths": {},
            "errors": [],
            "results": [],
        }
        with self._lock:
            self._cache[job_id] = record
            self._flush()
        return record

    def update(self, job_id: str, **kwargs) -> dict:
        """
        Update fields of an existing job.
        Automatically sets `updated_at` to now.
        """
        with self._lock:
            if job_id not in self._cache:
                # Auto-create if missing (e.g. crash recovery)
                self._cache[job_id] = {
                    "job_id": job_id,
                    "status": "UNKNOWN",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            self._cache[job_id].update(kwargs)
            self._cache[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._flush()
        return self._cache[job_id]

    def get(self, job_id: str) -> Optional[dict]:
        """Return a job record by ID, or None if not found."""
        with self._lock:
            return self._cache.get(job_id)

    def all(self) -> list[dict]:
        """Return all job records as a list."""
        with self._lock:
            return list(self._cache.values())

    def exists(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._cache

    # ── Internals ─────────────────────────────────────────────────────────────

    def _load(self) -> dict:
        """Load existing jobs from file."""
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return {j["job_id"]: j for j in data if "job_id" in j}
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, KeyError):
                pass
        return {}

    def _flush(self) -> None:
        """Write current cache to disk (must be called within lock)."""
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(list(self._cache.values()), f, indent=2,
                          ensure_ascii=False, default=str)
        except Exception:
            pass  # Never crash the pipeline over logging


# Module-level default instance (lazy-init via function)
_DEFAULT_STORE: Optional[PersistentJobStore] = None


def get_job_store(output_dir: str = "output") -> PersistentJobStore:
    """Get or create the default persistent job store."""
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = PersistentJobStore(
            path=str(Path(output_dir) / "jobs.json")
        )
    return _DEFAULT_STORE
