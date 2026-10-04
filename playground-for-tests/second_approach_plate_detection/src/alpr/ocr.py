"""Lazy EasyOCR adapter and plate-text normalization."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, Protocol

import cv2
import numpy as np

from .models import Image, OCRResult

ALLOWED_CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


class OCRBackend(Protocol):
    def recognize(self, image: Image) -> list[OCRResult]: ...


def compact_text(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def normalize_text(text: str) -> str:
    cleaned = re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()
    return re.sub(r"\s+", " ", cleaned)


class EasyOCRBackend:
    def __init__(
        self,
        languages: tuple[str, ...] = ("en",),
        gpu: bool = False,
        reader_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.languages = languages
        self.gpu = gpu
        self.reader_factory = reader_factory
        self._reader: Any = None

    def _get_reader(self) -> Any:
        if self._reader is None:
            if self.reader_factory is None:
                import easyocr

                factory = easyocr.Reader
            else:
                factory = self.reader_factory
            self._reader = factory(list(self.languages), gpu=self.gpu)
        return self._reader

    def recognize(self, image: Image) -> list[OCRResult]:
        reader = self._get_reader()
        results: list[OCRResult] = []
        for variant in self._variants(image):
            raw_results = reader.readtext(
                variant,
                allowlist=ALLOWED_CHARACTERS,
                detail=1,
                paragraph=False,
                decoder="greedy",
            )
            for item in raw_results:
                if len(item) < 3:
                    continue
                text = normalize_text(str(item[1]))
                confidence = float(item[2])
                compact = compact_text(text)
                if 3 <= len(compact) <= 10:
                    results.append(OCRResult(text, confidence))
        best_by_text: dict[str, OCRResult] = {}
        for result in results:
            key = compact_text(result.text)
            if key not in best_by_text or result.confidence > best_by_text[key].confidence:
                best_by_text[key] = result
        return sorted(best_by_text.values(), key=lambda result: result.confidence, reverse=True)

    @staticmethod
    def _variants(image: Image) -> list[Image]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        sharpened = cv2.addWeighted(gray, 1.8, cv2.GaussianBlur(gray, (0, 0), 1.2), -0.8, 0)
        thresholded = cv2.adaptiveThreshold(
            sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
        )
        return [gray, sharpened, thresholded]
