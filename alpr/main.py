from find_license_plates import LpFinder
from read_images import ImageReader
from deskew_license_plates import LpDeskew
from ocr import Ocr
import shutil

import os
import time
from pathlib import Path
import cv2
import math
import numpy as np


def flood(gray, n=10, bright=45, tol=5):
    h, w = gray.shape
    mask = np.zeros((h + 2, w + 2), np.uint8)

    # sample central 50%
    xs = np.random.randint(w//4, 3*w//4, n)
    ys = np.random.randint(h//4, 3*h//4, n)

    for x, y in zip(xs, ys):
        if gray[y, x] >= bright:
            cv2.floodFill(
                gray.copy(), mask, (x, y), 255,
                loDiff=tol, upDiff=tol,
                flags=cv2.FLOODFILL_MASK_ONLY | 4 | (255 << 8)
            )

    return mask[1:-1, 1:-1]


def enhance_plate(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img

    # Normalize slow illumination changes
    bg = cv2.GaussianBlur(gray, (0, 0), sigmaX=15)
    norm = cv2.divide(gray, bg, scale=180)

    # Local contrast
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 4))
    norm = clahe.apply(norm)

    return norm

def quantize(gray, levels=7, keep=None):
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

ir = ImageReader()
records = ir.load()

lpf = LpFinder()
lpd = LpDeskew()
ocr = Ocr()

tt = "ignore " + str("output")

try:
    shutil.rmtree(tt)
except Exception as e:
    print(e)

os.mkdir(tt)

mosaic = []

for rec in records:
    output = lpf.infere(rec["image"])[0]
    #print(output)
    #print(rec)
    os.mkdir(Path(tt) / rec["just_filename"][:-4])

    for i, res in enumerate(output.boxes):
        #print("RES IS ", res)
        #exit()
        xyxy = [int(x) for x in res.xyxy[0]]
        
        #print(xyxy)
        try:
            img = rec["image"][xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]]
            img2 = lpd.deskew(img)
            img3 = ocr.process(img2)


            #img4 = flood(img3)
            img4 = enhance_plate(img3)
            #img5 = cv2.adaptiveThreshold(
            #    img4, 255,
            #    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            #    cv2.THRESH_BINARY,
            #    31, 7
            #)


            img4 = quantize(img4, keep=[2, 3, 4, 5, 6])

            mosaic.append(img3)
            mosaic.append(img4)
            #mosaic.append(img5)

            #cv2.imwrite(Path(tt) / rec["just_filename"][:-4] / (str(i) + ".png"), img)
            #cv2.imwrite(Path(tt) / rec["just_filename"][:-4] / (str(i) + "_deskewed.png"), img2)
            #cv2.imwrite(Path(tt) / rec["just_filename"][:-4] / (str(i) + "_preprocessed.png"), img3)
        except:
            pass

    


n = math.ceil(math.sqrt(len(mosaic)))
h, w = mosaic[0].shape[:2]

imgs = [cv2.resize(x, (w, h)) for x in mosaic]

blank = np.zeros_like(imgs[0])
imgs += [blank] * (n*n - len(imgs))

result = np.vstack([
    np.hstack(imgs[i*n:(i+1)*n])
    for i in range(n)
])

cv2.imwrite(Path(tt) / "mosaic.png", result)