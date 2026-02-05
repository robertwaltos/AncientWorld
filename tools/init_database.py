"""
Database initialization for two-stage harvesting system.

Creates SQLite database with proper schema for 500GB corpus management.
"""

import sqlite3
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH, LARGE_STORAGE_ROOT

def main():
    """Initialize the database schema."""
    print("Initializing AncientWorld two-stage harvesting database...")
    print(f"Storage root: {LARGE_STORAGE_ROOT}")
    print(f"Database: {DB_PATH}")

    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(db_path)

    # Enable WAL mode for better concurrent access
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")

    # Candidates table - stores discovered image URLs before download
    con.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINC REMENT,
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
        sha256_local TEXT,
        phash TEXT,
        error TEXT,

        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    );
    """)

    # Indexes
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_candidates_unique_url ON candidates(source, image_url);")
    con.execute("CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);")
    con.execute("CREATE INDEX IF NOT EXISTS idx_candidates_source_query ON candidates(source, query);")
    con.execute("CREATE INDEX IF NOT EXISTS idx_candidates_sha256 ON candidates(sha256_local);")
    con.execute("CREATE INDEX IF NOT EXISTS idx_candidates_phash ON candidates(phash);")

    # Stats table
    con.execute("""
    CREATE TABLE IF NOT EXISTS stats (
        k TEXT PRIMARY KEY,
        v INTEGER NOT NULL
    );
    """)

    con.execute("INSERT OR IGNORE INTO stats(k, v) VALUES ('total_downloaded_bytes', 0);")
    con.execute("INSERT OR IGNORE INTO stats(k, v) VALUES ('total_files_downloaded', 0);")
    con.execute("INSERT OR IGNORE INTO stats(k, v) VALUES ('total_candidates', 0);")
    con.execute("INSERT OR IGNORE INTO stats(k, v) VALUES ('total_failed', 0);")
    con.execute("INSERT OR IGNORE INTO stats(k, v) VALUES ('total_skipped', 0);")

    # Analysis results
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

    con.execute("CREATE INDEX IF NOT EXISTS idx_analysis_candidate ON analysis_results(candidate_id);")
    con.execute("CREATE INDEX IF NOT EXISTS idx_analysis_type ON analysis_results(analysis_type);")

    con.commit()
    con.close()

    print(f"\n✓ Database initialized successfully!")
    print(f"  Location: {db_path}")
    print(f"  Tables created:")
    print(f"    - candidates (discovered URLs)")
    print(f"    - stats (download tracking)")
    print(f"    - analysis_results (processed data)")
    print(f"\nReady for discovery phase!")

if __name__ == "__main__":
    main()
