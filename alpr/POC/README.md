# ALPR proof of concept

The existing prototype is collected here. Its path from a NumPy image to an
annotated result is:

1. `read_images.py` loads BGR `uint8` images from the directory named in `path`.
2. `find_license_plates.py` detects plate boxes with the YOLO model.
3. `main.py` crops each box and passes it to `deskew_license_plates.py`.
4. `ocr.py` reads the crop with RapidOCR, trying contrast and deskewed views
   when the first reading is weak, and formats the plate text.
5. `main.py` draws boxes and text on the source image and assembles a labeled
   crop mosaic in `output/`. `mosaic.png` is the previously saved example.

Install dependencies with `python -m pip install -r POC/requirements.txt`.
Set `POC/path` to a directory containing `plates.json` and its referenced
images, then run `python POC/main.py` from the repository root. The model is
downloaded on first use and cached by Hugging Face Hub. Outputs are written
to `POC/output/`; that directory is ignored by Git.

For a NumPy image already in memory, call the POC steps directly:

```python
from POC.main import annotate_image
from POC.find_license_plates import LpFinder
from POC.deskew_license_plates import LpDeskew
from POC.ocr import Ocr

annotated, plate_tiles = annotate_image(image, "frame", LpFinder(), LpDeskew(), Ocr())
```

For application use, `ACT/alpr.py` has one `ALPR` class. Example:

```python
import cv2
from ACT.alpr import ALPR

image = cv2.imread("car.jpg")  # NumPy BGR uint8 image
plate = ALPR().predict(image)   # e.g. "CT 730FA", or None
```

The class also accepts grayscale or BGRA NumPy images and an optional local
`model_path`. With several visible plates it returns the valid reading with
the highest product of detector and OCR confidence. It does not infer which
vehicle a user intended when several vehicles appear in one image.
