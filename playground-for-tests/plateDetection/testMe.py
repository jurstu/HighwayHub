import torch
import os
import cv2
import requests
import hashlib
from urllib.parse import urlparse



# --- Patch torch.load to always allow full pickle unpickling ---
_orig_load = torch.load
def _torch_load_patch(*args, **kwargs):
    kwargs["weights_only"] = False
    return _orig_load(*args, **kwargs)
torch.load = _torch_load_patch
# ----------------------------------------------------------------

import yolov5
import numpy as np
import time

# load YOLOv5 license plate detection model from HuggingFace
model = yolov5.load('keremberke/yolov5m-license-plate')

# set model parameters
model.conf = 0.25
model.iou = 0.45
model.agnostic = False
model.multi_label = False
model.max_det = 1000

# test image
img = "https://tablica-rejestracyjna.pl/images/photos/20251009180009.jpeg"



def get_image_from_url(url: str) -> str:
    """Download image from URL if not already cached, then return local file path."""
    os.makedirs("assets", exist_ok=True)

    # Derive file extension from URL if present
    parsed = urlparse(url)
    _, ext = os.path.splitext(parsed.path)
    ext = ext if ext else ".jpg"  # default if missing

    # Hash the URL to create a unique filename
    url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    filename = f"{url_hash}{ext}"
    filepath = os.path.join("assets", filename)

    # Use cached version if available
    if os.path.exists(filepath):
        print(f"✅ Using cached image: {filepath}")
        return filepath

    # Otherwise, download it
    print(f"⬇️ Downloading image from {url}")
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    with open(filepath, "wb") as f:
        f.write(response.content)

    print(f"💾 Saved image to {filepath}")
    return filepath

img = cv2.imread(get_image_from_url(img))



import time
import numpy as np
import cv2
import torch

# --- Run inference ---
t = time.time()
results = model(img, size=640)
print("⏱ Inference time:", time.time() - t)

# Fix for OpenCV draw compatibility
if isinstance(results.ims, list):
    results.ims = [np.ascontiguousarray(im.copy()) for im in results.ims]
else:
    results.ims = np.ascontiguousarray(results.ims.copy())

# --- Parse results ---
predictions = results.pred[0]  # tensor: (num_detections, 6)
boxes = predictions[:, :4]     # xyxy
scores = predictions[:, 4]
categories = predictions[:, 5].int()

# --- Extract detected objects ---
detected_objects = []
for i, (box, score, cat_id) in enumerate(zip(boxes, scores, categories)):
    x1, y1, x2, y2 = map(int, box.tolist())
    label = model.names[int(cat_id)] if hasattr(model, "names") else str(cat_id)
    conf = float(score.item())
    detected_objects.append({
        "id": i,
        "label": label,
        "confidence": conf,
        "box": (x1, y1, x2, y2),
    })

print("✅ Detected objects:")
for obj in detected_objects:
    print(f" • {obj['label']} ({obj['confidence']:.2f}) at {obj['box']}")

from ultralytics import YOLO
model = YOLO('assets/Charcter-LP.pt')

# --- Optionally crop and save ---
os.makedirs("detections", exist_ok=True)
for obj in detected_objects:
    x1, y1, x2, y2 = obj["box"]
    print(x1, y1, x2, y2)
    crop = img[y1:y2, x1:x2]
    cv2.imwrite(f"detections/{obj['id']}_{obj['label']}.jpg", crop)
    results = model(crop)
    image = crop
    for result in results:
        boxes = result.boxes.cpu().numpy()  # Get bounding boxes
        for box in boxes:
            # Get box coordinates
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # Draw bounding box
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # If you have class names, you can add them to the image
            if box.cls is not None:
                label = f"{result.names[int(box.cls[0])]} {box.conf[0]:.2f}"
                cv2.putText(image, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)



    cv2.imwrite(f"detections/{obj['id']}_{obj['label']}.jpg", image)

    