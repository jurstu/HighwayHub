from ultralytics import YOLO
import cv2
import numpy as np
import os
import time

def load_char_detector(model_path: str) -> YOLO:
    model = YOLO(model_path)
    return model

def detect_plate_characters(model: YOLO, img: np.ndarray, conf_thresh: float = 0.25):
    """
    Run character detection on image, return list of detected characters with boxes.
    """
    results = model(img) #, size=640)
    # Fix for drawing as before
    if isinstance(results, list):
        results.ims = [np.ascontiguousarray(im.copy()) for im in results]
    else:
        results.ims = np.ascontiguousarray(results.copy())

    detections = results.pred[0]  # shape (n, 6): x1, y1, x2, y2, conf, cls

    char_objects = []
    for det in detections:
        x1, y1, x2, y2, conf, cls_id = det.cpu().numpy()
        if conf < conf_thresh:
            continue
        x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
        label = model.names[int(cls_id)]
        char_objects.append({
            "box": (x1, y1, x2, y2),
            "label": label,
            "confidence": float(conf)
        })

    return char_objects, results

def annotate_and_assemble_plate(img: np.ndarray, char_objs: list):
    """
    Annotate the image with drawn boxes/labels, and try to assemble the license plate string
    by sorting left-to-right.
    """
    # Draw boxes & labels
    annotated = img.copy()
    for obj in char_objs:
        x1, y1, x2, y2 = obj["box"]
        label = obj["label"]
        conf = obj["confidence"]
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(annotated, f"{label}:{conf:.2f}",
                    (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Sort characters by x1 coordinate (left-to-right)
    sorted_chars = sorted(char_objs, key=lambda o: o["box"][0])
    plate_string = "".join([o["label"] for o in sorted_chars])

    return annotated, plate_string

if __name__ == "__main__":
    # Path to the downloaded .pt model from MKgoud repository
    model_path = "assets/Charcter-LP.pt"  # Make sure you download this and have correct path

    # Load char detector
    char_model = load_char_detector(model_path)

    # Read your license-plate (or car) image
    img = cv2.imread("assets/66f8ca173528.jpeg")
    if img is None:
        raise RuntimeError("Could not load image file")

    # Detect characters
    char_objs, results = detect_plate_characters(char_model, img, conf_thresh=0.3)

    # Annotate and assemble
    annotated_img, plate_text = annotate_and_assemble_plate(img, char_objs)

    print("Detected plate text:", plate_text)

    # Save / show
    os.makedirs("char_results", exist_ok=True)
    cv2.imwrite("char_results/annotated.jpg", annotated_img)
    cv2.imshow("Annotated", annotated_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
