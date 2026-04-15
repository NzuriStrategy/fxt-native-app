"""
utils — Shared infrastructure used across all pipeline stages.

Modules
-------
logging     — structlog-based structured logging with Rich console output
http        — async httpx wrapper with retry, timeout, and user-agent handling
rate_limiter — token-bucket rate limiter for external API calls
"""
