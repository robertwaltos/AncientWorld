"""
Database initialization for two-stage harvesting system.

Creates SQLite database with:
- candidates table (discovered image URLs + metadata)
- stats table (tracks total downloaded bytes for 500GB cap)
- Proper indexes for efficient queries
"""

import sqlite3
from pathlib import Path

# Configure paths - change E: drive if needed
DB_PATH = Path(r"E:\ancientgeo\db\assets.sqlite3")

def main():
    """Initialize the database schema."""
    print("Initializing AncientWorld database...")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)

    # Enable WAL mode for better concurrent access
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")

    # Candidates table - stores discovered image URLs before download
    con.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        query TEXT,
        title TEXT,
        page_url TEXT,
        image_url TEXT NOT NULL,
        width INTEGER,
        height INTEGER,
        mime TEXT,
        sha1 TEXT,
        license TEXT,
        artist TEXT,
        credit TEXT,
        date TEXT,
        institution TEXT,
        description TEXT,
        categories_json TEXT,

        status TEXT NOT NULL DEFAULT 'pending',
        http_status INTEGER,
        content_length INTEGER,
        downloaded_bytes INTEGER,
        local_path TEXT,
        error TEXT,

        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    );
    """)

    # Unique constraint on source + URL (prevent duplicate discoveries)
    con.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_candidates_unique_url
    ON candidates(source, image_url);
    """)

    # Index on status for efficient batch selection
    con.execute("""
    CREATE INDEX IF NOT EXISTS idx_candidates_status
    ON candidates(status);
    """)

    # Index on source and query
    con.execute("""
    CREATE INDEX IF NOT EXISTS idx_candidates_source_query
    ON candidates(source, query);
    """)

    # Stats table - tracks download progress
    con.execute("""
    CREATE TABLE IF NOT EXISTS stats (
        k TEXT PRIMARY KEY,
        v INTEGER NOT NULL
    );
    """)

    # Initialize total downloaded bytes counter
    con.execute("INSERT OR IGNORE INTO stats(k, v) VALUES ('total_downloaded_bytes', 0);")
    con.execute("INSERT OR IGNORE INTO stats(k, v) VALUES ('total_files_downloaded', 0);")

    # Analysis results table
    con.execute("""
    CREATE TABLE IF NOT EXISTS analysis_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id INTEGER NOT NULL,
        analysis_type TEXT NOT NULL,
        results_json TEXT NOT NULL,
        confidence REAL,
        processing_time REAL,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (candidate_id) REFERENCES candidates(id)
    );
    """)

    con.execute("""
    CREATE INDEX IF NOT EXISTS idx_analysis_candidate
    ON analysis_results(candidate_id);
    """)

    con.commit()
    con.close()

    print(f"✓ Database initialized at {DB_PATH}")
    print(f"  - candidates table: ready for discovery")
    print(f"  - stats table: tracking enabled")
    print(f"  - analysis_results table: ready for processed data")

if __name__ == "__main__":
    main()
