"""
parsing.base — Abstract contract for content parsers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ParsedDocument:
    """
    Structured, clean content extracted from a single CrawlResult.

    Downstream signal detectors work entirely on ParsedDocument objects —
    they never touch raw HTML. This separation makes signal detectors
    independently testable with synthetic documents.
    """

    company_id: str
    source_url: str

    # Clean body text, boilerplate removed
    body_text: str

    # Document title / headline (if detectable)
    title: str | None = None

    # Publication or "last updated" date (if present on the page)
    published_at: datetime | None = None

    # Content classification (e.g. "careers", "press_release", "about")
    page_type: str | None = None

    # Named entities extracted during parsing
    mentioned_companies: list[str] = field(default_factory=list)
    mentioned_locations: list[str] = field(default_factory=list)

    # Raw keyword hits found during parsing (for fast signal matching)
    keyword_hits: list[str] = field(default_factory=list)

    parsed_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def word_count(self) -> int:
        return len(self.body_text.split())


class AbstractParser(ABC):
    """
    Base class for content parsers.

    Parsers accept a CrawlResult (raw content) and produce a ParsedDocument
    (clean, structured content). They must not perform I/O — any external
    calls (e.g. NER models) should be initialised in __init__ and reused.
    """

    # MIME types this parser handles (used by ParsingOrchestrator for dispatch)
    supported_content_types: list[str] = []

    @abstractmethod
    def parse(self, content: str, url: str, company_id: str) -> ParsedDocument:
        """
        Parse `content` and return a structured ParsedDocument.

        Parameters
        ----------
        content:
            Raw page content (HTML string or document text).
        url:
            Source URL, carried through for provenance.
        company_id:
            Company this content belongs to.
        """
        ...

    def can_parse(self, content_type: str) -> bool:
        """Return True if this parser handles the given MIME type."""
        return any(ct in content_type for ct in self.supported_content_types)


class ParserError(Exception):
    """Raised when a parser cannot process the given content."""
