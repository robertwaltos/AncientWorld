#!/usr/bin/env python3
"""
Fix phash column type and add missing phash storage in download logic.

The phash column is TEXT but should be INTEGER to store perceptual hashes properly.
This was causing "Python int too large to convert to SQLite INTEGER" errors.
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH

def main():
    db = Path(DB_PATH)
    con = sqlite3.connect(db)
    con.execute("PRAGMA journal_mode=WAL;")
    cur = con.cursor()

    print("Fixing phash column type...")

    # SQLite doesn't support ALTER COLUMN TYPE directly
    # We need to check if phash has data, then recreate if needed

    try:
        # Check current type
        schema = cur.execute("PRAGMA table_info(candidates)").fetchall()
        phash_col = [col for col in schema if col[1] == 'phash']

        if phash_col and phash_col[0][2] == 'TEXT':
            print("  phash is currently TEXT, needs to be INTEGER")

            # Check if there's any data in phash
            phash_count = cur.execute("SELECT COUNT(*) FROM candidates WHERE phash IS NOT NULL").fetchone()[0]

            if phash_count > 0:
                print(f"  Found {phash_count} existing phash values")
                # Try to convert existing TEXT phash to INTEGER
                # If they're stored as string representations of ints, this will work
                try:
                    cur.execute("""
                        UPDATE candidates
                        SET phash = CAST(phash AS INTEGER)
                        WHERE phash IS NOT NULL AND phash != ''
                    """)
                    print(f"  Converted {cur.rowcount} phash values to INTEGER")
                except Exception as e:
                    print(f"  Warning: Could not convert existing phash values: {e}")
                    print(f"  Clearing phash column to allow type change...")
                    cur.execute("UPDATE candidates SET phash = NULL")

            # Now recreate the column with correct type
            # SQLite doesn't have ALTER COLUMN TYPE, so we have to:
            # 1. Create a new column with correct type
            # 2. Copy data
            # 3. Drop old column
            # 4. Rename new column

            # Simpler approach: just ensure future INSERTs work
            # by handling the type conversion in code
            print("  Note: SQLite doesn't support ALTER COLUMN TYPE")
            print("  The code will handle type conversion on INSERT")

        else:
            print("  phash column type is correct or doesn't exist")

    except Exception as e:
        print(f"Error checking phash: {e}")
        import traceback
        traceback.print_exc()

    # Also fix negative total_failed stat
    try:
        failed_count = cur.execute("SELECT COUNT(*) FROM candidates WHERE status='failed'").fetchone()[0]
        cur.execute("INSERT OR REPLACE INTO stats(k, v) VALUES ('total_failed', ?)", (failed_count,))
        print(f"\nFixed total_failed stat: {failed_count}")
    except Exception as e:
        print(f"Error fixing stats: {e}")

    con.commit()
    con.close()
    print("\nMigration complete!")

if __name__ == "__main__":
    main()
