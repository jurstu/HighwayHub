from dataclasses import dataclass
from math import atan2, ceil, degrees, hypot, pi

import cv2


@dataclass(frozen=True)
class ReferenceLine:
    start: tuple[int, int]
    end: tuple[int, int]
    angle: float
    weight: float


class LpDeskew:
    """Straighten a plate using its near-horizontal edges and text strokes."""

    def find_reference_lines(self, image) -> list[ReferenceLine]:
        if image is None or image.size == 0:
            raise ValueError("image must be a non-empty OpenCV image")

        if image.ndim == 2:
            gray = image
        elif image.ndim == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif image.ndim == 3 and image.shape[2] == 4:
            gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        else:
            raise ValueError("image must be grayscale, BGR, or BGRA")

        width = gray.shape[1]
        edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 50, 150)
        segments = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=pi / 180,
            threshold=max(8, round(width * 0.1)),
            minLineLength=max(8, round(width * 0.2)),
            maxLineGap=max(2, round(width * 0.05)),
        )

        references = []
        if segments is None:
            return references

        for x1, y1, x2, y2 in segments.reshape(-1, 4):
            dx, dy = int(x2 - x1), int(y2 - y1)
            # A line has no direction: both endpoint orders must give the same angle.
            angle = (degrees(atan2(dy, dx)) + 90) % 180 - 90
            if -40 <= angle <= 40:
                references.append(
                    ReferenceLine(
                        start=(int(x1), int(y1)),
                        end=(int(x2), int(y2)),
                        angle=angle,
                        weight=hypot(dx, dy),
                    )
                )
        return references

    def estimate_angle(self, image) -> float:
        """Return the length-weighted angle of the dominant line direction."""
        references = self.find_reference_lines(image)
        if not references:
            return 0.0

        # Pick the dominant direction first so unrelated lines do not cancel it.
        ordered = sorted(references, key=lambda line: line.angle)
        half_weight = sum(line.weight for line in ordered) / 2
        cumulative_weight = 0.0
        median_angle = ordered[-1].angle
        for line in ordered:
            cumulative_weight += line.weight
            if cumulative_weight >= half_weight:
                median_angle = line.angle
                break

        inliers = [line for line in references if abs(line.angle - median_angle) <= 5]
        total_weight = sum(line.weight for line in inliers)
        return sum(line.angle * line.weight for line in inliers) / total_weight

    def deskew(self, image):
        """Return a rotated copy of image, retaining the full rotated canvas."""
        angle = self.estimate_angle(image)
        if abs(angle) < 0.01:
            return image.copy()

        height, width = image.shape[:2]
        rotation = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)
        new_width = ceil(height * abs(rotation[0, 1]) + width * abs(rotation[0, 0]))
        new_height = ceil(height * abs(rotation[0, 0]) + width * abs(rotation[0, 1]))
        rotation[0, 2] += (new_width - width) / 2
        rotation[1, 2] += (new_height - height) / 2
        return cv2.warpAffine(
            image,
            rotation,
            (new_width, new_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )
