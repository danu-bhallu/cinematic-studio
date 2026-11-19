#!/usr/bin/env python3
"""Finishing pass: LUT -> halation -> bloom -> chromatic fringe -> grain -> vignette -> letterbox -> sharpen.
Usage: python grade.py IN.mp4 OUT.mp4 [--lut print_film] [--lut-mix 0.85] [--halation 0.35] [--bloom 0.25]
                       [--grain 10] [--vignette 0.35] [--ca 1] [--letterbox 2.39] [--audio keep|none|PATH]
Presets: --preset film | music | clean | noir
All effects are pure ffmpeg filters so the chain is fast and deterministic."""
import argparse, os, subprocess

LUTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "luts")
PRESETS = {
    "film":  dict(lut="print_film", lut_mix=0.9, halation=0.35, bloom=0.2, grain=9, vignette=0.32, ca=1),
    "music": dict(lut="neon_split", lut_mix=0.8, halation=0.45, bloom=0.35, grain=11, vignette=0.38, ca=2),
    "clean": dict(lut="kodak_portrait", lut_mix=0.7, halation=0.15, bloom=0.1, grain=4, vignette=0.2, ca=0),
    "noir":  dict(lut="noir_mono", lut_mix=1.0, halation=0.0, bloom=0.25, grain=16, vignette=0.45, ca=0),
}

ap = argparse.ArgumentParser()
ap.add_argument("inp"); ap.add_argument("out"); ap.add_argument("--preset")
ap.add_argument("--lut"); ap.add_argument("--lut-mix", type=float); ap.add_argument("--halation", type=float)
ap.add_argument("--bloom", type=float); ap.add_argument("--grain", type=float); ap.add_argument("--vignette", type=float)
ap.add_argument("--ca", type=int); ap.add_argument("--letterbox", type=float, default=0)
ap.add_argument("--audio", default="keep"); ap.add_argument("--crf", type=int, default=15)
a = ap.parse_args()
p = dict(PRESETS.get(a.preset or "film"))
for k in ["lut", "lut_mix", "halation", "bloom", "grain", "vignette", "ca"]:
    v = getattr(a, k)
    if v is not None: p[k] = v

chain, last = [], "0:v"
def add(f, out):
    global last
    chain.append(f"[{last}]{f}[{out}]" if not f.startswith("[") else f + f"[{out}]"); last = out

# base: high precision
add("format=gbrpf32le", "b0")
if p["lut"]:
    lut = p["lut"] if os.path.isfile(p["lut"]) else os.path.join(LUTS, p["lut"] + ".cube")
    chain.append(f"[{last}]split[pre][l_in];[l_in]lut3d=file='{lut}':interp=tetrahedral[l_out];[pre][l_out]blend=all_expr='A*(1-{p['lut_mix']})+B*{p['lut_mix']}'[b1]"); last = "b1"
if p["halation"] > 0:
    # red-orange glow bleeding from highlights, like light scattering off film base
    h = p["halation"]
    chain.append(f"[{last}]split[hb][hs];[hs]curves=all='0/0 0.72/0 1/1',gblur=sigma=18,colorchannelmixer=rr=1:gg=0.35:bb=0.12[hg];"
                 f"[hb][hg]blend=all_expr='A+B*{h}-A*B*{h}'[b2]"); last = "b2"
if p["bloom"] > 0:
    bl = p["bloom"]
    chain.append(f"[{last}]split[bb][bs];[bs]curves=all='0/0 0.6/0 1/1',gblur=sigma=40[bg];[bb][bg]blend=all_expr='A+B*{bl}-A*B*{bl}'[b3]"); last = "b3"
add("format=yuv444p", "b4")
if p["ca"] > 0:
    add(f"rgbashift=rh=-{p['ca']}:bh={p['ca']}:edge=smear", "b5")
if p["vignette"] > 0:
    add(f"vignette=angle={0.35 + p['vignette'] * 0.6:.3f}:mode=forward:eval=init", "b6")
if p["grain"] > 0:
    # temporal, luma-weighted grain, softened so it reads as film not digital noise
    g = p["grain"]
    chain.append(f"[{last}]split[ga][gb];[gb]noise=c0s={g}:c0f=t+u:c1s={g*0.4}:c1f=t+u:c2s={g*0.4}:c2f=t+u,gblur=sigma=0.6[gn];[ga][gn]blend=all_mode=normal:all_opacity=0.85[b7]"); last = "b7"
add("unsharp=5:5:0.35:5:5:0", "b8")
if a.letterbox:
    add(f"drawbox=x=0:y=0:w=iw:h=(ih-iw/{a.letterbox})/2:color=black:t=fill,drawbox=x=0:y=ih-(ih-iw/{a.letterbox})/2:w=iw:h=(ih-iw/{a.letterbox})/2:color=black:t=fill", "b9")
add("format=yuv420p", "vout")

cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", a.inp]
amap = []
if a.audio not in ("keep", "none"):
    cmd += ["-i", a.audio]; amap = ["-map", "1:a:0", "-shortest"]
elif a.audio == "keep":
    amap = ["-map", "0:a?"]
cmd += ["-filter_complex", ";".join(chain), "-map", "[vout]"] + amap + [
    "-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf), "-tune", "grain", "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", a.out]
subprocess.run(cmd, check=True)
print("graded ->", a.out, p)
