#!/usr/bin/env python3
"""Generate original film-emulation .cube LUTs (33^3). No third-party LUT licensing.
Usage: python gen_luts.py OUT_DIR
Looks are tuned for display-referred sRGB (photos / Rec.709 video)."""
import sys, os
import numpy as np

N = 33

def luma(c):
    return c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722

def scurve(x, strength=1.0, pivot=0.45):
    # smooth filmic S-curve with soft toe and shoulder
    x = np.clip(x, 0, 1)
    k = 1 + 2.2 * strength
    lo = pivot * (x / pivot) ** k
    hi = 1 - (1 - pivot) * ((1 - x) / (1 - pivot)) ** k
    return np.where(x < pivot, lo, hi)

def sat(c, s):
    y = luma(c)[..., None]
    return y + (c - y) * s

def split_tone(c, shadow_rgb, high_rgb, amount=0.12, balance=0.5):
    y = luma(c)[..., None]
    w_hi = np.clip((y - balance) * 2.0, 0, 1)
    w_lo = np.clip((balance - y) * 2.0, 0, 1)
    return c + amount * (w_lo * (np.array(shadow_rgb) - 0.5) + w_hi * (np.array(high_rgb) - 0.5))

def lift_gamma_gain(c, lift=0.0, gamma=1.0, gain=1.0, black=0.0):
    c = c * gain
    c = np.clip(c, 0, None) ** (1 / gamma)
    return black + lift + c * (1 - black - lift)

def hue_protect_skin(orig, graded, amount=0.5):
    # pull skin-tone region back toward original so faces stay human
    r, g, b = orig[..., 0], orig[..., 1], orig[..., 2]
    skin = np.clip(((r > g) & (g > b)).astype(float) * (1 - np.abs((r - g) - 0.12) * 4), 0, 1)
    w = (skin * amount)[..., None]
    return graded * (1 - w) + orig * w

LOOKS = {}

def look(fn):
    LOOKS[fn.__name__] = fn
    return fn

@look
def print_film(c):
    """Warm print stock: dense blacks, soft highlight roll-off, teal-ish shadows, warm mids."""
    c = split_tone(c, (0.40, 0.52, 0.56), (0.60, 0.53, 0.44), 0.18)
    c = scurve(c, 0.55)
    c = sat(c, 0.88)
    return lift_gamma_gain(c, lift=0.015, gain=0.97)

@look
def teal_orange(c):
    """Blockbuster complementary grade with skin protection."""
    o = c
    y = luma(c)[..., None]
    c = split_tone(c, (0.30, 0.55, 0.62), (0.68, 0.52, 0.38), 0.28)
    c = scurve(c, 0.6)
    c = sat(c, 1.05)
    return hue_protect_skin(np.clip(sat(o, 1.05), 0, 1), c, 0.35)

@look
def bleach_bypass(c):
    """Silver-retention look: hard contrast, crushed saturation, metallic."""
    y = luma(c)[..., None]
    c = c * 0.45 + np.repeat(y, 3, -1) * 0.55
    c = scurve(c, 1.1, 0.5)
    return c

@look
def noir_mono(c):
    """B&W with red-filter response (smooth skin, dark skies) and deep blacks."""
    y = c[..., 0] * 0.5 + c[..., 1] * 0.4 + c[..., 2] * 0.1
    y = scurve(y, 0.9, 0.42)
    y = lift_gamma_gain(y, lift=0.01)
    return np.stack([y, y, y], -1)

@look
def faded_matte(c):
    """Editorial matte: lifted blacks, compressed whites, muted color."""
    c = sat(c, 0.75)
    c = scurve(c, 0.25)
    c = lift_gamma_gain(c, lift=0.07, gain=0.93)
    return split_tone(c, (0.46, 0.50, 0.56), (0.56, 0.52, 0.46), 0.10)

@look
def golden_hour(c):
    """Warm sunset glow, gentle contrast."""
    c = c * np.array([1.06, 1.0, 0.86])
    c = split_tone(c, (0.50, 0.45, 0.48), (0.68, 0.55, 0.38), 0.18)
    c = scurve(c, 0.35)
    return sat(c, 1.08)

@look
def midnight_blue(c):
    """Cold night look: blue shadows, crushed blacks, desaturated warm highlights."""
    c = split_tone(c, (0.32, 0.42, 0.70), (0.55, 0.53, 0.50), 0.30)
    c = scurve(c, 0.7)
    c = sat(c, 0.8)
    return lift_gamma_gain(c, gamma=0.92)

@look
def neon_split(c):
    """Music-video split tone: magenta highlights, cyan shadows, punchy."""
    c = split_tone(c, (0.30, 0.58, 0.66), (0.70, 0.42, 0.64), 0.32)
    c = scurve(c, 0.65)
    return sat(c, 1.15)

@look
def pastel_dream(c):
    """Soft, airy, low-contrast pastel for dreamy / R&B / pop."""
    c = sat(c, 0.8)
    c = lift_gamma_gain(c, lift=0.06, gamma=1.1)
    return split_tone(c, (0.52, 0.48, 0.58), (0.58, 0.52, 0.54), 0.12)

@look
def kodak_portrait(c):
    """Portrait negative feel: warm skin, soft greens, creamy highlights."""
    o = c
    c = c * np.array([1.03, 1.0, 0.95])
    hsv_g = np.clip(c[..., 1] - np.maximum(c[..., 0], c[..., 2]), 0, 1)[..., None]
    c = c - hsv_g * np.array([0, 0.25, -0.05])  # tame greens
    c = scurve(c, 0.4)
    c = lift_gamma_gain(c, lift=0.02, gain=0.98)
    return sat(c, 0.95)

@look
def gritty_street(c):
    """Rap/drill: green-yellow tint, hard contrast, desat."""
    c = split_tone(c, (0.42, 0.52, 0.46), (0.58, 0.56, 0.42), 0.22)
    c = sat(c, 0.7)
    return scurve(c, 0.95)

def write_cube(path, title, fn):
    r = np.linspace(0, 1, N)
    # .cube order: R fastest, then G, then B
    b, g, rr = np.meshgrid(r, r, r, indexing="ij")
    grid = np.stack([rr, g, b], -1).reshape(-1, 3)
    out = np.clip(fn(grid.copy()), 0, 1)
    with open(path, "w") as f:
        f.write(f'TITLE "{title}"\nLUT_3D_SIZE {N}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        np.savetxt(f, out, fmt="%.6f")

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    for name, fn in LOOKS.items():
        write_cube(os.path.join(out, f"{name}.cube"), name, fn)
        print("wrote", name, "-", (fn.__doc__ or "").strip())
