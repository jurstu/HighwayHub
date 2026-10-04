"""Classical OpenCV license-plate candidate detection."""

from __future__ import annotations

import cv2
import numpy as np

from .geometry import perspective_crop
from .models import Image, PlateCandidate, Points


class PlateDetector:
    def __init__(self, max_dimension: int = 1600, max_candidates: int = 12) -> None:
        self.max_dimension = max_dimension
        self.max_candidates = max_candidates

    def detect(self, image: Image) -> list[PlateCandidate]:
        if image is None or image.size == 0:
            return []
        working, scale = self._resize(image)
        gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY) if working.ndim == 3 else working
        gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        masks = self._candidate_masks(gray)
        contours: list[np.ndarray] = []
        for mask in masks:
            found, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            contours.extend(found)

        ranked: list[tuple[float, Points, tuple[int, int, int, int]]] = []
        seen: list[tuple[int, int, int, int]] = []
        image_area = gray.shape[0] * gray.shape[1]
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:500]:
            item = self._score_contour(contour, gray, image_area)
            if item is None:
                continue
            score, corners, bbox = item
            if any(self._iou(bbox, existing) > 0.55 for existing in seen):
                continue
            seen.append(bbox)
            ranked.append((score, corners, bbox))
        ranked.sort(key=lambda item: item[0], reverse=True)

        results: list[PlateCandidate] = []
        for score, corners, bbox in ranked[: self.max_candidates]:
            original_corners = corners / scale
            try:
                crop = perspective_crop(image, original_corners)
            except (ValueError, cv2.error):
                continue
            x, y, width, height = bbox
            original_bbox = tuple(int(round(value / scale)) for value in (x, y, width, height))
            results.append(PlateCandidate(original_corners, crop, score, original_bbox))
        return results

    def _resize(self, image: Image) -> tuple[Image, float]:
        height, width = image.shape[:2]
        scale = min(1.0, self.max_dimension / max(height, width))
        if scale == 1.0:
            return image, scale
        resized = cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)
        return resized, scale

    @staticmethod
    def _candidate_masks(gray: Image) -> list[Image]:
        width = gray.shape[1]
        horizontal = max(13, (width // 40) | 1)
        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal, 5))
        close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(9, horizontal // 2), 3))

        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, rect_kernel)
        gradient = cv2.Sobel(blackhat, cv2.CV_32F, 1, 0, ksize=3)
        gradient = cv2.convertScaleAbs(gradient)
        _, gradient = cv2.threshold(gradient, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        gradient = cv2.morphologyEx(gradient, cv2.MORPH_CLOSE, rect_kernel, iterations=2)

        bright = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, rect_kernel)
        _, bright = cv2.threshold(bright, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        bright = cv2.morphologyEx(bright, cv2.MORPH_CLOSE, close_kernel, iterations=2)

        edges = cv2.Canny(gray, 60, 180)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, rect_kernel, iterations=2)
        for mask in (gradient, bright, edges):
            cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), dst=mask)
        return [gradient, bright, edges]

    @staticmethod
    def _score_contour(
        contour: np.ndarray, gray: Image, image_area: int
    ) -> tuple[float, Points, tuple[int, int, int, int]] | None:
        area = cv2.contourArea(contour)
        if area < image_area * 0.00008 or area > image_area * 0.12:
            return None
        rectangle = cv2.minAreaRect(contour)
        rect_width, rect_height = rectangle[1]
        if min(rect_width, rect_height) < 8:
            return None
        long_side, short_side = max(rect_width, rect_height), min(rect_width, rect_height)
        aspect = long_side / short_side
        if not 1.7 <= aspect <= 8.5:
            return None
        rect_area = rect_width * rect_height
        rectangularity = min(1.0, area / max(rect_area, 1.0))
        if rectangularity < 0.25:
            return None
        corners = cv2.boxPoints(rectangle).astype(np.float32)
        x, y, width, height = cv2.boundingRect(corners.astype(np.int32))
        x, y = max(0, x), max(0, y)
        roi = gray[y : min(gray.shape[0], y + height), x : min(gray.shape[1], x + width)]
        if roi.size == 0:
            return None
        edge_density = float(np.count_nonzero(cv2.Canny(roi, 60, 180))) / roi.size
        brightness = float(np.mean(roi)) / 255.0
        aspect_score = float(np.exp(-abs(aspect - 4.5) / 3.0))
        size_score = min(1.0, area / (image_area * 0.004))
        score = 0.34 * aspect_score + 0.25 * rectangularity + 0.2 * min(1.0, edge_density * 5) + 0.11 * brightness + 0.1 * size_score
        return score, corners, (x, y, width, height)

    @staticmethod
    def _iou(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> float:
        ax, ay, aw, ah = first
        bx, by, bw, bh = second
        intersection_width = max(0, min(ax + aw, bx + bw) - max(ax, bx))
        intersection_height = max(0, min(ay + ah, by + bh) - max(ay, by))
        intersection = intersection_width * intersection_height
        union = aw * ah + bw * bh - intersection
        return intersection / union if union else 0.0