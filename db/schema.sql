CREATE TABLE IF NOT EXISTS ohlcv (
    id          BIGSERIAL PRIMARY KEY,
    ticker      TEXT        NOT NULL,
    open        NUMERIC     NOT NULL,
    high        NUMERIC     NOT NULL,
    low         NUMERIC     NOT NULL,
    close       NUMERIC     NOT NULL,
    volume      BIGINT      NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL,
    timeframe   TEXT        NOT NULL DEFAULT '1Min',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ticker, timestamp, timeframe)
);

CREATE TABLE IF NOT EXISTS llm_analysis (
    id              BIGSERIAL   PRIMARY KEY,
    tickers         TEXT[]      NOT NULL,
    sentiment       TEXT        NOT NULL,
    raw_object_key  TEXT        NOT NULL,
    event_timestamp TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feature_vectors (
    id                   BIGSERIAL   PRIMARY KEY,
    ticker               TEXT        NOT NULL,
    snapshot_timestamp   TIMESTAMPTZ NOT NULL,
    prediction_horizon   TEXT        NOT NULL,  -- '1h', '4h', '1d', etc.
    features             JSONB       NOT NULL,
    actual_pct_change    NUMERIC,               -- null until reconciled
    predicted_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prediction_logs (
    id                   BIGSERIAL PRIMARY KEY,
    feature_vector_id    BIGINT    NOT NULL REFERENCES feature_vectors(id),
    ticker               TEXT      NOT NULL,
    model_version        TEXT      NOT NULL,
    predicted_pct_change NUMERIC   NOT NULL,
    derived_direction    TEXT      NOT NULL CHECK (derived_direction IN ('bullish', 'bearish')),
    actual_pct_change    NUMERIC,               -- filled by reconciliation job
    error                NUMERIC,               -- predicted minus actual
    predicted_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at          TIMESTAMPTZ            -- null until reconciled
);

