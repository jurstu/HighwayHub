import cv2
import json
from pathlib import Path

class ImageReader:
    def __init__(self):
        with open("path", "r") as f:
            self.p = f.read()

        with open(self.p + "/plates.json", "r") as f:
            self.data = json.load(f)["plates"]
            return

        self.data = {}
        

    def load(self):
        self.records = []
        #print(self.data)
        for rec in self.data:
            file = Path(self.p) / rec["file"]
            out = {
                "file": file,
                "just_filename": rec["file"],
                "image": cv2.imread(file),
                "registration": rec["plate"]
            }
            self.records.append(out)

        #print(self.records)
        return self.records


if __name__ == "__main__":
    ir = ImageReader()
    ir.load()

        