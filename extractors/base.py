"""
extractors/base.py
------------------
Abstract base class for all extractors.
Defines the plug-and-play interface every extractor must implement.
"""

from abc import ABC, abstractmethod


class BaseExtractor(ABC):
    """
    Abstract base extractor.

    To add a new extractor (e.g., for JSON, XML, API, S3):
        1. Subclass BaseExtractor
        2. Implement `extract()` and `supports()`
        3. Register in pipeline/orchestrator.py EXTRACTOR_REGISTRY

    That's it — no other changes needed in the pipeline.
    """

    @abstractmethod
    def extract(self, source: str, config: dict) -> list[dict]:
        """
        Extract data from the given source.

        Args:
            source : File path, URL, or DB URI
            config : Full pipeline config dict

        Returns:
            List of raw record dicts.
            Each dict should have at minimum:
                - "source"   : source type string
                - "content"  : extracted text
                - "metadata" : dict with title, author, date, url,
                               file_name, extracted_at, source_type
        """

    @abstractmethod
    def supports(self, source_type: str) -> bool:
        """
        Return True if this extractor handles the given source type.

        Args:
            source_type : One of "url", "pdf", "csv", "excel", "database"
        """
