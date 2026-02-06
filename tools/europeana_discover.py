"""
Europeana API Discovery - Enhanced with IIIF Manifest Support

Harvests images and IIIF manifests from thousands of European cultural institutions.
Requires free API key from: https://pro.europeana.eu/page/get-api

IIIF Manifest Pattern: https://iiif.europeana.eu/presentation/{collectionId}/{recordId}/manifest
"""

import os
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH, REQUEST_TIMEOUT
from config.search_queries import QUERIES

BASE_URL = "https://api.europeana.eu/record/v2"
USER_AGENT = "AncientWorld/1.0 (europeana harvester; https://github.com/robertwaltos/AncientWorld)"


def ensure_manifests_table(con: sqlite3.Connection):
    """Ensure manifests table exists."""
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
    con.execute("CREATE INDEX IF NOT EXISTS idx_manifests_status ON manifests(status);")
    con.commit()


def get_api_key():
    """Get Europeana API key from environment."""
    key = os.environ.get("EUROPEANA_API_KEY")
    if not key:
        print("ERROR: EUROPEANA_API_KEY environment variable not set.")
        print("\nTo get a free API key:")
        print("1. Visit: https://pro.europeana.eu/page/get-api")
        print("2. Register for an API key")
        print("3. Set in .env file: EUROPEANA_API_KEY=your-key-here")
        sys.exit(1)
    return key


def extract_europeana_id_parts(europeana_id: str) -> tuple:
    """
    Extract collection and record IDs from Europeana item ID.
    Format: /collectionId/recordId
    Example: /9200396/BibliographicResource_3000126321991
    Returns: (collectionId, recordId) or (None, None)
    """
    if not europeana_id or not europeana_id.startswith("/"):
        return None, None

    parts = europeana_id.strip("/").split("/")
    if len(parts) >= 2:
        collection_id = parts[0]
        record_id = "/".join(parts[1:])  # Handle IDs with slashes
        return collection_id, record_id

    return None, None


def build_iiif_manifest_url(collection_id: str, record_id: str) -> str:
    """
    Construct IIIF Presentation API manifest URL for Europeana item.
    Pattern: https://iiif.europeana.eu/presentation/{collectionId}/{recordId}/manifest
    """
    # URL-encode the record ID to handle special characters
    encoded_record = quote(record_id, safe='')
    return f"https://iiif.europeana.eu/presentation/{collection_id}/{encoded_record}/manifest"


def extract_title(item: dict) -> str:
    """Extract title from Europeana item, handling various formats."""
    title = item.get("title") or item.get("dcTitle") or item.get("dcDescription")

    if not title:
        return None

    # Handle list format
    if isinstance(title, list):
        title = title[0] if title else None

    # Handle language-aware dict format
    if isinstance(title, dict):
        for lang_key in ['en', 'de', 'fr', 'it', 'es', 'def']:
            if lang_key in title:
                title = title[lang_key]
                if isinstance(title, list):
                    title = title[0] if title else None
                break

    return str(title) if title else None


def main(rows_per_query=200):
    """Discover images and IIIF manifests from Europeana."""
    api_key = get_api_key()

    print("=" * 70)
    print("Europeana Discovery - Enhanced with IIIF Manifest Support")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print(f"Queries: {len(QUERIES)}")
    print(f"Rows per query: {rows_per_query}\n")

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("ERROR: Database not found. Run init_database.py first.")
        return 1

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")
    ensure_manifests_table(con)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    total_images = 0
    total_manifests = 0

    for query in QUERIES:
        print(f"[EUROPEANA] Searching: {query}")

        try:
            # Search for items with media
            params = {
                "wskey": api_key,
                "query": query,
                "media": "true",  # Only items with media
                "rows": str(rows_per_query),
                "profile": "rich"
            }

            r = session.get(
                f"{BASE_URL}/search.json",
                params=params,
                timeout=REQUEST_TIMEOUT
            )
            r.raise_for_status()
            data = r.json()

            items = data.get("items", [])
            total_results = data.get("totalResults", 0)
            print(f"  Found: {len(items)} items (total available: {total_results:,})")

            images_added = 0
            manifests_added = 0

            for item in items:
                try:
                    # Extract item ID and title
                    europeana_id = item.get("id")
                    if not europeana_id:
                        continue

                    title = extract_title(item)
                    page_url = f"https://www.europeana.eu/item{europeana_id}"

                    # Try to construct IIIF manifest URL
                    collection_id, record_id = extract_europeana_id_parts(europeana_id)

                    if collection_id and record_id:
                        manifest_url = build_iiif_manifest_url(collection_id, record_id)

                        # Store as IIIF manifest for later processing
                        con.execute("""
                            INSERT OR IGNORE INTO manifests(
                                source, query, record_url, manifest_url, title, status
                            )
                            VALUES ('europeana', ?, ?, ?, ?, 'pending')
                        """, (query, page_url, manifest_url, title))

                        if con.total_changes > 0:
                            manifests_added += 1

                    else:
                        # Fallback: try to get direct image URL
                        img_url = None

                        # Try edmIsShownBy first (direct media link)
                        edmIsShownBy = item.get("edmIsShownBy")
                        if edmIsShownBy:
                            if isinstance(edmIsShownBy, list):
                                img_url = edmIsShownBy[0]
                            else:
                                img_url = edmIsShownBy

                        # Try edmPreview if no direct link
                        if not img_url:
                            edmPreview = item.get("edmPreview")
                            if edmPreview:
                                if isinstance(edmPreview, list):
                                    img_url = edmPreview[0]
                                else:
                                    img_url = edmPreview

                        if img_url and img_url.startswith('http'):
                            con.execute("""
                                INSERT OR IGNORE INTO candidates(
                                    source, query, title, page_url, image_url, status
                                )
                                VALUES ('europeana', ?, ?, ?, ?, 'pending')
                            """, (query, title, page_url, img_url))

                            if con.total_changes > 0:
                                images_added += 1

                except Exception as e:
                    # Skip problematic items silently
                    continue

            con.commit()
            total_images += images_added
            total_manifests += manifests_added

            print(f"  Added: {images_added} direct images, {manifests_added} IIIF manifests\n")

            # Be polite to the API
            time.sleep(1.0)

        except Exception as e:
            print(f"  ERROR: {e}\n")
            continue

    con.close()

    print("=" * 70)
    print("Europeana Discovery Complete!")
    print(f"Total direct images: {total_images:,}")
    print(f"Total IIIF manifests: {total_manifests:,}")
    print("\nNext steps:")
    print("  1. Run iiif_harvest_manifest.py to extract images from manifests")
    print("  2. Run download_capped.py to download images")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
