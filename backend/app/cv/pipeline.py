"""Board-level inspection pipeline: align -> compare -> detect."""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from . import aligner, detector


def inspect_board(
    ref_gray: np.ndarray,
    test_gray: np.ndarray,
    specs: List[detector.ComponentSpec],
    thresholds: Optional[Dict[str, float]] = None,
) -> detector.BoardInspection:
    """Run the full inspection for one test image against the reference."""
    aligned, ok = aligner.register_images(ref_gray, test_gray)
    return detector.BoardInspection(
        results=detector.compare_components(
            ref_gray, aligned, specs, thresholds=thresholds, alignment_ok=ok
        ),
        alignment_ok=ok,
    )
