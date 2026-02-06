import sqlite3
from pathlib import Path
import cv2

from config.storage_config import DB_PATH
from src.analysis.tda import extract_tda_features

DB = Path(DB_PATH)

def _load_image(path: Path):
    data = path.read_bytes()
    return cv2.imdecode(bytearray(data), cv2.IMREAD_COLOR)

def main(limit: int = 200):
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL;")
    cur = con.cursor()

    rows = cur.execute("""
      SELECT c.id, c.local_path
      FROM candidates c
      LEFT JOIN tda_features t ON t.candidate_id = c.id
      WHERE c.status='downloaded' AND c.local_path IS NOT NULL AND t.candidate_id IS NULL
      ORDER BY c.id ASC
      LIMIT ?
    """, (limit,)).fetchall()

    if not rows:
        print("No new images for TDA.")
        return

    done = 0
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

        feats = extract_tda_features(img).to_dict()
        cur.execute("""
          INSERT OR REPLACE INTO tda_features(candidate_id, method, betti0_sum, betti1_sum, betti1_max, point_count)
          VALUES (?, ?, ?, ?, ?, ?)
        """, (cid, feats["method"], feats["betti0_sum"], feats["betti1_sum"], feats["betti1_max"], feats["point_count"]))
        done += 1

    con.commit()
    con.close()
    print(f"TDA features computed for {done} images.")

if __name__ == "__main__":
    main(limit=200)
