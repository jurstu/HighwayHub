#!/usr/bin/env python3
import os
import cv2
import hailo
import numpy as np
from pathlib import Path

from object_detection_post_process import inference_result_handler

# -------------------------------------------------------------------------------------
# Config
# -------------------------------------------------------------------------------------
MODEL_PATH = "/usr/share/hailo-models/yolov8s_h8.hef"
LABELS = ["person", "car", "truck", "bus", "bicycle"]
CONFIG_DATA = {"visualization_params": {"score_thres": 0.5, "max_boxes_to_draw": 50}}

# -------------------------------------------------------------------------------------
# Load Hailo model
# -------------------------------------------------------------------------------------
hef = hailo.Hef(MODEL_PATH)
device = hailo.Device()
config_params = hailo.ConfigureParams.create_from_hef(hef)
net_groups = device.configure(hef, config_params)
net_group = net_groups[0]

input_vstream = net_group.get_input_vstream_infos()[0]
output_vstream = net_group.get_output_vstream_infos()[0]

width, height = input_vstream.shape.width, input_vstream.shape.height
print(f"✅ Model loaded: {MODEL_PATH} ({width}x{height})")

# -------------------------------------------------------------------------------------
# Create VStream pipeline
# -------------------------------------------------------------------------------------
input_vstream = hailo.InputVStream(input_vstream)
output_vstream = hailo.OutputVStream(output_vstream)
input_vstream.activate(device)
output_vstream.activate(device)

# -------------------------------------------------------------------------------------
# Main loop — capture, infer, draw
# -------------------------------------------------------------------------------------
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("Cannot open camera")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Preprocess to match model input
        resized = cv2.resize(frame, (width, height))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        tensor = np.ascontiguousarray(rgb, dtype=np.uint8)

        # Run inference
        input_vstream.write(device, tensor)
        raw_output = output_vstream.read(device)

        # Postprocess & draw
        frame_with_boxes = inference_result_handler(frame, [raw_output], LABELS, CONFIG_DATA)
        cv2.imshow("Hailo Inference", frame_with_boxes)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
    input_vstream.deactivate(device)
    output_vstream.deactivate(device)
    device.release()
