"""
extractors/web_extractor.py
---------------------------
Extracts text and metadata from web pages using BeautifulSoup.
Falls back to Playwright for JavaScript-heavy pages (if configured).
"""

from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from extractors.base import BaseExtractor


class WebExtractor(BaseExtractor):
    """Extracts content from HTTP/HTTPS URLs."""

    def supports(self, source_type: str) -> bool:
        return source_type == "url"

    def extract(self, source: str, config: dict) -> list[dict]:
        """
        Fetch a web page and extract title, headings, paragraphs, tables, links.

        Args:
            source : HTTP/HTTPS URL
            config : Pipeline config (web.timeout, web.use_playwright)

        Returns:
            List with a single record dict per page
        """
        web_cfg = config.get("web", {})
        timeout = web_cfg.get("timeout", 15)
        use_playwright = web_cfg.get("use_playwright", False)
        user_agent = web_cfg.get(
            "user_agent",
            "Mozilla/5.0 (compatible; DataExtractionEngine/1.0)"
        )

        if not HAS_REQUESTS:
            raise ImportError("requests and beautifulsoup4 are required for WebExtractor.")

        html = self._fetch_html(source, timeout, user_agent, use_playwright)
        return [self._parse_html(html, source)]

    # ── Fetching ──────────────────────────────────────────────────────────────

    def _fetch_html(
        self,
        url: str,
        timeout: int,
        user_agent: str,
        use_playwright: bool,
    ) -> str:
        """Fetch HTML from a URL, with optional Playwright fallback."""
        if use_playwright:
            return self._fetch_with_playwright(url, timeout)
        return self._fetch_with_requests(url, timeout, user_agent)

    @staticmethod
    def _fetch_with_requests(url: str, timeout: int, user_agent: str) -> str:
        headers = {"User-Agent": user_agent}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
        return response.text

    @staticmethod
    def _fetch_with_playwright(url: str, timeout: int) -> str:
        """
        Use Playwright (headless Chromium) to fetch JS-rendered pages.
        Playwright must be installed and `playwright install` run beforehand.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "playwright is required for use_playwright=true. "
                "Install it: pip install playwright && playwright install"
            )
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=timeout * 1000)
            page.wait_for_load_state("networkidle")
            html = page.content()
            browser.close()
        return html

    # ── Parsing ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_html(html: str, url: str) -> dict:
        """Parse HTML into a structured record."""
        soup = BeautifulSoup(html, "lxml")

        # Remove script/style noise
        for tag in soup(["script", "style", "noscript", "iframe"]):
            tag.decompose()

        # Title
        title = soup.title.string.strip() if soup.title else ""

        # Meta tags
        author = _meta(soup, "author") or _meta(soup, "dc.creator")
        date = (
            _meta(soup, "date")
            or _meta(soup, "article:published_time")
            or _meta(soup, "publishedDate")
        )

        # Content extraction
        headings = [
            h.get_text(strip=True)
            for h in soup.find_all(["h1", "h2", "h3", "h4"])
        ]
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]

        # Tables
        tables_text = []
        for table in soup.find_all("table"):
            rows = []
            for row in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in row.find_all(["th", "td"])]
                if any(cells):
                    rows.append(" | ".join(cells))
            if rows:
                tables_text.append("\n".join(rows))

        # Links
        links = [
            a.get("href", "")
            for a in soup.find_all("a", href=True)
            if a.get("href", "").startswith("http")
        ][:50]  # cap at 50 links

        content_raw_parts = []
        if title:
            content_raw_parts.append(f"Title: {title}")
        if headings:
            content_raw_parts.append("Headings: " + " | ".join(headings))
        content_raw_parts.extend(paragraphs)
        if tables_text:
            content_raw_parts.append("Tables:\n" + "\n\n".join(tables_text))

        raw = "\n".join(content_raw_parts)

        # Structured content dict
        content = {
            "title": title or None,
            "headings": headings or [],
            "paragraphs": paragraphs or [],
            "tables": tables_text or [],
            "links": links or [],
        }

        return {
            "source": "web",
            "content": content,          # structured dict
            "metadata": {
                "title": title or None,
                "author": author or None,
                "date": date or None,
                "url": url,
                "file_name": None,
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "source_type": "web",
            },
            "raw": raw,
        }


def _meta(soup, name: str) -> Optional[str]:
    """Extract a meta tag value by name or property."""
    tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
    return tag.get("content", "").strip() if tag else None
