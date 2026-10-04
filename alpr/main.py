from find_license_plates import LpFinder
from read_images import ImageReader
from deskew_license_plates import LpDeskew
from ocr import Ocr

from pathlib import Path
import cv2
import math
import numpy as np


TILE_WIDTH = 400
TILE_HEIGHT = 200


def mosaic_tile(image, filename, detection_index, texts):
    """Show a plate crop with its source and recognized text below it."""
    tile = np.full((TILE_HEIGHT, TILE_WIDTH, 3), 28, dtype=np.uint8)
    cv2.putText(
        tile, f"{filename}  /  detection {detection_index}", (12, 23),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (190, 190, 190), 1, cv2.LINE_AA,
    )

    available_width, available_height = TILE_WIDTH - 24, 112
    height, width = image.shape[:2]
    scale = min(available_width / width, available_height / height)
    interpolation = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    plate = cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=interpolation)
    x = (TILE_WIDTH - plate.shape[1]) // 2
    y = 34 + (available_height - plate.shape[0]) // 2
    tile[y:y + plate.shape[0], x:x + plate.shape[1]] = plate

    caption = ", ".join(texts) if texts else "No text detected"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.9
    text_width = cv2.getTextSize(caption, font, font_scale, 2)[0][0]
    if text_width > TILE_WIDTH - 24:
        font_scale *= (TILE_WIDTH - 24) / text_width
        text_width = cv2.getTextSize(caption, font, font_scale, 2)[0][0]
    cv2.putText(
        tile, caption, ((TILE_WIDTH - text_width) // 2, 182),
        font, font_scale, (255, 255, 255), 2, cv2.LINE_AA,
    )
    return tile


ir = ImageReader()
records = ir.load()

lpf = LpFinder()
lpd = LpDeskew()
ocr = Ocr()

tt = Path("ignore output")
tt.mkdir(exist_ok=True)

mosaic = []

for rec in records:
    output = lpf.infere(rec["image"])[0]
    #print(output)
    #print(rec)
    for i, res in enumerate(output.boxes):
        #print("RES IS ", res)
        #exit()
        xyxy = [int(x) for x in res.xyxy[0]]
        
        #print(xyxy)
        try:
            img = rec["image"][xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]]
            img2 = lpd.deskew(img)
            img3, txts = ocr.process(img2, original=img)
            print(f"{rec['just_filename']} detection {i}: {txts}")

            

            #img4 = flood(img3)
            #img4 = enhance_plate(img3)
            #img5 = cv2.adaptiveThreshold(
            #    img4, 255,
            #    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            #    cv2.THRESH_BINARY,
            #    31, 7
            #)


            #img4 = quantize(img4, keep=[2, 3, 4, 5, 6])

            mosaic.append(mosaic_tile(img3, rec["just_filename"], i, txts))
            #mosaic.append(img4)
            #mosaic.append(img5)

            #cv2.imwrite(Path(tt) / rec["just_filename"][:-4] / (str(i) + ".png"), img)
            #cv2.imwrite(Path(tt) / rec["just_filename"][:-4] / (str(i) + "_deskewed.png"), img2)
            #cv2.imwrite(Path(tt) / rec["just_filename"][:-4] / (str(i) + "_preprocessed.png"), img3)
        except:
            pass

    


n = math.ceil(math.sqrt(len(mosaic)))
blank = np.full_like(mosaic[0], 28)
mosaic += [blank] * (n*n - len(mosaic))

result = np.vstack([
    np.hstack(mosaic[i*n:(i+1)*n])
    for i in range(n)
])

cv2.imwrite(tt / "mosaic.png", result)
