"""Show video frames with detected plates boxed and labeled."""

import cv2

if __package__:
    from .alpr import ALPR
else:
    from alpr import ALPR


VIDEO_PATH = "/home/jur/alpr.mp4"


def annotate_plate(frame, plate, box):
    """Draw a plate rectangle and label on a BGR frame in place."""
    if box is None:
        return frame

    x1, y1, x2, y2 = box
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    label = f"Plate: {plate}" if plate else "Plate"
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale, thickness = 0.7, 2
    (text_width, text_height), baseline = cv2.getTextSize(label, font, scale, thickness)
    padding = 6
    label_width = text_width + 2 * padding
    label_height = text_height + baseline + 2 * padding
    height, width = frame.shape[:2]
    label_x = min(max(0, x1), max(0, width - label_width))
    label_y = y1 - label_height - 4
    if label_y < 0:
        label_y = y2 + 4
    label_y = min(label_y, max(0, height - label_height))
    cv2.rectangle(
        frame,
        (label_x, label_y),
        (label_x + label_width, label_y + label_height),
        (0, 0, 0),
        -1,
    )
    cv2.putText(
        frame,
        label,
        (label_x + padding, label_y + text_height + padding),
        font,
        scale,
        (0, 255, 0),
        thickness,
        cv2.LINE_AA,
    )
    return frame


def main():
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        raise SystemExit(f"Could not open video file: {VIDEO_PATH}")

    alpr = ALPR()
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"Total frames: {frame_count}, FPS: {fps}")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.resize(frame, (1280, 720))
            plate, box = alpr.predict_with_box(frame)
            print(plate)
            annotate_plate(frame, plate, box)
            cv2.imshow("Video Frame", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
