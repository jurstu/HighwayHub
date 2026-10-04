from find_license_plates import LpFinder
from read_images import ImageReader

import os
import time
from pathlib import Path
import cv2

ir = ImageReader()
records = ir.load()

lpf = LpFinder()

tt = "ignore" + str(time.time())

os.mkdir(str(tt))
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
            
            cv2.imwrite(Path(tt) / rec["just_filename"][:-4] / (str(i) + ".png"), img)
        except:
            pass

    
