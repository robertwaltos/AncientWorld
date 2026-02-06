import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH

DB = Path(DB_PATH)

def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    cur = con.cursor()

    # Evidence vs discourse tags
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tags (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      candidate_id INTEGER NOT NULL,
      tag TEXT NOT NULL,
      tag_type TEXT NOT NULL,
      created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tags_candidate ON tags(candidate_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);")

    # Signals (time-window / record gap metrics, etc.)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS signals (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      candidate_id INTEGER NOT NULL,
      signal TEXT NOT NULL,
      value REAL,
      confidence REAL,
      created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_signals_candidate ON signals(candidate_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_signals_signal ON signals(signal);")

    # Geometry + scale features
    cur.execute("""
    CREATE TABLE IF NOT EXISTS image_features (
      candidate_id INTEGER PRIMARY KEY,
      width INTEGER,
      height INTEGER,
      edge_density REAL,
      line_count INTEGER,
      vertical_line_ratio REAL,
      horizontal_line_ratio REAL,
      orientation_entropy REAL,
      circle_count INTEGER,
      symmetry_lr REAL,
      symmetry_ud REAL,
      radialness REAL,

      opening_count INTEGER,
      door_window_aspect_mean REAL,
      door_window_aspect_median REAL,
      door_window_aspect_p90 REAL,

      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );
    """)

    # CLIP embeddings (float32 bytes)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
      candidate_id INTEGER PRIMARY KEY,
      model TEXT NOT NULL,
      dim INTEGER NOT NULL,
      vector BLOB NOT NULL,
      created_at TEXT DEFAULT (datetime('now'))
    );
    """)

    # TDA summaries
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tda_features (
      candidate_id INTEGER PRIMARY KEY,
      method TEXT NOT NULL,
      betti0_sum REAL,
      betti1_sum REAL,
      betti1_max REAL,
      point_count INTEGER,
      created_at TEXT DEFAULT (datetime('now'))
    );
    """)

    con.commit()
    con.close()
    print(f"OK: analysis tables ensured in {DB}")

if __name__ == "__main__":
    main()
