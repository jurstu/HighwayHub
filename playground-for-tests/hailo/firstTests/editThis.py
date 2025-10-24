#!/usr/bin/env python3
import argparse
import os
import sys

import queue
import threading
from functools import partial
from types import SimpleNamespace
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.tracker.byte_tracker import BYTETracker
from common.hailo_inference import HailoInfer
from common.toolbox import init_input_source, get_labels, load_json_file, preprocess, visualize, FrameRateTracker
from object_detection_post_process import inference_result_handler


import argparse
from pathlib import Path

import cv2
from threading import Thread

CLASS_NAMES = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light',
    'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
    'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
    'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
    'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
    'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
    'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard',
    'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase',
    'scissors', 'teddy bear', 'hair drier', 'toothbrush'
]

class CameraHandler:
    def __init__(self, ug, src=0):
        self.src = src
        self.ug = ug
        self.modelPath = "/usr/share/hailo-models/yolov8s_h8.hef"
        self.frameNumber = 0
        self.thread = Thread(target=self._run_capture, daemon=True)
        self.thread.start()

    def _run_capture(self):
        
        self.cap = cv2.VideoCapture(self.src)
        if not self.cap.isOpened():
            raise IOError(f"Cannot open camera index {self.src}")

        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.frame = None
        self.running = True
        batch_size = 1
        hailo_inference = HailoInfer(self.modelPath, batch_size)
        height, width, _ = hailo_inference.get_input_shape()

        while self.running:
            ret, image = self.cap.read()
            if not ret:
                print("Camera read failed or end of stream reached.")
                self.running = False
                break
            
            self.frameNumber += 1
            img_h, img_w, _ = image.shape[:3]
            scale = min(width / img_w, height / img_h)
            new_img_w, new_img_h = int(img_w * scale), int(img_h * scale)
            image_net = cv2.resize(image, (new_img_w, new_img_h), interpolation=cv2.INTER_CUBIC)
            #print("image_net shape", image_net.shape)
            
            padded_image = np.full((height, width, 3), (114, 114, 114), dtype=np.uint8)
            x_offset = (width - new_img_w) // 2
            y_offset = (height - new_img_h) // 2
            padded_image[y_offset:y_offset + new_img_h, x_offset:x_offset + new_img_w] = image_net
            
            #padded_image = cv2.resize(image, (640, 640))
            batch = ([padded_image], [padded_image])
            

            # Prepare the callback for handling the inference result
            inference_callback_fn = partial(
                self.inference_callback,
                frameNumber=self.frameNumber,
                image_raw = image.copy()
            )
            hailo_inference.run(batch, inference_callback_fn)

        self.cap.release()
        hailo_inference.close()
        print("Camera capture thread stopped.")





    def inference_callback(
            self,
        completion_info,
        bindings_list: list,
        frameNumber: int,
        image_raw
    ) -> None:
        
        if completion_info.exception:
            print(f'Inference error: {completion_info.exception}')
        else:
            for i, bindings in enumerate(bindings_list):
                if len(bindings._output_names) == 1:
                    result = bindings.output().get_buffer()
                else:
                    result = {
                        name: np.expand_dims(
                            bindings.output(name).get_buffer(), axis=0
                        )
                        for name in bindings._output_names
                    }


            hh, ww, _ = image_raw.shape
            #print("\n\n", len(result), len(CLASS_NAMES))
#            for c, res in zip(CLASS_NAMES, result):
#                for obj in res:
#                    mult = [hh, ww, hh, ww, 1]
#                    y, x, h, w, _ = [int(z * mult[i]) for i, z in enumerate(obj)]
#                    conf = obj[4]
#                    if(conf > 0.5):
#                        image_raw = cv2.rectangle(image_raw, (x-w//2, y-h//2), (x+w//2, y+h//2), (0, 255, 0), 2)
#                        image_raw = cv2.putText(image_raw, c, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3, cv2.LINE_AA)
#                    else:
#                        print(conf)




            for c, res in zip(CLASS_NAMES, result):
                for obj in res:
                    mult = [hh, ww, hh, ww, 1]
                    y, x, y2, x2, _ = [int(z * mult[i]) for i, z in enumerate(obj)]
                    conf = obj[4]
                    if(conf > 0.5):
                        image_raw = cv2.rectangle(image_raw, (x, y), (x2, y2), (0, 255, 0), 2)
                        image_raw = cv2.putText(image_raw, c, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3, cv2.LINE_AA)



            
            self.ug.newFrame(image_raw)
            #cv2.imwrite("output.png", image_raw)
            #original, infer, *rest = result
            #infer = infer[0] if isinstance(infer, list) and len(infer) == 1 else infer
    






from nicegui import ui, app
from fastapi.responses import Response
import time
import threading
import numpy as np
import cv2


class UiGen:
    def __init__(self):
        self.controls = {}
        self.resolution = [1280, 720]
        self.lastImage = np.empty((self.resolution[1], self.resolution[0], 3))
        self.lastImage[:] = 255
        self.spawnGui()
        
    def run(self):
        self.t = threading.Thread(target=self.host, daemon=True)
        self.t.start()

    def host(self):
        ui.run(reload=False, show=False)

    def newFrame(self, image):
        self.lastImage = image

    def spawnGui(self):
        dark = ui.dark_mode()
        dark.enable()        
        
        with ui.card() as card:
            with ui.row():
                style = f"width: {self.resolution[0]}px; height: {self.resolution[1]}px; object-fit: contain;"
                self.controls["image"] = ui.interactive_image().classes("border").style(style)  # , size=(self.resolution[0], self.resolution[1]))#.classes('w-full h-full')
            with ui.row().classes("w-full"):
                pass
        ui.timer(interval=0.03, callback=lambda: self.controls["image"].set_source(f'/video/frame?{time.time()}'))

        @app.get("/video/frame", response_class=Response)
        def grabVideoFrame() -> Response:
            _, raw = cv2.imencode(".jpg", self.lastImage)
            return Response(content=raw.tobytes(), media_type="image/jpg")




def main() -> None:
    import time
    ug = UiGen()
    ch = CameraHandler(ug)

    ug.run()


    while(1):
        time.sleep(1)



if __name__ == "__main__":
    main()