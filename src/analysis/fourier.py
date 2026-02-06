import numpy as np
import cv2

def radial_fft_spectrum(image_bgr, out_angles=360):
    """
    1D FFT magnitude of angular mean after polar transform.
    Useful for rotational periodicity (rose windows / tracery).
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    h, w = gray.shape[:2]
    center = (w // 2, h // 2)
    max_radius = min(center[0], center[1])

    polar = cv2.warpPolar(
        gray,
        (out_angles, max_radius),
        center,
        max_radius,
        cv2.WARP_POLAR_LINEAR
    )
    ang_profile = polar.mean(axis=0)
    fft = np.fft.rfft(ang_profile - ang_profile.mean())
    return np.abs(fft)
