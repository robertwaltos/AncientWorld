"""
Exact duplicate removal using SHA256.

Removes files with identical SHA256 hashes, keeping only the first occurrence.
"""

import hashlib
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    """Remove exact duplicates from downloaded files."""
    print("="*60)
    print("Exact Duplicate Removal")
    print("="*60)

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("ERROR: Database not found.")
        return 1

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")

    rows = con.execute("""
        SELECT id, local_path, sha256_local
        FROM candidates
        WHERE status='downloaded' AND local_path IS NOT NULL
        ORDER BY id ASC
    """).fetchall()

    print(f"Checking {len(rows)} downloaded files...")

    seen_hashes = {}
    removed = 0
    bytes_freed = 0

    for cid, local_path, existing_sha256 in rows:
        path = Path(local_path)

        if not path.exists():
            continue

        sha256 = existing_sha256 or compute_sha256(path)

        if sha256 in seen_hashes:
            size = path.stat().st_size
            try:
                path.unlink()
                bytes_freed += size
                con.execute("""
                    UPDATE candidates
                    SET status='duplicate', downloaded_bytes=0
                    WHERE id=?
                """, (cid,))
                removed += 1
            except Exception:
                pass
        else:
            seen_hashes[sha256] = cid

    con.execute("""
        UPDATE stats SET v = v - ? WHERE k = 'total_downloaded_bytes'
    """, (bytes_freed,))

    con.commit()
    con.close()

    print(f"Duplicates removed: {removed:,}")
    print(f"Space freed: {bytes_freed / 1024**3:.2f} GB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
