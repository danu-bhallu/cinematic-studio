#!/usr/bin/env python3
"""Voiceover: script -> polished narration WAV (+ line timings for captions), and music ducking.
Engines: ElevenLabs (best; needs ELEVENLABS_API_KEY) -> Kokoro-82M local (free, fast on CPU, Apache-2.0).

Usage:
  python voiceover.py SCRIPT.txt OUT.wav [--engine auto|kokoro|elevenlabs] [--voice af_heart] [--speed 0.95] [--pause 0.35]
  python voiceover.py --voices                        # list Kokoro voices
  python voiceover.py --duck MUSIC.mp3 VO.wav MIXED.wav [--duck-db 8] [--vo-at 0]
SCRIPT.txt: one line per phrase (a pause is added between lines). Lines starting with '#' are ignored.
Good Kokoro voices: af_heart, af_bella, af_nicole (female); am_michael, am_fenrir, bm_george (male); bf_emma (British).
ElevenLabs: --voice takes a voice_id (default: a deep narrator voice)."""
import argparse, json, os, subprocess, sys, urllib.request
import numpy as np, soundfile as sf

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KMODEL = os.path.join(STUDIO, "models", "kokoro-v1.0.onnx"); KVOICES = os.path.join(STUDIO, "models", "voices-v1.0.bin")

def kokoro_lines(lines, voice, speed):
    from kokoro_onnx import Kokoro
    k = Kokoro(KMODEL, KVOICES)
    for ln in lines:
        s, sr = k.create(ln, voice=voice, speed=speed, lang="en-gb" if voice[:1] == "b" else "en-us")
        yield np.asarray(s, dtype=np.float32), sr

def eleven_lines(lines, voice, speed):
    key = os.environ["ELEVENLABS_API_KEY"]; voice = voice or "pNInz6obpgDQGcFmaJgB"
    for ln in lines:
        body = json.dumps({"text": ln, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35, "speed": speed}}).encode()
        req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=pcm_44100", data=body,
                                     headers={"xi-api-key": key, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            pcm = np.frombuffer(r.read(), dtype=np.int16).astype(np.float32) / 32768
        yield pcm, 44100

def polish(x, sr):
    try:
        from pedalboard import Pedalboard, HighpassFilter, Compressor, PeakFilter, Limiter, Gain
        board = Pedalboard([HighpassFilter(80), PeakFilter(6500, -3, 2.0), PeakFilter(180, 1.5, 0.8),  # de-ess-ish + warmth
                            Compressor(threshold_db=-20, ratio=3, attack_ms=5, release_ms=120), Gain(3), Limiter(-1.0)])
        return board(x[None, :], sr)[0]
    except Exception:
        return x / (np.abs(x).max() + 1e-9) * 0.89

def synth(a):
    lines = [l.strip() for l in open(a.script, encoding="utf-8") if l.strip() and not l.startswith("#")]
    eng = a.engine
    if eng == "auto": eng = "elevenlabs" if os.environ.get("ELEVENLABS_API_KEY") else "kokoro"
    if eng == "kokoro" and not os.path.exists(KMODEL): sys.exit(f"Kokoro model missing at {KMODEL}. Run setup.sh.")
    gen = eleven_lines(lines, a.voice if eng == "elevenlabs" else None, a.speed) if eng == "elevenlabs" else kokoro_lines(lines, a.voice or "af_heart", a.speed)
    out, timings, t, sr0 = [], [], 0.0, None
    for ln, (x, sr) in zip(lines, gen):
        sr0 = sr0 or sr
        timings.append({"text": ln, "start": round(t, 3), "end": round(t + len(x) / sr, 3)})
        out += [x, np.zeros(int(a.pause * sr), np.float32)]; t += len(x) / sr + a.pause
    y = polish(np.concatenate(out), sr0)
    sf.write(a.out, y, sr0, subtype="PCM_24")
    json.dump(timings, open(os.path.splitext(a.out)[0] + "_lines.json", "w"), indent=1)
    print(f"voiceover ({eng}) -> {a.out}  {t:.1f}s, {len(lines)} lines; timings in {os.path.splitext(a.out)[0]}_lines.json")

def duck(music, vo, out, db, at):
    # sidechain compression: music dips ~db under the voice, recovers smoothly
    ratio = max(2, db)
    f = (f"[1:a]adelay={int(at*1000)}|{int(at*1000)},apad[vo];[vo]asplit[vo1][sc];"
         f"[0:a][sc]sidechaincompress=threshold=0.02:ratio={ratio}:attack=40:release=450:makeup=1[m];"
         f"[m][vo1]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", music, "-i", vo, "-filter_complex", f, "-map", "[a]", out], check=True)
    print("ducked mix ->", out)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("script", nargs="?"); ap.add_argument("out", nargs="?")
    ap.add_argument("--engine", default="auto"); ap.add_argument("--voice"); ap.add_argument("--speed", type=float, default=0.95)
    ap.add_argument("--pause", type=float, default=0.35); ap.add_argument("--voices", action="store_true")
    ap.add_argument("--duck", nargs=3, metavar=("MUSIC", "VO", "OUT")); ap.add_argument("--duck-db", type=float, default=8); ap.add_argument("--vo-at", type=float, default=0)
    a = ap.parse_args()
    if a.voices:
        from kokoro_onnx import Kokoro; print("\n".join(sorted(Kokoro(KMODEL, KVOICES).get_voices())))
    elif a.duck: duck(*a.duck, a.duck_db, a.vo_at)
    elif a.script and a.out: synth(a)
    else: ap.print_help()
