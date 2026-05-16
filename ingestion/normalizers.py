"""
ingestion.normalizers — Pure functions for normalising raw company field values.

All functions are stateless and free of I/O so they can be tested in isolation
and reused across ingestors.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse


def normalize_domain(raw: str | None) -> str | None:
    """
    Return a bare, lower-case hostname (no scheme, no www., no trailing slash).

    Returns None for blank input, unparseable URLs, and strings that lack a
    dot (and are not 'localhost') — these cannot be valid public domains.

    Examples
    --------
    >>> normalize_domain("https://www.Acme.com/")
    'acme.com'
    >>> normalize_domain("www.example.co.uk")
    'example.co.uk'
    >>> normalize_domain("notadomain")   # no dot → None
    >>> normalize_domain(None)
    """
    if not raw or not raw.strip():
        return None

    raw = raw.strip()

    # Inject a scheme so urlparse can split host from path
    if not re.match(r"^https?://", raw, re.IGNORECASE):
        raw = "https://" + raw

    try:
        parsed = urlparse(raw)
        hostname = parsed.hostname  # lower-cased and port-stripped by urlparse
    except Exception:
        return None

    if not hostname:
        return None

    if hostname.startswith("www."):
        hostname = hostname[4:]

    if "." not in hostname and hostname != "localhost":
        return None

    return hostname


def normalize_company_name(raw: str | None) -> str | None:
    """
    Strip leading/trailing whitespace and collapse internal whitespace runs.

    Returns None for blank or whitespace-only input.
    """
    if not raw or not raw.strip():
        return None
    return " ".join(raw.split())
