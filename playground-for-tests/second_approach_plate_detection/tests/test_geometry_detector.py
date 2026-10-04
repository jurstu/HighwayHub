import cv2
import numpy as np

from alpr.detector import PlateDetector
from alpr.geometry import order_points, perspective_crop


def make_synthetic_plate() -> np.ndarray:
    image = np.full((480, 800, 3), 45, dtype=np.uint8)
    source = np.full((100, 440, 3), 245, dtype=np.uint8)
    cv2.rectangle(source, (2, 2), (437, 97), (20, 20, 20), 4)
    cv2.putText(source, "WX 1234A", (30, 72), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (10, 10, 10), 4)
    destination = np.float32([[170, 180], [650, 140], [670, 265], [145, 290]])
    matrix = cv2.getPerspectiveTransform(np.float32([[0, 0], [439, 0], [439, 99], [0, 99]]), destination)
    warped = cv2.warpPerspective(source, matrix, (800, 480))
    mask = cv2.warpPerspective(np.full((100, 440), 255, dtype=np.uint8), matrix, (800, 480))
    image[mask > 0] = warped[mask > 0]
    return image


def test_order_points_and_perspective_crop() -> None:
    points = np.float32([[390, 80], [40, 110], [420, 190], [20, 210]])
    ordered = order_points(points)
    assert np.allclose(ordered[0], [40, 110])
    image = np.full((260, 480, 3), 255, dtype=np.uint8)
    crop = perspective_crop(image, points)
    assert crop.shape[1] > crop.shape[0]
    assert crop.shape[0] >= 80


def test_detector_finds_synthetic_skewed_plate() -> None:
    candidates = PlateDetector(max_candidates=5).detect(make_synthetic_plate())
    assert candidates
    assert any(candidate.crop.shape[1] / candidate.crop.shape[0] > 2.0 for candidate in candidates)
