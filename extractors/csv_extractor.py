"""
extractors/csv_extractor.py
---------------------------
Extracts data from CSV and Excel files using pandas.
Supports chunked reading for large files.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

from extractors.base import BaseExtractor


class CSVExtractor(BaseExtractor):
    """Extracts records from CSV and Excel files."""

    def supports(self, source_type: str) -> bool:
        return source_type in {"csv", "excel"}

    def extract(self, source: str, config: dict) -> list[dict]:
        """
        Read a CSV or Excel file and return one record per row.

        Args:
            source : Path to .csv or .xlsx/.xls file
            config : Pipeline config (batch_size used as chunksize)

        Returns:
            List of record dicts, one per data row
        """
        if not HAS_PANDAS:
            raise ImportError("pandas is required for CSVExtractor.")

        file_name = Path(source).name
        ext = Path(source).suffix.lower()
        source_type = "excel" if ext in {".xlsx", ".xls", ".xlsm", ".ods"} else "csv"
        chunk_size = config.get("batch_size", 1000)

        extracted_at = datetime.now(timezone.utc).isoformat()
        records = []

        if source_type == "excel":
            # Excel doesn't support chunked reading natively
            df = pd.read_excel(source, engine="openpyxl")
            records = self._df_to_records(df, source_type, file_name, extracted_at)
        else:
            # Chunked CSV reading for large files
            try:
                for chunk in pd.read_csv(
                    source,
                    chunksize=chunk_size,
                    encoding="utf-8",
                    on_bad_lines="skip",
                ):
                    records.extend(
                        self._df_to_records(chunk, source_type, file_name, extracted_at)
                    )
            except UnicodeDecodeError:
                # Try latin-1 as fallback
                for chunk in pd.read_csv(
                    source,
                    chunksize=chunk_size,
                    encoding="latin-1",
                    on_bad_lines="skip",
                ):
                    records.extend(
                        self._df_to_records(chunk, source_type, file_name, extracted_at)
                    )

        return records

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _df_to_records(
        df: "pd.DataFrame",
        source_type: str,
        file_name: str,
        extracted_at: str,
    ) -> list[dict]:
        """
        Convert a DataFrame to a list of schema-compatible record dicts.
        Each row becomes one record with a structured dict `content`.
        """
        # Replace NaN with None for JSON compatibility
        df = df.where(pd.notna(df), other=None)

        records = []
        for _, row in df.iterrows():
            row_dict = row.to_dict()

            # Structured content: key-value pairs with regex-normalised keys
            # Removes special chars, keeps only alphanumerics + underscores
            content = {
                _normalize_column(str(k)): v
                for k, v in row_dict.items()
            }
            # Raw flat text for LLM formatting
            raw = " | ".join(
                f"{k}: {v}" for k, v in row_dict.items() if v is not None
            )

            records.append({
                "source": source_type,
                "content": content,       # structured dict
                "metadata": {
                    "title": None,
                    "author": None,
                    "date": None,
                    "url": None,
                    "file_name": file_name,
                    "extracted_at": extracted_at,
                    "source_type": source_type,
                },
                "raw": raw,
            })

        return records


def _normalize_column(col: str) -> str:
    """
    Normalize a CSV column name to a consistent snake_case identifier.
    - Strip leading/trailing whitespace
    - Lowercase
    - Replace spaces, hyphens, dots with underscores
    - Remove any remaining special characters (keep alphanumeric + _)
    - Collapse multiple underscores
    """
    import re
    col = col.strip().lower()
    col = re.sub(r"[\s\-\.]+", "_", col)      # spaces/hyphens/dots → _
    col = re.sub(r"[^a-z0-9_]", "", col)       # remove special chars
    col = re.sub(r"_+", "_", col).strip("_")   # collapse repeated _
    return col or "field"                        # fallback if empty
