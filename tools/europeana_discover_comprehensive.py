"""
Europeana Discovery - ULTRA-COMPREHENSIVE

Applies comprehensive architectural search terms to Europeana's collections.
Includes Boolean queries for windows, geometry, Islamic patterns, etc.

API: https://api.europeana.eu/record/v2
"""

import os
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH, REQUEST_TIMEOUT

BASE_URL = "https://api.europeana.eu/record/v2"
USER_AGENT = "AncientWorld/1.0 (europeana ultra-comprehensive)"

# Ultra-comprehensive queries combining user's detailed terms
COMPREHENSIVE_QUERIES = [
    # Window types - user provided
    "rose window",
    "wheel window",
    "oculus window",
    "circular window",
    "radial window",
    "stained glass window",
    "cathedral window",
    "gothic window",

    # Style + Building type combinations
    "gothic cathedral",
    "gothic church",
    "gothic architecture",
    "medieval cathedral",
    "medieval church",
    "medieval architecture",
    "romanesque cathedral",
    "romanesque church",
    "romanesque architecture",
    "renaissance cathedral",
    "renaissance architecture",
    "byzantine cathedral",
    "byzantine architecture",
    "islamic mosque",
    "islamic architecture",
    "classical architecture",
    "roman architecture",
    "greek architecture",

    # Architectural elements
    "cathedral facade",
    "church facade",
    "west front",
    "architectural elevation",
    "architectural plan",
    "architectural section",
    "dome",
   "vault",
    "tracery",
    "flying buttress",
    "rose window tracery",

    # Geometry terms - user provided
    "geometric pattern",
    "geometric ornament",
    "decorative geometry",
    "architectural geometry",
    "radial symmetry",
    "geometric construction",

    # Islamic geometry - user provided
    "islamic geometry",
    "islamic geometric pattern",
    "girih",
    "muqarnas",
    "zellige",
    "mashrabiya",
    "arabesque",

    # Drawing types - user provided
    "architectural drawing",
    "architectural study",
    "measured drawing",
    "architectural plate",
    "ornament study",
    "decorative arts study",
    "architectural detail",
    "ornamental stonework",

    # Additional architectural terms
    "stereotomy",
    "stone cutting",
    "masonry",
    "column",
    "arch",
    "pillar",
    "spire",
    "tower",
    "minaret",
    "basilica",
    "temple",
    "monastery",
    "cloister",
]


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
    con.commit()


def get_api_key():
    """Get Europeana API key from environment."""
    key = os.environ.get("EUROPEANA_API_KEY")
    if not key:
        print("ERROR: EUROPEANA_API_KEY environment variable not set.")
        sys.exit(1)
    return key


def extract_europeana_id_parts(europeana_id: str) -> tuple:
    """Extract collection and record IDs from Europeana item ID."""
    if not europeana_id or not europeana_id.startswith("/"):
        return None, None

    parts = europeana_id.strip("/").split("/")
    if len(parts) >= 2:
        collection_id = parts[0]
        record_id = "/".join(parts[1:])
        return collection_id, record_id

    return None, None


def build_iiif_manifest_url(collection_id: str, record_id: str) -> str:
    """Construct IIIF Presentation API manifest URL for Europeana item."""
    encoded_record = quote(record_id, safe='')
    return f"https://iiif.europeana.eu/presentation/{collection_id}/{encoded_record}/manifest"


def extract_title(item: dict) -> str:
    """Extract title from Europeana item."""
    title = item.get("title") or item.get("dcTitle") or item.get("dcDescription")

    if not title:
        return None

    if isinstance(title, list):
        title = title[0] if title else None

    if isinstance(title, dict):
        for lang_key in ['en', 'de', 'fr', 'it', 'es', 'def']:
            if lang_key in title:
                title = title[lang_key]
                if isinstance(title, list):
                    title = title[0] if title else None
                break

    return str(title) if title else None


def main(rows_per_query=200):
    """Ultra-comprehensive Europeana discovery."""
    api_key = get_api_key()

    print("=" * 80)
    print("Europeana Discovery - ULTRA-COMPREHENSIVE")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"Queries: {len(COMPREHENSIVE_QUERIES)}")
    print(f"Rows per query: {rows_per_query}\n")

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

    for idx, query in enumerate(COMPREHENSIVE_QUERIES, 1):
        print(f"[{idx}/{len(COMPREHENSIVE_QUERIES)}] Searching: {query}")

        try:
            params = {
                "wskey": api_key,
                "query": query,
                "media": "true",
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
                    europeana_id = item.get("id")
                    if not europeana_id:
                        continue

                    title = extract_title(item)
                    page_url = f"https://www.europeana.eu/item{europeana_id}"

                    # Try to construct IIIF manifest URL
                    collection_id, record_id = extract_europeana_id_parts(europeana_id)

                    if collection_id and record_id:
                        manifest_url = build_iiif_manifest_url(collection_id, record_id)

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

                        edmIsShownBy = item.get("edmIsShownBy")
                        if edmIsShownBy:
                            if isinstance(edmIsShownBy, list):
                                img_url = edmIsShownBy[0]
                            else:
                                img_url = edmIsShownBy

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

                except Exception:
                    continue

            con.commit()
            total_images += images_added
            total_manifests += manifests_added

            print(f"  Added: {images_added} direct images, {manifests_added} IIIF manifests\n")

            time.sleep(1.0)

        except Exception as e:
            print(f"  ERROR: {e}\n")
            continue

    con.close()

    print("=" * 80)
    print("Europeana Ultra-Comprehensive Discovery Complete!")
    print(f"Total direct images: {total_images:,}")
    print(f"Total IIIF manifests: {total_manifests:,}")
    print(f"Combined total: {total_images + total_manifests:,}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
