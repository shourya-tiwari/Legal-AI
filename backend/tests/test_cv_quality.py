import numpy as np

from app.services.cv.quality import assess_image_quality
from app.services.cv.redaction import detect_redacted_regions
from app.services.cv.utils import to_grayscale


def test_sharp_high_frequency_image_is_not_low_quality():
    checkerboard = np.zeros((800, 800, 3), dtype=np.uint8)
    checkerboard[::2, ::2] = 255

    result = assess_image_quality(checkerboard)
    assert result["is_low_quality"] is False
    assert result["blur_score"] > 100.0


def test_flat_image_is_flagged_low_quality():
    flat = np.full((800, 800, 3), 128, dtype=np.uint8)

    result = assess_image_quality(flat)
    assert result["is_low_quality"] is True
    assert result["blur_score"] == 0.0


def test_sharp_but_normal_page_sized_image_is_not_flagged_by_dimensions_alone():
    # A standard page rendered at PyMuPDF's default ~72dpi is ~595x842px --
    # well below any "real scan resolution" threshold even for a perfectly
    # sharp page, since render DPI (not source quality) drives pixel size.
    # The dimension check must not fire on ordinary page sizes like this.
    page_sized_checkerboard = np.zeros((842, 595, 3), dtype=np.uint8)
    page_sized_checkerboard[::2, ::2] = 255

    result = assess_image_quality(page_sized_checkerboard)
    assert result["is_low_quality"] is False


def test_degenerate_tiny_image_is_flagged_low_quality():
    tiny = np.zeros((20, 20, 3), dtype=np.uint8)
    tiny[::2, ::2] = 255

    result = assess_image_quality(tiny)
    assert result["is_low_quality"] is True


def test_detects_a_solid_black_rectangle_as_a_redacted_region():
    image = np.full((400, 400, 3), 255, dtype=np.uint8)
    image[100:150, 50:250] = 0  # a 200x50 solid black block

    regions = detect_redacted_regions(image)
    assert len(regions) == 1
    assert regions[0]["width"] == 200
    assert regions[0]["height"] == 50


def test_no_redacted_regions_on_a_blank_page():
    image = np.full((400, 400, 3), 255, dtype=np.uint8)
    assert detect_redacted_regions(image) == []


def test_to_grayscale_handles_rgb_rgba_and_already_gray():
    rgb = np.zeros((10, 10, 3), dtype=np.uint8)
    rgba = np.zeros((10, 10, 4), dtype=np.uint8)
    gray = np.zeros((10, 10), dtype=np.uint8)

    assert to_grayscale(rgb).shape == (10, 10)
    assert to_grayscale(rgba).shape == (10, 10)
    assert to_grayscale(gray).shape == (10, 10)
