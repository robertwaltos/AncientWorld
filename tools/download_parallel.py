"""
Parallel Multi-Source Downloader

Downloads from multiple sources simultaneously to optimize rate limits.
Each source respects its own rate limit independently.

Features:
- Parallel downloads from different sources
- Source-specific rate limiting
- Storage cap enforcement
- Progress tracking per source
"""

import hashlib
import os
import re
import sqlite3
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path
from queue import Queue, Empty
from threading import Lock

import requests
from PIL import Image

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import (
    DB_PATH,
    IMAGES_ROOT,
    MAX_STORAGE_BYTES,
    MAX_STORAGE_GB,
    SLEEP_BETWEEN_DOWNLOADS,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
)

USER_AGENT = "AncientWorld/1.0 (research; https://github.com/robertwaltos/AncientWorld)"

# Source-specific rate limits (seconds between downloads)
SOURCE_RATE_LIMITS = {
    'wikimedia_commons': 1.0,
    'gallica_direct': 1.5,
    'europeana': 1.0,
    'metmuseum': 0.5,
    'archive_org': 1.0,
    'default': 1.0
}

# Global stats
stats_lock = Lock()
total_bytes_downloaded = 0
source_stats = defaultdict(lambda: {'downloaded': 0, 'failed': 0, 'bytes': 0})


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
    """Create prefix-based subdirectory structure."""
    p1 = filename[:2] if len(filename) >= 2 else "xx"
    p2 = filename[2:4] if len(filename) >= 4 else "yy"
    d = Path(IMAGES_ROOT) / p1 / p2
    d.mkdir(parents=True, exist_ok=True)
    return d


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_worker(source: str, queue: Queue, db_path: Path, stop_event: threading.Event):
    """Worker thread for downloading from a specific source."""
    global total_bytes_downloaded

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    rate_limit = SOURCE_RATE_LIMITS.get(source, SOURCE_RATE_LIMITS['default'])

    while not stop_event.is_set():
        try:
            # Get task from queue
            try:
                task = queue.get(timeout=1.0)
            except Empty:
                continue

            if task is None:  # Poison pill
                break

            cid, url, mime, sha1, width, height = task

            # Check storage cap
            with stats_lock:
                if total_bytes_downloaded >= MAX_STORAGE_BYTES:
                    queue.put(task)  # Put back for other workers
                    stop_event.set()
                    break

            # Mark as downloading
            con.execute(
                "UPDATE candidates SET status='downloading' WHERE id=?",
                (cid,)
            )
            con.commit()

            # Determine filename
            name_base = sha1.lower() if sha1 else f"id{cid}"
            ext = safe_ext(mime, url)
            out_dir = ensure_prefix_path(name_base)
            dest = out_dir / (name_base + ext)

            # Skip if exists
            if dest.exists():
                size = dest.stat().st_size
                sha256 = compute_sha256(dest)
                con.execute("""
                    UPDATE candidates
                    SET status='downloaded', local_path=?, downloaded_bytes=?, sha256_local=?
                    WHERE id=?
                """, (str(dest), size, sha256, cid))
                con.commit()

                with stats_lock:
                    source_stats[source]['downloaded'] += 1
                    source_stats[source]['bytes'] += size

                queue.task_done()
                continue

            # Download
            try:
                dest_tmp = dest.with_suffix(dest.suffix + ".part")
                bytes_written = 0

                with session.get(url, stream=True, timeout=REQUEST_TIMEOUT) as r:
                    r.raise_for_status()
                    with open(dest_tmp, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 256):
                            if chunk:
                                f.write(chunk)
                                bytes_written += len(chunk)

                # Atomic rename
                os.replace(dest_tmp, dest)

                # Verify dimensions
                try:
                    with Image.open(dest) as img:
                        w, h = img.size
                        if w < 900 or h < 900:
                            dest.unlink()
                            con.execute(
                                "UPDATE candidates SET status='rejected', error='dimensions' WHERE id=?",
                                (cid,)
                            )
                            con.commit()
                            queue.task_done()
                            time.sleep(rate_limit)
                            continue
                except Exception:
                    pass

                # Success
                sha256 = compute_sha256(dest)
                con.execute("""
                    UPDATE candidates
                    SET status='downloaded', local_path=?, downloaded_bytes=?, sha256_local=?
                    WHERE id=?
                """, (str(dest), bytes_written, sha256, cid))
                con.commit()

                with stats_lock:
                    total_bytes_downloaded += bytes_written
                    source_stats[source]['downloaded'] += 1
                    source_stats[source]['bytes'] += bytes_written

                print(f"[{source:15s}] Downloaded: {name_base}{ext} ({bytes_written/1024:.1f} KB)")

            except Exception as e:
                error_msg = str(e)
                con.execute(
                    "UPDATE candidates SET status='failed', error=? WHERE id=?",
                    (error_msg[:500], cid)
                )
                con.commit()

                with stats_lock:
                    source_stats[source]['failed'] += 1

                print(f"[{source:15s}] ERROR: {name_base}{ext} - {error_msg[:100]}")

            queue.task_done()

            # Rate limiting
            time.sleep(rate_limit)

        except Exception as e:
            print(f"[{source:15s}] Worker error: {e}")
            continue

    con.close()


def main():
    """Main parallel downloader."""
    global total_bytes_downloaded

    print("=" * 70)
    print("AncientWorld Parallel Multi-Source Downloader")
    print("=" * 70)
    print(f"Storage cap: {MAX_STORAGE_GB} GB ({MAX_STORAGE_BYTES:,} bytes)")
    print(f"Database: {DB_PATH}")
    print(f"Images root: {IMAGES_ROOT}\n")

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("ERROR: Database not found.")
        return 1

    Path(IMAGES_ROOT).mkdir(parents=True, exist_ok=True)

    # Get initial downloaded bytes
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")

    try:
        result = con.execute(
            "SELECT v FROM stats WHERE k='total_downloaded_bytes'"
        ).fetchone()
        if result:
            total_bytes_downloaded = int(result[0])
    except:
        pass

    print(f"Already downloaded: {total_bytes_downloaded / 1024**3:.2f} GB\n")

    # Get sources with pending candidates
    sources = con.execute("""
        SELECT DISTINCT source, COUNT(*)
        FROM candidates
        WHERE status='pending'
        GROUP BY source
        ORDER BY COUNT(*) DESC
    """).fetchall()

    con.close()

    if not sources:
        print("No pending candidates!")
        return 0

    print("Sources with pending downloads:")
    for source, count in sources:
        print(f"  {source:20s} {count:8,} images")
    print()

    # Create queues and threads for each source
    queues = {}
    threads = []
    stop_event = threading.Event()

    for source, count in sources:
        queue = Queue(maxsize=100)
        queues[source] = queue

        # Start worker thread for this source
        thread = threading.Thread(
            target=download_worker,
            args=(source, queue, db_path, stop_event),
            daemon=True
        )
        thread.start()
        threads.append(thread)
        print(f"Started worker for: {source}")

    print("\nStarting parallel downloads...\n")

    # Feed tasks to queues
    con = sqlite3.connect(db_path)

    while total_bytes_downloaded < MAX_STORAGE_BYTES and not stop_event.is_set():
        # Get pending candidates for each source
        for source in queues.keys():
            if stop_event.is_set():
                break

            batch = con.execute("""
                SELECT id, image_url, mime, sha1, width, height
                FROM candidates
                WHERE status='pending' AND source=?
                LIMIT 50
            """, (source,)).fetchall()

            if not batch:
                continue

            for task in batch:
                if stop_event.is_set():
                    break
                queues[source].put(task)

        # Check if any work left
        total_pending = con.execute(
            "SELECT COUNT(*) FROM candidates WHERE status='pending'"
        ).fetchone()[0]

        if total_pending == 0:
            print("\nNo more pending candidates!")
            break

        # Print progress
        print(f"\rTotal downloaded: {total_bytes_downloaded / 1024**3:.2f} GB / {MAX_STORAGE_GB} GB", end="", flush=True)

        time.sleep(5)

    con.close()

    # Stop workers
    print("\n\nShutting down workers...")
    stop_event.set()

    for queue in queues.values():
        queue.put(None)  # Poison pill

    for thread in threads:
        thread.join(timeout=5)

    # Final stats
    print("\n" + "=" * 70)
    print("Download Complete!")
    print("=" * 70)
    print(f"\nTotal downloaded: {total_bytes_downloaded / 1024**3:.2f} GB")
    print("\nPer-source statistics:")

    for source, stats in sorted(source_stats.items()):
        print(f"  {source:20s} Downloaded: {stats['downloaded']:6,}  Failed: {stats['failed']:5,}  Size: {stats['bytes']/1024**3:.2f} GB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
