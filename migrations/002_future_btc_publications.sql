CREATE TABLE IF NOT EXISTS future_btc_signal_publications (
    event_id TEXT PRIMARY KEY,
    state TEXT NOT NULL CHECK(state IN (
        'received', 'publication_pending', 'published',
        'retryable_failure', 'permanent_failure', 'weekly_limited')),
    discord_message_id TEXT,
    first_publication_attempt TEXT,
    last_publication_attempt TEXT,
    published_at TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count <= 6),
    safe_error_code TEXT,
    FOREIGN KEY (event_id) REFERENCES future_btc_signal_events(event_id)
);
