"""Missing-component detection: compare reference ROIs against aligned test ROIs.

Decision logic (modular, thresholded):

* ``diff``         mean absolute pixel difference (0..1, after lighting
                   normalization of both ROIs)
* ``ssim``         structural similarity between reference and test ROIs
* ``edge_cov``     fraction of reference edge pixels still visible in the test ROI
* ``context_diff`` difference in the PCB area surrounding the component

A weighted "missing score" is computed from the four indicators; the status is
``present`` / ``review`` / ``missing`` according to configurable thresholds.
The multi-indicator combination avoids false "missing" verdicts on lighting or
camera changes, while still detecting genuinely empty component regions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from . import comparator, normalizer

STATUS_PRESENT = "present"
STATUS_REVIEW = "review"
STATUS_MISSING = "missing"

# Verdict bands (missing score -> status).
PRESENT_BAND = 0.40
REVIEW_BAND = 0.60

# Default thresholds; every one is user-configurable via the settings API.
DEFAULT_THRESHOLDS: Dict[str, float] = {
    # Mean absolute pixel difference (0..1): below this the ROI matches the reference.
    "diff_ok": 0.20,
    "diff_review": 0.45,
    # Structural similarity between the component ROIs.
    "ssim_ok": 0.78,
    "ssim_review": 0.60,
    # Edge coverage: how many reference component edges survive in the test ROI.
    "edge_ok": 0.80,
    "edge_review": 0.50,
    # Surrounding PCB context: if it differs this much, alignment is suspect and
    # uncertain verdicts are escalated to "review".
    "context_veto": 0.55,
}


@dataclass
class ComponentSpec:
    """A named, annotated component in normalized [0, 1] image coordinates."""

    name: str
    x: float
    y: float
    width: float
    height: float


@dataclass
class ComponentResult:
    """Per-component verdict with confidence and a human-readable explanation."""

    name: str
    status: str
    confidence: float
    explanation: str
    bbox: Dict[str, float]


@dataclass
class BoardInspection:
    results: List[ComponentResult]
    alignment_ok: bool

    def to_dict(self) -> Dict[str, Any]:
        return {"results": [asdict(r) for r in self.results], "alignment_ok": self.alignment_ok}


def _clamp(v: float, lo: float, hi: float) -> float:
    return float(min(max(v, lo), hi))


def _missing_score(
    diff: float,
    ssim: float,
    edge_cov: float,
    context_diff: float,
    thresholds: Dict[str, float],
) -> float:
    """Weighted "missing-ness" in [0, 1]: 0 = present, 1 = missing.

    Combines several visual indicators so that a single weak signal (e.g. a
    slightly different lighting or camera change) does not declare a component
    missing on its own.
    """
    diff_score = min(diff / thresholds["diff_ok"], 1.0)
    ssim_gap = _clamp(
        (thresholds["ssim_ok"] - ssim) / (thresholds["ssim_ok"] - thresholds["ssim_review"] + 1e-9),
        0.0,
        1.0,
    )
    edge_gap = _clamp(
        (thresholds["edge_ok"] - edge_cov) / (thresholds["edge_ok"] - thresholds["edge_review"] + 1e-9),
        0.0,
        1.0,
    )
    context_score = min(context_diff / thresholds["context_veto"], 1.0)
    return (
        0.40 * diff_score
        + 0.30 * ssim_gap
        + 0.15 * edge_gap
        + 0.15 * context_score
    )


def _compare_one(
    ref_gray: np.ndarray,
    test_gray: np.ndarray,
    spec: ComponentSpec,
    thresholds: Dict[str, float],
    alignment_ok: bool,
) -> ComponentResult:
    h_img, w_img = ref_gray.shape[:2]
    bbox = {
        "x": _clamp(spec.x, 0.0, 1.0),
        "y": _clamp(spec.y, 0.0, 1.0),
        "width": _clamp(spec.width, 0.005, max(0.005, 1.0 - spec.x)),
        "height": _clamp(spec.height, 0.005, max(0.005, 1.0 - spec.y)),
    }
    x = int(round(bbox["x"] * w_img))
    y = int(round(bbox["y"] * h_img))
    w = max(int(round(bbox["width"] * w_img)), 8)
    h = max(int(round(bbox["height"] * h_img)), 8)
    x = max(0, min(x, w_img - 1))
    y = max(0, min(y, h_img - 1))
    w = min(w, w_img - x)
    h = min(h, h_img - y)

    ref_roi = comparator.crop_rect(ref_gray, x, y, w, h)
    test_roi = comparator.crop_rect(test_gray, x, y, w, h)
    if ref_roi.size == 0 or test_roi.size == 0 or w < 4 or h < 4:
        return ComponentResult(
            spec.name,
            STATUS_REVIEW,
            0.5,
            "Component region is too small or outside the image to analyze.",
            bbox,
        )

    # Metrics on the component ROIs. We compare the raw CLAHE outputs and map
    # the test ROI onto the reference's percentile range: identical images give
    # diff=0/ssim=1, while lighting or contrast shifts between images do not
    # inflate the difference (which would read as "missing").
    r = normalizer.clahe(comparator.resize_exact(ref_roi))
    t_raw = normalizer.clahe(comparator.resize_exact(test_roi))
    lo_r, hi_r = np.percentile(r, [1.0, 99.0])
    lo_t, hi_t = np.percentile(t_raw, [1.0, 99.0])
    if hi_t > lo_t and hi_r > lo_r:
        t = np.clip(
            (t_raw.astype(np.float64) - lo_t) / (hi_t - lo_t) * (hi_r - lo_r) + lo_r, 0, 255
        ).astype(np.uint8)
    else:
        t = np.zeros_like(t_raw)
    diff = comparator.mean_abs_diff(r, t)
    ssim = comparator.ssim(r, t)
    edge_cov = comparator.edge_coverage(comparator.edge_map(r), comparator.edge_map(t))

    context_diff = 0.0
    ref_ring = comparator.ring_crop(ref_gray, (x, y, w, h))
    test_ring = comparator.ring_crop(test_gray, (x, y, w, h))
    if ref_ring.size > 0 and test_ring.shape == ref_ring.shape:
        rr = normalizer.percentiles_stretch(comparator.resize_exact(ref_ring))
        tr = normalizer.percentiles_stretch(comparator.resize_exact(test_ring))
        context_diff = comparator.mean_abs_diff(rr, tr)

    missing = _missing_score(diff, ssim, edge_cov, context_diff, thresholds)

    if not alignment_ok:
        status = STATUS_REVIEW
    elif missing < PRESENT_BAND:
        status = STATUS_PRESENT
    elif missing < REVIEW_BAND:
        status = STATUS_REVIEW
    else:
        status = STATUS_MISSING

    confidence = round(_clamp(1.0 - missing, 0.0, 1.0), 3)
    explanation = (
        f"diff={diff:.3f} ssim={ssim:.3f} edge_cov={edge_cov:.3f} context_diff={context_diff:.3f}"
    )
    if status == STATUS_MISSING:
        explanation += " -> component appears absent/blank in the test image"
    elif status == STATUS_REVIEW:
        explanation += " -> uncertain, marked review"
    else:
        explanation += " -> present"

    return ComponentResult(spec.name, status, confidence, explanation, bbox)


def compare_components(
    ref_gray: np.ndarray,
    test_gray: np.ndarray,
    specs: List[ComponentSpec],
    thresholds: Optional[Dict[str, float]] = None,
    alignment_ok: bool = True,
) -> List[ComponentResult]:
    """Compare each component ROI in the reference against the aligned test image."""
    if thresholds is None:
        thresholds = dict(DEFAULT_THRESHOLDS)
    return [
        _compare_one(ref_gray, test_gray, spec, thresholds, alignment_ok)
        for spec in sorted(specs, key=lambda s: (s.y, s.x))
    ]
