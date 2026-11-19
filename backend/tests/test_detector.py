"""Detector: present/missing/review classification on synthetic boards."""

from __future__ import annotations

import cv2
import numpy as np

from app.cv.detector import DEFAULT_THRESHOLDS, ComponentSpec, compare_components


def _board(with_second: bool = True) -> np.ndarray:
    img = np.full((300, 400), 30, np.uint8)
    cv2.rectangle(img, (40, 40), (90, 60), (220, 220, 220), 2)  # R1 outline
    cv2.rectangle(img, (46, 45), (84, 55), (220, 220, 220), -1)  # R1 filled middle
    if with_second:
        cv2.circle(img, (280, 50), 12, (220, 220, 220), 4)  # C2 ring
        cv2.circle(img, (280, 50), 7, (220, 220, 220), -1)  # C2 disk (patterned)
    return img


def _specs() -> list:
    return [
        ComponentSpec(name="R1", x=0.10, y=0.13, width=0.125, height=0.067),
        ComponentSpec(name="C2", x=0.625, y=0.1333, width=0.15, height=0.067),
    ]


def test_detect_present_components():
    ref = _board(True)
    results = compare_components(ref, _board(True), _specs(), alignment_ok=True)
    assert [r.status for r in results] == ["present", "present"]
    assert results[0].confidence > 0.8


def test_detect_missing_component():
    ref = _board(True)
    results = compare_components(ref, _board(False), _specs(), alignment_ok=True)
    assert results[0].status == "present"
    assert results[1].status == "missing"


def test_brightness_and_noise_are_not_missing():
    """The detector must not declare missing due to lighting/camera changes."""
    ref = _board(True)
    test = cv2.convertScaleAbs(ref, alpha=1.4, beta=8)
    rng = np.random.default_rng(3)
    noise = rng.integers(-5, 6, test.shape).astype(np.int16)
    test = np.clip(test.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    results = compare_components(ref, test, _specs(), alignment_ok=True)
    # Safety property: brightness/noise on an unchanged board is never "missing".
    assert all(r.status != "missing" for r in results)


def test_unverified_alignment_marks_review():
    ref = _board(True)
    results = compare_components(ref, _board(False), _specs(), alignment_ok=False)
    assert all(r.status == "review" for r in results)


def test_thresholds_are_configurable():
    ref = _board(True)
    thresholds = dict(DEFAULT_THRESHOLDS, diff_ok=0.05)
    results = compare_components(
        ref, _board(False), _specs(), thresholds=thresholds, alignment_ok=True
    )
    assert results[1].status == "missing"


def test_confidence_and_explanation_present():
    ref = _board(True)
    results = compare_components(ref, _board(True), _specs(), alignment_ok=True)
    r = results[0]
    assert r.confidence > 0.8
    for key in ("diff=", "ssim=", "edge_cov=", "context_diff="):
        assert key in r.explanation
    assert r.bbox["x"] == 0.10 and r.bbox["y"] == 0.13
