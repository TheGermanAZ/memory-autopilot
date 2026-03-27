CREATE TABLE IF NOT EXISTS caller_profiles (
    caller_id           TEXT PRIMARY KEY,
    customer_name       TEXT NOT NULL DEFAULT '',
    issue_summary       TEXT NOT NULL DEFAULT '',
    issue_type          TEXT NOT NULL DEFAULT '',
    order_id            TEXT NOT NULL DEFAULT '',
    customer_sentiment  TEXT NOT NULL DEFAULT '',
    open_actions        TEXT NOT NULL DEFAULT '',
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memory_snapshots (
    conversation_id     TEXT PRIMARY KEY,
    caller_id           TEXT NOT NULL REFERENCES caller_profiles(caller_id),
    agent_id            TEXT,
    source              TEXT NOT NULL,
    data_collection     JSONB NOT NULL,
    transcript_summary  TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_snapshots_caller
    ON memory_snapshots (caller_id, created_at DESC);
