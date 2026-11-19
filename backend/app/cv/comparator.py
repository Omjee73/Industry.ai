"""Image comparison primitives: SSIM, pixel difference, edge analysis."""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np
from skimage.metrics import structural_similarity

COMPARE_SIZE = 220  # component ROIs are resized to a common square


def to_gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def crop_rect(img: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
    h_img, w_img = img.shape[:2]
    x = max(0, min(x, w_img - 1))
    y = max(0, min(y, h_img - 1))
    w = max(1, min(w, w_img - x))
    h = max(1, min(h, h_img - y))
    return img[y : y + h, x : x + w]


def resize_exact(img: np.ndarray, size: Tuple[int, int] = (COMPARE_SIZE, COMPARE_SIZE)) -> np.ndarray:
    if img.shape[:2] == size:
        return img
    return cv2.resize(img, size, interpolation=cv2.INTER_AREA)


def ssim(a: np.ndarray, b: np.ndarray) -> float:
    """Structural similarity between two equal-shaped grayscale images."""
    if a.shape != b.shape or a.size == 0:
        return 0.0
    try:
        value = structural_similarity(a, b, win_size=7, data_range=255)
    except ValueError:
        value = 0.0
    return float(value)


def mean_abs_diff(a: np.ndarray, b: np.ndarray) -> float:
    """Mean absolute difference, scaled to [0, 1]."""
    if a.shape != b.shape or a.size == 0:
        return 1.0
    return float(np.mean(np.abs(a.astype(np.int16) - b.astype(np.int16)))) / 255.0


def edge_map(gray: np.ndarray) -> np.ndarray:
    if gray.size == 0:
        return np.zeros_like(gray)
    edges = cv2.Canny(gray, 50, 150)
    return (edges > 0).astype(np.uint8) * 255


def edge_density(gray: np.ndarray) -> float:
    if gray.size == 0:
        return 0.0
    return float((edge_map(gray) > 0).mean())


def edge_coverage(ref_edges: np.ndarray, test_edges: np.ndarray) -> float:
    """Fraction of reference edge pixels present (within 1 px) in the test image."""
    ref_mask = ref_edges > 0
    total = int(ref_mask.sum())
    if total == 0:
        return 1.0
    dilated = cv2.dilate(test_edges, np.ones((3, 3), np.uint8))
    return min(int(dilated[ref_mask].sum()) / total, 1.0)


def ring_crop(img: np.ndarray, rect: Tuple[int, int, int, int], pad: int = 6) -> np.ndarray:
    """Area around a rectangle (the component itself + ~2px excluded).

    Used as "surrounding PCB context": if it differs strongly between the
    reference and the test, the alignment is suspect and verdicts become
    more cautious.
    """
    x, y, w, h = rect
    h_img, w_img = img.shape[:2]
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(w_img, x + w + pad), min(h_img, y + h + pad)
    if x1 <= x0 or y1 <= y0:
        return np.zeros((0, 0), np.uint8)
    ring = img[y0:y1, x0:x1].copy()
    mask = np.zeros(ring.shape[:2], np.uint8)
    mx0, my0 = max(0, x - x0) - 2, max(0, y - y0) - 2
    mx1, my1 = min(ring.shape[1], x + w - x0) + 2, min(ring.shape[0], y + h - y0) + 2
    if mx1 > mx0 and my1 > my0:
        cv2.rectangle(mask, (mx0, my0), (mx1, my1), 255, -1)
        ring[mask > 0] = 0
    return ring
