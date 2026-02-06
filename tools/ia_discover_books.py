import argparse
import sqlite3
import sys
import time
import requests
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH

UA = "ancientgeo/1.0 (IA discovery; local research)"
TIMEOUT = 60

ADVANCED_SEARCH = "https://archive.org/advancedsearch.php"
IIIF_MANIFEST_TEMPLATE = "https://iiif.archive.org/iiif/{identifier}/manifest.json"


DEFAULT_QUERIES = [
    # Architecture / facades / drawings
    'mediatype:(texts) AND (title:(architecture OR architectural OR cathedral OR "church facade" OR elevation) '
    'OR subject:(architecture OR cathedral OR tracery OR "rose window" OR "gothic" OR "roman" OR "islamic art"))',

    # Geometry / construction / stereotomy / ornament
    'mediatype:(texts) AND (title:(geometry OR proportion OR stereotomy OR "stone cutting" OR "geometric ornament" OR girih OR muqarnas OR zellige) '
    'OR subject:(geometry OR proportion OR stereotomy OR tracery OR ornament OR "geometric pattern" OR girih OR muqarnas OR zellige))',

    # Classic treatise names (broad net)
    'mediatype:(texts) AND (title:(vitruvius OR palladio OR serlio OR "viollet-le-duc" OR choisy) '
    'OR creator:(Vitruvius OR Palladio OR Serlio OR "Viollet-le-Duc" OR Choisy))',
]


def ensure_manifests_table(con: sqlite3.Connection):
    con.execute("""
    CREATE TABLE IF NOT EXISTS manifests (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source TEXT NOT NULL,
      query TEXT,
      record_url TEXT,
      manifest_url TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );
    """)
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_manifests_unique ON manifests(source, manifest_url);")
    con.execute("CREATE INDEX IF NOT EXISTS idx_manifests_status ON manifests(status);")
    con.commit()


def advanced_search(session: requests.Session, q: str, fields: list[str], rows: int, page: int, sorts: str | None):
    params = {
        "q": q,
        "fl[]": fields,       # fields to return :contentReference[oaicite:5]{index=5}
        "rows": rows,
        "page": page,
        "output": "json",
    }
    if sorts:
        params["sort[]"] = sorts
    r = session.get(ADVANCED_SEARCH, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser(description="Discover Internet Archive items and seed IIIF manifests into SQLite.")
    ap.add_argument("--rows", type=int, default=200, help="Results per page (IA caps apply).")
    ap.add_argument("--pages-per-query", type=int, default=50, help="How many pages to fetch per query.")
    ap.add_argument("--sleep", type=float, default=0.2, help="Delay between requests.")
    ap.add_argument("--sort", type=str, default="downloads desc", help="IA sort, e.g. 'downloads desc'.")
    ap.add_argument("--queries-file", type=str, default=None, help="Optional: file with one IA query per line.")
    args = ap.parse_args()

    queries = list(DEFAULT_QUERIES)
    if args.queries_file:
        p = Path(args.queries_file)
        extra = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.strip().startswith("#")]
        queries = extra

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Run tools/init_database.py first.")
        return 1

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    ensure_manifests_table(con)
    cur = con.cursor()

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    total_ids = 0
    total_inserted = 0

    for qi, q in enumerate(queries, start=1):
        print(f"\n[IA] Query {qi}/{len(queries)}: {q}")

        for page in range(1, args.pages_per_query + 1):
            data = advanced_search(
                session, q=q,
                fields=["identifier", "title", "creator", "date", "downloads", "mediatype", "collection"],
                rows=args.rows,
                page=page,
                sorts=args.sort
            )

            docs = (data.get("response") or {}).get("docs") or []
            if not docs:
                break

            inserted_this_page = 0
            for d in docs:
                ident = d.get("identifier")
                if not ident:
                    continue

                total_ids += 1
                record_url = f"https://archive.org/details/{ident}"
                manifest_url = IIIF_MANIFEST_TEMPLATE.format(identifier=ident)

                cur.execute("""
                    INSERT OR IGNORE INTO manifests(source, query, record_url, manifest_url, status)
                    VALUES ('internet_archive', ?, ?, ?, 'pending')
                """, (q, record_url, manifest_url))
                inserted_this_page += cur.rowcount

            con.commit()
            total_inserted += inserted_this_page
            print(f"  page {page}: docs={len(docs)} manifests+={inserted_this_page}")
            time.sleep(args.sleep)

    con.close()
    print(f"\nDone. Items seen={total_ids}, manifests inserted={total_inserted}")
    print("Next: python tools\\iiif_harvest_manifest.py  (to create image candidates)")
    print("Then: python tools\\download_until_cap.py  (to download up to 500GB)")


if __name__ == "__main__":
    main()
