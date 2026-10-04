# ALPR design

This project reads the image directory from `pathToData.json`, detects likely
license plates with OpenCV, rectifies them with a perspective transform, and
recognizes their text with lazily loaded EasyOCR.

## Pipeline

1. **Input** — validate `{ "path": "..." }`, discover supported images in a
   deterministic order, and optionally load `plates.json` as evaluation labels.
2. **Detection** — resize only for detection, normalize luminance with CLAHE,
   then combine black-hat, bright-region, and edge morphology. Contours are
   filtered and ranked by plate-like aspect ratio, rectangularity, edge density,
   brightness, and size. Coordinates are mapped back to the original image.
3. **Rectification** — order either an approximated quadrilateral or the corners
   of `minAreaRect`, apply a four-point transform, rotate portrait results, and
   upscale small crops.
4. **Recognition** — initialize EasyOCR only when recognition is requested,
   allow only uppercase Latin letters and digits, normalize punctuation, and
   combine OCR and detector confidence when selecting the result.
5. **Output** — emit a human-readable table or JSON. Optional debug output
   contains plate crops and annotated source images. Labels are used only after
   inference to calculate exact normalized matches.

## Constraints

The detector is deliberately model-free and cannot guarantee detection in every
scene. Very small, blurred, dark, or non-standard plates are challenging.
EasyOCR may download model weights on its first real invocation. Unit tests use
synthetic images and injected OCR and therefore require no model download.
PyTorch and TorchVision are resolved from PyTorch's CPU-only wheel index to
avoid downloading CUDA/NVIDIA runtime packages for the default CPU workflow.

## Usage

```sh
./install.sh
uv run alpr --config pathToData.json --output-dir output
uv run alpr --config pathToData.json --no-ocr --json
uv run pytest
```
