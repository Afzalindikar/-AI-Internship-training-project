"""
extractors/db_extractor.py
---------------------------
Extracts data from databases using SQLAlchemy.
Auto-discovers tables via reflection; supports configurable table list.
"""

from datetime import datetime, timezone

try:
    from sqlalchemy import create_engine, inspect, text
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

from extractors.base import BaseExtractor


class DBExtractor(BaseExtractor):
    """Extracts records from SQL databases via SQLAlchemy."""

    def supports(self, source_type: str) -> bool:
        return source_type == "database"

    def extract(self, source: str, config: dict) -> list[dict]:
        """
        Connect to a database and extract all (or configured) tables.

        Args:
            source : SQLAlchemy-compatible DB URI
                     e.g. sqlite:///path/to/db.sqlite
                          postgresql://user:pass@host/dbname
            config : Pipeline config (db.tables for table filter)

        Returns:
            List of record dicts, one per row across all tables
        """
        if not HAS_SQLALCHEMY:
            raise ImportError("sqlalchemy is required for DBExtractor.")

        db_cfg = config.get("db", {})
        table_filter: list[str] = db_cfg.get("tables", [])

        engine = create_engine(source)
        inspector = inspect(engine)
        available_tables = inspector.get_table_names()

        # Apply table filter if configured
        tables_to_extract = (
            [t for t in table_filter if t in available_tables]
            if table_filter
            else available_tables
        )

        extracted_at = datetime.now(timezone.utc).isoformat()
        records = []

        with engine.connect() as conn:
            for table_name in tables_to_extract:
                try:
                    rows = conn.execute(text(f"SELECT * FROM {table_name}")).fetchall()
                    columns = inspector.get_columns(table_name)
                    col_names = [c["name"] for c in columns]

                    for row in rows:
                        row_dict = dict(zip(col_names, row))

                        # Structured content: all column key-value pairs as dict
                        content = {
                            str(k).strip().lower().replace(" ", "_"): v
                            for k, v in row_dict.items()
                        }
                        raw = " | ".join(
                            f"{k}: {v}" for k, v in row_dict.items() if v is not None
                        )

                        records.append({
                            "source": "database",
                            "content": content,       # structured dict
                            "metadata": {
                                "title": table_name,
                                "author": None,
                                "date": None,
                                "url": None,
                                "file_name": source,
                                "extracted_at": extracted_at,
                                "source_type": "database",
                                "table": table_name,
                            },
                            "raw": raw,
                        })
                except Exception as exc:
                    # Log table-level errors but continue with other tables
                    records.append({
                        "source": "database",
                        "content": {},
                        "metadata": {
                            "title": table_name,
                            "author": None,
                            "date": None,
                            "url": None,
                            "file_name": source,
                            "extracted_at": extracted_at,
                            "source_type": "database",
                            "table": table_name,
                        },
                        "raw": "",
                        "failed": True,
                        "error": str(exc),
                    })

        engine.dispose()
        return records
