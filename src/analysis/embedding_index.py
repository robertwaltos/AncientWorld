from __future__ import annotations
import sqlite3
import numpy as np
from typing import List, Tuple

def _blob_to_vec(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-12
    return float(np.dot(a, b) / denom)

def nearest_neighbors_sqlite(db_path: str, candidate_id: int, model: str, topk: int = 12) -> List[Tuple[int, float]]:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    row = cur.execute("SELECT vector FROM embeddings WHERE candidate_id=? AND model=?", (candidate_id, model)).fetchone()
    if not row:
        con.close()
        return []
    q = _blob_to_vec(row[0])
    rows = cur.execute("SELECT candidate_id, vector FROM embeddings WHERE model=? AND candidate_id != ?", (model, candidate_id)).fetchall()
    con.close()
    sims = []
    for cid, blob in rows:
        v = _blob_to_vec(blob)
        sims.append((cid, cosine_similarity(q, v)))
    sims.sort(key=lambda x: x[1], reverse=True)
    return sims[:topk]
