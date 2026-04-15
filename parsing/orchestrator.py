"""
parsing.orchestrator — Dispatches CrawlResults to the appropriate parser.
"""

from __future__ import annotations

from crawling.base import CrawlResult
from utils.logging import get_logger
from .base import AbstractParser, ParsedDocument
from .html_parser import HTMLParser
from .document_parser import DocumentParser

logger = get_logger(__name__)


class ParsingOrchestrator:
    """
    Selects the right parser for each CrawlResult based on content type
    and runs parsing, skipping failed or empty crawls.
    """

    def __init__(self) -> None:
        self._parsers: list[AbstractParser] = [
            HTMLParser(),
            DocumentParser(),
        ]

    def run(self, crawl_results: list[CrawlResult]) -> list[ParsedDocument]:
        """
        Parse all successful crawl results.

        Failed crawls (status_code >= 400 or empty content) are logged
        and skipped — they don't abort the pipeline.
        """
        docs: list[ParsedDocument] = []

        for result in crawl_results:
            if not result.is_success or not result.content:
                logger.debug(
                    "parsing.skipped",
                    url=result.url,
                    reason="failed_crawl" if not result.is_success else "empty_content",
                )
                continue

            parser = self._select_parser(result.content_type)
            if parser is None:
                logger.warning("parsing.no_parser", url=result.url, content_type=result.content_type)
                continue

            try:
                doc = parser.parse(result.content, result.url, result.company_id)
                docs.append(doc)
            except Exception as exc:
                logger.error("parsing.error", url=result.url, error=str(exc))

        return docs

    def _select_parser(self, content_type: str) -> AbstractParser | None:
        for parser in self._parsers:
            if parser.can_parse(content_type):
                return parser
        return None
