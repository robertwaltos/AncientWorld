"""
Rijksmuseum Discovery - NO API KEY REQUIRED!

Uses the new Rijksmuseum Search API (Linked Art format)
API: https://data.rijksmuseum.nl/search/collection

No API key needed! Returns Linked Open Data identifiers.
"""

import sqlite3
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH, REQUEST_TIMEOUT

SEARCH_API = "https://data.rijksmuseum.nl/search/collection"
USER_AGENT = "AncientWorld/1.0 (rijksmuseum linked art harvester)"

# Search queries for architectural content
SEARCHES = [
    # Paintings with architectural subjects
    {"type": "painting", "description": "architecture"},
    {"type": "painting", "description": "cathedral"},
    {"type": "painting", "description": "church"},
    {"type": "painting", "description": "building"},

    # Drawings and prints
    {"type": "drawing", "description": "architecture"},
    {"type": "drawing", "description": "architectural"},
    {"type": "print", "description": "architecture"},
    {"type": "print", "description": "building"},

    # Specific techniques
    {"technique": "etching", "description": "architecture"},
    {"technique": "engraving", "description": "building"},

    # By title
    {"title": "architecture"},
    {"title": "cathedral"},
    {"title": "church"},
    {"title": "gothic"},
]


def resolve_lod_identifier(session: requests.Session, lod_id: str) -> dict:
    """
    Resolve Linked Open Data identifier to get object details.

    LOD IDs like: https://id.rijksmuseum.nl/200100988
    Can be resolved by requesting with Accept: application/json
    """
    try:
        r = session.get(
            lod_id,
            headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT
            },
            timeout=REQUEST_TIMEOUT
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"    ERROR resolving {lod_id}: {e}")
        return None


def extract_image_url(obj_data: dict) -> str:
    """Extract image URL from resolved object data."""
    if not obj_data:
        return None

    # Try to find digital representation
    representations = obj_data.get("representation", [])
    if not isinstance(representations, list):
        representations = [representations]

    for rep in representations:
        if isinstance(rep, dict):
            # Look for access point (image URL)
            access = rep.get("access_point", [])
            if isinstance(access, list) and len(access) > 0:
                access_point = access[0]
                if isinstance(access_point, dict):
                    img_url = access_point.get("id")
                    if img_url and img_url.startswith("http"):
                        return img_url

    # Fallback: try to find any URL-like field
    if "id" in obj_data and obj_data["id"].endswith((".jpg", ".jpeg", ".png")):
        return obj_data["id"]

    return None


def search_collection(session: requests.Session, search_params: dict, max_pages: int = 5) -> list:
    """
    Search the Rijksmuseum collection and return LOD identifiers.

    Returns list of (lod_id, search_query) tuples.
    """
    results = []
    url = SEARCH_API
    pages = 0

    # Add imageAvailable filter
    params = search_params.copy()
    params["imageAvailable"] = "true"

    while url and pages < max_pages:
        try:
            r = session.get(
                url,
                params=params if pages == 0 else None,  # params only on first page
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT
            )
            r.raise_for_status()
            data = r.json()

            # Extract LOD identifiers from orderedItems
            items = data.get("orderedItems", [])
            for item in items:
                lod_id = item.get("id")
                if lod_id:
                    results.append(lod_id)

            # Get next page URL
            next_page = data.get("next", {})
            url = next_page.get("id") if isinstance(next_page, dict) else None
            params = None  # Don't send params on subsequent pages

            pages += 1

            if items:
                print(f"    Page {pages}: {len(items)} items")

            time.sleep(0.5)  # Be polite

        except Exception as e:
            print(f"    ERROR fetching page: {e}")
            break

    return results


def main(max_pages_per_search: int = 3):
    """Discover images from Rijksmuseum using new Search API."""
    print("=" * 70)
    print("Rijksmuseum Discovery - NEW API (No API Key Required!)")
    print("=" * 70)
    print(f"Search API: {SEARCH_API}")
    print(f"Searches: {len(SEARCHES)}")
    print(f"Max pages per search: {max_pages_per_search}\n")

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("ERROR: Database not found.")
        return 1

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    total_discovered = 0
    total_added = 0

    for idx, search_params in enumerate(SEARCHES, 1):
        # Create readable search description
        search_desc = ", ".join(f"{k}={v}" for k, v in search_params.items())
        print(f"[{idx}/{len(SEARCHES)}] Searching: {search_desc}")

        # Search collection
        lod_ids = search_collection(session, search_params, max_pages=max_pages_per_search)
        print(f"  Found: {len(lod_ids)} LOD identifiers")

        total_discovered += len(lod_ids)
        added = 0

        # Resolve LOD identifiers and extract images
        for lod_id in lod_ids[:100]:  # Limit to first 100 per search to avoid overwhelming DB
            try:
                # Resolve LOD ID to get object data
                obj_data = resolve_lod_identifier(session, lod_id)
                if not obj_data:
                    continue

                # Extract metadata
                title = None
                if "_label" in obj_data:
                    label = obj_data["_label"]
                    if isinstance(label, list) and len(label) > 0:
                        title = label[0].get("value") if isinstance(label[0], dict) else str(label[0])
                    elif isinstance(label, dict):
                        title = label.get("value")
                    else:
                        title = str(label)

                # Extract image URL
                img_url = extract_image_url(obj_data)
                if not img_url:
                    # Try alternative approach - use the LOD ID directly as page URL
                    # and check if there's a simple image URL pattern
                    continue

                # Store in database
                con.execute("""
                    INSERT OR IGNORE INTO candidates(
                        source, query, title, page_url, image_url, status
                    )
                    VALUES ('rijksmuseum', ?, ?, ?, ?, 'pending')
                """, (search_desc, title, lod_id, img_url))

                if con.total_changes > 0:
                    added += 1

                time.sleep(0.1)  # Small delay between resolutions

            except Exception as e:
                continue

        con.commit()
        total_added += added

        print(f"  Added: {added} images\n")
        time.sleep(1.0)  # Delay between searches

    con.close()

    print("=" * 70)
    print("Rijksmuseum Discovery Complete!")
    print(f"Total discovered: {total_discovered:,} LOD identifiers")
    print(f"Total images added: {total_added:,}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
