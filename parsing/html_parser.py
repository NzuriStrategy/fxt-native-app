"""
parsing.html_parser — BeautifulSoup-based parser for web pages.

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

from utils.logging import get_logger
from .base import AbstractParser, ParsedDocument

logger = get_logger(__name__)


class HTMLParser(AbstractParser):
    """
    Extracts clean body text from HTML pages.

    Strategy (planned):
    1. Parse with BeautifulSoup (lxml backend for speed)
    2. Remove <nav>, <footer>, <header>, <script>, <style> tags
    3. Extract <main> or largest text-density block as body
    4. Identify page type from URL path and meta tags
    5. Run lightweight keyword scan for fast signal hints
    """

    supported_content_types = ["text/html", "application/xhtml"]

    def parse(self, content: str, url: str, company_id: str) -> ParsedDocument:
        """
        TODO: Implement HTML parsing with BeautifulSoup.

        Pseudocode:
          soup = BeautifulSoup(content, "lxml")
          [tag.decompose() for tag in soup(["nav","footer","script","style"])]
          body_text = soup.get_text(separator=" ", strip=True)
          title = soup.title.string if soup.title else None
          ...
          return ParsedDocument(company_id=company_id, source_url=url,
                                body_text=body_text, title=title, ...)
        """
        raise NotImplementedError
