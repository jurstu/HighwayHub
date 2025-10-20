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

class CameraHandler:
    def __init__(self, src=0):
        self.src = src
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
            print("image_net shape", image_net.shape)
            padded_image = np.full((height, width, 3), (114, 114, 114), dtype=np.uint8)
            x_offset = (width - new_img_w) // 2
            y_offset = (height - new_img_h) // 2
            padded_image[y_offset:y_offset + new_img_h, x_offset:x_offset + new_img_w] = image_net
            
            padded_image = cv2.resize(image, (640, 640))
            batch = ([padded_image], [padded_image])
            

            # Prepare the callback for handling the inference result
            inference_callback_fn = partial(
                inference_callback,
                frameNumber=self.frameNumber
            )
            hailo_inference.run(batch, inference_callback_fn)

        self.cap.release()
        hailo_inference.close()
        print("Camera capture thread stopped.")





def inference_callback(
    completion_info,
    bindings_list: list,
    frameNumber: int
) -> None:
    """
    inference callback to handle inference results and push them to a queue.

    Args:
        completion_info: Hailo inference completion info.
        bindings_list (list): Output bindings for each inference.
        input_batch (list): Original input frames.
        output_queue (queue.Queue): Queue to push output results to.
    """
    print("processed frame number", frameNumber)
    
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

        print(result)
#            output_queue.put((input_batch[i], result))


def main() -> None:
    import time
    ch = CameraHandler()
    while(1):
        time.sleep(1)



if __name__ == "__main__":
    main()