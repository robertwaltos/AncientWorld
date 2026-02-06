"""
Reset failed downloads back to pending status for retry.

This allows re-attempting downloads that failed due to rate limiting
or temporary network issues.
"""

import sqlite3
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH


def main():
    """Reset failed downloads to pending."""
    print("="*60)
    print("Retry Failed Downloads")
    print("="*60)

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("ERROR: Database not found.")
        return 1

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")

    # Count current failed downloads
    (failed_count,) = con.execute(
        "SELECT COUNT(*) FROM candidates WHERE status='failed'"
    ).fetchone()

    print(f"\nFound {failed_count} failed downloads")

    if failed_count == 0:
        print("No failed downloads to retry.")
        con.close()
        return 0

    # Show error breakdown
    print("\nError types:")
    error_types = con.execute("""
        SELECT
            CASE
                WHEN error LIKE '%429%' THEN 'Rate Limiting (429)'
                WHEN error LIKE '%timeout%' THEN 'Timeout'
                WHEN error LIKE '%404%' OR http_status = 404 THEN '404 Not Found'
                WHEN error LIKE '%403%' OR http_status = 403 THEN '403 Forbidden'
                WHEN error LIKE '%500%' OR http_status >= 500 THEN 'Server Error'
                WHEN error LIKE '%Connection%' THEN 'Connection Error'
                ELSE 'Other'
            END as error_type,
            COUNT(*) as count
        FROM candidates
        WHERE status='failed'
        GROUP BY error_type
        ORDER BY count DESC
    """).fetchall()

    for error_type, count in error_types:
        print(f"  - {error_type}: {count:,}")

    # Ask for confirmation
    print(f"\nThis will reset {failed_count} failed downloads to 'pending' status.")
    print("They will be retried on the next download run.")
    response = input("\nProceed? (y/n): ").strip().lower()

    if response != 'y':
        print("Cancelled.")
        con.close()
        return 0

    # Reset failed to pending
    con.execute("""
        UPDATE candidates
        SET status = 'pending',
            error = NULL,
            updated_at = datetime('now')
        WHERE status = 'failed'
    """)

    # Update stats
    con.execute("""
        UPDATE stats
        SET v = v - ?
        WHERE k = 'total_failed'
    """, (failed_count,))

    con.commit()
    con.close()

    print(f"\n[SUCCESS] Reset {failed_count} downloads to pending status")
    print("Run download_capped.py to retry these downloads")
    print("\nIMPORTANT: Make sure SLEEP_BETWEEN_DOWNLOADS is set to at least 1.0")
    print("           to avoid rate limiting issues.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
