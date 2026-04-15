"""
parsing — Extract structured content from raw HTML and documents.

Responsibilities
----------------
- Accept CrawlResult objects containing raw page content
- Strip boilerplate (nav, footer, ads) and extract main body text
- Identify named entities (company names, locations, monetary figures)
- Normalise dates and produce ParsedDocument objects

Two parsers are provided:
  HTMLParser     — BeautifulSoup-based parser for web pages
  DocumentParser — handles PDFs and Word docs (press releases, annual reports)

The ParsingOrchestrator dispatches to the correct parser based on content type.
"""

from .base import AbstractParser, ParsedDocument
from .orchestrator import ParsingOrchestrator

__all__ = [
    "AbstractParser",
    "ParsedDocument",
    "ParsingOrchestrator",
]
