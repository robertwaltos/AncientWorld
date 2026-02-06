from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, List

import cv2
import numpy as np


@dataclass
class ScaleFeatures:
    opening_count: int
    aspect_mean: float
    aspect_median: float
    aspect_p90: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def estimate_opening_aspects(image_bgr: np.ndarray) -> ScaleFeatures:
    """
    Conservative heuristic:
    - Find large rectangular contours that could correspond to door/window openings
    - Compute aspect ratios (height / width)
    - Returns summary stats (no claims about real-world meters/feet)
    """
    h, w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(gray, 60, 180)
    edges = cv2.dilate(edges, None, iterations=1)

    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    aspects: List[float] = []
    min_area = (w * h) * 0.002
    max_area = (w * h) * 0.6

    for c in cnts:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cw * ch
        if area < min_area or area > max_area:
            continue
        if cw < 20 or ch < 20:
            continue

        aspect = ch / (cw + 1e-6)
        if aspect < 0.6 or aspect > 6.0:
            continue
        aspects.append(float(aspect))

    if not aspects:
        return ScaleFeatures(opening_count=0, aspect_mean=0.0, aspect_median=0.0, aspect_p90=0.0)

    a = np.array(aspects, dtype=np.float32)
    return ScaleFeatures(
        opening_count=int(len(aspects)),
        aspect_mean=float(a.mean()),
        aspect_median=float(np.median(a)),
        aspect_p90=float(np.percentile(a, 90)),
    )
