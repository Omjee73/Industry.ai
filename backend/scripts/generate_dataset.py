"""Synthetic PCB dataset generator for the PCB Missing Component Detection app.

Usage (from the repository root, with Python on PATH):

    python backend/scripts/generate_dataset.py

Writes PNG images plus a reference manifest into ``backend/data/demo/``:

- ``reference.png``                - a good, fully populated reference board
- ``reference.json``               - manifest with component names + normalized positions
- ``test_01_complete.png``         - complete board, small brightness/noise variations
- ``test_02_missing_c1_d2.png``    - C1 and D2 missing
- ``test_03_missing_r2.png``       - R2 missing
- ``test_04_translated_scaled.png``- complete board, translated + slightly scaled
- ``test_05_dark_noise_u2.png``    - U2 missing, darker and noisier

All images share the same camera viewpoint: the reference is the base image and
each test image is derived from it, so ORB alignment behaves the way it does on a
factory camera with a fixed viewpoint.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, Sequence, Tuple

import cv2
import numpy as np

W, H = 1024, 768
BG = (30, 30, 30)          # dark PCB background (BGR)
TEXT = (220, 220, 220)     # light component outlines (BGR)

_DEFAULT_OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "demo"


def component_specs() -> list[Dict[str, object]]:
    """Fixed, deterministic layout of the demo board (pixel coordinates, BGR)."""
    return [
        {"name": "R1", "x": 100, "y": 60,  "w": 90,  "h": 26, "shape": "resistor"},
        {"name": "C1", "x": 330, "y": 80,  "w": 46,  "h": 26, "shape": "capacitor"},
        {"name": "U1", "x": 620, "y": 90,  "w": 150, "h": 78, "shape": "chip"},
        {"name": "D1", "x": 850, "y": 80,  "w": 20,  "h": 24, "shape": "diode"},
        {"name": "R2", "x": 100, "y": 320, "w": 90,  "h": 30, "shape": "resistor"},
        {"name": "C2", "x": 330, "y": 350, "w": 52,  "h": 30, "shape": "capacitor"},
        {"name": "U2", "x": 620, "y": 340, "w": 150, "h": 82, "shape": "chip"},
        {"name": "D2", "x": 850, "y": 340, "w": 20,  "h": 24, "shape": "diode"},
    ]


def _draw_resistor(img: np.ndarray, spec: Dict[str, object]) -> None:
    x, y, w, h = int(spec["x"]), int(spec["y"]), int(spec["w"]), int(spec["h"])
    cv2.rectangle(img, (x, y), (x + w, y + h), TEXT, 3)
    for dy in (-h // 2, h // 2):
        cv2.rectangle(img, (x + w // 2 - 8, y + dy), (x + w // 2 + 8, y + dy + 8), TEXT, -1)


def _draw_capacitor(img: np.ndarray, spec: Dict[str, object]) -> None:
    x, y, w, h = int(spec["x"]), int(spec["y"]), int(spec["w"]), int(spec["h"])
    cx, cy = x + w // 2, y + h // 2
    cv2.ellipse(img, (cx, cy), (w // 2, h // 2), 0, 0, 360, TEXT, 2)
    cv2.rectangle(img, (x + 4, y - 6), (x + 14, y + h + 6), TEXT, -1)
    cv2.rectangle(img, (x + w - 14, y - 6), (x + w - 4, y + h + 6), TEXT, -1)


def _draw_chip(img: np.ndarray, spec: Dict[str, object]) -> None:
    x, y, w, h = int(spec["x"]), int(spec["y"]), int(spec["w"]), int(spec["h"])
    cv2.rectangle(img, (x, y), (x + w, y + h), TEXT, 2)
    # a few pins along the top and bottom edges
    for x0 in range(x + 8, x + w - 8, 22):
        cv2.line(img, (x0, y), (x0, y + 4), TEXT, 2)
        cv2.line(img, (x0, y + h), (x0, y + h - 4), TEXT, 2)


def _draw_diode(img: np.ndarray, spec: Dict[str, object]) -> None:
    x, y, w, h = int(spec["x"]), int(spec["y"]), int(spec["w"]), int(spec["h"])
    cx = x + w // 2
    pts = np.array([[cx, y], [x, y + h], [x + w, y + h]], np.int32)
    cv2.polylines(img, [pts], True, TEXT, 2)
    cv2.line(img, (x, y + 2), (x + w, y + 2), TEXT, 2)
    cv2.line(img, (cx, y + h), (cx, y + h - 6), TEXT, 2)


def _draw_led(img: np.ndarray, spec: Dict[str, object]) -> None:
    x, y, w, h = int(spec["x"]), int(spec["y"]), int(spec["w"]), int(spec["h"])
    cx, cy = x + w // 2, y + h // 2
    cv2.circle(img, (cx, cy), w // 2, TEXT, 2)
    cv2.circle(img, (cx, cy), max(w // 4, 2), TEXT, -1)


def build_reference_image(
    seed: int = 42,
    missing: Iterable[str] = (),
    brightness: float = 1.0,
    noise: float = 0.0,
    size: Tuple[int, int] = (W, H),
) -> np.ndarray:
    """Render the reference board as a BGR image."""
    w, h = size
    img = np.full((h, w, 3), BG, np.uint8)
    rng = np.random.default_rng(seed)

    # subtle texture, rich enough for ORB feature detection
    for _ in range(700):
        px, py = int(rng.integers(0, w)), int(rng.integers(0, h))
        c = int(rng.integers(36, 58))
        cv2.circle(img, (px, py), int(rng.integers(1, 3)), (c, c, c), -1)

    # PCB outline + fiducial markers (consistent across all images)
    cv2.rectangle(img, (8, 8), (w - 8, h - 8), (70, 70, 70), 3)
    for fx, fy in ((26, 26), (w - 26, 26), (26, h - 26), (w - 26, h - 26)):
        cv2.circle(img, (fx, fy), 10, (170, 170, 170), 2)

    missing_set = set(missing)
    for spec in component_specs():
        if spec["name"] in missing_set:
            continue
        shape = spec["shape"]
        if shape == "resistor":
            _draw_resistor(img, spec)
        elif shape == "capacitor":
            _draw_capacitor(img, spec)
        elif shape == "chip":
            _draw_chip(img, spec)
        elif shape == "diode":
            _draw_diode(img, spec)
        elif shape == "led":
            _draw_led(img, spec)

    if brightness != 1.0:
        img = np.clip(img.astype(np.float32) * brightness, 0, 255).astype(np.uint8)
    if noise > 0:
        img = np.clip(
            img.astype(np.int32) + rng.normal(0, noise, img.shape).astype(np.int32),
            0,
            255,
        ).astype(np.uint8)
    return img


def build_test_image(
    reference_img: np.ndarray,
    seed: int = 7,
    missing: Iterable[str] = (),
    brightness: float = 1.0,
    noise: float = 0.0,
    translate: Tuple[int, int] = (0, 0),
    scale: float = 1.0,
) -> np.ndarray:
    """Build a test image: same board/view as the reference, optionally modified."""
    img = build_reference_image(seed=seed, missing=missing, brightness=brightness, noise=noise)
    if scale != 1.0:
        h, w = img.shape[:2]
        bigger = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        img = cv2.resize(bigger, (w, h), interpolation=cv2.INTER_AREA)
    if translate != (0, 0):
        h, w = img.shape[:2]
        m = np.float32([[1, 0, translate[0]], [0, 1, translate[1]]])
        img = cv2.warpAffine(img, m, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=BG)
    return img


def _write_image(out_dir: Path, name: str, img: np.ndarray) -> Path:
    path = out_dir / name
    assert cv2.imwrite(str(path), img), f"failed to write {path}"
    return path


def generate_dataset(out_dir: Path) -> Dict[str, list]:
    """Generate the reference + test images; returns the manifest dictionary."""
    out_dir.mkdir(parents=True, exist_ok=True)

    reference = build_reference_image(seed=42)
    _write_image(out_dir, "reference.png", reference)

    specs = component_specs()
    manifest = {
        "generator": "backend/scripts/generate_dataset.py",
        "version": 1,
        "size": {"width": W, "height": H},
        "components": [
            {
                "name": s["name"],
                "shape": s["shape"],
                "x": round(float(s["x"]) / W, 6),
                "y": round(float(s["y"]) / H, 6),
                "width": round(float(s["w"]) / W, 6),
                "height": round(float(s["h"]) / H, 6),
            }
            for s in specs
        ],
    }
    (out_dir / "reference.json").write_text(json.dumps(manifest, indent=2) + "\n")

    cases = [
        ("test_01_complete.png", dict(seed=101, brightness=1.05, noise=3.0)),
        ("test_02_missing_c1_d2.png", dict(seed=102, missing=("C1", "D2"), noise=2.0)),
        ("test_03_missing_r2.png", dict(seed=103, missing=("R2",), brightness=0.97, noise=2.0)),
        ("test_04_translated_scaled.png", dict(seed=104, translate=(-30, 18), scale=1.04)),
        ("test_05_dark_noise_u2.png", dict(seed=105, missing=("U2",), brightness=0.88, noise=6.0)),
    ]
    for name, kwargs in cases:
        _write_image(out_dir, name, build_test_image(reference, **kwargs))

    print(f"Dataset written to {out_dir}")
    print(f"  reference: {reference.shape[1]}x{reference.shape[0]}")
    for name, _ in cases:
        img = cv2.imread(str(out_dir / name))
        print(f"  {name}: {img.shape[1]}x{img.shape[0]}")
    print(f"  components: {[c['name'] for c in manifest['components']]}")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic PCB dataset.")
    parser.add_argument("--out", default=str(_DEFAULT_OUT_DIR), help="Output directory")
    args = parser.parse_args()
    generate_dataset(Path(args.out).expanduser())


if __name__ == "__main__":
    main()
