"""
Metropolitan Museum of Art Collection Discovery

Harvests high-resolution images from The Met's Open Access collection.
API docs: https://metmuseum.github.io/
"""

import sqlite3
import sys
import time
from pathlib import Path

import requests

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH, REQUEST_TIMEOUT
from config.search_queries import QUERIES

BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"
USER_AGENT = "AncientWorld/1.0 (met harvester; https://github.com/robertwaltos/AncientWorld)"


def main():
    """Discover images from The Met Collection."""
    print("=" * 60)
    print("Met Museum Collection Discovery")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Queries: {len(QUERIES)}\n")

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("ERROR: Database not found. Run init_database.py first.")
        return 1

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    total_added = 0

    for query in QUERIES:
        print(f"[MET] Searching: {query}")

        try:
            # Search
            r = session.get(
                f"{BASE_URL}/search",
                params={"q": query, "hasImages": "true"},
                timeout=REQUEST_TIMEOUT
            )
            r.raise_for_status()
            data = r.json()

            object_ids = data.get("objectIDs") or []
            print(f"  Found: {len(object_ids)} objects")

            # Limit per query to avoid overwhelming
            for oid in object_ids[:1000]:
                try:
                    # Get object details
                    obj_r = session.get(f"{BASE_URL}/objects/{oid}", timeout=REQUEST_TIMEOUT)
                    obj_r.raise_for_status()
                    obj = obj_r.json()

                    img_url = obj.get("primaryImage") or ""
                    if not img_url:
                        continue

                    title = obj.get("title") or f"Met Object {oid}"
                    page_url = obj.get("objectURL")

                    # Get dimensions if available
                    width = None
                    height = None

                    # Additional metadata
                    artist = obj.get("artistDisplayName")
                    date = obj.get("objectDate")
                    culture = obj.get("culture")

                    con.execute("""
                        INSERT OR IGNORE INTO candidates(
                            source, query, title, page_url, image_url,
                            artist, date, institution, status
                        )
                        VALUES ('metmuseum', ?, ?, ?, ?, ?, ?, ?, 'pending')
                    """, (query, title, page_url, img_url, artist, date, culture))

                    if con.total_changes > 0:
                        total_added += 1

                    # Be polite - slow down to avoid 403
                    time.sleep(0.5)

                except Exception as e:
                    continue

            con.commit()
            print(f"  Added: {total_added} new candidates\n")

            # Be polite between queries to avoid 403
            time.sleep(2.0)

        except Exception as e:
            print(f"  ERROR: {e}\n")
            continue

    con.close()

    print("=" * 60)
    print("Met Discovery Complete!")
    print(f"Total candidates added: {total_added:,}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
