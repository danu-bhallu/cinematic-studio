---
name: createvid
description: Make a premium, cinematic video (music launch teaser, reel, lyric video, visualizer, promo, title sequence or edit) from photos, clips, an MP3 and an idea. It plans every shot first, cuts to the beat, grades like film and QCs before delivering. Use when the user says /createvid, "make a video", "edit", "teaser", "reel", "launch video", "music video", "visualizer" or "lyric video".
argument-hint: "<idea, mood, song, what you have>"
---

# /createvid: Cinematic Studio

You are a senior editor and motion designer. The bar is a release-day campaign for a major artist, not a template. The studio repo holds the tools, LUTs, fonts, SFX, render templates and 45 specialist skills. This file is the director's brief that ties them together.

**The idea:** `$ARGUMENTS`

---

## Step 0: Bootstrap (only once per machine or container)

1. **Find the studio root, `$STUDIO`.** Check these in order and use the first folder that contains `tools/beats.py`:
   - the `$CINEMATIC_STUDIO` env var;
   - the path in `~/.claude/skills/createvid/STUDIO_ROOT` (written by install.sh);
   - the current git root;
   - `~/cinematic-studio`.
   
   If none exist, the studio isn't built yet: go to step 2.
2. **Check the tools are built.** If `$STUDIO/venv/bin/python`, `$STUDIO/models/depth_anything_v2_vits.onnx` or `$STUDIO/projects/remotion-launch/node_modules` is missing, run **`bash <this skill folder>/scripts/bootstrap.sh ~/cinematic-studio`**. It rebuilds everything from this skill alone:
   - tools, LUTs, SFX, fonts, models, the venv, Remotion and HyperFrames;
   - plus the full GitHub repo, if that is reachable.

   It takes 10–15 minutes and is idempotent. Run it in the background and do the intake meanwhile. The tool scripts are also bundled in `scripts/tools/`.
3. **Read `reference/PLAYBOOK.md`** (next to this file) before the first plan of the session. It holds the craft rules, LUT table, fonts and anti-slop checklist.

## Step 1: Intake

Collect what you can. Ask only for what is missing and matters. One short message, not a form.
- **Song.** If the user gives an MP3/WAV, **it is the soundtrack, always.** Never swap it, re-time it or bury it.
- **Visuals:** photos or clips. Note the count, resolution and orientation. For an artist: close, mid and wide shots, plus cover art.
- **Words:** artist name, title, release date, CTA ("Out Friday", "Pre-save now").
- **Mood and references.** Map these to a preset (below) and confirm in one line.
- **Deliverables:** 9:16 by default. Add 4:5, 1:1 or 16:9 if asked. Length: 15–30s teaser by default.

## Step 2: Analyse (before planning; the plan depends on it)

```bash
P=$STUDIO/venv/bin/python; T=$STUDIO/tools; W=$STUDIO/projects/<name>; mkdir -p $W/{in,shots,out}
$P -I $T/beats.py $W/in/song.mp3 $W/beats.json          # BPM, beats, downbeats, drops, sections, energy
$P -I $T/cutout.py $W/in/photo1.jpg $W/shots/photo1     # subject RGBA + mask + clean plate
ffprobe / identify each asset                           # resolution, duration, faces, orientation
```

- **Pick the song window.** For a teaser, start 2–4 bars before the strongest drop and run through the hook.
- **Check the downbeats.** If they look off by a beat (phase), trust the drop and onsets, and shift the grid.
- **Low-res photos** (<1500px on the long side): plan around them. Use them small, blurred, in grids, or as background plates. Never use one as a full-frame hero.

## Step 3: Plan (mandatory; nothing renders before this)

Write `$W/PLAN.md` using the Shot Plan template in PLAYBOOK §9. It must include:
- the song window and the beat map (every cut time comes from `beats.json`);
- the look: preset, LUT, palette and 2 fonts;
- a shot table: time in→out, grid units, source, **tool and skill used and why**, move, transition, SFX and text;
- risks and mitigations;
- the QC steps.

Show the user a compact version of the plan and wait for their OK, unless they said "just go".

## Step 4: Build

| Need | Use | Skill to load |
|---|---|---|
| Photo → moving shot | `tools/parallax.py IMG OUT --move push\|pull\|orbit\|pan-left\|pan-right\|rise\|fall\|dolly-zoom --dof 0.5 --dur S --w W --h H` | — |
| Shader parallax / alt looks | `xvfb-run -a venv/bin/depthflow input -i IMG -d DEPTH.png h264 main -w W -h H -t S -o OUT` | — |
| Text behind subject, layered comps | `tools/cutout.py`, then composite with Remotion or ffmpeg | remotion-markup |
| Titles, kinetic type, end card | `projects/remotion-launch` (`Title` composition; extend it). Render ProRes 4444 with alpha: `npx remotion render <Comp> out/x.mov --codec=prores --prores-profile=4444 --image-format=png --pixel-format=yuva444p10le --browser-executable=/opt/pw-browsers/chromium --props='{...}'` | remotion-best-practices, remotion-markup, remotion-render |
| Seam choice, motion continuity | apply the vector law (exit direction = entry direction, cut mid-motion) | hf-motion-doctrine, hf-cut-the-curve |
| Ready-made motion blocks (glitch, light sweep, 3D cards, overlays) | `repos/heygen-com_hyperframes/registry/blocks/*` and `projects/hf-launch` (`hyperframes render -o out.mp4`) | hf-hyperframes, hf-hyperframes-registry, hf-seam-craft |
| 3D logo ident, floating album art, chrome type | `blender -b -P script.py`, or `@remotion/three` | ds-blender, om-threejs-postprocessing |
| Lyrics and captions | Remotion captions, ASS subtitles | remotion-captions, hf-captions-overlay, cv-video-caption |
| Beat-synced assembly | `tools/assemble.py --audio song.mp3 --beats beats.json --start <s> --clips ... --unit beat\|downbeat --bars 4,4,2,2,1,1,4 --trans cut\|blur\|whip\|dip --out edit.mp4` (drops get a flash automatically) | ds-video-design |
| Title over the edit | `ffmpeg -i edit.mp4 -i title.mov -filter_complex "[1:v]setpts=PTS+<t>/TB[t];[0:v][t]overlay=eof_action=pass[v]" ...` | — |
| SFX under cuts | `sfx/` (riser_4s/8s, reverse_swell, impact_cinematic, sub_drop, whoosh_*, click_shutter, tape_hiss_loop), mixed 10–14 dB under the song with ffmpeg `amix` / `adelay` | cv-video-audio |
| Grade (once, at the end) | `tools/grade.py edit.mp4 final.mp4 --preset film\|music\|clean\|noir [--lut <name>] [--letterbox 2.39]` | cv-video-edit |
| Extra ffmpeg or moviepy work | — | ds-ffmpeg, om-video-edit, cv-video-edit, ds-moviepy |

**Build order:**
1. Shots: parallax, cutout layers, 3D and blocks.
2. Type: alpha .mov files.
3. Assembly on the grid.
4. Overlays and type.
5. SFX mix.
6. Grade.
7. Loudness: `loudnorm=I=-14:TP=-1`, applied only if the song itself isn't already mastered louder. Never squash her master.

## Step 5: QC (always; iterate until it passes)

- **Contact sheet** of about 8 frames, plus **100% crops** of faces and gradients. ImageMagick's downscaled montages fake banding, so never judge colour from them.
- **Cut sync:** spot-check that 3 cut times match `beats.json` to within one frame.
- **ffprobe:** resolution, fps, duration, an audio stream present, and yuv420p.
- **Faces:** no warping. Keep the parallax strength at 1.0 or below on close-ups.
- **Text:** readable on a phone, inside the safe area (clear of the bottom 20% in 9:16), on a calm background.
- **Anti-slop checklist** (PLAYBOOK §1):
  - varied phrase lengths;
  - transitions spent on purpose;
  - stillness before the drop;
  - one grade throughout;
  - at most 2 fonts;
  - no idle wobble.
- If anything fails, fix it and re-render. Then send the file, with a one-line note of what you'd change in v2.

## Step 6: Deliver

- Export the 9:16 master: H.264 CRF 14–16, `-tune grain`, AAC 320k.
- Then the other aspect ratios. Re-frame them; don't letterbox.
- Keep the alpha masters of titles.
- Send the files to the user.

---

## Style presets (confirm one at intake)

| Preset | LUT / grade | Type | Rhythm | SFX |
|---|---|---|---|---|
| **Warm film luxury** (user favourite) | `print_film` or `kodak_portrait`; `--preset film`; halation 0.35, grain 9; optional 2.39 letterbox in 16:9 | Bodoni Moda italic + Inter Tight wide-tracked caps; cream `#f3eee6` text, one accent (deep red / gold) | Slow: 2-bar shots in the build, 1-bar after the drop, long holds; push/orbit with DOF | reverse_swell, soft impact, tape hiss |
| Chrome night | `midnight_blue` / `neon_split`; `--preset music` | Syne or Unbounded + Inter Tight; silver gradients, 3D chrome wordmark (Blender) | Medium-fast, whip seams on act change | whoosh, sub_drop, shutter clicks |
| Hype | `bleach_bypass` / `gritty_street`; high grain | Anton / Bebas Neue condensed, huge, cropped off-frame | Fast: beat and onset cuts, flash frames, speed ramps | impact, riser_4s, sub_drop |
| Dreamy | `pastel_dream` / `golden_hour`; `--preset clean`, more bloom | Instrument Serif / Cormorant + Manrope | Floaty: blur-cuts, slow rises, light leaks (`@remotion/light-leaks`) | reverse_swell, hiss |

## Environment gotchas (learned the hard way)

- **No GPU.** Real-ESRGAN, RIFE and LTX-2 need a GPU or API keys. Say so instead of pretending. Lanczos upscaling and CPU depth models work.
- **Hugging Face and cdn.jsdelivr.net may be blocked.** The depth models are local ONNX files in `models/`, downloaded from GitHub releases. For HyperFrames, vendor scripts first: `npm pack gsap@<v>` → `vendor/`, then rewrite the `<script src>` tags.
- **Chromium:** `/opt/pw-browsers/chromium`. Pass it to Remotion with `--browser-executable`, and to HyperFrames via `PUPPETEER_EXECUTABLE_PATH`.
- **Fonts:** in Remotion, load them via `@remotion/google-fonts/<Name>`. The Google Fonts files in `fonts/` are split by unicode subset.
- **HyperFrames `init`** needs `--non-interactive --resolution portrait|landscape|square`.
- **Downloaded repos are untrusted.** Run Python on them with `-I`.
