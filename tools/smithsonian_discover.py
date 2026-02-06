"""
Smithsonian Open Access Discovery - ENHANCED

Comprehensive harvester for Smithsonian's 11+ million item collection.
Features:
- All open access images (not just CC0)
- Pagination support (multi-page results)
- Better image extraction (handles multiple formats)
- Expanded architectural queries
- IIIF manifest support

API: https://api.si.edu/openaccess/api/v1.0
Requires API key from: https://api.si.edu/#signup
"""

import os
import sqlite3
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH, REQUEST_TIMEOUT
from config.search_queries import QUERIES

BASE_URL = "https://api.si.edu/openaccess/api/v1.0/search"
USER_AGENT = "AncientWorld/1.0 (smithsonian enhanced harvester)"


def ensure_manifests_table(con: sqlite3.Connection):
    """Ensure manifests table exists for IIIF support."""
    con.execute("""
    CREATE TABLE IF NOT EXISTS manifests (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source TEXT NOT NULL,
      query TEXT,
      record_url TEXT,
      manifest_url TEXT NOT NULL,
      title TEXT,
      status TEXT NOT NULL DEFAULT 'pending',
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );
    """)
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_manifests_unique ON manifests(source, manifest_url);")
    con.commit()


def get_api_key():
    """Get Smithsonian API key from environment."""
    key = os.environ.get("SMITHSONIAN_API_KEY")
    if not key:
        print("WARNING: SMITHSONIAN_API_KEY not set.")
        print("Get a free key from: https://api.si.edu/#signup")
        return None
    return key


def extract_images_from_item(item: dict) -> list:
    """
    Extract all available image URLs from a Smithsonian item.
    Returns list of (image_url, iiif_manifest_url) tuples.
    """
    results = []

    # Try multiple paths in the API response
    content = item.get("content", {})
    descriptive = content.get("descriptiveNonRepeating", {})

    # Path 1: online_media
    online_media = descriptive.get("online_media", {})
    media_items = online_media.get("media", [])

    for media in media_items:
        if media.get("type") == "Images":
            resources = media.get("resources", [])

            # Try to get high-resolution first, then fall back
            for priority in ["High-resolution", "Screen Image", "Thumbnail"]:
                for resource in resources:
                    if resource.get("label") == priority:
                        url = resource.get("url")
                        if url:
                            results.append((url, None))
                            break
                if results:
                    break

            # If no labeled resource found, take first available
            if not results and resources:
                url = resources[0].get("url")
                if url:
                    results.append((url, None))

    # Path 2: IIIF manifest
    iiif_url = descriptive.get("online_media", {}).get("iiif", {}).get("url")
    if iiif_url:
        results.append((None, iiif_url))

    # Path 3: Direct media links
    if not results:
        # Try freetext for embedded URLs
        freetext = content.get("freetext", {})
        for key, values in freetext.items():
            if isinstance(values, list):
                for val in values:
                    if isinstance(val, dict):
                        content_text = val.get("content", "")
                        if "iiif" in content_text.lower() and "http" in content_text:
                            # Potential IIIF URL in text
                            pass

    return results


def search_with_pagination(session: requests.Session, api_key: str, query: str,
                          max_pages: int = 10, rows_per_page: int = 100) -> list:
    """
    Search Smithsonian with pagination support.
    Returns list of item dictionaries.
    """
    all_items = []
    start = 0

    for page in range(max_pages):
        try:
            params = {
                "api_key": api_key,
                "q": query,
                "rows": str(rows_per_page),
                "start": str(start),
                # Remove CC0 restriction - get all open access
                "online_media_type": "Images"
            }

            r = session.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()

            response = data.get("response", {})
            items = response.get("rows", [])
            row_count = response.get("rowCount", 0)

            if not items:
                break

            all_items.extend(items)

            print(f"    Page {page + 1}: {len(items)} items (total so far: {len(all_items)})")

            # Check if we've reached the end
            if start + len(items) >= row_count:
                break

            start += rows_per_page
            time.sleep(0.5)  # Be polite between pages

        except Exception as e:
            print(f"    ERROR on page {page + 1}: {e}")
            break

    return all_items


def main(max_pages_per_query: int = 10):
    """Discover images from Smithsonian with enhanced coverage."""
    api_key = get_api_key()
    if not api_key:
        return 1

    print("=" * 70)
    print("Smithsonian Open Access Discovery - ENHANCED")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print(f"Queries: {len(QUERIES)}")
    print(f"Max pages per query: {max_pages_per_query}")
    print(f"Features: All open access + Pagination + IIIF support\n")

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("ERROR: Database not found.")
        return 1

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")
    ensure_manifests_table(con)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    total_images = 0
    total_manifests = 0

    for idx, query in enumerate(QUERIES, 1):
        print(f"[{idx}/{len(QUERIES)}] Searching: {query}")

        try:
            # Search with pagination
            items = search_with_pagination(
                session, api_key, query,
                max_pages=max_pages_per_query
            )

            print(f"  Total items retrieved: {len(items)}")

            images_added = 0
            manifests_added = 0

            for item in items:
                try:
                    # Extract metadata
                    title = item.get("title")
                    unit_code = item.get("unitCode")
                    id_val = item.get("id")
                    page_url = f"https://collections.si.edu/search/detail/{id_val}" if id_val else None

                    # Extract all available images
                    image_results = extract_images_from_item(item)

                    for img_url, iiif_url in image_results:
                        if iiif_url:
                            # Store IIIF manifest
                            con.execute("""
                                INSERT OR IGNORE INTO manifests(
                                    source, query, record_url, manifest_url, title, status
                                )
                                VALUES ('smithsonian', ?, ?, ?, ?, 'pending')
                            """, (query, page_url, iiif_url, title))

                            if con.total_changes > 0:
                                manifests_added += 1

                        elif img_url:
                            # Store direct image
                            con.execute("""
                                INSERT OR IGNORE INTO candidates(
                                    source, query, title, page_url, image_url, status
                                )
                                VALUES ('smithsonian', ?, ?, ?, ?, 'pending')
                            """, (query, title, page_url, img_url))

                            if con.total_changes > 0:
                                images_added += 1

                except Exception as e:
                    continue

            con.commit()
            total_images += images_added
            total_manifests += manifests_added

            print(f"  Added: {images_added} direct images, {manifests_added} IIIF manifests\n")

            time.sleep(1.0)  # Polite delay between queries

        except Exception as e:
            print(f"  ERROR: {e}\n")
            continue

    con.close()

    print("=" * 70)
    print("Smithsonian Enhanced Discovery Complete!")
    print(f"Total direct images: {total_images:,}")
    print(f"Total IIIF manifests: {total_manifests:,}")
    print(f"Combined total: {total_images + total_manifests:,}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
