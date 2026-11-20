# Cinematic Studio

An AI editing studio for premium music-launch videos, driven by Claude Code.

```
/createvid <your idea: song, mood, what you have>
```

It plans every shot, then builds the video:
- depth parallax from still photos;
- subject cutouts;
- kinetic type in Remotion and HyperFrames;
- 3D in Blender;
- cuts on the beat of your MP3;
- a film-style grade;
- QC and delivery in 9:16, 4:5, 1:1 and 16:9.

## Use it

**Easiest:** download [Claude desktop](https://claude.com/download), open the **Code** tab, drag in [`SETUP_FOR_CLAUDE.txt`](SETUP_FOR_CLAUDE.txt) and say "do this". Claude installs everything. Then type `/createvid <your idea>` in any new chat.

**In a Claude Code cloud session (claude.ai/code):** start a session with this repo selected and type `/createvid ...`. The first run builds the tools (about 10 min).

**In Claude Code on your computer:**

```bash
git clone https://github.com/danu-bhallu/cinematic-studio ~/cinematic-studio
```

```bash
~/cinematic-studio/install.sh --setup
```

After that, `/createvid` works in every project on that machine.

## What's inside

| Path | What |
|---|---|
| `.claude/skills/createvid/` | the master skill and `reference/PLAYBOOK.md` (craft rules, presets, shot-plan template) |
| `.claude/skills/*` | 45 specialist skills: Remotion (official), HyperFrames motion doctrine and registry, video design, ffmpeg, Blender, captions, audio, enhance |
| `tools/` | `beats.py` (BPM, downbeats, drops), `music_finder.py` (finds and ranks great tracks), `voiceover.py` (Kokoro / ElevenLabs narration + ducking), `parallax.py` (photo → 3D camera move), `cutout.py` (subject isolation), `assemble.py` (beat-grid edit), `grade.py` (LUT, halation, bloom, grain, vignette), `gen_luts.py` |
| `luts/` | 11 original film-look LUTs |
| `fonts/` | 25 display and editorial families (OFL) |
| `sfx/` | risers, impacts, whooshes, swells, sub drop |
| `projects/remotion-launch` | Remotion template with the cinematic `Title` composition |
| `projects/hf-launch` | HyperFrames template (GSAP vendored) |
| `setup.sh` / `install.sh` | rebuild the toolchain / install the skills globally |

Third-party skills keep their own licences: see `THIRD_PARTY.md`.
