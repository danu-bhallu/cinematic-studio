#!/usr/bin/env python3
"""Subject isolation for layered comps (text-behind-subject, double exposure, glow outlines).
Usage: python cutout.py IMG OUT_PREFIX [--model human|general]
Writes OUT_PREFIX_rgba.png (subject on transparent), OUT_PREFIX_mask.png, OUT_PREFIX_bg.png (subject removed, inpainted)."""
import argparse, numpy as np, cv2
from PIL import Image
from rembg import remove, new_session

ap = argparse.ArgumentParser(); ap.add_argument("img"); ap.add_argument("out"); ap.add_argument("--model", default="human")
a = ap.parse_args()
sess = new_session("u2net_human_seg" if a.model == "human" else "isnet-general-use")
im = Image.open(a.img).convert("RGB")
rgba = remove(im, session=sess, alpha_matting=True, alpha_matting_foreground_threshold=240, alpha_matting_background_threshold=15, alpha_matting_erode_size=8)
rgba.save(f"{a.out}_rgba.png")
mask = np.array(rgba)[..., 3]
cv2.imwrite(f"{a.out}_mask.png", mask)
bgr = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
dil = cv2.dilate((mask > 20).astype(np.uint8) * 255, np.ones((25, 25), np.uint8))
cv2.imwrite(f"{a.out}_bg.png", cv2.inpaint(bgr, dil, 9, cv2.INPAINT_TELEA))
print("wrote", f"{a.out}_rgba.png", f"{a.out}_mask.png", f"{a.out}_bg.png")
