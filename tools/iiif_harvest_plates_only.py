import re
import json
import sqlite3
import sys
import requests
from pathlib import Path
from typing import Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH

UA = "ancientgeo/1.0 (iiif plates-only harvester)"
TIMEOUT = 60

# Heuristics: common plate words across languages + abbreviations
PLATE_PATTERNS = [
    r"\bplate\b", r"\bpl\.\b", r"\bpl\b",
    r"\bplanche\b", r"\bplanches\b",
    r"\btafel\b", r"\btaf\.\b", r"\btaf\b",
    r"\btavola\b", r"\btav\.\b", r"\btav\b",
    r"\btabula\b",
    r"\bfig\b", r"\bfig\.\b", r"\bfigure\b",
    r"\billustration\b", r"\bill\.\b",
    r"\bfrontispiece\b",
    r"\bdiagram\b", r"\bschema\b", r"\bgeometr",  # geometr* catches geometry/geométrie/geometría
]

PLATE_RE = re.compile("|".join(PLATE_PATTERNS), re.IGNORECASE)

ROMAN_RE = re.compile(r"^(?=[MDCLXVI])M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$", re.I)


def iiif_full_image_url(service_id: str) -> str:
    # IIIF Image API: full/max, 0 rotation, default quality, jpg
    service_id = service_id.rstrip("/")
    return f"{service_id}/full/max/0/default.jpg"


def normalize_label(label: Any) -> str:
    """
    IIIF v2: label is often string
    IIIF v3: label can be {"en": ["..."]} or similar
    """
    if label is None:
        return ""
    if isinstance(label, str):
        return label.strip()
    if isinstance(label, dict):
        parts = []
        for v in label.values():
            if isinstance(v, list):
                parts.extend([str(x) for x in v])
            else:
                parts.append(str(v))
        return " ".join(parts).strip()
    if isinstance(label, list):
        return " ".join([str(x) for x in label]).strip()
    return str(label).strip()


def looks_like_plate(label: str) -> bool:
    if not label:
        return False
    s = label.strip()

    # Common: "Plate 12", "Pl. IV", "Planche 3", "Tafel IX", "Tav. 7"
    if PLATE_RE.search(s):
        return True

    # Sometimes the label is just a roman numeral for plates in plate sections
    # But this is risky globally; only treat as plate if it is roman numeral *and* short.
    if len(s) <= 8 and ROMAN_RE.match(s):
        return True

    return False


def iter_canvases(manifest: dict) -> list[dict]:
    """
    Supports IIIF Presentation v2 and v3.
    v2: manifest['sequences'][0]['canvases']
    v3: manifest['items'] (canvases)
    """
    if isinstance(manifest.get("items"), list):
        return [c for c in manifest["items"] if isinstance(c, dict)]

    seqs = manifest.get("sequences")
    if isinstance(seqs, list) and seqs:
        canv = seqs[0].get("canvases")
        if isinstance(canv, list):
            return [c for c in canv if isinstance(c, dict)]

    return []


def extract_image_service_ids_from_canvas(canvas: dict) -> list[str]:
    """
    Try common paths:
    v3: canvas.items[].items[].body.service.id
    v2: canvas.images[].resource.service.@id
    Plus generic service crawling inside this canvas.
    """
    services = []

    def add_service(svc: Any):
        if isinstance(svc, dict):
            sid = svc.get("id") or svc.get("@id")
            if isinstance(sid, str) and sid.startswith("http"):
                services.append(sid)
        elif isinstance(svc, list):
            for x in svc:
                add_service(x)

    # v3 path
    items = canvas.get("items")
    if isinstance(items, list):
        for annopage in items:
            if not isinstance(annopage, dict):
                continue
            ap_items = annopage.get("items")
            if not isinstance(ap_items, list):
                continue
            for anno in ap_items:
                if not isinstance(anno, dict):
                    continue
                body = anno.get("body")
                if isinstance(body, dict):
                    add_service(body.get("service"))
                elif isinstance(body, list):
                    for b in body:
                        if isinstance(b, dict):
                            add_service(b.get("service"))

    # v2 path
    imgs = canvas.get("images")
    if isinstance(imgs, list):
        for anno in imgs:
            if not isinstance(anno, dict):
                continue
            res = anno.get("resource")
            if isinstance(res, dict):
                add_service(res.get("service"))

    # generic: sometimes service is directly on canvas
    add_service(canvas.get("service"))

    # de-dupe preserve order
    out = []
    seen = set()
    for s in services:
        if s not in seen:
            out.append(s)
            seen.add(s)
    return out


def ensure_tables(con: sqlite3.Connection):
    # candidates exists from init_db.py; manifests exists from your migration.
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
    con.commit()


def main(limit: int = 50, source_filter: str = "internet_archive"):
    db_path = Path(DB_PATH)
    if not db_path.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Run tools/init_database.py first.")
        return 1

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    ensure_tables(con)
    cur = con.cursor()

    rows = cur.execute("""
        SELECT id, source, query, record_url, manifest_url
        FROM manifests
        WHERE status='pending' AND source=?
        ORDER BY id ASC
        LIMIT ?
    """, (source_filter, limit)).fetchall()

    if not rows:
        print(f"No pending manifests for source='{source_filter}'.")
        return

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    for mid, source, query, record_url, manifest_url in rows:
        try:
            cur.execute("UPDATE manifests SET status='downloading', updated_at=datetime('now') WHERE id=?", (mid,))
            con.commit()

            r = session.get(manifest_url, timeout=TIMEOUT)
            r.raise_for_status()
            manifest = r.json()

            canvases = iter_canvases(manifest)
            plate_canvases = []
            for c in canvases:
                label = normalize_label(c.get("label"))
                if looks_like_plate(label):
                    plate_canvases.append((c, label))

            inserted = 0
            canv_used = 0

            for c, label in plate_canvases:
                service_ids = extract_image_service_ids_from_canvas(c)
                if not service_ids:
                    continue
                canv_used += 1
                for sid in service_ids:
                    img_url = iiif_full_image_url(sid)
                    # Use the label in title to preserve plate numbering
                    cur.execute("""
                        INSERT OR IGNORE INTO candidates(source, query, title, page_url, image_url, status)
                        VALUES (?, ?, ?, ?, ?, 'pending')
                    """, (source, query, label or None, record_url or manifest_url, img_url))
                    inserted += cur.rowcount

            cur.execute("UPDATE manifests SET status='done', updated_at=datetime('now') WHERE id=?", (mid,))
            con.commit()

            print(f"[{source}] manifest {mid}: canvases={len(canvases)} plates={len(plate_canvases)} used={canv_used} candidates+={inserted}")

        except Exception as e:
            cur.execute("UPDATE manifests SET status='failed', updated_at=datetime('now') WHERE id=?", (mid,))
            con.commit()
            print(f"[{source}] manifest {mid} FAILED: {e}")

    con.close()


if __name__ == "__main__":
    # You can edit these defaults or wrap with argparse if you want
    main(limit=50, source_filter="internet_archive")
