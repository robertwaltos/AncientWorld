import sqlite3
import sys
from pathlib import Path
import cv2

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH
from src.analysis.geometry_features import extract_geometry_features

DB = Path(DB_PATH)

def _load_image(path: Path):
    data = path.read_bytes()
    return cv2.imdecode(bytearray(data), cv2.IMREAD_COLOR)

def main(limit: int = 1000):
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL;")
    cur = con.cursor()

    rows = cur.execute("""
      SELECT id, local_path
      FROM candidates
      WHERE status='downloaded'
        AND local_path IS NOT NULL
        AND id NOT IN (SELECT candidate_id FROM image_features)
      ORDER BY id ASC
      LIMIT ?
    """, (limit,)).fetchall()

    if not rows:
        print("No new images for geometry features.")
        return

    ok = 0
    for cid, lp in rows:
        p = Path(lp)
        if not p.exists():
            continue
        try:
            img = _load_image(p)
        except Exception:
            continue
        if img is None:
            continue

        feats = extract_geometry_features(img).to_dict()
        cur.execute("""
          INSERT OR REPLACE INTO image_features(
            candidate_id, width, height, edge_density, line_count,
            vertical_line_ratio, horizontal_line_ratio, orientation_entropy,
            circle_count, symmetry_lr, symmetry_ud, radialness,
            updated_at
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            cid,
            feats["width"], feats["height"], feats["edge_density"], feats["line_count"],
            feats["vertical_line_ratio"], feats["horizontal_line_ratio"], feats["orientation_entropy"],
            feats["circle_count"], feats["symmetry_lr"], feats["symmetry_ud"], feats["radialness"],
        ))
        ok += 1

    con.commit()
    con.close()
    print(f"Geometry features computed for {ok} images.")

if __name__ == "__main__":
    main()
