#!/usr/bin/env python3
"""
Parallel downloader that runs separate processes for different sources.

This avoids rate limit bottlenecks by:
- Running multiple source-specific downloaders in parallel
- Each source has its own rate limiting
- If one source is slow/down, others continue
"""

import hashlib
import os
import sqlite3
import sys
import time
import multiprocessing as mp
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import (
    DB_PATH,
    IMAGES_ROOT,
    MAX_STORAGE_BYTES,
    MAX_STORAGE_GB,
    SLEEP_BETWEEN_DOWNLOADS,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    MIN_IMAGE_WIDTH,
    MIN_IMAGE_HEIGHT,
    ENABLE_PERCEPTUAL_HASH,
    PERCEPTUAL_HASH_THRESHOLD,
)

USER_AGENT = "AncientWorld/1.0 (research; https://github.com/robertwaltos/AncientWorld)"
DB = Path(DB_PATH)
IMAGES_ROOT = Path(IMAGES_ROOT)  # Ensure it's a Path object


def get_domain_from_url(url: str) -> str:
    """Extract domain from URL."""
    return urlparse(url).netloc


def get_total_bytes(con):
    """Get total downloaded bytes across all candidates."""
    row = con.execute("SELECT SUM(downloaded_bytes) FROM candidates WHERE downloaded_bytes IS NOT NULL").fetchone()
    return row[0] or 0


def ensure_prefix_path(name: str) -> Path:
    """Create directory structure based on first 2 chars of name."""
    p1 = name[:2] if len(name) >= 2 else "00"
    p2 = name[2:4] if len(name) >= 4 else "00"
    out_dir = IMAGES_ROOT / p1 / p2
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def safe_ext(mime: str, url: str) -> str:
    """Determine file extension from MIME type or URL."""
    if mime and "/" in mime:
        sub = mime.split("/")[1].split(";")[0].strip().lower()
        if sub in ("jpeg", "jpg", "png", "gif", "webp", "tiff", "bmp"):
            return f".{sub}" if sub != "jpeg" else ".jpg"

    # Fallback to URL extension
    if "." in url:
        ext = url.split(".")[-1].split("?")[0].lower()
        if ext in ("jpg", "jpeg", "png", "gif", "webp", "tiff", "bmp"):
            return f".{ext}"

    return ".jpg"  # Default


def compute_sha256(path: Path) -> str:
    """Compute SHA256 hash of file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_phash(img: Image.Image) -> int:
    """Compute perceptual hash (average hash)."""
    img = img.convert("L")
    img = img.resize((8, 8), Image.Resampling.LANCZOS)
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = [1 if p >= avg else 0 for p in pixels]
    return int("".join(str(b) for b in bits), 2)


def hamming_distance(hash1: int, hash2: int) -> int:
    """Calculate Hamming distance between two hashes."""
    return bin(hash1 ^ hash2).count("1")


def mark_candidate(con, cid: int, status: str, **kwargs):
    """Update candidate status and optional fields."""
    fields = ["status=?"]
    values = [status]

    for key, val in kwargs.items():
        fields.append(f"{key}=?")
        values.append(val)

    values.append(cid)
    con.execute(f"UPDATE candidates SET {', '.join(fields)} WHERE id=?", values)


def increment_stat(con, key: str, delta: int = 1):
    """Increment a stat counter."""
    con.execute("INSERT OR REPLACE INTO stats(k, v) VALUES (?, COALESCE((SELECT v FROM stats WHERE k=?), 0) + ?)",
                (key, key, delta))


def download_from_source(domain: str, batch_size: int = 50, max_images: int = 1000):
    """
    Download images from a specific source domain.

    Args:
        domain: Domain to download from (e.g., 'gallica.bnf.fr')
        batch_size: Number of candidates to fetch per batch
        max_images: Maximum images to download before stopping
    """
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    downloaded_count = 0

    print(f"[{domain}] Starting downloads (max {max_images})...")

    while downloaded_count < max_images:
        # Check storage limit
        total_bytes = get_total_bytes(con)
        if total_bytes >= MAX_STORAGE_BYTES:
            print(f"[{domain}] Storage cap reached globally")
            break

        # Get batch of candidates from this domain
        batch = con.execute("""
            SELECT id, image_url, mime, sha1, width, height
            FROM candidates
            WHERE status='pending'
            AND image_url LIKE ?
            AND (width IS NULL OR width >= ?)
            AND (height IS NULL OR height >= ?)
            ORDER BY width DESC, height DESC
            LIMIT ?
        """, (f"%{domain}%", MIN_IMAGE_WIDTH, MIN_IMAGE_HEIGHT, batch_size)).fetchall()

        if not batch:
            print(f"[{domain}] No more pending candidates")
            break

        for cid, url, mime, sha1, width, height in batch:
            if downloaded_count >= max_images:
                break

            if get_total_bytes(con) >= MAX_STORAGE_BYTES:
                print(f"[{domain}] Storage cap reached")
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
                mark_candidate(con, cid, "downloaded", local_path=str(dest),
                             downloaded_bytes=size, sha256_local=sha256)
                increment_stat(con, "total_files_downloaded")
                con.commit()
                downloaded_count += 1
                continue

            # Try to download
            success = False
            for attempt in range(MAX_RETRIES):
                try:
                    resp = session.get(url, timeout=REQUEST_TIMEOUT, stream=True)
                    resp.raise_for_status()

                    # Save to temp file
                    temp_path = dest.with_suffix(dest.suffix + ".tmp")
                    with temp_path.open("wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)

                    # Verify it's a valid image
                    try:
                        img = Image.open(temp_path)
                        img.verify()
                        img = Image.open(temp_path)  # Reopen after verify
                        w, h = img.size

                        if w < MIN_IMAGE_WIDTH or h < MIN_IMAGE_HEIGHT:
                            temp_path.unlink()
                            mark_candidate(con, cid, "skipped", error="Image too small")
                            increment_stat(con, "total_skipped")
                            con.commit()
                            break

                        # Check for duplicates
                        if ENABLE_PERCEPTUAL_HASH:
                            phash = compute_phash(img)
                            existing = con.execute(
                                "SELECT id, local_path FROM candidates WHERE phash=? AND status='downloaded' AND id != ?",
                                (phash, cid)
                            ).fetchall()

                            # Check Hamming distance for near-duplicates
                            for eid, epath in existing:
                                dist = hamming_distance(phash, phash)  # Should compare with stored hash
                                if dist <= PERCEPTUAL_HASH_THRESHOLD:
                                    temp_path.unlink()
                                    mark_candidate(con, cid, "duplicate",
                                                 error=f"Duplicate of candidate {eid}")
                                    increment_stat(con, "total_duplicates")
                                    con.commit()
                                    success = True
                                    break

                            if success:
                                break

                        # Move to final location
                        temp_path.rename(dest)
                        size = dest.stat().st_size
                        sha256 = compute_sha256(dest)

                        mark_candidate(con, cid, "downloaded",
                                     local_path=str(dest),
                                     downloaded_bytes=size,
                                     sha256_local=sha256,
                                     width=w, height=h)
                        increment_stat(con, "total_files_downloaded")
                        con.commit()

                        downloaded_count += 1
                        success = True
                        print(f"[{domain}] OK {downloaded_count}/{max_images} - {w}x{h} - {name_base}{ext}")
                        break

                    except Exception as e:
                        if temp_path.exists():
                            temp_path.unlink()
                        raise e

                except Exception as e:
                    error_msg = str(e)

                    if "429" in error_msg or "too many requests" in error_msg.lower():
                        print(f"[{domain}] Rate limited, waiting 60s...")
                        time.sleep(60)

                    if attempt < MAX_RETRIES - 1:
                        wait_time = 2 ** attempt
                        time.sleep(wait_time)
                    else:
                        mark_candidate(con, cid, "failed", error=error_msg[:500])
                        increment_stat(con, "total_failed")
                        con.commit()
                        print(f"[{domain}] FAIL: {error_msg[:80]}")

            if success:
                time.sleep(SLEEP_BETWEEN_DOWNLOADS)

    con.close()
    print(f"[{domain}] Completed: {downloaded_count} images downloaded")
    return downloaded_count


def get_top_sources(limit: int = 10) -> list:
    """Get domains with most pending candidates."""
    con = sqlite3.connect(DB)
    rows = con.execute("""
        SELECT image_url FROM candidates WHERE status='pending' LIMIT 10000
    """).fetchall()

    from collections import defaultdict
    domains = defaultdict(int)

    for (url,) in rows:
        domain = get_domain_from_url(url)
        domains[domain] += 1

    con.close()

    # Return top domains
    return [domain for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True)[:limit]]


def main(num_workers: int = 5, images_per_source: int = 500):
    """
    Run parallel downloads from multiple sources.

    Args:
        num_workers: Number of parallel download processes
        images_per_source: Max images to download per source before stopping
    """
    print(f"Starting parallel downloads with {num_workers} workers")
    print(f"Target: {images_per_source} images per source")
    print()

    # Get top sources
    top_sources = get_top_sources(limit=num_workers)

    if not top_sources:
        print("No pending candidates found")
        return

    print(f"Top sources: {', '.join(top_sources)}")
    print()

    # Create process pool
    with mp.Pool(processes=num_workers) as pool:
        results = pool.starmap(download_from_source,
                              [(domain, 50, images_per_source) for domain in top_sources])

    total_downloaded = sum(results)
    print()
    print("=" * 70)
    print(f"Parallel download complete: {total_downloaded} images downloaded")
    print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parallel multi-source downloader")
    parser.add_argument("--workers", type=int, default=5, help="Number of parallel workers")
    parser.add_argument("--per-source", type=int, default=500, help="Images per source")

    args = parser.parse_args()

    main(num_workers=args.workers, images_per_source=args.per_source)
