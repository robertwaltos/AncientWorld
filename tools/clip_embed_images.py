import sqlite3
import sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH

import torch
from transformers import CLIPProcessor, CLIPModel

DB = Path(DB_PATH)
MODEL_NAME = "openai/clip-vit-base-patch32"

def main(limit: int = 200):
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL;")
    cur = con.cursor()

    model = CLIPModel.from_pretrained(MODEL_NAME)
    processor = CLIPProcessor.from_pretrained(MODEL_NAME)
    model.eval()

    rows = cur.execute("""
      SELECT c.id, c.local_path
      FROM candidates c
      LEFT JOIN embeddings e ON e.candidate_id = c.id AND e.model = ?
      WHERE c.status='downloaded' AND c.local_path IS NOT NULL AND e.candidate_id IS NULL
      ORDER BY c.id ASC
      LIMIT ?
    """, (MODEL_NAME, limit)).fetchall()

    if not rows:
        print("No new images to embed.")
        return

    done = 0
    for cid, lp in rows:
        p = Path(lp)
        if not p.exists():
            continue
        try:
            img = Image.open(p).convert("RGB")
        except Exception:
            continue

        inputs = processor(images=img, return_tensors="pt")
        with torch.no_grad():
            feats = model.get_image_features(**inputs)
            feats = feats / feats.norm(dim=-1, keepdim=True)
        vec = feats[0].cpu().numpy().astype(np.float32)

        cur.execute("""
          INSERT OR REPLACE INTO embeddings(candidate_id, model, dim, vector)
          VALUES (?, ?, ?, ?)
        """, (cid, MODEL_NAME, int(vec.shape[0]), vec.tobytes()))
        done += 1

    con.commit()
    con.close()
    print(f"Embedded {done} images with {MODEL_NAME}")

if __name__ == "__main__":
    main(limit=200)
