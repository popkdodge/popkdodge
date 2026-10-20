"""Prep a headshot for ASCII: remove background, boost local contrast, flatten onto white.

Usage: python prep_photo.py [input] [output]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

HERE = Path(__file__).resolve().parent
src = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "source-photo.jpg"
out = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE.parent / "source-prepped.png"

session = new_session("u2net")  # Apache-2.0 model; the default BRIA model is non-commercial
rgba = np.array(remove(Image.open(src).convert("RGB"), session=session))  # RGBA, background alpha = 0
lab = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2LAB)
lab[:, :, 0] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lab[:, :, 0])
rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB).astype(np.float32)

# Hard mask: no half-transparent edge pixels compositing to near-white.
alpha = (rgba[:, :, 3:4] >= 128).astype(np.float32)
flat = rgb * alpha + 255 * (1 - alpha)  # composite onto pure white
Image.fromarray(flat.round().astype(np.uint8)).convert("L").save(out)
print(f"wrote {out}")
