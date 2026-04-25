"""
SQLite-compatible schema.

Uses INTEGER PRIMARY KEY AUTOINCREMENT for users (SQLite-native),
TEXT for everything else. UUIDs are stored as TEXT.
"""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    created_at      TEXT DEFAULT (datetime('now')),
    source_doc_name TEXT,
    source_doc_text TEXT,
    status          TEXT DEFAULT 'pending',
    iteration_count INTEGER DEFAULT 0,
    result_json     TEXT,
    error_message   TEXT
);
"""
