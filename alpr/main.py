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
            img3, txts = ocr.process(img2)
            print(txts)

            

            #img4 = flood(img3)
            #img4 = enhance_plate(img3)
            #img5 = cv2.adaptiveThreshold(
            #    img4, 255,
            #    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            #    cv2.THRESH_BINARY,
            #    31, 7
            #)


            #img4 = quantize(img4, keep=[2, 3, 4, 5, 6])

            mosaic.append(img3)
            #mosaic.append(img4)
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