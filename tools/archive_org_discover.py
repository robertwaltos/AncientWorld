"""
Internet Archive Discovery

Searches for architectural books and extracts IIIF manifests.
IA provides stable IIIF manifests at: https://iiif.archive.org/iiif/{identifier}/manifest.json
"""

import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

import requests

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH, REQUEST_TIMEOUT
from config.search_queries import QUERIES

SEARCH_URL = "https://archive.org/advancedsearch.php"
USER_AGENT = "AncientWorld/1.0 (archive.org harvester; https://github.com/robertwaltos/AncientWorld)"


def ia_identifier_to_manifest(identifier: str) -> str:
    """Convert IA identifier to IIIF manifest URL."""
    return f"https://iiif.archive.org/iiif/{identifier}/manifest.json"


def main(items_per_query=100):
    """Discover Internet Archive items with IIIF manifests."""
    print("=" * 60)
    print("Internet Archive Discovery")
    print("=" * 60)
    print(f"Search URL: {SEARCH_URL}")
    print(f"Queries: {len(QUERIES)}\n")

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("ERROR: Database not found. Run init_database.py first.")
        return 1

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    total_manifests = 0

    for query in QUERIES:
        print(f"[ARCHIVE.ORG] Searching: {query}")

        try:
            # Advanced search query
            # Focus on books and images with high image count
            params = {
                "q": f'({query}) AND mediatype:(texts OR image)',
                "fl[]": ["identifier", "title", "imagecount"],
                "rows": str(items_per_query),
                "page": "1",
                "output": "json",
                "sort": "downloads desc"
            }

            r = session.get(SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()

            items = data.get("response", {}).get("docs", [])
            print(f"  Found: {len(items)} items")

            for item in items:
                try:
                    identifier = item.get("identifier")
                    if not identifier:
                        continue

                    title = item.get("title")
                    imagecount = item.get("imagecount", 0)

                    # Skip items with very few images
                    if imagecount < 10:
                        continue

                    # Build manifest URL
                    manifest_url = ia_identifier_to_manifest(identifier)
                    record_url = f"https://archive.org/details/{identifier}"

                    # Insert into manifests
                    con.execute("""
                        INSERT OR IGNORE INTO manifests(
                            source, query, record_url, manifest_url, title, status
                        )
                        VALUES ('archive_org', ?, ?, ?, ?, 'pending')
                    """, (query, record_url, manifest_url, title))

                    if con.total_changes > 0:
                        total_manifests += 1

                except Exception as e:
                    continue

            con.commit()
            print(f"  Added: {total_manifests} manifests\n")

            # Be polite
            time.sleep(1.0)

        except Exception as e:
            print(f"  ERROR: {e}\n")
            continue

    con.close()

    print("=" * 60)
    print("Internet Archive Discovery Complete!")
    print(f"Total manifests added: {total_manifests:,}")
    print("\nNext step: Run iiif_harvest_manifest.py to extract images")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
