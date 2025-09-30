import torch

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
img = "https://huggingface.co/api/resolve-cache/models/keremberke/yolov5m-license-plate/2bc5d847462e40bbae9fa8a868c2a402e8491331/sample_visuals.jpg"

# run inference
t = time.time()
results = model(img, size=640)
print(time.time() - t)

# make result images writable before plotting (fixes cv2.rectangle error)
if isinstance(results.ims, list):
    results.ims = [np.ascontiguousarray(im.copy()) for im in results.ims]
else:
    results.ims = np.ascontiguousarray(results.ims.copy())

# parse results
predictions = results.pred[0]
boxes = predictions[:, :4]
scores = predictions[:, 4]
categories = predictions[:, 5]

# save annotated results
results.save(save_dir='results/')

print("✅ Inference complete, results saved in 'results/'")

