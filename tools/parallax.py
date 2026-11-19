#!/usr/bin/env python3
"""Still photo -> cinematic 2.5D camera move (depth parallax), CPU only.
Depth from Depth-Anything-V2 (ONNX, local). Renders straight to ProRes/H.264 via ffmpeg.

Usage:
  python parallax.py IMG OUT.mp4 [--move push|pull|orbit|pan-left|pan-right|rise|fall|dolly-zoom]
                     [--dur 4] [--fps 30] [--w 1080 --h 1920] [--strength 1.0]
                     [--ease inout|in|out|linear] [--dof 0.0] [--focus auto|0..1]
                     [--depth-out depth.png] [--model vits|vitb]
Notes:
  * Output is cropped/fit (cover) to WxH. Use 1080x1920 for Reels/TikTok, 1920x1080 for YouTube.
  * --dof adds depth-of-field blur away from the focus plane (0.3-1.0 looks good).
  * Keep strength 0.6-1.2: bigger moves reveal stretching at depth edges.
"""
import argparse, os, subprocess, sys
import numpy as np, cv2
import onnxruntime as ort

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(os.path.dirname(HERE), "models")

def estimate_depth(img_bgr, model="vits"):
    sess = ort.InferenceSession(os.path.join(MODELS, f"depth_anything_v2_{model}.onnx"), providers=["CPUExecutionProvider"])
    h, w = img_bgr.shape[:2]
    x = cv2.resize(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), (518, 518), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    d = sess.run(None, {sess.get_inputs()[0].name: x})[0][0]
    d = cv2.resize(d, (w, h), interpolation=cv2.INTER_CUBIC)
    d = (d - d.min()) / (d.max() - d.min() + 1e-8)  # 1 = near, 0 = far
    # edge-aware smoothing so foreground silhouettes don't tear
    d = cv2.bilateralFilter(d.astype(np.float32), 9, 0.1, 9)
    return d

def cover(img, W, H, margin=1.12):
    """scale to cover WxH with extra margin for camera travel; return image, offsets"""
    h, w = img.shape[:2]
    s = max(W / w, H / h) * margin
    return cv2.resize(img, (int(round(w * s)), int(round(h * s))), interpolation=cv2.INTER_LANCZOS4 if img.ndim == 3 else cv2.INTER_LINEAR)

EASE = {
    "linear": lambda t: t,
    "in": lambda t: t ** 3,
    "out": lambda t: 1 - (1 - t) ** 3,
    "inout": lambda t: 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2,
    "expo": lambda t: t if t in (0, 1) else (2 ** (20 * t - 10) / 2 if t < 0.5 else (2 - 2 ** (-20 * t + 10)) / 2),
}

def camera(move, t, s):
    """returns (tx, ty, zoom, parallax_x, parallax_y, parallax_z)"""
    # depth-zoom (6th value) kept small: large values bulge faces on close portraits
    if move == "push":      return 0, 0, 1 + 0.10 * s * t, 0, 0, 0.03 * s * t
    if move == "pull":      return 0, 0, 1 + 0.10 * s * (1 - t), 0, 0, 0.03 * s * (1 - t)
    if move == "orbit":     a = (t - 0.5) * 2; return 0, 0, 1.04, 0.035 * s * a, 0.006 * s * np.sin(np.pi * t), 0.02 * s
    if move == "pan-left":  a = (t - 0.5) * 2; return -0.03 * s * a, 0, 1.03, -0.03 * s * a, 0, 0
    if move == "pan-right": a = (t - 0.5) * 2; return 0.03 * s * a, 0, 1.03, 0.03 * s * a, 0, 0
    if move == "rise":      a = (t - 0.5) * 2; return 0, -0.02 * s * a, 1.04, 0, -0.03 * s * a, 0.02 * s * t
    if move == "fall":      a = (t - 0.5) * 2; return 0, 0.02 * s * a, 1.04, 0, 0.03 * s * a, 0.02 * s * t
    if move == "dolly-zoom":return 0, 0, 1 + 0.12 * s * t, 0, 0, -0.09 * s * t  # vertigo: bg grows vs subject
    raise SystemExit(f"unknown move {move}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("img"); ap.add_argument("out")
    ap.add_argument("--move", default="push"); ap.add_argument("--dur", type=float, default=4)
    ap.add_argument("--fps", type=float, default=30); ap.add_argument("--w", type=int, default=1080); ap.add_argument("--h", type=int, default=1920)
    ap.add_argument("--strength", type=float, default=1.0); ap.add_argument("--ease", default="inout")
    ap.add_argument("--dof", type=float, default=0.0); ap.add_argument("--focus", default="auto")
    ap.add_argument("--depth-out"); ap.add_argument("--depth-in"); ap.add_argument("--model", default="vits")
    ap.add_argument("--crf", type=int, default=14)
    a = ap.parse_args()

    img = cv2.imread(a.img, cv2.IMREAD_COLOR)
    if img is None: sys.exit(f"cannot read {a.img}")
    depth = cv2.imread(a.depth_in, cv2.IMREAD_UNCHANGED).astype(np.float32) / (65535 if a.depth_in.endswith(".png") else 255) if a.depth_in else estimate_depth(img, a.model)
    if a.depth_out: cv2.imwrite(a.depth_out, (depth * 65535).astype(np.uint16))

    src = cover(img, a.w, a.h); dep = cv2.resize(depth, (src.shape[1], src.shape[0]))
    H, W = src.shape[:2]
    focus = float(np.percentile(dep, 90)) if a.focus == "auto" else float(a.focus)
    # pre-blur stack for DOF
    if a.dof > 0:
        levels = [src] + [cv2.GaussianBlur(src, (0, 0), a.dof * k) for k in (2, 5, 10)]
        coc = np.clip(np.abs(dep - focus) * 3, 0, 3)  # 0..3 level index
        lo = np.floor(coc).astype(int); fr = (coc - lo)[..., None]
        stack = np.stack(levels)
        hi = np.clip(lo + 1, 0, 3)
        yy, xx = np.indices(lo.shape)
        src = (stack[lo, yy, xx] * (1 - fr) + stack[hi, yy, xx] * fr).astype(np.uint8)

    yy, xx = np.indices((a.h, a.w), dtype=np.float32)
    cx, cy = W / 2, H / 2
    n = int(round(a.dur * a.fps))
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{a.w}x{a.h}", "-r", str(a.fps), "-i", "-",
                           "-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    dsm = cv2.GaussianBlur(dep, (0, 0), 3)
    for i in range(n):
        t = EASE[a.ease](i / max(n - 1, 1))
        tx, ty, zoom, px, py, pz = camera(a.move, t, a.strength)
        # output pixel -> source coords (centered, zoomed, translated)
        sx = cx + (xx - a.w / 2) / zoom + tx * W
        sy = cy + (yy - a.h / 2) / zoom + ty * H
        sx = sx.astype(np.float32); sy = sy.astype(np.float32)
        d = cv2.remap(dsm, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        dd = d - focus * 0.5  # near objects move more than far
        sx2 = sx - px * W * dd - (sx - cx) * pz * dd
        sy2 = sy - py * H * dd - (sy - cy) * pz * dd
        frame = cv2.remap(src, sx2.astype(np.float32), sy2.astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        ff.stdin.write(frame.tobytes())
    ff.stdin.close(); ff.wait()
    print(f"wrote {a.out}  {a.w}x{a.h} {a.dur}s {a.move}")

if __name__ == "__main__":
    main()
