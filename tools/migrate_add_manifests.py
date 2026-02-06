"""
Add manifests table for IIIF sources.

This table stores IIIF manifest URLs that will be processed
to extract individual image URLs.
"""

import sqlite3
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH


def main():
    """Add manifests table to database."""
    print("=" * 60)
    print("Adding IIIF Manifests Table")
    print("=" * 60)

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("ERROR: Database not found. Run init_database.py first.")
        return 1

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")

    # Create manifests table
    con.execute("""
    CREATE TABLE IF NOT EXISTS manifests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        query TEXT,
        record_url TEXT,
        manifest_url TEXT NOT NULL,
        title TEXT,
        metadata_json TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        error TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    );
    """)

    # Create indexes
    con.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_manifests_unique
        ON manifests(source, manifest_url);
    """)
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_manifests_status
        ON manifests(status);
    """)

    con.commit()
    con.close()

    print("\n[SUCCESS] Manifests table added successfully!")
    print("  - manifests table created")
    print("  - Indexes created")
    print("\nReady for IIIF harvesting!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
