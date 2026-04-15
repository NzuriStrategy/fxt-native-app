"""
parsing.document_parser — Parser for PDFs and Office documents.

Handles press releases and annual/quarterly reports that are often
distributed as PDFs from investor relations pages.

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

from utils.logging import get_logger
from .base import AbstractParser, ParsedDocument

logger = get_logger(__name__)


class DocumentParser(AbstractParser):
    """
    Extracts text from PDF and Word documents.

    Strategy (planned):
    1. Detect file type from content_type header
    2. PDF: use pdfminer.six or pypdf for text extraction
    3. DOCX: use python-docx
    4. Clean extracted text (remove headers/footers, fix encoding artifacts)
    5. Return as ParsedDocument with page_type="document"
    """

    supported_content_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument",
        "application/msword",
    ]

    def parse(self, content: str, url: str, company_id: str) -> ParsedDocument:
        """
        TODO: Implement PDF/DOCX text extraction.
        """
        raise NotImplementedError
