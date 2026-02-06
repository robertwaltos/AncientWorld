import cv2
import numpy as np

def symmetry_lr_score(image_bgr) -> float:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gray = (gray - gray.mean()) / (gray.std() + 1e-6)
    flipped = cv2.flip(gray, 1)
    corr = float((gray * flipped).mean())
    return max(0.0, min(1.0, (corr + 1.0) / 2.0))

def symmetry_ud_score(image_bgr) -> float:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gray = (gray - gray.mean()) / (gray.std() + 1e-6)
    flipped = cv2.flip(gray, 0)
    corr = float((gray * flipped).mean())
    return max(0.0, min(1.0, (corr + 1.0) / 2.0))
