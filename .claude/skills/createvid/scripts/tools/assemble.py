#!/usr/bin/env python3
"""Beat-synced assembly: lay clips on the music grid and cut on beats/downbeats.
Usage:
  python assemble.py --audio song.mp3 --beats beats.json --out edit.mp4 \
      --clips c1.mp4 c2.mp4 c3.mp4 [--start 0] [--bars 1,1,2] [--unit downbeat|beat] \
      [--trans cut|flash|blur|whip|dip] [--trans-dur 0.25] [--w 1080 --h 1920 --fps 30]
--bars: how many grid units each clip holds (cycled). Every cut lands exactly on a grid point.
--trans applies at each cut ('flash' = white flash on cut, 'blur' = rack-focus blur cut,
'whip' = directional motion-blur slide, 'dip' = dip to black). Drops from beats.json get a flash automatically.
Clips shorter than their slot are slowed (setpts) to fill; longer ones are trimmed."""
import argparse, json, subprocess, os

ap = argparse.ArgumentParser()
ap.add_argument("--audio"); ap.add_argument("--beats"); ap.add_argument("--out", required=True)
ap.add_argument("--clips", nargs="+", required=True); ap.add_argument("--start", type=float, default=0)
ap.add_argument("--bars", default="1"); ap.add_argument("--unit", default="downbeat")
ap.add_argument("--trans", default="cut"); ap.add_argument("--trans-dur", type=float, default=0.25)
ap.add_argument("--w", type=int, default=1080); ap.add_argument("--h", type=int, default=1920); ap.add_argument("--fps", type=float, default=30)
ap.add_argument("--length", type=float, default=0, help="total seconds (default: until clips run out)")
a = ap.parse_args()

B = json.load(open(a.beats))
grid = [t for t in (B["downbeats"] if a.unit == "downbeat" else B["beats"]) if t >= a.start - 1e-3]
if not grid or grid[0] > a.start + 1e-3: grid = [a.start] + grid
bars = [int(x) for x in a.bars.split(",")]
drops = set(round(d, 2) for d in B.get("drops", []))

# slots: (start, end) per clip
slots, gi = [], 0
for i, c in enumerate(a.clips):
    n = bars[i % len(bars)]
    if gi + n >= len(grid): break
    slots.append((grid[gi], grid[gi + n])); gi += n
if a.length:
    slots = [(s, min(e, a.start + a.length)) for s, e in slots if s < a.start + a.length]

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).strip())

td = a.trans_dur
xf = {"cut": None, "flash": "fadewhite", "blur": "hblur", "whip": "smoothleft", "dip": "fadeblack"}
modes = []
for i in range(1, len(slots)):
    tr = "flash" if round(slots[i][0], 2) in drops else a.trans
    modes.append(xf.get(tr))
any_x = any(m for m in modes)
pad = td if any_x else 0.0   # every segment gets td extra tail so transitions can overlap

inputs, filt = [], []
for i, (c, (s, e)) in enumerate(zip(a.clips, slots)):
    d = e - s + pad; cd = dur(c)
    inputs += ["-i", c]
    speed = min(1.0, cd / d)  # slow down if clip too short for its slot
    filt.append(f"[{i}:v]scale={a.w}:{a.h}:force_original_aspect_ratio=increase,crop={a.w}:{a.h},fps={a.fps},setpts=PTS/{speed:.5f},trim=0:{d:.4f},setpts=PTS-STARTPTS,format=yuv420p,settb=AVTB[v{i}]")

# transition i is centred on the grid time T_i (relative to the first slot)
cur = "v0"
for i in range(1, len(slots)):
    T = slots[i][0] - slots[0][0]
    m = modes[i - 1] or ("fade" if any_x else None)
    if m is None:
        filt.append(f"[{cur}][v{i}]concat=n=2:v=1:a=0[x{i}]")
    else:
        d_ = td if modes[i - 1] else 1 / a.fps   # plain cut inside a transition chain = 1-frame xfade
        filt.append(f"[{cur}][v{i}]xfade=transition={m}:duration={d_:.4f}:offset={T - d_/2:.4f}[x{i}]")
    cur = f"x{i}"

total = slots[-1][1] - slots[0][0]
cmd = ["ffmpeg", "-y", "-loglevel", "error"] + inputs
amap = []
if a.audio:
    cmd += ["-ss", f"{slots[0][0]:.4f}", "-i", a.audio]
    ai = len(a.clips)
    filt.append(f"[{ai}:a]atrim=0:{total:.4f},afade=t=out:st={max(0,total-0.6):.3f}:d=0.6[aout]")
    amap = ["-map", "[aout]", "-c:a", "aac", "-b:a", "320k"]
cmd += ["-filter_complex", ";".join(filt), "-map", f"[{cur}]"] + amap + ["-t", f"{total:.4f}", "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
subprocess.run(cmd, check=True)
print(f"assembled {len(slots)} shots, {total:.2f}s ->", a.out)
for (s, e), c in zip(slots, a.clips): print(f"  {s:7.3f} -> {e:7.3f}  {os.path.basename(c)}")
