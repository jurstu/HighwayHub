from huggingface_hub import hf_hub_download
from ultralytics import YOLO


class LpFinder:
    def __init__(self):
        self.model_path = hf_hub_download(
            repo_id="morsetechlab/yolov11-license-plate-detection",
            filename="license-plate-finetune-v1n.pt",
        )

        # Load with Ultralytics
        self.model = YOLO(self.model_path)

    def infere(self, image):

        results = self.model.predict(
            source=image,
            conf=0.25,
            imgsz=1280,
            save=False
        )

        # Inspect detections
        #for result in results:
        #    for box in result.boxes:
        #        print("xyxy:", box.xyxy.cpu().numpy())
        #        print("confidence:", float(box.conf))
        #        print("class:", int(box.cls))
        return results
        