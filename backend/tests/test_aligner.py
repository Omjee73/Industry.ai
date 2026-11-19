"""Alignment tests: ORB + RANSAC homography and the phase-correlation fallback."""

from __future__ import annotations

import cv2
import numpy as np

from app.cv import aligner


def _textured_image(seed: int = 0, shape=(400, 500)) -> np.ndarray:
    rng = np.random.default_rng(seed)
    img = np.full(shape, 30, np.uint8)
    img[100:200, 100:200] = 255
    img[250:320, 350:420] = 255
    img[200:300, 50:120] = rng.integers(0, 255, (100, 70)).astype(np.uint8)
    img[320:360, 380:460] = rng.integers(0, 255, (40, 80)).astype(np.uint8)
    return img


def _warped(img: np.ndarray, tx: int, ty: int, scale: float = 1.0, rot: float = 0.0) -> np.ndarray:
    h, w = img.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, scale)
    M[0, 2] += tx
    M[1, 2] += ty
    return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_CONSTANT)


def test_orb_registration_translation():
    ref = _textured_image()
    test = _warped(ref, 37, -22)
    warped, ok = aligner.register_images(ref, test)
    assert ok
    mad = np.abs(warped.astype(int) - ref.astype(int)).mean()
    assert mad < 12, f"mean abs diff after alignment: {mad}"


def test_orb_registration_rotation_and_scale():
    ref = _textured_image()
    test = _warped(ref, 4, -5, scale=0.97, rot=6)
    warped, ok = aligner.register_images(ref, test)
    assert ok
    mad = np.abs(warped.astype(int) - ref.astype(int)).mean()
    assert mad < 15, f"mean abs diff after alignment: {mad}"


def test_phase_correlation_fallback_translation():
    ref = _textured_image()
    test = _warped(ref, 29, -11)
    warped, ok = aligner._phase_corr_register(ref, test)
    assert ok
    mad = np.abs(warped.astype(int) - ref.astype(int)).mean()
    assert mad < 8, f"mean abs diff after phase correlation: {mad}"
