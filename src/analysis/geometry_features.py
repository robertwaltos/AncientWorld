from __future__ import annotations
import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, List

import cv2
import numpy as np


@dataclass
class GeometryFeatures:
    width: int
    height: int
    edge_density: float
    line_count: int
    vertical_line_ratio: float
    horizontal_line_ratio: float
    orientation_entropy: float
    circle_count: int
    symmetry_lr: float
    symmetry_ud: float
    radialness: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _entropy(p: np.ndarray) -> float:
    p = p[p > 0]
    if p.size == 0:
        return 0.0
    return float(-(p * np.log2(p)).sum())


def _symmetry_score(gray: np.ndarray, axis: str) -> float:
    flipped = cv2.flip(gray, 1 if axis == "lr" else 0)
    a = gray.astype(np.float32)
    b = flipped.astype(np.float32)
    a = (a - a.mean()) / (a.std() + 1e-6)
    b = (b - b.mean()) / (b.std() + 1e-6)
    corr = float((a * b).mean())
    return max(0.0, min(1.0, (corr + 1.0) / 2.0))


def extract_geometry_features(image_bgr: np.ndarray) -> GeometryFeatures:
    h, w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray_eq = cv2.equalizeHist(gray)

    edges = cv2.Canny(gray_eq, 60, 180)
    edge_density = float(np.count_nonzero(edges)) / float(w * h)

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180.0,
        threshold=120,
        minLineLength=max(30, min(w, h) // 40),
        maxLineGap=max(10, min(w, h) // 80),
    )

    angles: List[float] = []
    v_count = 0
    h_count = 0
    line_count = 0
    if lines is not None:
        line_count = int(len(lines))
        for (x1, y1, x2, y2) in lines[:, 0]:
            dx = (x2 - x1)
            dy = (y2 - y1)
            ang = math.atan2(dy, dx) % math.pi
            angles.append(ang)
            if abs(ang - (math.pi / 2)) < (math.pi / 12):
                v_count += 1
            if min(abs(ang - 0), abs(ang - math.pi)) < (math.pi / 12):
                h_count += 1

    vertical_line_ratio = float(v_count) / float(line_count) if line_count else 0.0
    horizontal_line_ratio = float(h_count) / float(line_count) if line_count else 0.0

    if angles:
        hist, _ = np.histogram(np.array(angles), bins=18, range=(0, math.pi), density=True)
        hist = hist / (hist.sum() + 1e-12)
        orientation_entropy = _entropy(hist)
    else:
        orientation_entropy = 0.0

    scale = 800.0 / max(w, h) if max(w, h) > 800 else 1.0
    small = cv2.resize(gray_eq, (int(w * scale), int(h * scale))) if scale != 1.0 else gray_eq
    small_blur = cv2.GaussianBlur(small, (9, 9), 2)

    circles = cv2.HoughCircles(
        small_blur,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(20, min(small.shape) // 10),
        param1=150,
        param2=35,
        minRadius=max(10, min(small.shape) // 20),
        maxRadius=max(0, min(small.shape) // 3),
    )
    circle_count = int(circles.shape[1]) if circles is not None else 0

    symmetry_lr = _symmetry_score(gray_eq, "lr")
    symmetry_ud = _symmetry_score(gray_eq, "ud")

    radialness = float(
        min(1.0, 0.35 * (1.0 if circle_count > 0 else 0.0)
            + 0.35 * min(1.0, orientation_entropy / 3.0)
            + 0.30 * symmetry_lr)
    )

    return GeometryFeatures(
        width=w,
        height=h,
        edge_density=edge_density,
        line_count=line_count,
        vertical_line_ratio=vertical_line_ratio,
        horizontal_line_ratio=horizontal_line_ratio,
        orientation_entropy=orientation_entropy,
        circle_count=circle_count,
        symmetry_lr=symmetry_lr,
        symmetry_ud=symmetry_ud,
        radialness=radialness,
    )
