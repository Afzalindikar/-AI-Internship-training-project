"""
extractors/pdf_extractor.py
---------------------------
Extracts text and tables from PDF files.
Primary: pdfplumber for digital PDFs.
OCR Fallback: pdf2image + pytesseract for scanned PDFs.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from pdf2image import convert_from_path
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

from extractors.base import BaseExtractor


class PDFExtractor(BaseExtractor):
    """Extracts content from PDF files (text-based and scanned)."""

    def supports(self, source_type: str) -> bool:
        return source_type == "pdf"

    def extract(self, source: str, config: dict) -> list[dict]:
        """
        Extract text from a PDF, one record per page.

        Args:
            source : Path to a .pdf file
            config : Pipeline config (enable_ocr, pdf.language, pdf.dpi)

        Returns:
            List of record dicts, one per page
        """
        if not HAS_PDFPLUMBER:
            raise ImportError("pdfplumber is required for PDFExtractor.")

        enable_ocr = config.get("enable_ocr", True)
        pdf_cfg = config.get("pdf", {})
        language = pdf_cfg.get("language", "eng")
        dpi = pdf_cfg.get("dpi", 300)

        file_name = Path(source).name
        pdf_meta = self._get_pdf_metadata(source)

        records = []
        full_text = []
        full_tables = []
        
        with pdfplumber.open(source) as pdf:
            total_pages = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                tables_text = self._extract_tables(page)

                # OCR fallback for image/scanned pages
                if not text.strip() and enable_ocr and HAS_OCR:
                    text = self._ocr_page(source, page_num, language, dpi)

                if text.strip():
                    full_text.append(text.strip())
                if tables_text.strip():
                    full_tables.append(tables_text.strip())

            combined_text = "\n\n".join(full_text)
            combined_tables = "\n\n".join(full_tables)
            
            combined_raw = combined_text
            if combined_tables:
                combined_raw += "\n\nTables:\n" + combined_tables
            
            content = {
                "text": combined_text.strip() or None,
                "tables": combined_tables.strip() or None,
                "total_pages": total_pages,
            }
            
            records.append({
                "source": "pdf",
                "content": content,
                "metadata": {
                    "title": pdf_meta.get("title") or Path(source).stem,
                    "author": pdf_meta.get("author"),
                    "date": pdf_meta.get("date"),
                    "url": None,
                    "file_name": file_name,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "source_type": "pdf",
                    "total_pages": total_pages,
                },
                "raw": combined_raw,
            })

        if not records:
            # Nothing extracted — try full OCR if available
            if enable_ocr and HAS_OCR:
                records = self._ocr_full_pdf(source, language, dpi, file_name, pdf_meta)

        return records

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _get_pdf_metadata(path: str) -> dict:
        """Read PDF document metadata via pdfplumber."""
        try:
            with pdfplumber.open(path) as pdf:
                info = pdf.metadata or {}
                return {
                    "title": info.get("Title") or info.get("/Title"),
                    "author": info.get("Author") or info.get("/Author"),
                    "date": info.get("CreationDate") or info.get("/CreationDate"),
                }
        except Exception:
            return {}

    @staticmethod
    def _extract_tables(page) -> str:
        """Extract tables from a pdfplumber page as plain text."""
        try:
            tables = page.extract_tables()
            if not tables:
                return ""
            rows_text = []
            for table in tables:
                for row in table:
                    cells = [str(c).strip() if c else "" for c in row]
                    rows_text.append(" | ".join(cells))
            return "\n".join(rows_text)
        except Exception:
            return ""

    @staticmethod
    def _ocr_page(pdf_path: str, page_num: int, language: str, dpi: int) -> str:
        """OCR a single page of a PDF using pytesseract."""
        try:
            images = convert_from_path(
                pdf_path,
                dpi=dpi,
                first_page=page_num,
                last_page=page_num,
            )
            if images:
                return pytesseract.image_to_string(images[0], lang=language)
        except Exception:
            pass
        return ""

    @staticmethod
    def _ocr_full_pdf(
        pdf_path: str, language: str, dpi: int, file_name: str, pdf_meta: dict
    ) -> list[dict]:
        """OCR every page of a PDF and return one record per page."""
        try:
            images = convert_from_path(pdf_path, dpi=dpi)
        except Exception:
            return []

        records = []
        full_text = []
        for page_num, image in enumerate(images, start=1):
            text = pytesseract.image_to_string(image, lang=language).strip()
            if text:
                full_text.append(text)
                
        combined_text = "\n\n".join(full_text)
        if combined_text:
            content = {
                "text": combined_text,
                "tables": None,
                "total_pages": len(images),
            }
            records.append({
                "source": "pdf",
                "content": content,
                "metadata": {
                    "title": pdf_meta.get("title") or Path(pdf_path).stem,
                    "author": pdf_meta.get("author"),
                    "date": pdf_meta.get("date"),
                    "url": None,
                    "file_name": file_name,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "source_type": "pdf",
                    "total_pages": len(images),
                },
                "raw": combined_text,
            })
        return records
