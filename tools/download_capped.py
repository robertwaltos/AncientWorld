"""
Capped downloader - downloads images until 500GB limit is reached.

Two-stage architecture:
1. Discovery spider fills candidates table with URLs
2. This downloader pulls from database and downloads until cap

Features:
- Hard stop at storage cap
- Resumes from where it left off
- Tracks total downloaded bytes
- Proper error handling
- Deduplication via SHA256
"""

import hashlib
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

import requests
from PIL import Image

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import (
    DB_PATH,
    IMAGES_ROOT,
    MAX_STORAGE_BYTES,
    MAX_STORAGE_GB,
    BATCH_SIZE,
    SLEEP_BETWEEN_DOWNLOADS,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
)

USER_AGENT = "AncientWorld/1.0 (research; https://github.com/robertwaltos/AncientWorld)"


def safe_ext(mime: str, url: str) -> str:
    """Determine file extension from MIME type or URL."""
    if mime:
        mime = mime.lower()
        if "jpeg" in mime:
            return ".jpg"
        if "png" in mime:
            return ".png"
        if "tiff" in mime or "tif" in mime:
            return ".tif"
        if "webp" in mime:
            return ".webp"

    # Fallback from URL
    m = re.search(r"\.(jpg|jpeg|png|tif|tiff|webp)(\?|$)", url, re.I)
    if m:
        ext = m.group(1).lower()
        return "." + ext.replace("jpeg", "jpg").replace("tiff", "tif")

    return ".jpg"  # Default


def ensure_prefix_path(filename: str) -> Path:
    """
    Create prefix-based subdirectory structure.

    Example: "ab123..." -> IMAGES_ROOT/ab/12/ab123...jpg

    This avoids having millions of files in one directory.
    """
    p1 = filename[:2] if len(filename) >= 2 else "xx"
    p2 = filename[2:4] if len(filename) >= 4 else "yy"
    d = Path(IMAGES_ROOT) / p1 / p2
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_total_bytes(con) -> int:
    """Get total downloaded bytes from stats table."""
    (v,) = con.execute(
        "SELECT v FROM stats WHERE k='total_downloaded_bytes'"
    ).fetchone()
    return int(v)


def set_total_bytes(con, v: int):
    """Update total downloaded bytes."""
    con.execute(
        "UPDATE stats SET v=? WHERE k='total_downloaded_bytes'",
        (int(v),)
    )
    con.commit()


def increment_stat(con, key: str, amount: int = 1):
    """Increment a stat counter."""
    con.execute(f"UPDATE stats SET v = v + ? WHERE k = ?", (amount, key))


def pick_batch(con, batch_size: int):
    """Pick next batch of pending candidates."""
    return con.execute("""
        SELECT id, image_url, mime, sha1, width, height
        FROM candidates
        WHERE status='pending'
        AND (width IS NULL OR width >= 900)
        AND (height IS NULL OR height >= 900)
        ORDER BY width DESC, height DESC
        LIMIT ?
    """, (batch_size,)).fetchall()


def mark_candidate(con, cid: int, status: str, **fields):
    """Update candidate status and fields."""
    cols = ["status=?", "updated_at=datetime('now')"]
    vals = [status]
    for k, v in fields.items():
        cols.append(f"{k}=?")
        vals.append(v)
    vals.append(cid)
    con.execute(
        f"UPDATE candidates SET {', '.join(cols)} WHERE id=?",
        vals
    )


def head_size(session: requests.Session, url: str):
    """Get content length with HEAD request."""
    try:
        r = session.head(
            url,
            allow_redirects=True,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT}
        )
        cl = r.headers.get("Content-Length")
        return r.status_code, int(cl) if cl and cl.isdigit() else None
    except Exception:
        return None, None


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(session: requests.Session, url: str, dest: Path):
    """
    Download a file with progress tracking.

    Returns:
        (bytes_written, http_status_code)
    """
    dest_tmp = dest.with_suffix(dest.suffix + ".part")
    bytes_written = 0

    with session.get(
        url,
        stream=True,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT}
    ) as r:
        r.raise_for_status()
        with open(dest_tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
                    bytes_written += len(chunk)

    # Atomic rename
    os.replace(dest_tmp, dest)
    return bytes_written, r.status_code


def main():
    """Main downloader loop."""
    print("="*60)
    print("AncientWorld Capped Downloader")
    print("="*60)
    print(f"Storage cap: {MAX_STORAGE_GB} GB ({MAX_STORAGE_BYTES:,} bytes)")
    print(f"Database: {DB_PATH}")
    print(f"Images root: {IMAGES_ROOT}")
    print()

    # Connect to database
    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("ERROR: Database not found. Run init_database.py first.")
        return 1

    Path(IMAGES_ROOT).mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")

    total_bytes = get_total_bytes(con)
    print(f"Already downloaded: {total_bytes / 1024**3:.2f} GB\n")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    while total_bytes < MAX_STORAGE_BYTES:
        batch = pick_batch(con, BATCH_SIZE)

        if not batch:
            print("\n✓ No more pending candidates!")
            break

        for cid, url, mime, sha1, width, height in batch:
            if total_bytes >= MAX_STORAGE_BYTES:
                print(f"\n✓ Reached storage cap: {MAX_STORAGE_GB} GB")
                break

            # Mark as downloading
            mark_candidate(con, cid, "downloading")
            con.commit()

            # Determine filename
            name_base = sha1.lower() if sha1 else f"id{cid}"
            ext = safe_ext(mime, url)
            out_dir = ensure_prefix_path(name_base)
            dest = out_dir / (name_base + ext)

            # Skip if already exists
            if dest.exists():
                size = dest.stat().st_size
                sha256 = compute_sha256(dest)
                mark_candidate(
                    con, cid, "downloaded",
                    local_path=str(dest),
                    downloaded_bytes=size,
                    sha256_local=sha256
                )
                increment_stat(con, "total_files_downloaded")
                con.commit()
                continue

            # HEAD request to check size
            status, content_length = head_size(session, url)
            if content_length and total_bytes + content_length > MAX_STORAGE_BYTES:
                mark_candidate(
                    con,cid, "skipped",
                    http_status=status,
                    content_length=content_length,
                    error="would exceed storage cap"
                )
                increment_stat(con, "total_skipped")
                con.commit()
                print("Stopping: next file would exceed cap")
                total_bytes = MAX_STORAGE_BYTES
                break

            # Download with retries
            success = False
            for attempt in range(MAX_RETRIES):
                try:
                    bytes_written, http_status = download_file(session, url, dest)

                    # Compute SHA256
                    sha256 = compute_sha256(dest)

                    # Update database
                    total_bytes += bytes_written
                    set_total_bytes(con, total_bytes)

                    mark_candidate(
                        con, cid, "downloaded",
                        http_status=http_status,
                        content_length=content_length,
                        downloaded_bytes=bytes_written,
                        local_path=str(dest),
                        sha256_local=sha256
                    )
                    increment_stat(con, "total_files_downloaded")
                    con.commit()

                    success = True

                    if cid % 10 == 0:
                        print(f"Progress: {total_bytes / 1024**3:.2f} GB / {MAX_STORAGE_GB} GB")

                    break

                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        mark_candidate(
                            con, cid, "failed",
                            error=str(e)
                        )
                        increment_stat(con, "total_failed")
                        con.commit()
                        print(f"Failed: {url[:80]}... ({e})")

            if success:
                time.sleep(SLEEP_BETWEEN_DOWNLOADS)

    # Final stats
    print("\n" + "="*60)
    print("Download complete!")
    print("="*60)

    stats = dict(con.execute("SELECT k, v FROM stats").fetchall())
    print(f"Total downloaded: {total_bytes / 1024**3:.2f} GB")
    print(f"Files downloaded: {stats.get('total_files_downloaded', 0):,}")
    print(f"Failed: {stats.get('total_failed', 0):,}")
    print(f"Skipped: {stats.get('total_skipped', 0):,}")

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
