#!/usr/bin/env python3
"""Find a GREAT track when the user did not upload one.
Searches Jamendo (if JAMENDO_CLIENT_ID is set; free key at developer.jamendo.com) and Openverse (no key),
downloads candidates, analyses each with librosa and ranks them on production quality and editability.
Optionally generates a custom track with ElevenLabs Music (ELEVENLABS_API_KEY).

Usage:
  python music_finder.py "warm luxury cinematic" OUT_DIR [--bpm 70-110] [--min-len 60] [--commercial] [--top 3] [--generate]
  python music_finder.py --score-local OUT_DIR a.mp3 b.wav ...      # rank local files only (offline test)
Writes OUT_DIR/candidates.json and OUT_DIR/preview_<n>.mp3 (20s around each track's best moment).
RULE: if the user uploaded a song, do NOT run this - use theirs exactly."""
import argparse, json, os, re, subprocess, sys, urllib.parse, urllib.request
import numpy as np

UA = {"User-Agent": "cinematic-studio-music-finder/1.0"}
MOODS = {  # brief keyword -> search tags
    "luxury": ["cinematic", "piano", "soul", "lounge", "orchestral", "elegant"],
    "warm": ["soul", "jazz", "acoustic", "rnb", "piano"],
    "film": ["cinematic", "orchestral", "score", "epic"],
    "cinematic": ["cinematic", "epic", "orchestral", "trailer"],
    "hype": ["trap", "hiphop", "edm", "bass", "energetic"],
    "rap": ["hiphop", "trap", "beats"], "drill": ["trap", "drill", "hiphop"],
    "dreamy": ["dreampop", "ambient", "chillwave", "lofi"],
    "sad": ["piano", "ambient", "emotional", "melancholic"],
    "dark": ["dark", "electronic", "industrial", "cinematic"],
    "night": ["synthwave", "electronic", "deephouse", "rnb"],
    "pop": ["pop", "electropop", "dance"], "rnb": ["rnb", "soul", "neosoul"],
    "chill": ["chillout", "lofi", "downtempo"], "epic": ["epic", "trailer", "orchestral"],
    "fashion": ["deephouse", "electronic", "minimal", "lounge"],
}

def tags_for(brief):
    t = []
    for w in re.findall(r"[a-z]+", brief.lower()):
        t += MOODS.get(w, [])
    return list(dict.fromkeys(t or re.findall(r"[a-z]+", brief.lower())))[:6]

def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def search_jamendo(tags, min_len, commercial):
    cid = os.environ.get("JAMENDO_CLIENT_ID")
    if not cid: return []
    out = []
    for tag in tags[:4]:
        q = dict(client_id=cid, format="json", limit=20, tags=tag, order="popularity_total",
                 audioformat="mp32", include="musicinfo licenses", durationbetween=f"{min_len}_600", vocalinstrumental="instrumental")
        try:
            for r in get_json("https://api.jamendo.com/v3.0/tracks/?" + urllib.parse.urlencode(q)).get("results", []):
                lic = r.get("license_ccurl", "")
                if commercial and "-nc" in lic: continue
                out.append(dict(source="jamendo", id=f"jm{r['id']}", title=r["name"], artist=r["artist_name"], url=r.get("audiodownload") or r["audio"],
                                page=r.get("shareurl"), license=lic, duration=r.get("duration"), popularity=1.0,
                                attribution=f'"{r["name"]}" by {r["artist_name"]} (Jamendo) — {lic}'))
        except Exception as e:
            print("jamendo error:", e, file=sys.stderr)
    return out

def search_openverse(tags, min_len, commercial):
    out = []
    for q in [" ".join(tags[:2]), tags[0] if tags else "cinematic"]:
        p = dict(q=q, category="music", page_size=20, mature="false")
        if commercial: p["license_type"] = "commercial"
        try:
            for r in get_json("https://api.openverse.org/v1/audio/?" + urllib.parse.urlencode(p)).get("results", []):
                d = (r.get("duration") or 0) / 1000
                if d and d < min_len: continue
                out.append(dict(source=f"openverse:{r.get('source')}", id=f"ov{r['id']}", title=r.get("title"), artist=r.get("creator"),
                                url=r.get("url"), page=r.get("foreign_landing_url"), license=f"{r.get('license')} {r.get('license_version','')}".strip(),
                                duration=d, popularity=0.6, attribution=r.get("attribution") or f'{r.get("title")} by {r.get("creator")}'))
        except Exception as e:
            print("openverse error:", e, file=sys.stderr)
    return out

def analyse(path, bpm_lo, bpm_hi):
    import librosa
    y, sr = librosa.load(path, sr=22050, mono=True, duration=240)
    dur = len(y) / sr
    if dur < 15: return None
    rms = librosa.feature.rms(y=y)[0]; t = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
    tempo = float(np.atleast_1d(librosa.beat.beat_track(y=y, sr=sr)[0])[0])
    db = 20 * np.log10(rms + 1e-9)
    loud = float(np.percentile(db, 90))                       # how "mastered" it is
    dyn = float(np.percentile(db, 90) - np.percentile(db, 20))  # build/drop contrast
    cent = float(np.median(librosa.feature.spectral_centroid(y=y, sr=sr)))
    bw = float(np.median(librosa.feature.spectral_bandwidth(y=y, sr=sr)))
    low = float(np.mean(np.abs(librosa.stft(y, n_fft=2048))[:20]) / (np.mean(np.abs(librosa.stft(y, n_fft=2048))) + 1e-9))
    sm = np.convolve(rms, np.ones(43) / 43, "same"); lag = int(2 * sr / 512)
    jump = np.r_[np.zeros(lag), sm[lag:] - sm[:-lag]]
    best = float(t[int(np.argmax(jump))]) if len(jump) else 0.0
    onset = librosa.onset.onset_strength(y=y, sr=sr); punch = float(np.percentile(onset, 95) / (np.median(onset) + 1e-9))
    # scoring (0..1 each)
    s_loud = np.clip((loud + 30) / 20, 0, 1)        # -30 dBFS rms = thin demo, -10 = mastered
    s_dyn = np.clip((dyn - 4) / 14, 0, 1)            # flat loops score low
    s_full = np.clip(bw / 2500, 0, 1) * 0.6 + np.clip(low / 3, 0, 1) * 0.4
    s_punch = np.clip((punch - 2) / 6, 0, 1)
    if bpm_lo <= tempo <= bpm_hi or bpm_lo <= tempo * 2 <= bpm_hi or bpm_lo <= tempo / 2 <= bpm_hi: s_tempo = 1.0
    else: s_tempo = 0.4
    s_drop = np.clip(float(jump.max()) / (float(sm.mean()) + 1e-9) * 2, 0, 1)
    score = 0.25 * s_loud + 0.2 * s_dyn + 0.15 * s_full + 0.15 * s_drop + 0.1 * s_punch + 0.15 * s_tempo
    reject = loud < -32 or cent < 500 or dur < 20
    return dict(duration=round(dur, 1), bpm=round(tempo, 1), loudness_db=round(loud, 1), dynamics_db=round(dyn, 1),
                best_moment=round(best, 2), score=round(float(score), 3), reject=bool(reject),
                parts=dict(loud=round(float(s_loud), 2), dyn=round(float(s_dyn), 2), full=round(float(s_full), 2), drop=round(float(s_drop), 2), punch=round(float(s_punch), 2), tempo=s_tempo))

def preview(src, dst, at):
    st = max(0, at - 8)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{st}", "-i", src, "-t", "20", "-af", "afade=t=in:d=0.5,afade=t=out:st=19:d=1", "-b:a", "192k", dst], check=False)

def generate_eleven(brief, out, seconds):
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key: return None
    body = json.dumps({"prompt": f"{brief}. Instrumental, premium production, clear build and a strong drop, suitable for a cinematic music video.", "music_length_ms": int(seconds * 1000)}).encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1/music", data=body, headers={**UA, "xi-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r, open(out, "wb") as f:
        f.write(r.read())
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brief", nargs="?"); ap.add_argument("out", nargs="?")
    ap.add_argument("--bpm", default="60-180"); ap.add_argument("--min-len", type=float, default=45)
    ap.add_argument("--commercial", action="store_true"); ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--max", type=int, default=15); ap.add_argument("--generate", action="store_true")
    ap.add_argument("--score-local", nargs="+", metavar=("OUT_DIR", "FILES"))
    a = ap.parse_args()
    lo, hi = [float(x) for x in a.bpm.split("-")]

    if a.score_local:
        out, files = a.score_local[0], a.score_local[1:]
        cands = [dict(source="local", id=f"local{i}", title=os.path.basename(f), artist="", url=f, license="", attribution="", popularity=0.5, file=f) for i, f in enumerate(files)]
    else:
        out = a.out
        tags = tags_for(a.brief)
        print("search tags:", tags)
        cands = search_jamendo(tags, a.min_len, a.commercial) + search_openverse(tags, a.min_len, a.commercial)
        seen, uniq = set(), []
        for c in cands:
            k = (str(c["title"]).lower(), str(c["artist"]).lower())
            if c["url"] and k not in seen: seen.add(k); uniq.append(c)
        cands = uniq[: a.max]
    os.makedirs(out, exist_ok=True)
    if not a.score_local and not cands and not a.generate:
        sys.exit("No results (network blocked or no matches). Try other words, set JAMENDO_CLIENT_ID, use --generate, or ask the user to upload a track.")

    ranked = []
    for i, c in enumerate(cands):
        f = c.get("file") or os.path.join(out, f"cand_{i}.mp3")
        if not c.get("file"):
            try:
                req = urllib.request.Request(c["url"], headers=UA)
                with urllib.request.urlopen(req, timeout=60) as r, open(f, "wb") as fh: fh.write(r.read())
            except Exception as e:
                print("download failed:", c["title"], e, file=sys.stderr); continue
        try: m = analyse(f, lo, hi)
        except Exception as e: print("analyse failed:", c["title"], e, file=sys.stderr); continue
        if not m: continue
        c.update(m, file=f); c["score"] = round(c["score"] * 0.85 + 0.15 * c.get("popularity", 0.5), 3)
        ranked.append(c); print(f"  {c['score']:.3f} {'REJECT ' if c['reject'] else ''}{c['title']} — {c['artist']}  {c['bpm']}bpm {c['duration']}s")

    if a.generate:
        g = os.path.join(out, "generated_elevenlabs.mp3")
        try:
            if generate_eleven(a.brief or "cinematic", g, max(a.min_len, 60)):
                m = analyse(g, lo, hi) or {}
                ranked.append(dict(source="elevenlabs-music", id="gen", title="Custom generated track", artist="ElevenLabs Music", file=g, license="per ElevenLabs terms", attribution="", **m))
        except Exception as e: print("generation failed:", e, file=sys.stderr)

    ranked.sort(key=lambda c: (not c.get("reject", False), c.get("score", 0)), reverse=True)
    top = [c for c in ranked if not c.get("reject")][: a.top] or ranked[: a.top]
    for n, c in enumerate(top, 1):
        c["preview"] = os.path.join(out, f"preview_{n}.mp3"); preview(c["file"], c["preview"], c.get("best_moment", 30))
    json.dump(dict(top=top, all=ranked), open(os.path.join(out, "candidates.json"), "w"), indent=1)
    print("\nTOP PICKS (show these previews to the user and let them choose):")
    for n, c in enumerate(top, 1):
        print(f" {n}. {c['title']} — {c['artist']} | {c.get('bpm')} BPM | score {c.get('score')} | {c.get('license')}\n    preview: {c['preview']}\n    credit: {c.get('attribution')}")

if __name__ == "__main__":
    main()
