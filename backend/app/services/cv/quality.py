# backend/app/services/cv/quality.py
"""
Lightweight, CPU-only document quality triage (docs/v2/COMPUTER_VISION.md's
"quality triage" stage, without the GPU-dependent layout models). Blur is
measured via Laplacian variance (a standard, cheap focus-quality proxy) and
skew via Hough-line angle estimation — both plain OpenCV, no trained model.

This is a deliberately narrow stand-in for the full CV pipeline described in
docs/v2 (LayoutLMv3/Donut/Table Transformer are GPU-dependent and deferred —
see docs/v2/ROADMAP.md's GPU upgrade phase).
"""
from __future__ import annotations

from typing import Any, Dict

import cv2
import numpy as np

from .utils import to_grayscale

BLUR_VARIANCE_THRESHOLD = 100.0
# A sanity floor only, not a resolution-quality signal: PyMuPDF's default
# pixmap render is ~72dpi, so a normal full page's pixel dimensions reflect
# render settings, not the source scan's actual quality (which the blur
# score, not dimensions, correctly captures at any fixed render DPI). This
# just catches genuinely degenerate/corrupt renders (e.g. a stray tiny crop).
MIN_DIMENSION_PX = 50


def assess_image_quality(image_array: np.ndarray) -> Dict[str, Any]:
    gray = to_grayscale(image_array)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    skew_angle = _estimate_skew_angle(gray)
    height, width = gray.shape[:2]

    is_low_quality = blur_score < BLUR_VARIANCE_THRESHOLD or min(width, height) < MIN_DIMENSION_PX

    return {
        "blur_score": round(blur_score, 2),
        "skew_angle_degrees": round(skew_angle, 2),
        "width": int(width),
        "height": int(height),
        "is_low_quality": bool(is_low_quality),
    }


def _estimate_skew_angle(gray: np.ndarray) -> float:
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=150, minLineLength=100, maxLineGap=10)
    if lines is None:
        return 0.0

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if -45 < angle < 45:  # ignore near-vertical lines (table borders, margins)
            angles.append(angle)

    return float(np.median(angles)) if angles else 0.0
