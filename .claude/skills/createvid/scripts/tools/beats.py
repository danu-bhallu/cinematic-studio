#!/usr/bin/env python3
"""Analyze a track (mp3/wav/...) for editing: tempo, beats, downbeats, onsets,
energy curve, sections and drop candidates. Writes JSON for cutting on the music.
Usage: python beats.py SONG.mp3 [OUT.json] [--fps 30]"""
import sys, json, argparse
import numpy as np
import librosa

ap = argparse.ArgumentParser()
ap.add_argument("audio")
ap.add_argument("out", nargs="?", default=None)
ap.add_argument("--fps", type=float, default=30)
a = ap.parse_args()

y, sr = librosa.load(a.audio, sr=22050, mono=True)
dur = len(y) / sr
hop = 512

tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop, units="frames")
tempo = float(np.atleast_1d(tempo)[0])
beats = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop)

# downbeat guess: choose the beat phase (0..3) whose beats carry the most low-end onset energy
y_harm, y_perc = librosa.effects.hpss(y)
low = librosa.onset.onset_strength(y=y_perc, sr=sr, hop_length=hop, fmax=200)
phase_score = [low[beat_frames[p::4]].sum() if len(beat_frames) > p else 0 for p in range(4)]
phase = int(np.argmax(phase_score))
downbeats = beats[phase::4]

onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, hop_length=hop, units="time")
on_strength = onset_env[librosa.time_to_frames(onsets, sr=sr, hop_length=hop)]
strong = onsets[on_strength > np.percentile(on_strength, 85)] if len(onsets) else onsets

rms = librosa.feature.rms(y=y, hop_length=hop)[0]
t_rms = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
# energy per second (normalized) for pacing decisions
sec = np.arange(0, int(np.ceil(dur)))
energy = [float(rms[(t_rms >= s) & (t_rms < s + 1)].mean()) if np.any((t_rms >= s) & (t_rms < s + 1)) else 0 for s in sec]
emax = max(energy) or 1
energy = [round(e / emax, 3) for e in energy]

# sections via agglomerative clustering on beat-synced chroma+mfcc
try:
    chroma = librosa.feature.chroma_cqt(y=y_harm, sr=sr, hop_length=hop)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop, n_mfcc=13)
    feat = np.vstack([librosa.util.normalize(chroma), librosa.util.normalize(mfcc)])
    k = int(np.clip(dur // 20, 3, 10))
    bounds = librosa.segment.agglomerative(feat, k)
    section_times = sorted(set([0.0] + [round(float(t), 3) for t in librosa.frames_to_time(bounds, sr=sr, hop_length=hop)] + [round(dur, 3)]))
except Exception as e:
    section_times = [0.0, round(dur, 3)]
sections = []
for i in range(len(section_times) - 1):
    s, e = section_times[i], section_times[i + 1]
    m = (t_rms >= s) & (t_rms < e)
    sections.append({"start": s, "end": e, "energy": round(float(rms[m].mean() / (rms.max() or 1)), 3) if m.any() else 0})

# drop candidates: biggest positive jumps in smoothed energy, snapped to nearest downbeat
sm = np.convolve(rms, np.ones(43) / 43, mode="same")
lag = int(2 * sr / hop)
jump = np.zeros_like(sm)
jump[lag:] = sm[lag:] - sm[:-lag]
cand = []
for idx in np.argsort(jump)[::-1]:
    t = float(t_rms[idx])
    if jump[idx] <= 0 or any(abs(t - c) < 8 for c in cand):
        continue
    cand.append(t)
    if len(cand) >= 4:
        break
snap = lambda t: float(downbeats[np.argmin(np.abs(downbeats - t))]) if len(downbeats) else t
drops = sorted({round(snap(t), 3) for t in cand})

r = lambda arr: [round(float(x), 3) for x in arr]
out = {
    "file": a.audio, "duration": round(dur, 3), "tempo_bpm": round(tempo, 2),
    "beat_period": round(60 / tempo, 4) if tempo else None, "fps": a.fps,
    "beats": r(beats), "downbeats": r(downbeats), "bars": len(downbeats),
    "onsets_strong": r(strong), "drops": drops, "sections": sections,
    "energy_per_second": energy,
    "beats_frames": [int(round(b * a.fps)) for b in beats],
    "downbeats_frames": [int(round(b * a.fps)) for b in downbeats],
}
js = json.dumps(out, indent=1)
if a.out:
    open(a.out, "w").write(js)
print(f"{dur:.1f}s  {tempo:.1f} BPM  {len(beats)} beats  {len(downbeats)} bars  drops={drops}  sections={len(sections)}")
