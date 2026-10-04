"""Shared data structures for the ALPR pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

Image = NDArray[np.uint8]
Points = NDArray[np.float32]


@dataclass(slots=True)
class PlateCandidate:
    corners: Points
    crop: Image
    score: float
    bbox: tuple[int, int, int, int]


@dataclass(slots=True)
class OCRResult:
    text: str
    confidence: float


@dataclass(slots=True)
class ImageResult:
    path: Path
    text: str = ""
    confidence: float = 0.0
    detector_score: float = 0.0
    candidate: PlateCandidate | None = None
    expected: str | None = None
    error: str | None = None
    alternatives: list[OCRResult] = field(default_factory=list)

    @property
    def detected(self) -> bool:
        return self.candidate is not None
