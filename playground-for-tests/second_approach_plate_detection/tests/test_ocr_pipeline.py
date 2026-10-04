from pathlib import Path

import cv2
import numpy as np

from alpr.detector import PlateDetector
from alpr.models import OCRResult, PlateCandidate
from alpr.ocr import EasyOCRBackend, compact_text, normalize_text
from alpr.pipeline import ALPRPipeline, is_exact_match


class StubDetector(PlateDetector):
    def detect(self, image: np.ndarray) -> list[PlateCandidate]:
        corners = np.float32([[10, 10], [190, 10], [190, 60], [10, 60]])
        return [PlateCandidate(corners, image[10:60, 10:190], 0.8, (10, 10, 180, 50))]


class StubOCR:
    def recognize(self, image: np.ndarray) -> list[OCRResult]:
        return [OCRResult("AB 123CD", 0.93)]


def test_text_normalization() -> None:
    assert normalize_text(" ab-123.cd ") == "AB 123 CD"
    assert compact_text("AB 123-CD") == "AB123CD"


def test_easyocr_is_lazy_and_deduplicates_variants() -> None:
    calls = []

    class Reader:
        def readtext(self, image: np.ndarray, **kwargs: object) -> list[tuple[list[int], str, float]]:
            return [([], "ab-123", 0.88)]

    def factory(languages: list[str], gpu: bool) -> Reader:
        calls.append((languages, gpu))
        return Reader()

    backend = EasyOCRBackend(reader_factory=factory)
    assert calls == []
    results = backend.recognize(np.full((80, 240, 3), 255, dtype=np.uint8))
    assert calls == [(["en"], False)]
    assert results == [OCRResult("AB 123", 0.88)]


def test_pipeline_with_injected_ocr(tmp_path: Path) -> None:
    path = tmp_path / "car.png"
    cv2.imwrite(str(path), np.full((100, 220, 3), 200, dtype=np.uint8))
    result = ALPRPipeline(StubDetector(), StubOCR()).process_path(path, "AB123CD")
    assert result.text == "AB 123CD"
    assert is_exact_match(result)
    assert result.error is None
