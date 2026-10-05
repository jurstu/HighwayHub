"""POC: NumPy BGR image -> detected crop -> deskew -> OCR -> annotations."""

from pathlib import Path
import math

import cv2
import numpy as np

if __package__:
    from .find_license_plates import LpFinder
    from .read_images import ImageReader
    from .deskew_license_plates import LpDeskew
    from .ocr import Ocr
else:
    from find_license_plates import LpFinder
    from read_images import ImageReader
    from deskew_license_plates import LpDeskew
    from ocr import Ocr


TILE_WIDTH = 400
TILE_HEIGHT = 200
OUTPUT_DIR = Path(__file__).parent / "output"


def mosaic_tile(image, filename, detection_index, texts):
    """Show a plate crop with its source and recognized text below it."""
    tile = np.full((TILE_HEIGHT, TILE_WIDTH, 3), 28, dtype=np.uint8)
    cv2.putText(
        tile, f"{filename}  /  detection {detection_index}", (12, 23),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (190, 190, 190), 1, cv2.LINE_AA,
    )

    available_width, available_height = TILE_WIDTH - 24, 112
    height, width = image.shape[:2]
    scale = min(available_width / width, available_height / height)
    interpolation = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    plate = cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=interpolation)
    x = (TILE_WIDTH - plate.shape[1]) // 2
    y = 34 + (available_height - plate.shape[0]) // 2
    tile[y:y + plate.shape[0], x:x + plate.shape[1]] = plate

    caption = ", ".join(texts) if texts else "No text detected"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.9
    text_width = cv2.getTextSize(caption, font, font_scale, 2)[0][0]
    if text_width > TILE_WIDTH - 24:
        font_scale *= (TILE_WIDTH - 24) / text_width
        text_width = cv2.getTextSize(caption, font, font_scale, 2)[0][0]
    cv2.putText(
        tile, caption, ((TILE_WIDTH - text_width) // 2, 182),
        font, font_scale, (255, 255, 255), 2, cv2.LINE_AA,
    )
    return tile


def annotate_image(image, filename, finder, deskewer, reader):
    """Return an annotated copy of a NumPy BGR image and its labeled crops."""
    annotated = image.copy()
    tiles = []
    height, width = image.shape[:2]

    for index, box in enumerate(finder.infere(image)[0].boxes):
        x1, y1, x2, y2 = (int(value) for value in box.xyxy[0])
        x1, x2 = max(0, x1), min(width, x2)
        y1, y2 = max(0, y1), min(height, y2)
        if x1 >= x2 or y1 >= y2:
            continue

        crop = image[y1:y2, x1:x2]
        straightened = deskewer.deskew(crop)
        ocr_view, texts = reader.process(straightened, original=crop)
        tiles.append(mosaic_tile(ocr_view, filename, index, texts))

        label = ", ".join(texts) if texts else "Unreadable"
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 220, 0), 2)
        label_size, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        label_x = min(x1, max(0, width - label_size[0] - 8))
        label_y = max(label_size[1] + 8, y1 - 6)
        cv2.rectangle(
            annotated,
            (label_x, label_y - label_size[1] - 6),
            (label_x + label_size[0] + 8, label_y + baseline),
            (0, 120, 0), -1,
        )
        cv2.putText(
            annotated, label, (label_x + 4, label_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA,
        )
        print(f"{filename} detection {index}: {texts}")

    return annotated, tiles


def main():
    records = ImageReader().load()
    finder, deskewer, reader = LpFinder(), LpDeskew(), Ocr()
    OUTPUT_DIR.mkdir(exist_ok=True)
    tiles = []

    for record in records:
        filename = record["just_filename"]
        annotated, crops = annotate_image(record["image"], filename, finder, deskewer, reader)
        tiles.extend(crops)
        output_file = OUTPUT_DIR / f"{Path(filename).stem}_annotated.png"
        if not cv2.imwrite(str(output_file), annotated):
            raise OSError(f"Could not write {output_file}")

    if tiles:
        side = math.ceil(math.sqrt(len(tiles)))
        blank = np.full_like(tiles[0], 28)
        tiles.extend([blank] * (side * side - len(tiles)))
        mosaic = np.vstack([
            np.hstack(tiles[row * side:(row + 1) * side])
            for row in range(side)
        ])
        output_file = OUTPUT_DIR / "mosaic.png"
        if not cv2.imwrite(str(output_file), mosaic):
            raise OSError(f"Could not write {output_file}")


if __name__ == "__main__":
    main()
