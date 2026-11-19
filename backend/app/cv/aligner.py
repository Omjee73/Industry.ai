"""Reference-to-test image registration (alignment).

Primary strategy: ORB feature detection + ratio-tested matching + RANSAC
homography, which supports translation, rotation, scale and small perspective
changes between the reference and the test images.

Fallbacks when ORB finds nothing: phase-correlation translation, then an
identity warp. The ``ok`` return flag tells callers whether alignment was
verified; callers should treat unverified results as uncertain.
"""

from __future__ import annotations

from typing import Optional, Tuple

import cv2
import numpy as np

MIN_MATCHES = 6
RATIO_CANDIDATES = (0.70, 0.80, 0.88, 0.95)
REPROJ_TOL = 4.0


def _mean_reproj_err(
    src: np.ndarray, dst: np.ndarray, H: np.ndarray, mask: Optional[np.ndarray]
) -> Optional[float]:
    if mask is None:
        mask = np.ones((src.shape[0], 1), np.uint8)
    src_h = np.hstack([src.reshape(-1, 2), np.ones((src.reshape(-1, 2).shape[0], 1))]).T
    proj = H @ src_h
    proj = proj[:2] / (proj[2] + 1e-9)
    proj = proj.T.reshape(-1, 2)
    inl = mask.reshape(-1).astype(bool)
    if not inl.any():
        return None
    err = np.sqrt(((proj[inl] - dst.reshape(-1, 2)[inl]) ** 2).sum(axis=1))
    return float(err.mean())


def _orb_register(ref: np.ndarray, test: np.ndarray) -> Tuple[np.ndarray, bool]:
    """Estimate a homography test->ref via ORB + RANSAC (verified)."""
    orb = cv2.ORB_create(nfeatures=8000, scaleFactor=1.15, nlevels=6)
    kp_ref, desc_ref = orb.detectAndCompute(ref, None)
    kp_test, desc_test = orb.detectAndCompute(test, None)
    if desc_ref is None or desc_test is None or len(desc_test) < 2 or len(desc_ref) < 2:
        return ref.copy(), False

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    for ratio in RATIO_CANDIDATES:
        knn = bf.knnMatch(desc_test, desc_ref, k=2)
        good = [m for m, n in knn if m.distance < ratio * n.distance]
        if len(good) < MIN_MATCHES:
            continue
        src = np.float32([kp_test[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst = np.float32([kp_ref[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
        if H is None or mask is None:
            continue
        inliers = int(mask.sum())
        if inliers < MIN_MATCHES or inliers < 0.4 * len(good):
            continue
        err = _mean_reproj_err(src, dst, H, mask)
        if err is None or err > REPROJ_TOL:
            continue
        # H maps test coords -> ref coords; warpPerspective inverts it
        # internally, so passing H directly warps test onto the ref frame.
        warped = cv2.warpPerspective(test, H, (ref.shape[1], ref.shape[0]))
        return warped, True
    return ref.copy(), False


def _phase_corr_register(ref: np.ndarray, test: np.ndarray) -> Tuple[np.ndarray, bool]:
    """Translation fallback via phase correlation (verified)."""
    h, w = ref.shape[:2]
    if h < 16 or w < 16:
        return ref.copy(), False
    ds = 4
    ref_s = cv2.resize(ref, (w // ds, h // ds), interpolation=cv2.INTER_AREA)
    test_s = cv2.resize(test, (w // ds, h // ds), interpolation=cv2.INTER_AREA)
    if ref_s.shape != test_s.shape or ref_s.size == 0:
        return ref.copy(), False
    try:
        shift, response = cv2.phaseCorrelate(ref_s.astype(np.float32), test_s.astype(np.float32))
    except cv2.error:
        return ref.copy(), False
    if response < 0.1 or not np.all(np.isfinite(shift)):
        return ref.copy(), False
    dx, dy = float(shift[0]) * ds, float(shift[1]) * ds
    M = np.float32([[1, 0, -dx], [0, 1, -dy]])
    warped = cv2.warpAffine(
        test, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0
    )
    return warped, True


def register_images(ref_gray: np.ndarray, test_gray: np.ndarray) -> Tuple[np.ndarray, bool]:
    """Align ``test_gray`` onto ``ref_gray``'s frame.

    Returns ``(aligned_test, ok)`` where ``ok`` is True when the alignment was
    verified by ORB or phase correlation; False when we fell back to identity.
    """
    if ref_gray.size == 0 or test_gray.size == 0:
        return ref_gray.copy(), False
    warped, ok = _orb_register(ref_gray, test_gray)
    if ok:
        return warped, True
    warped, ok = _phase_corr_register(ref_gray, test_gray)
    return warped, ok
