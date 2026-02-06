#!/usr/bin/env python3
"""Monitor download progress in real-time."""
import sqlite3
import time
from pathlib import Path

DB = Path(r'F:\AncientWorld\db\assets.sqlite3')

def get_stats(con):
    downloaded = con.execute('SELECT COUNT(*) FROM candidates WHERE status="downloaded"').fetchone()[0]
    downloading = con.execute('SELECT COUNT(*) FROM candidates WHERE status="downloading"').fetchone()[0]
    pending = con.execute('SELECT COUNT(*) FROM candidates WHERE status="pending"').fetchone()[0]
    failed = con.execute('SELECT COUNT(*) FROM candidates WHERE status="failed"').fetchone()[0]
    return downloaded, downloading, pending, failed

def main():
    con = sqlite3.connect(DB)

    print("Monitoring download progress...")
    print("Press Ctrl+C to stop\n")

    start_downloaded, _, start_pending, start_failed = get_stats(con)
    print(f"Starting: {start_downloaded:,} downloaded, {start_pending:,} pending\n")

    try:
        for i in range(12):  # Monitor for 60 seconds
            time.sleep(5)
            downloaded, downloading, pending, failed = get_stats(con)
            new_downloads = downloaded - start_downloaded
            new_failures = failed - start_failed

            print(f"[{(i+1)*5:3}s] Downloaded: {downloaded:,} (+{new_downloads}) | "
                  f"Downloading: {downloading} | Pending: {pending:,} | Failed: {failed} (+{new_failures})")
    except KeyboardInterrupt:
        print("\nStopped monitoring")

    con.close()

    # Final summary
    final_downloaded, _, final_pending, final_failed = get_stats(con)
    print(f"\nSummary:")
    print(f"  New downloads: {final_downloaded - start_downloaded}")
    print(f"  New failures: {final_failed - start_failed}")

if __name__ == "__main__":
    main()
