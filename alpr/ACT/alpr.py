"""Single-image Polish ALPR: a NumPy image in, one plate string out.

Dependencies: numpy, opencv-python, ultralytics, rapidocr, huggingface_hub.
Images are uint8 OpenCV arrays (BGR, BGRA, or grayscale). The model is cached
by Hugging Face Hub after the first download.
"""

from math import atan2, ceil, degrees, hypot, pi
from pathlib import Path
import re

import cv2
import numpy as np
from huggingface_hub import hf_hub_download
from rapidocr import RapidOCR
from ultralytics import YOLO


class ALPR:
    """Detect and read the strongest valid license plate in an image.

    Example:
        alpr = ALPR()
        plate = alpr.predict(cv2.imread("car.jpg"))  # e.g. "CT 730FA"

    Returns None if no detection passes OCR. If the image has several plates,
    the result with the highest detector-confidence × OCR-confidence wins.
    """

    MODEL_REPO = "morsetechlab/yolov11-license-plate-detection"
    MODEL_FILE = "license-plate-finetune-v1n.pt"
    MODEL_REVISION = "251a30d7daedca065f56e04b0af04052c907c68f"

    def __init__(
        self,
        model_path: str | Path | None = None,
        *,
        detection_confidence: float = 0.25,
        ocr_confidence: float = 0.5,
        image_size: int = 1280,
    ) -> None:
        if not 0 <= detection_confidence <= 1 or not 0 <= ocr_confidence <= 1:
            raise ValueError("confidence thresholds must be between 0 and 1")
        if image_size <= 0:
            raise ValueError("image_size must be positive")

        if model_path is None:
            model_path = hf_hub_download(
                repo_id=self.MODEL_REPO,
                filename=self.MODEL_FILE,
                revision=self.MODEL_REVISION,
            )
        self.detector = YOLO(str(model_path))
        self.ocr = RapidOCR()
        self.detection_confidence = detection_confidence
        self.ocr_confidence = ocr_confidence
        self.image_size = image_size

    @staticmethod
    def _format_plate(text: str) -> str | None:
        plate = re.sub(r"[^A-Z0-9]", "", text.upper())
        if not 4 <= len(plate) <= 8:
            return None

        if re.fullmatch(r"[A-Z][0-9][A-Z]{3}", plate):
            prefix_length = 2  # Temporary plates, e.g. S6 EVA.
        else:
            prefix = re.match(r"[A-Z]{1,3}", plate)
            if prefix is None:
                return None
            prefix_length = len(prefix.group())

        if prefix_length == len(plate):
            return None
        return f"{plate[:prefix_length]} {plate[prefix_length:]}"

    def _recognize(self, image: np.ndarray) -> tuple[str | None, float]:
        # Detection is already done by YOLO; read the entire crop as one line.
        result = self.ocr(image, use_det=False)
        if not result.txts:
            return None, 0.0
        return self._format_plate(result.txts[0]), float(result.scores[0])

    @staticmethod
    def _deskew(image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 50, 150)
        segments = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=pi / 180,
            threshold=max(8, round(width * 0.1)),
            minLineLength=max(8, round(width * 0.2)),
            maxLineGap=max(2, round(width * 0.05)),
        )
        if segments is None:
            return image

        directions = []
        for x1, y1, x2, y2 in segments.reshape(-1, 4):
            dx, dy = int(x2 - x1), int(y2 - y1)
            angle = (degrees(atan2(dy, dx)) + 90) % 180 - 90
            if -40 <= angle <= 40:
                directions.append((angle, hypot(dx, dy)))
        if not directions:
            return image

        ordered = sorted(directions)
        halfway = sum(weight for _, weight in ordered) / 2
        accumulated = 0.0
        median = ordered[-1][0]
        for angle, weight in ordered:
            accumulated += weight
            if accumulated >= halfway:
                median = angle
                break
        inliers = [(angle, weight) for angle, weight in directions if abs(angle - median) <= 5]
        angle = sum(a * w for a, w in inliers) / sum(w for _, w in inliers)
        if abs(angle) < 0.01:
            return image

        rotation = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)
        new_width = ceil(height * abs(rotation[0, 1]) + width * abs(rotation[0, 0]))
        new_height = ceil(height * abs(rotation[0, 0]) + width * abs(rotation[0, 1]))
        rotation[0, 2] += (new_width - width) / 2
        rotation[1, 2] += (new_height - height) / 2
        return cv2.warpAffine(
            image, rotation, (new_width, new_height),
            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE,
        )

    def _read_crop(self, crop: np.ndarray) -> tuple[str | None, float]:
        text, score = self._recognize(crop)
        if text is not None and score >= 0.9:
            return text, score

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        contrast = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 2)).apply(gray)
        straightened = self._deskew(crop)
        candidates = [contrast]
        if straightened is not crop:
            candidates.append(straightened)

        for candidate in candidates:
            candidate_text, candidate_score = self._recognize(candidate)
            if candidate_text is not None and (text is None or candidate_score > score):
                text, score = candidate_text, candidate_score
        return text, score

    def predict(self, image: np.ndarray) -> str | None:
        """Return a formatted plate number, or None when no plate can be read."""
        plate, _ = self.predict_with_box(image)
        return plate

    def predict_with_box(
        self, image: np.ndarray
    ) -> tuple[str | None, tuple[int, int, int, int] | None]:
        """Return the plate text and its (x1, y1, x2, y2) image coordinates.

        If detection succeeds but OCR does not, return (None, strongest box).
        """
        if not isinstance(image, np.ndarray):
            raise TypeError("image must be a NumPy array")
        if image.dtype != np.uint8 or image.ndim not in (2, 3) or image.size == 0:
            raise ValueError("image must be a non-empty uint8 grayscale, BGR, or BGRA array")
        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.shape[2] == 1:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        elif image.shape[2] != 3:
            raise ValueError("image must have 1, 3, or 4 channels")
        image = np.ascontiguousarray(image)

        results = self.detector.predict(
            source=image,
            conf=self.detection_confidence,
            imgsz=self.image_size,
            save=False,
            verbose=False,
        )
        if not results:
            return None, None

        best_text, best_box, best_score = None, None, -1.0
        fallback_box, fallback_score = None, -1.0
        height, width = image.shape[:2]
        for box in results[0].boxes:
            x1, y1, x2, y2 = (int(value) for value in box.xyxy[0])
            x1, x2 = max(0, x1), min(width, x2)
            y1, y2 = max(0, y1), min(height, y2)
            if x1 >= x2 or y1 >= y2:
                continue

            coordinates = (x1, y1, x2, y2)
            detection_score = float(box.conf[0])
            if detection_score > fallback_score:
                fallback_box, fallback_score = coordinates, detection_score

            text, ocr_score = self._read_crop(image[y1:y2, x1:x2])
            if text is None or ocr_score < self.ocr_confidence:
                continue
            combined_score = detection_score * ocr_score
            if combined_score > best_score:
                best_text, best_box, best_score = text, coordinates, combined_score
        return best_text, best_box if best_box is not None else fallback_box

    __call__ = predict
