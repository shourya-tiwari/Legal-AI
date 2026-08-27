# backend/app/services/cv/utils.py
"""Shared helpers for the CV pipeline. No PIL dependency: PyMuPDF pixmaps
convert straight to numpy arrays, which is all OpenCV needs."""
from __future__ import annotations

import numpy as np


def pixmap_to_array(pix) -> np.ndarray:
    """Converts a PyMuPDF (fitz) Pixmap into an (H, W, channels) uint8 array."""
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)


def to_grayscale(image_array: np.ndarray):
    import cv2

    if image_array.ndim == 2:
        return image_array
    channels = image_array.shape[2]
    if channels == 1:
        return image_array[:, :, 0]
    if channels == 4:
        return cv2.cvtColor(image_array, cv2.COLOR_RGBA2GRAY)
    return cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
