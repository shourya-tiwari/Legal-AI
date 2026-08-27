# backend/app/services/cv/redaction.py
"""
Heuristic redaction-region detection: finds solid black rectangular blocks,
the overwhelmingly common visual pattern for a redaction in a scanned legal
document. This is contour/fill-ratio geometry, not a trained model — a
deliberately narrow stand-in for a learned redaction detector (see
docs/v2/COMPUTER_VISION.md and the GPU upgrade phase in docs/v2/ROADMAP.md).

False positives are possible (e.g. a solid black logo or table cell); this is
a screening signal, not a certified redaction audit.
"""
from __future__ import annotations

from typing import Any, Dict, List

import cv2
import numpy as np

from .utils import to_grayscale

MIN_REGION_AREA_PX = 500
MIN_FILL_RATIO = 0.85


def detect_redacted_regions(image_array: np.ndarray) -> List[Dict[str, Any]]:
    gray = to_grayscale(image_array)
    _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < MIN_REGION_AREA_PX:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        fill_ratio = area / float(w * h) if w * h else 0.0
        if fill_ratio >= MIN_FILL_RATIO and w > 20 and h > 8:
            regions.append({"x": int(x), "y": int(y), "width": int(w), "height": int(h)})

    return regions
