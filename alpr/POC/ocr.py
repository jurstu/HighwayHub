import re

import cv2
from rapidocr import RapidOCR

class Ocr:
    def __init__(self):
        self.engine = RapidOCR()

    @staticmethod
    def format_plate(text):
        """Keep plate characters and restore the space after the region prefix."""
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

    def _recognize(self, image):
        # The plate finder has already isolated the plate. RapidOCR's text
        # detector often misses short or blurred crops, so read the whole crop.
        result = self.engine(image, use_det=False)
        if not result.txts:
            return None, 0.0
        return self.format_plate(result.txts[0]), float(result.scores[0])

    def process(self, img, original=None):
        """Return the best OCR view and a tuple of recognized plate texts."""
        source = original if original is not None else img
        best_image = source
        best_text, best_score = self._recognize(source)

        if best_score < 0.9 or best_text is None:
            gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY) if source.ndim == 3 else source
            contrast = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 2)).apply(gray)
            candidates = [contrast]
            if original is not None and (img.shape != source.shape or not (img == source).all()):
                candidates.append(img)

            for candidate in candidates:
                text, score = self._recognize(candidate)
                if text is not None and (best_text is None or score > best_score):
                    best_image, best_text, best_score = candidate, text, score

        if best_image.ndim == 2:
            best_image = cv2.cvtColor(best_image, cv2.COLOR_GRAY2BGR)
        return best_image, (best_text,) if best_text is not None and best_score >= 0.5 else None
