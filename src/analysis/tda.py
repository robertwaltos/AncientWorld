from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any
import numpy as np
import cv2

try:
    from ripser import ripser
except Exception:
    ripser = None


@dataclass
class TDAFeatures:
    method: str
    betti0_sum: float
    betti1_sum: float
    betti1_max: float
    point_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _sample_edge_points(image_bgr, max_points=1500):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(gray, 60, 180)
    ys, xs = np.nonzero(edges)
    if len(xs) == 0:
        return np.zeros((0,2), dtype=np.float32)
    pts = np.stack([xs, ys], axis=1).astype(np.float32)
    if pts.shape[0] > max_points:
        idx = np.random.choice(pts.shape[0], size=max_points, replace=False)
        pts = pts[idx]
    pts[:,0] = pts[:,0] / (image_bgr.shape[1] + 1e-6)
    pts[:,1] = pts[:,1] / (image_bgr.shape[0] + 1e-6)
    return pts


def extract_tda_features(image_bgr, max_points=1500) -> TDAFeatures:
    if ripser is None:
        return TDAFeatures(method="ripser", betti0_sum=0.0, betti1_sum=0.0, betti1_max=0.0, point_count=0)

    pts = _sample_edge_points(image_bgr, max_points=max_points)
    if pts.shape[0] < 50:
        return TDAFeatures(method="ripser", betti0_sum=0.0, betti1_sum=0.0, betti1_max=0.0, point_count=int(pts.shape[0]))

    dgms = ripser(pts, maxdim=1)["dgms"]

    def lifetime_sum(dgm):
        if dgm.size == 0:
            return 0.0
        births = dgm[:,0]
        deaths = dgm[:,1]
        finite = np.isfinite(deaths)
        lt = deaths[finite] - births[finite]
        return float(np.maximum(lt, 0).sum())

    def lifetime_max(dgm):
        if dgm.size == 0:
            return 0.0
        births = dgm[:,0]
        deaths = dgm[:,1]
        finite = np.isfinite(deaths)
        lt = deaths[finite] - births[finite]
        return float(np.maximum(lt, 0).max()) if lt.size else 0.0

    betti0 = lifetime_sum(dgms[0]) if len(dgms) > 0 else 0.0
    betti1 = lifetime_sum(dgms[1]) if len(dgms) > 1 else 0.0
    betti1_max = lifetime_max(dgms[1]) if len(dgms) > 1 else 0.0

    return TDAFeatures(method="ripser", betti0_sum=betti0, betti1_sum=betti1, betti1_max=betti1_max, point_count=int(pts.shape[0]))
