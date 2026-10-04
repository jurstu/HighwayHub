"""High-level ALPR orchestration."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .config import discover_images, load_labels
from .detector import PlateDetector
from .models import ImageResult, OCRResult, PlateCandidate
from .ocr import OCRBackend, compact_text


class ALPRPipeline:
    def __init__(self, detector: PlateDetector | None = None, ocr: OCRBackend | None = None) -> None:
        self.detector = detector or PlateDetector()
        self.ocr = ocr

    def process_path(self, path: Path, expected: str | None = None) -> ImageResult:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            return ImageResult(path=path, expected=expected, error="image could not be decoded")
        candidates = self.detector.detect(image)
        if not candidates:
            return ImageResult(path=path, expected=expected, error="no plate candidate detected")
        if self.ocr is None:
            candidate = candidates[0]
            return ImageResult(path=path, detector_score=candidate.score, candidate=candidate, expected=expected)

        scored: list[tuple[float, PlateCandidate, OCRResult, list[OCRResult]]] = []
        try:
            for candidate in candidates:
                alternatives = self.ocr.recognize(candidate.crop)
                if alternatives:
                    best = alternatives[0]
                    combined = 0.75 * best.confidence + 0.25 * candidate.score
                    scored.append((combined, candidate, best, alternatives))
        except Exception as exc:
            return ImageResult(path=path, candidate=candidates[0], expected=expected, error=f"OCR failed: {exc}")
        if not scored:
            candidate = candidates[0]
            return ImageResult(
                path=path,
                detector_score=candidate.score,
                candidate=candidate,
                expected=expected,
                error="plate detected but no text recognized",
            )
        combined, candidate, best, alternatives = max(scored, key=lambda item: item[0])
        return ImageResult(
            path=path,
            text=best.text,
            confidence=best.confidence,
            detector_score=candidate.score,
            candidate=candidate,
            expected=expected,
            alternatives=alternatives,
        )

    def process_directory(self, data_path: Path) -> list[ImageResult]:
        labels = load_labels(data_path)
        return [self.process_path(path, labels.get(path.name)) for path in discover_images(data_path)]

    @staticmethod
    def save_debug(result: ImageResult, output_dir: Path) -> None:
        if result.candidate is None:
            return
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = result.path.stem
        cv2.imwrite(str(output_dir / f"{stem}_plate.png"), result.candidate.crop)
        image = cv2.imread(str(result.path), cv2.IMREAD_COLOR)
        if image is None:
            return
        corners = np.round(result.candidate.corners).astype(np.int32)
        cv2.polylines(image, [corners], True, (0, 255, 0), 3)
        label = result.text or "plate"
        x, y = corners[:, 0].min(), max(24, corners[:, 1].min() - 8)
        cv2.putText(image, label, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imwrite(str(output_dir / f"{stem}_annotated.jpg"), image)


def is_exact_match(result: ImageResult) -> bool:
    return result.expected is not None and compact_text(result.text) == compact_text(result.expected)
