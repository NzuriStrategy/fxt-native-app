# FXT Lead Intelligence Pipeline

A modular Python pipeline that automatically identifies companies likely
facing **warehouse densification constraints** — companies running out of
storage space and evaluating high-density racking, ASRS, or 3PL solutions.

---

## Why Poetry

This project uses [Poetry](https://python-poetry.org/) instead of a plain
`requirements.txt` for three reasons:

1. **Lock file** — `poetry.lock` pins every transitive dependency to an exact
   version, making builds fully reproducible across machines and CI.
2. **Dependency groups** — dev tools (pytest, mypy, ruff) are isolated from
   production deps in a single `pyproject.toml`, not two separate files.
3. **Virtualenv management** — `poetry install` creates and activates the venv
   automatically; no manual `python -m venv` dance.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    External Data Sources                         │
│  News APIs  │  Job Boards  │  Company Registries / CRM exports  │
└──────┬──────┴──────┬───────┴───────────────┬────────────────────┘
       │             │                        │
       ▼             ▼                        ▼
┌──────────────────────────────────────────────────┐
│  1. INGESTION                                     │
│  NewsFeedIngestor │ JobBoardIngestor │            │
│  CompanyRegistryIngestor                          │
│                                                  │
│  Output: list[RawCompanyRecord]                  │
└────────────────────────┬─────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│  2. CRAWLING                                      │
│  WebCrawler (httpx) │ SitemapCrawler              │
│                                                  │
│  Visits: careers page, press room, IR page,      │
│  news mentions, sitemap-discovered pages          │
│                                                  │
│  Output: list[CrawlResult]                       │
└────────────────────────┬─────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│  3. PARSING                                       │
│  HTMLParser (BeautifulSoup) │ DocumentParser      │
│  (PDFs, DOCX press releases)                      │
│                                                  │
│  Strips boilerplate, extracts body text,         │
│  identifies entities, produces keyword_hits      │
│                                                  │
│  Output: list[ParsedDocument]                    │
└────────────────────────┬─────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│  4. SIGNAL DETECTION                              │
│                                                  │
│  Warehouse signals    Employment signals          │
│  ─────────────────    ─────────────────          │
│  • densification      • logistics hiring surge   │
│    keywords           • VP Supply Chain hire     │
│  • expansion          • warehouse ops postings   │
│    mentions                                       │
│  • capacity           Real-estate signals        │
│    constraints        ─────────────────          │
│  • WMS evaluation     • new lease signed         │
│  • SKU growth         • DC construction          │
│                                                  │
│  Output: list[CompanySignalBundle]               │
└────────────────────────┬─────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│  5. SCORING                                       │
│  Weighted sum of signals × confidence × decay    │
│  Normalised to 0–100 composite score             │
│                                                  │
│  Tiers: HOT ≥80 │ WARM ≥60 │ COOL ≥40 │ COLD    │
│  Qualified = score ≥ SCORING__LEAD_THRESHOLD     │
│                                                  │
│  Output: list[ScoredLead]  (qualified only →)   │
└────────────────────────┬─────────────────────────┘
                         │  (qualified leads only)
                         ▼
┌──────────────────────────────────────────────────┐
│  6. AI ENRICHMENT (Anthropic Claude)              │
│  Per qualified lead:                             │
│  • Confidence classification: HIGH/MEDIUM/LOW    │
│  • Narrative summary (2–3 sentences)             │
│  • Recommended outreach angle                    │
│                                                  │
│  Prompt caching reduces cost for repeat runs     │
│  --skip-ai flag bypasses this stage              │
│                                                  │
│  Output: list[EnrichedLead]                      │
└────────────────────────┬─────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│  7. STORAGE (Postgres / SQLite)                   │
│  Tables: companies, leads, signal_results,       │
│  crawl_cache                                     │
│                                                  │
│  Idempotent upserts — re-running the pipeline    │
│  updates existing records, no duplicates         │
│  --dry-run flag skips all writes                 │
└──────────────────────────────────────────────────┘
```

---

## Project Structure

```
fxt-lead-intelligence/
├── main.py                   # Pipeline orchestrator & CLI entry point
├── config.py                 # Centralised settings (pydantic-settings)
├── pyproject.toml            # Poetry dependencies and tool config
├── .env.example              # Environment variable template
│
├── ingestion/                # Pull raw company data from external sources
│   ├── base.py               #   AbstractIngestor, RawCompanyRecord
│   ├── orchestrator.py       #   IngestionOrchestrator (source selection)
│   ├── news_feed.py          #   News API / RSS ingestor
│   ├── job_boards.py         #   Job board ingestor
│   └── company_registry.py   #   CSV / CRM / B2B database ingestor
│
├── crawling/                 # Fetch web pages for enrichment
│   ├── base.py               #   AbstractCrawler, CrawlResult, CrawlTarget
│   ├── orchestrator.py       #   CrawlingOrchestrator (target building)
│   ├── web_crawler.py        #   httpx-based async HTTP crawler
│   └── sitemap_crawler.py    #   sitemap.xml discovery + crawl
│
├── parsing/                  # Extract structured content from raw HTML/docs
│   ├── base.py               #   AbstractParser, ParsedDocument
│   ├── orchestrator.py       #   ParsingOrchestrator (content-type dispatch)
│   ├── html_parser.py        #   BeautifulSoup HTML parser
│   └── document_parser.py    #   PDF / DOCX parser
│
├── signals/                  # Domain-specific signal detectors
│   ├── base.py               #   AbstractSignal, SignalResult, CompanySignalBundle
│   ├── orchestrator.py       #   SignalOrchestrator (fan-out across all detectors)
│   ├── warehouse.py          #   Densification, expansion, capacity signals
│   ├── employment.py         #   Logistics hiring surge signals
│   └── real_estate.py        #   Lease and construction signals
│
├── scoring/                  # Aggregate signals into a 0–100 lead score
│   ├── base.py               #   ScoredLead
│   ├── scorer.py             #   Scorer (weighted + decayed aggregation)
│   └── weights.py            #   Per-signal-type weights and decay config
│
├── ai/                       # LLM enrichment via Anthropic Claude
│   ├── base.py               #   AbstractAIClient, EnrichedLead, ConfidenceClass
│   ├── orchestrator.py       #   AIEnrichmentOrchestrator (batching)
│   ├── classifier.py         #   LeadClassifier (prompt + response parsing)
│   └── enricher.py           #   AnthropicClient (SDK wrapper + caching)
│
├── storage/                  # Persist results to Postgres / SQLite
│   ├── base.py               #   AbstractRepository
│   ├── models.py             #   SQLAlchemy ORM models
│   └── repository.py         #   LeadRepository (idempotent upserts)
│
└── utils/                    # Shared infrastructure
    ├── logging.py            #   structlog setup (JSON prod / Rich dev)
    ├── http.py               #   httpx wrapper with retry + size guard
    └── rate_limiter.py       #   Async token-bucket rate limiter
```

---

## Data Flow (Summary)

```
External sources
    → RawCompanyRecord          (ingestion)
    → CrawlResult               (crawling)
    → ParsedDocument            (parsing)
    → CompanySignalBundle       (signals)
    → ScoredLead                (scoring)
    → EnrichedLead              (ai)
    → DB rows                   (storage)
```

Each stage consumes the output of the previous stage as plain Python
dataclass objects. No stage writes to the database — only
`storage.LeadRepository` does. This means every stage is independently
unit-testable by constructing synthetic input objects.

---

## Quickstart

```bash
# 1. Install dependencies
poetry install

# Install Playwright browsers (needed for JS-rendered pages)
poetry run playwright install chromium

# 2. Configure environment
cp .env.example .env
# Edit .env: set DATABASE__URL and AI__ANTHROPIC_API_KEY

# 3. Run the pipeline
poetry run python main.py --source all

# Skip AI enrichment (faster, no API cost)
poetry run python main.py --skip-ai

# Dry run — no database writes
poetry run python main.py --dry-run

# Process only 10 companies (useful for testing)
poetry run python main.py --limit 10

# Run a single source
poetry run python main.py --source news
```

---

## Configuration Reference

All settings are environment variables (or `.env` keys), grouped by stage:

| Variable | Default | Description |
|---|---|---|
| `ENV` | `development` | `development` or `production` |
| `LOG_LEVEL` | `INFO` | Python log level |
| `DATABASE__URL` | `sqlite:///./lead_intelligence.db` | SQLAlchemy connection URL |
| `DATABASE__ECHO_SQL` | `false` | Log all SQL queries |
| `AI__ANTHROPIC_API_KEY` | _(required)_ | Anthropic API key |
| `AI__DEFAULT_MODEL` | `claude-sonnet-4-6` | Claude model to use |
| `CRAWLING__MAX_CONCURRENT_REQUESTS` | `10` | Async crawl concurrency |
| `CRAWLING__REQUEST_TIMEOUT_SECONDS` | `30` | Per-request timeout |
| `INGESTION__NEWS_API_KEY` | _(optional)_ | newsapi.org key |
| `SCORING__LEAD_THRESHOLD` | `60.0` | Minimum score to qualify a lead |

---

## Signal Weights

Signal weights are defined in `scoring/weights.py`. Higher weight = stronger
predictor of warehouse densification need. All weights are normalised
internally — only relative magnitudes matter.

| Signal | Weight | Rationale |
|---|---|---|
| `DENSIFICATION_KEYWORD` | 10 | Industry-specific language, very high precision |
| `CAPACITY_CONSTRAINT_MENTIONED` | 9 | Explicit operational pain |
| `WMS_EVALUATION` | 8 | Active tech evaluation = buying mode |
| `WAREHOUSE_EXPANSION_MENTIONED` | 7 | Footprint growing, needs optimisation |
| `VP_SUPPLY_CHAIN_HIRE` | 7 | Leadership change = strategy re-evaluation |
| `SKU_GROWTH_MENTIONED` | 6 | More SKUs → more space needed |
| `LOGISTICS_HIRING_SURGE` | 5 | Scaling operations |
| `NEW_LEASE_SIGNED` | 5 | At a space decision point |
| `THIRD_PARTY_LOGISTICS` | 4 | Evaluating external solutions |
| `WAREHOUSE_OPS_HIRING` | 4 | Operational growth |
| `DC_CONSTRUCTION_MENTIONED` | 3 | Long lead time, early pipeline |

---

## Adding a New Signal

1. Add a new `SignalType` value to `signals/base.py`
2. Create a detector class in the appropriate `signals/*.py` file
3. Add a weight to `scoring/weights.py`
4. Register the detector in `signals/orchestrator.py::ALL_DETECTORS`

---

## Adding a New Ingestion Source

1. Subclass `AbstractIngestor` in a new file under `ingestion/`
2. Set `source_name` and implement `fetch()`
3. Register the class in `ingestion/orchestrator.py::_SOURCE_MAP`

---

## Development

```bash
# Lint and format
poetry run ruff check . --fix
poetry run ruff format .

# Type check
poetry run mypy .

# Run tests
poetry run pytest --cov
```
