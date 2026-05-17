CREATE TABLE IF NOT EXISTS rss_feeds (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    source_name TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_checked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS news_articles (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_feed_id BIGINT REFERENCES rss_feeds(id) ON DELETE SET NULL,
    source_name TEXT,
    title TEXT,
    url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    url_hash TEXT NOT NULL UNIQUE,
    rss_guid TEXT,
    author TEXT,
    published_at TIMESTAMPTZ,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    parsed_at TIMESTAMPTZ,
    parse_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (parse_status IN ('pending', 'parsed', 'failed', 'skipped')),
    parse_error TEXT,
    html TEXT,
    text TEXT,
    top_image_url TEXT,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS news_articles_feed_guid_unique
    ON news_articles(source_feed_id, rss_guid)
    WHERE rss_guid IS NOT NULL;

CREATE INDEX IF NOT EXISTS news_articles_published_idx
    ON news_articles(published_at DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS news_articles_parse_status_idx
    ON news_articles(parse_status, discovered_at);

CREATE TABLE IF NOT EXISTS article_parse_attempts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    article_id BIGINT NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('success', 'failed')),
    error TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS article_ai_analyses (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    article_id BIGINT NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
    provider TEXT NOT NULL DEFAULT 'deepseek',
    model TEXT NOT NULL,
    tickers TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    companies TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    sectors TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    event_type TEXT,
    market_sentiment TEXT CHECK (
        market_sentiment IN ('positive', 'negative', 'neutral', 'mixed')
    ),
    market_significance NUMERIC(3,2)
        CHECK (market_significance >= 0 AND market_significance <= 1),
    macroeconomic_themes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    affected_industries TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    potential_winners TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    potential_losers TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    summary TEXT,
    raw_response JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(article_id, provider, model)
);

CREATE INDEX IF NOT EXISTS article_ai_analyses_tickers_gin
    ON article_ai_analyses USING gin(tickers);

CREATE INDEX IF NOT EXISTS article_ai_analyses_sentiment_idx
    ON article_ai_analyses(market_sentiment, market_significance DESC);
