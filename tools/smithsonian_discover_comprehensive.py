"""
Smithsonian Open Access Discovery - ULTRA-COMPREHENSIVE

Multi-strategy harvester targeting 100,000-200,000+ architectural images:
1. Collection-based browsing (specific museums)
2. Object type queries
3. Expanded keyword search with Boolean operators
4. Named architect queries
5. Faceted topic browsing

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

BASE_URL = "https://api.si.edu/openaccess/api/v1.0/search"
USER_AGENT = "AncientWorld/1.0 (smithsonian ultra-comprehensive harvester)"

# Strategy 1: Target specific museum collections with rich architectural holdings
ARCHITECTURAL_UNITS = {
    "CHNDM": "Cooper Hewitt Design Museum (architecture/design)",
    "AAA": "Archives of American Art",
    "NMAH": "National Museum of American History",
    "SAAM": "Smithsonian American Art Museum",
    "FSG": "Freer|Sackler Galleries (Islamic architecture)",
    "NPG": "National Portrait Gallery (architectural backgrounds)",
    "SOVA": "Smithsonian Online Virtual Archives",
}

# Strategy 2: Object type queries
OBJECT_TYPES = [
    "Drawings",
    "Architectural drawings",
    "Photographs",
    "Prints",
    "Plans",
    "Blueprints",
    "Negatives",
    "Slides",
    "Architectural models",
]

# Strategy 3: Comprehensive keyword search with Boolean operators
COMPREHENSIVE_QUERIES = [
    # User-provided detailed queries
    '("rose window" OR "wheel window" OR "oculus window" OR "circular window" OR "radial window" OR "stained glass window" OR "cathedral window" OR "gothic window")',

    '(gothic OR medieval OR romanesque OR renaissance OR byzantine OR islamic OR classical OR roman OR greek) AND (architecture OR cathedral OR church OR mosque OR temple OR basilica)',

    '(gothic OR medieval OR romanesque OR renaissance OR byzantine) AND (facade OR "west front" OR elevation OR plan OR section OR dome OR vault OR tracery)',

    '("geometric pattern" OR "geometric ornament" OR "decorative geometry" OR "architectural geometry" OR symmetry OR "radial symmetry" OR proportion OR "geometric construction")',

    '(islamic AND (geometry OR "geometric pattern" OR girih OR muqarnas OR zellige OR mashrabiya OR arabesque))',

    '("architectural drawing" OR "architectural study" OR "measured drawing" OR "architectural plate" OR "ornament study" OR "decorative arts study" OR "architectural detail" OR "ornamental stonework")',

    # Additional comprehensive terms
    "architecture",
    "architectural",
    "cathedral",
    "church",
    "mosque",
    "temple",
    "basilica",
    "synagogue",
    "chapel",

    # Architectural styles
    "gothic architecture",
    "romanesque architecture",
    "byzantine architecture",
    "baroque architecture",
    "renaissance architecture",
    "medieval architecture",
    "islamic architecture",
    "classical architecture",
    "neoclassical architecture",
    "art deco",
    "modernist architecture",
    "brutalist architecture",

    # Architectural elements
    "building facade",
    "architectural ornament",
    "architectural detail",
    "column",
    "pillar",
    "arch",
    "dome",
    "vault",
    "spire",
    "tower",
    "minaret",
    "steeple",

    # Materials & techniques
    "stone carving",
    "masonry",
    "stereotomy",
    "stone cutting",
    "woodwork",
    "metalwork",
    "stained glass",

    # Building types
    "skyscraper",
    "tower",
    "bridge",
    "monument",
    "palace",
    "castle",
    "fortress",

    # Technical drawings
    "floor plan",
    "site plan",
    "elevation drawing",
    "section drawing",
    "architectural blueprint",
]

# Strategy 4: Famous architects
ARCHITECTS = [
    "Frank Lloyd Wright",
    "Le Corbusier",
    "Louis Sullivan",
    "Daniel Burnham",
    "Charles Rennie Mackintosh",
    "Antoni Gaudí",
    "Mies van der Rohe",
    "Walter Gropius",
    "Philip Johnson",
    "I. M. Pei",
    "Frank Gehry",
    "Zaha Hadid",
    "Norman Foster",
    "Renzo Piano",
]

# Strategy 5: Topic/subject facets
TOPICS = [
    "Architecture",
    "Built environment",
    "Urban planning",
    "Architectural history",
    "Design",
    "Construction",
    "Engineering",
    "Historic preservation",
]


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
    """Extract all available image URLs from a Smithsonian item."""
    results = []

    content = item.get("content", {})
    descriptive = content.get("descriptiveNonRepeating", {})
    online_media = descriptive.get("online_media", {})
    media_items = online_media.get("media", [])

    for media in media_items:
        if media.get("type") == "Images":
            resources = media.get("resources", [])

            # Try all priority levels
            for priority in ["High-resolution", "Screen Image", "Thumbnail"]:
                for resource in resources:
                    if resource.get("label") == priority:
                        url = resource.get("url")
                        if url:
                            results.append((url, None))
                            break
                if results:
                    break

            # Fallback to first available
            if not results and resources:
                url = resources[0].get("url")
                if url:
                    results.append((url, None))

    # IIIF manifest
    iiif_url = online_media.get("iiif", {}).get("url")
    if iiif_url:
        results.append((None, iiif_url))

    return results


def search_with_pagination(session: requests.Session, api_key: str, query: str,
                          max_pages: int = 10, rows_per_page: int = 100) -> list:
    """Search Smithsonian with pagination support."""
    all_items = []
    start = 0

    for page in range(max_pages):
        try:
            params = {
                "api_key": api_key,
                "q": query,
                "rows": str(rows_per_page),
                "start": str(start),
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

            if page == 0:
                print(f"    Total results: {row_count:,}")
            print(f"    Page {page + 1}: {len(items)} items (retrieved so far: {len(all_items)})")

            if start + len(items) >= row_count or len(all_items) >= 1000:  # Cap at 1000 per query
                break

            start += rows_per_page
            time.sleep(0.5)

        except Exception as e:
            print(f"    ERROR on page {page + 1}: {e}")
            break

    return all_items


def process_items(con: sqlite3.Connection, items: list, strategy: str, query: str) -> dict:
    """Process items and add to database."""
    images_added = 0
    manifests_added = 0

    for item in items:
        try:
            title = item.get("title")
            id_val = item.get("id")
            page_url = f"https://collections.si.edu/search/detail/{id_val}" if id_val else None

            image_results = extract_images_from_item(item)

            for img_url, iiif_url in image_results:
                if iiif_url:
                    con.execute("""
                        INSERT OR IGNORE INTO manifests(
                            source, query, record_url, manifest_url, title, status
                        )
                        VALUES ('smithsonian', ?, ?, ?, ?, 'pending')
                    """, (f"{strategy}: {query}", page_url, iiif_url, title))

                    if con.total_changes > 0:
                        manifests_added += 1

                elif img_url:
                    con.execute("""
                        INSERT OR IGNORE INTO candidates(
                            source, query, title, page_url, image_url, status
                        )
                        VALUES ('smithsonian', ?, ?, ?, ?, 'pending')
                    """, (f"{strategy}: {query}", title, page_url, img_url))

                    if con.total_changes > 0:
                        images_added += 1

        except Exception:
            continue

    con.commit()
    return {"images": images_added, "manifests": manifests_added}


def main():
    """Ultra-comprehensive Smithsonian discovery."""
    api_key = get_api_key()
    if not api_key:
        return 1

    print("=" * 80)
    print("Smithsonian Open Access Discovery - ULTRA-COMPREHENSIVE")
    print("=" * 80)
    print("Multi-strategy approach targeting 100,000-200,000+ architectural images")
    print(f"API: {BASE_URL}\n")

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

    # STRATEGY 1: Collection-based browsing
    print("\n" + "=" * 80)
    print("STRATEGY 1: Collection-Based Browsing (Architectural Museums)")
    print("=" * 80)

    for unit_code, unit_name in ARCHITECTURAL_UNITS.items():
        print(f"\n[UNIT] {unit_name} ({unit_code})")

        query = f'unit_code:"{unit_code}" AND online_media_type:"Images"'
        items = search_with_pagination(session, api_key, query, max_pages=10)

        result = process_items(con, items, "Collection", unit_name)
        total_images += result["images"]
        total_manifests += result["manifests"]

        print(f"  Added: {result['images']} images, {result['manifests']} manifests")
        time.sleep(1.0)

    # STRATEGY 2: Object type queries
    print("\n" + "=" * 80)
    print("STRATEGY 2: Object Type Queries")
    print("=" * 80)

    for obj_type in OBJECT_TYPES:
        print(f"\n[TYPE] {obj_type}")

        query = f'object_type:"{obj_type}" AND (architecture OR architectural OR building)'
        items = search_with_pagination(session, api_key, query, max_pages=10)

        result = process_items(con, items, "ObjectType", obj_type)
        total_images += result["images"]
        total_manifests += result["manifests"]

        print(f"  Added: {result['images']} images, {result['manifests']} manifests")
        time.sleep(1.0)

    # STRATEGY 3: Comprehensive keyword search
    print("\n" + "=" * 80)
    print("STRATEGY 3: Comprehensive Keyword Search")
    print("=" * 80)

    for idx, query in enumerate(COMPREHENSIVE_QUERIES, 1):
        print(f"\n[{idx}/{len(COMPREHENSIVE_QUERIES)}] {query[:80]}...")

        items = search_with_pagination(session, api_key, query, max_pages=10)

        result = process_items(con, items, "Keyword", query[:100])
        total_images += result["images"]
        total_manifests += result["manifests"]

        print(f"  Added: {result['images']} images, {result['manifests']} manifests")
        time.sleep(1.0)

    # STRATEGY 4: Named architects
    print("\n" + "=" * 80)
    print("STRATEGY 4: Named Architect Queries")
    print("=" * 80)

    for architect in ARCHITECTS:
        print(f"\n[ARCHITECT] {architect}")

        query = f'"{architect}"'
        items = search_with_pagination(session, api_key, query, max_pages=5)

        result = process_items(con, items, "Architect", architect)
        total_images += result["images"]
        total_manifests += result["manifests"]

        print(f"  Added: {result['images']} images, {result['manifests']} manifests")
        time.sleep(1.0)

    # STRATEGY 5: Topic facets
    print("\n" + "=" * 80)
    print("STRATEGY 5: Topic/Subject Faceted Search")
    print("=" * 80)

    for topic in TOPICS:
        print(f"\n[TOPIC] {topic}")

        query = f'topic:"{topic}" AND online_media_type:"Images"'
        items = search_with_pagination(session, api_key, query, max_pages=10)

        result = process_items(con, items, "Topic", topic)
        total_images += result["images"]
        total_manifests += result["manifests"]

        print(f"  Added: {result['images']} images, {result['manifests']} manifests")
        time.sleep(1.0)

    con.close()

    print("\n" + "=" * 80)
    print("SMITHSONIAN ULTRA-COMPREHENSIVE DISCOVERY COMPLETE!")
    print("=" * 80)
    print(f"Total direct images: {total_images:,}")
    print(f"Total IIIF manifests: {total_manifests:,}")
    print(f"Combined total: {total_images + total_manifests:,}")
    print("\nStrategies executed:")
    print("  ✓ Collection-based browsing (7 museums)")
    print("  ✓ Object type queries (9 types)")
    print(f"  ✓ Comprehensive keywords ({len(COMPREHENSIVE_QUERIES)} queries)")
    print(f"  ✓ Named architects ({len(ARCHITECTS)} architects)")
    print(f"  ✓ Topic facets ({len(TOPICS)} topics)")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
