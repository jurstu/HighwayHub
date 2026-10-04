import cv2



class Ocr:
    def __init__(self):
        ...

    def process(self, img):
        # 1. Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2. Upscale — OCR generally benefits from larger characters
        h, w = gray.shape[:2]
        width = 640
        scale = width / w

        gray = cv2.resize(
            gray,
            (width, round(h * scale)),
            interpolation=cv2.INTER_CUBIC
        )

        ## 3. Local contrast normalization
        #clahe = cv2.createCLAHE(
        #    clipLimit=2.0,
        #    tileGridSize=(3, 3)
        #)
        #gray = clahe.apply(gray)

        # 4. Preserve character edges while reducing noise
        gray = cv2.bilateralFilter(gray, 7, 50, 50)

        ## 5. Local/adaptive threshold
        #binary = cv2.adaptiveThreshold(
        #    gray,
        #    255,
        #    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        #    cv2.THRESH_BINARY,
        #    blockSize=19,
        #    C=7
        #)

        return gray