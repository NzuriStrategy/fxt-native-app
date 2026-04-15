-- ====================================================================
-- FXT Lead Intelligence Pipeline — PostgreSQL Schema
-- ====================================================================
-- Apply once against a fresh database:
--   psql -d lead_intelligence -f storage/schema.sql
--
-- For changes after the initial deploy, generate Alembic migrations:
--   poetry run alembic revision --autogenerate -m "describe change"
--   poetry run alembic upgrade head
-- ====================================================================


-- ====================================================================
-- ENUM TYPES
-- ====================================================================

-- Ingestion origin: where did we first hear about this company?
CREATE TYPE source_type AS ENUM (
    'news_feed',
    'job_board',
    'company_registry'
);

-- All detectable signal types (mirrors signals.base.SignalType).
-- Adding a new signal requires: ALTER TYPE signal_type_enum ADD VALUE '...'
-- followed by a new Alembic migration.
CREATE TYPE signal_type_enum AS ENUM (
    'warehouse_expansion_mentioned',
    'densification_keyword',
    'sku_growth_mentioned',
    'wms_evaluation',
    'capacity_constraint_mentioned',
    'logistics_hiring_surge',
    'vp_supply_chain_hire',
    'warehouse_ops_hiring',
    'new_lease_signed',
    'dc_construction_mentioned',
    'third_party_logistics'
);

-- LLM-assigned confidence class (mirrors ai.base.ConfidenceClass)
CREATE TYPE confidence_class AS ENUM ('HIGH', 'MEDIUM', 'LOW');

-- CRM workflow state for a lead
CREATE TYPE lead_status AS ENUM (
    'new',          -- Just qualified; not yet reviewed
    'contacted',    -- Outreach initiated
    'disqualified', -- Reviewed and rejected
    'converted',    -- Became a real opportunity
    'snoozed'       -- Revisit later (see snoozed_until)
);

-- Score tier bucket
CREATE TYPE lead_tier AS ENUM ('HOT', 'WARM', 'COOL', 'COLD');


-- ====================================================================
-- companies
-- ====================================================================
-- Canonical company master record.  Every other table references
-- companies.id.  domain is the stable dedup key — two ingestion sources
-- mentioning the same domain are the same company.

CREATE TABLE companies (
    id              BIGSERIAL       PRIMARY KEY,

    -- Business key. Nullable because a company may be discovered from a
    -- news mention before we have resolved its website.
    domain          TEXT            UNIQUE,

    name            TEXT            NOT NULL,
    industry        TEXT,
    employee_count  INTEGER,
    hq_city         TEXT,
    hq_country      CHAR(2),        -- ISO 3166-1 alpha-2 (e.g. 'US', 'DE')

    -- Catch-all for source-specific metadata (LinkedIn ID, Clearbit slug, etc.)
    extra           JSONB           NOT NULL DEFAULT '{}',

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Full-text search on company name (useful for dedup UI and admin lookup)
CREATE INDEX idx_companies_name_fts
    ON companies USING GIN (to_tsvector('english', name));

CREATE INDEX idx_companies_industry   ON companies (industry);
CREATE INDEX idx_companies_hq_country ON companies (hq_country);


-- ====================================================================
-- sources
-- ====================================================================
-- One row per ingestion event (news article, job posting, registry entry).
-- content_hash is the primary dedup key: the same article is never stored
-- twice regardless of which run fetched it.

CREATE TABLE sources (
    id              BIGSERIAL       PRIMARY KEY,
    company_id      BIGINT          NOT NULL
                        REFERENCES companies (id) ON DELETE CASCADE,
    source_type     source_type     NOT NULL,

    -- Friendly provider label: 'newsapi.org', 'linkedin', 'apollo.io'
    source_name     TEXT            NOT NULL,
    source_url      TEXT,

    -- SHA-256 of normalised source content.  Primary dedup key.
    content_hash    CHAR(64)        NOT NULL,

    -- Key excerpt surfaced to signal detectors without loading raw_content
    snippet         TEXT,
    -- Full raw content kept for re-processing if detection logic changes
    raw_content     TEXT,

    published_at    TIMESTAMPTZ,
    ingested_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Dedup: same article from any source is stored exactly once
CREATE UNIQUE INDEX uidx_sources_content_hash ON sources (content_hash);

CREATE INDEX idx_sources_company_id   ON sources (company_id);
CREATE INDEX idx_sources_source_type  ON sources (source_type);
CREATE INDEX idx_sources_published_at ON sources (published_at DESC NULLS LAST);
CREATE INDEX idx_sources_ingested_at  ON sources (ingested_at DESC);


-- ====================================================================
-- pages
-- ====================================================================
-- One row per crawled URL.  Upserted on every re-crawl using
-- ON CONFLICT (url).  A changed content_hash triggers re-parsing
-- (body_text updated) and re-running signal detection.
--
-- Lifecycle of a page row:
--   1. Crawled  → content_hash set, body_text NULL
--   2. Parsed   → body_text populated
--   3. Re-crawl → if content_hash unchanged: only crawled_at updated,
--                 body_text and signals untouched (no-op re-parse)

CREATE TABLE pages (
    id              BIGSERIAL       PRIMARY KEY,
    company_id      BIGINT          NOT NULL
                        REFERENCES companies (id) ON DELETE CASCADE,
    url             TEXT            NOT NULL,

    -- SHA-256 of the raw HTTP response body.
    -- Unchanged hash → content not modified → skip re-parse.
    content_hash    CHAR(64)        NOT NULL,

    status_code     SMALLINT        NOT NULL,
    content_type    TEXT,

    -- Set by the parsing stage: 'careers', 'press_room', 'investor_relations', 'about', …
    page_type       TEXT,

    -- Clean body text extracted by the parser.  NULL means not yet parsed.
    body_text       TEXT,

    js_rendered     BOOLEAN         NOT NULL DEFAULT FALSE,

    -- created_at: first time this URL was crawled (immutable)
    -- crawled_at: updated on every re-crawl regardless of content change
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    crawled_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- URL is the natural dedup key for pages
CREATE UNIQUE INDEX uidx_pages_url ON pages (url);

CREATE INDEX idx_pages_company_id   ON pages (company_id);
CREATE INDEX idx_pages_content_hash ON pages (content_hash);
CREATE INDEX idx_pages_page_type    ON pages (page_type);
CREATE INDEX idx_pages_crawled_at   ON pages (crawled_at DESC);

-- Partial index used by the parsing worker to find pending pages efficiently
CREATE INDEX idx_pages_unparsed
    ON pages (company_id, crawled_at DESC)
    WHERE body_text IS NULL AND status_code = 200;


-- ====================================================================
-- signals
-- ====================================================================
-- One detected signal per (company, signal_type, origin).
-- Origin is XOR: a signal comes from EITHER a crawled page OR an
-- ingestion source — never both, never neither.
--
-- Dedup: (company, signal_type, page) and (company, signal_type, source)
-- are unique.  If the same signal fires twice for the same document,
-- keep the highest-confidence row via ON CONFLICT … DO UPDATE.

CREATE TABLE signals (
    id              BIGSERIAL           PRIMARY KEY,
    company_id      BIGINT              NOT NULL
                        REFERENCES companies (id) ON DELETE CASCADE,

    -- XOR origin — exactly one must be non-NULL
    page_id         BIGINT              REFERENCES pages   (id) ON DELETE CASCADE,
    source_id       BIGINT              REFERENCES sources (id) ON DELETE CASCADE,

    signal_type     signal_type_enum    NOT NULL,
    confidence      REAL                NOT NULL
                        CHECK (confidence >= 0.0 AND confidence <= 1.0),
    evidence_snippet TEXT,
    detected_at     TIMESTAMPTZ         NOT NULL DEFAULT NOW(),

    -- Enforces XOR: (page_id IS NULL) XOR (source_id IS NULL) must be true
    CONSTRAINT chk_signals_xor_origin
        CHECK ((page_id IS NULL) != (source_id IS NULL))
);

-- Dedup indexes — partial so they cover only the relevant branch
CREATE UNIQUE INDEX uidx_signals_company_page_type
    ON signals (company_id, signal_type, page_id)
    WHERE page_id IS NOT NULL;

CREATE UNIQUE INDEX uidx_signals_company_source_type
    ON signals (company_id, signal_type, source_id)
    WHERE source_id IS NOT NULL;

CREATE INDEX idx_signals_company_id      ON signals (company_id);
CREATE INDEX idx_signals_signal_type     ON signals (signal_type);
CREATE INDEX idx_signals_confidence      ON signals (confidence DESC);
CREATE INDEX idx_signals_detected_at     ON signals (detected_at DESC);

-- Composite used by the scoring query (group by company, filter by recency)
CREATE INDEX idx_signals_company_detected
    ON signals (company_id, detected_at DESC);


-- ====================================================================
-- ai_assessments
-- ====================================================================
-- One row per company; updated in place on re-assessment.
-- score_at_assessment records the pipeline score when the LLM was called
-- so that stale assessments (score has since drifted significantly) can be
-- detected and refreshed without re-assessing every company.

CREATE TABLE ai_assessments (
    id                  BIGSERIAL           PRIMARY KEY,
    company_id          BIGINT              NOT NULL UNIQUE
                            REFERENCES companies (id) ON DELETE CASCADE,
    model_used          TEXT                NOT NULL,
    confidence_class    confidence_class    NOT NULL,
    narrative_summary   TEXT                NOT NULL,
    outreach_angle      TEXT                NOT NULL,
    score_at_assessment REAL                NOT NULL,
    prompt_tokens       INTEGER             NOT NULL DEFAULT 0,
    completion_tokens   INTEGER             NOT NULL DEFAULT 0,
    assessed_at         TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    -- NULL means the assessment does not expire
    expires_at          TIMESTAMPTZ
);

CREATE INDEX idx_ai_assessments_confidence ON ai_assessments (confidence_class);
CREATE INDEX idx_ai_assessments_assessed   ON ai_assessments (assessed_at DESC);

-- Partial index for the refresh worker: find assessments past their TTL
CREATE INDEX idx_ai_assessments_stale
    ON ai_assessments (company_id, assessed_at)
    WHERE expires_at IS NOT NULL AND expires_at < NOW();


-- ====================================================================
-- lead_queue
-- ====================================================================
-- Pipeline output surface. One row per qualified company; updated in
-- place as scores and CRM statuses change.
--
-- top_signals (TEXT[]) is a deliberately denormalized summary of the
-- three highest-weight signal types detected.  Avoids a JOIN to the
-- signals table on every list-view query.

CREATE TABLE lead_queue (
    id              BIGSERIAL       PRIMARY KEY,
    company_id      BIGINT          NOT NULL UNIQUE
                        REFERENCES companies (id) ON DELETE CASCADE,

    -- NULL when --skip-ai is used or assessment has not yet been run
    assessment_id   BIGINT
                        REFERENCES ai_assessments (id) ON DELETE SET NULL,

    score           REAL            NOT NULL
                        CHECK (score >= 0.0 AND score <= 100.0),
    tier            lead_tier       NOT NULL,
    status          lead_status     NOT NULL DEFAULT 'new',
    signal_count    SMALLINT        NOT NULL DEFAULT 0,

    -- Denormalized: top 3 signal_type values by weight, for quick display
    top_signals     TEXT[]          NOT NULL DEFAULT '{}',

    qualified_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    last_scored_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- Set when status = 'snoozed'; NULL otherwise
    snoozed_until   TIMESTAMPTZ
);

CREATE INDEX idx_lead_queue_score          ON lead_queue (score DESC);
CREATE INDEX idx_lead_queue_tier           ON lead_queue (tier);
CREATE INDEX idx_lead_queue_status         ON lead_queue (status);
CREATE INDEX idx_lead_queue_last_scored    ON lead_queue (last_scored_at DESC);

-- Hot path: sales dashboard shows active leads ordered by score
CREATE INDEX idx_lead_queue_active_score
    ON lead_queue (score DESC)
    WHERE status NOT IN ('disqualified', 'converted');


-- ====================================================================
-- TRIGGERS
-- ====================================================================

-- Keeps companies.updated_at current automatically on any UPDATE
CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
