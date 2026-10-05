import cv2
import json
from pathlib import Path


class ImageReader:
    def __init__(self, dataset_dir=None):
        if dataset_dir is None:
            path_file = Path(__file__).parent / "path"
            dataset_dir = Path(path_file.read_text().strip()).expanduser()
            if not dataset_dir.is_absolute():
                dataset_dir = path_file.parent / dataset_dir
        self.p = Path(dataset_dir).expanduser()
        with (self.p / "plates.json").open() as f:
            self.data = json.load(f)["plates"]

    def load(self):
        self.records = []
        for rec in self.data:
            file = Path(self.p) / rec["file"]
            image = cv2.imread(str(file))
            if image is None:
                raise FileNotFoundError(f"Could not read image: {file}")
            out = {
                "file": file,
                "just_filename": rec["file"],
                "image": image,
                "registration": rec["plate"]
            }
            self.records.append(out)

        return self.records


if __name__ == "__main__":
    ir = ImageReader()
    print(f"Loaded {len(ir.load())} images from {ir.p}")
