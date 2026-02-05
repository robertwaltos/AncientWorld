import sqlite3
from pathlib import Path

DB_PATH = Path(r"E:\ancientgeo\db\assets.sqlite3")

def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")

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

        status TEXT NOT NULL DEFAULT 'pending',  -- pending|downloading|downloaded|failed|skipped
        http_status INTEGER,
        content_length INTEGER,
        downloaded_bytes INTEGER,
        local_path TEXT,
        error TEXT,

        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    );
    """)

    con.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_candidates_unique_url
    ON candidates(source, image_url);
    """)

    con.execute("""
    CREATE INDEX IF NOT EXISTS idx_candidates_status
    ON candidates(status);
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS stats (
        k TEXT PRIMARY KEY,
        v INTEGER NOT NULL
    );
    """)

    # Track total bytes downloaded across runs
    con.execute("INSERT OR IGNORE INTO stats(k, v) VALUES ('total_downloaded_bytes', 0);")
    con.commit()
    con.close()
    print(f"Initialized DB at {DB_PATH}")

if __name__ == "__main__":
    main()
