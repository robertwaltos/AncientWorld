"""
Near-duplicate removal using perceptual hashing.

Removes visually similar images (recrops, resizes, minor edits).
"""

import sqlite3
import sys
from pathlib import Path

from PIL import Image
import imagehash

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH, PERCEPTUAL_HASH_THRESHOLD


def main():
    """Remove near-duplicates using perceptual hashing."""
    print("="*60)
    print("Perceptual Hash Deduplication")
    print("="*60)
    print(f"Hamming distance threshold: {PERCEPTUAL_HASH_THRESHOLD}")

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("ERROR: Database not found.")
        return 1

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")

    rows = con.execute("""
        SELECT id, local_path, phash
        FROM candidates
        WHERE status='downloaded' AND local_path IS NOT NULL
        ORDER BY id ASC
    """).fetchall()

    print(f"Processing {len(rows)} images...")

    seen_hashes = {}
    removed = 0
    bytes_freed = 0

    for cid, local_path, existing_phash in rows:
        path = Path(local_path)

        if not path.exists():
            continue

        try:
            if existing_phash:
                phash = imagehash.hex_to_hash(existing_phash)
            else:
                img = Image.open(path)
                phash = imagehash.phash(img)
                con.execute("""
                    UPDATE candidates SET phash=? WHERE id=?
                """, (str(phash), cid))

            # Check for near-duplicates
            is_duplicate = False
            for seen_phash, seen_id in seen_hashes.items():
                if phash - seen_phash <= PERCEPTUAL_HASH_THRESHOLD:
                    is_duplicate = True
                    size = path.stat().st_size

                    try:
                        path.unlink()
                        bytes_freed += size
                        con.execute("""
                            UPDATE candidates
                            SET status='perceptual_duplicate', downloaded_bytes=0
                            WHERE id=?
                        """, (cid,))
                        removed += 1
                    except Exception:
                        pass

                    break

            if not is_duplicate:
                seen_hashes[phash] = cid

        except Exception as e:
            print(f"  Error processing {path}: {e}")

        if removed % 100 == 0 and removed > 0:
            print(f"  Removed {removed} near-duplicates")

    con.execute("""
        UPDATE stats SET v = v - ? WHERE k = 'total_downloaded_bytes'
    """, (bytes_freed,))

    con.commit()
    con.close()

    print("\n" + "="*60)
    print("Perceptual deduplication complete!")
    print("="*60)
    print(f"Near-duplicates removed: {removed:,}")
    print(f"Space freed: {bytes_freed / 1024**3:.2f} GB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
