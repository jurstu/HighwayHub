import cv2
import numpy as np
from rapidocr import RapidOCR

class Ocr:
    def __init__(self):
        self.engine = RapidOCR()

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
        
        gray = self.enhance_plate(gray)
        
        bin = self.quantize(gray, 7, [2, 3, 4, 5, 6, 7])
        occr = self.ocr(bin)
        return bin, occr

    def enhance_plate(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img

        # Normalize slow illumination changes
        bg = cv2.GaussianBlur(gray, (0, 0), sigmaX=15)
        norm = cv2.divide(gray, bg, scale=180)

        # Local contrast
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 4))
        norm = clahe.apply(norm)

        return norm

    def quantize(self, gray, levels=7, keep=None):
        x = gray.reshape(-1, 1).astype(np.float32)

        _, labels, centers = cv2.kmeans(
            x, levels, None,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1),
            5, cv2.KMEANS_PP_CENTERS
        )

        # Reorder labels: 0=darkest, levels-1=brightest
        order = np.argsort(centers.flatten())
        remap = np.zeros(levels, dtype=np.uint8)
        remap[order] = np.arange(levels)
        buckets = remap[labels.flatten()].reshape(gray.shape)

        if keep is None:
            keep = range(levels)

        # Selected buckets -> white, everything else -> black
        out = np.isin(buckets, keep).astype(np.uint8) * 255

        return out


    def ocr(self, image):
        result = self.engine(image)
        return result.txts
