import sqlite3
import sys
from pathlib import Path
import cv2

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH
from src.analysis.scale_estimation import estimate_opening_aspects

DB = Path(DB_PATH)

def _load_image(path: Path):
    data = path.read_bytes()
    return cv2.imdecode(bytearray(data), cv2.IMREAD_COLOR)

def main(limit: int = 1000):
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL;")
    cur = con.cursor()

    rows = cur.execute("""
      SELECT c.id, c.local_path
      FROM candidates c
      JOIN image_features f ON f.candidate_id = c.id
      WHERE c.status='downloaded'
        AND c.local_path IS NOT NULL
        AND (f.opening_count IS NULL OR f.opening_count = 0)
      ORDER BY c.id ASC
      LIMIT ?
    """, (limit,)).fetchall()

    if not rows:
        print("No new images for scale features.")
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

        feats = estimate_opening_aspects(img).to_dict()
        cur.execute("""
          UPDATE image_features
          SET opening_count=?,
              door_window_aspect_mean=?,
              door_window_aspect_median=?,
              door_window_aspect_p90=?,
              updated_at=datetime('now')
          WHERE candidate_id=?
        """, (
            feats["opening_count"],
            feats["aspect_mean"],
            feats["aspect_median"],
            feats["aspect_p90"],
            cid
        ))
        ok += 1

    con.commit()
    con.close()
    print(f"Scale features computed for {ok} images.")

if __name__ == "__main__":
    main()
