CREATE TABLE IF NOT EXISTS community_promotions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign TEXT NOT NULL,
    destination TEXT NOT NULL,
    promotion_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('reserved', 'delivered', 'retryable', 'permanent_failure')),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    discord_message_id TEXT,
    delivered_at TEXT,
    safe_error_code TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign, destination, promotion_date)
);

CREATE TABLE IF NOT EXISTS future_btc_signal_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    published_at TEXT NOT NULL,
    valid_until TEXT NOT NULL,
    received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
