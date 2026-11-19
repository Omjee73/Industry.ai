"""Lighting/contrast normalization for image comparison.

Both the reference and the aligned test image pass through these helpers
before comparison, so that brightness shifts and mild camera differences
do not read as "component missing".
"""

from __future__ import annotations

import cv2
import numpy as np


def percentiles_stretch(
    gray: np.ndarray,
    low: Optional[float] = None,
    high: Optional[float] = None,
    lo: Optional[float] = None,
    hi: Optional[float] = None,
) -> np.ndarray:
    """Stretch the histogram between the given percentiles to full range.

    When ``lo``/``hi`` are given explicitly (shared reference scale), they are
    used instead of the image's own percentiles; this keeps two similar images
    comparable when only lighting/noise differs.
    """
    if gray.size == 0:
        return gray
    if lo is None or hi is None:
        lo, hi = np.percentile(gray, [low if low is not None else 1.0, high if high is not None else 99.0])
    if hi <= lo:
        return np.zeros_like(gray)
    out = (gray.astype(np.float64) - lo) / (hi - lo)
    return np.clip(out * 255.0, 0, 255).astype(np.uint8)


def clahe(gray: np.ndarray) -> np.ndarray:
    """CLAHE on a grayscale image (the illumination-equalization core)."""
    if gray.size == 0:
        return gray
    clahe_op = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    return clahe_op.apply(gray)


def normalize_lighting(gray: np.ndarray) -> np.ndarray:
    """Robust illumination normalization: CLAHE + percentile stretch."""
    if gray.size == 0:
        return gray
    return percentiles_stretch(clahe(gray))
