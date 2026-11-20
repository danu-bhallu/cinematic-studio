---
name: cutcraft
description: Editing and animation craft for cinematic music videos. Covers cut grammar (hard, smash, match, J/L, jump, cut-on-action, invisible cuts), beat rhythm and phrase patterns, speed ramps, camera-move vocabulary, earned transitions with ffmpeg and Remotion code, kinetic-type and beat-reactive animation recipes, and a cut QC checklist. Load while building any edit in /createvid, or when the user asks about cuts, pacing, transitions, speed ramps, animation, kinetic type, "make it hit harder" or "make it feel more premium".
---

# Cutcraft: How a Senior Editor Cuts and Animates

The music decides **when**. The story decides **what**. Taste decides **how little**.
All times come from `beats.json` (`tools/beats.py`). Never eyeball a cut.

---

## 1. Cut grammar: pick the cut for a reason

| Cut | What it does | When to use it | How |
|---|---|---|---|
| **Hard cut** | Invisible and confident | 90% of cuts | `assemble.py --trans cut` |
| **Smash cut** | A shock jump from quiet to loud | The drop, or into the hook | 1 frame of black or white, then the hero shot, with `impact_cinematic.wav` |
| **Match cut** | Joins two shots by shape, colour, motion or eyeline | Turning points; it feels expensive | Line up the subject's position and scale across the cut. Use `parallax.py --focus` and crop so both centres match |
| **Cut on action** | Hides the cut inside movement | Any shot with motion (a turn, a hair flip, a camera push) | Cut 2–4 frames *after* the motion starts, then carry the motion on into the next shot |
| **J-cut / L-cut** | Sound leads or trails the picture | Voiceover, a vocal intro, scene changes | The audio of shot B starts 0.3–1s before its picture (J), or the audio of A continues over B (L) |
| **Jump cut** | Same framing, time skips | Energy, or the artist's "attitude" moments | 3–5 quick cuts of the same photo at different crops or zooms, on 1/8 or 1/16 notes |
| **Invisible cut** | Hides a cut behind a flash, black or a whip | Joining two parallax moves into one long "camera move" | `--trans whip` or `blur`, same direction both sides |
| **Cutaway / insert** | Detail: eyes, hands, a lyric word, cover art | To let the hero shot breathe | 4–8 frames, on an off-beat |

**Never**:
- cross-dissolve at random;
- use spins, page curls or star wipes;
- put a transition on every cut;
- cut *just before* a beat. Cut on it, or 1 frame after it, because audio arrives a little late in perception.

---

## 2. Rhythm: phrase patterns by energy

Count in grid units (`--unit beat|downbeat`). Vary the phrases; a uniform rhythm is the #1 tell of AI-made edits.

| Section | Pattern (beats per shot) | Notes |
|---|---|---|
| Intro / cold open | 8, 8 (or one 16) | Long and slow. Push with DOF. Almost silent |
| Verse / build | 4, 4, 2, 2, 4, 2, 2, 1, 1 | Accelerate into the drop |
| **Pre-drop** | hold 2–4 beats, then 1 frame of black | **Stillness before the climax.** Remove motion, then hit |
| Drop / hook | 1, 1, 2, 1, 1, 0.5, 0.5, 2 | Cut on strong onsets (`onsets_strong`), not just beats |
| Breakdown | 8, 4 | Let one hero image breathe. Slow rise or orbit |
| Outro / title | hold 4–8 on the title | Out on a downbeat |

Accents:
- Put the biggest visual change on the biggest audio change (the `drops` in beats.json).
- Add a flash or a scale-punch on snares only in the hook, not throughout.

---

## 3. Speed ramps (for clips, or parallax renders made longer than the slot)

Ramp speed **into** the beat, then slow down **after** it. Example: 1.0× → 3× for 6 frames before the cut → 0.4× after it.

```bash
# speed-ramp segment: fast section then slow-mo, re-timed with frame blending
ffmpeg -i shot.mp4 -filter_complex "[0:v]trim=0:1.2,setpts=PTS/2.5[a];[0:v]trim=1.2:3,setpts=(PTS-STARTPTS)*2.2,minterpolate=fps=30:mi_mode=blend[b];[a][b]concat=n=2:v=1[v]" -map "[v]" ramp.mp4
```

For photos: render `parallax.py --ease expo`. Expo already gives a fast-slow ramp.

---

## 4. Camera vocabulary (photos → `tools/parallax.py`)

| Intent | Move | Settings |
|---|---|---|
| Intimacy, a reveal | `push` | strength 0.6–0.9, `--dof 0.6` |
| Release, an ending | `pull` | strength 0.8 |
| Hero shot, 3D presence | `orbit` | strength 1.0, DOF 0.5 |
| Unease, the "moment" on the drop | `dolly-zoom` | strength 1.0–1.2, wide shots only |
| Rising emotion | `rise` | Use for the title and the chorus |
| Travel / continuity | `pan-left` / `pan-right` | Keep **one** direction for the whole film (the current) |

Make each parallax clip slightly longer than its slot, so the cut lands mid-motion (motion doctrine: never settle before a cut).

---

## 5. Transitions: only when earned

| Transition | Earned when | ffmpeg `xfade` | Remotion |
|---|---|---|---|
| Flash / white-dip | the drop, a camera flash, a lyric hit | `fadewhite` (dur 0.15–0.25) | `@remotion/transitions/fade` over a white layer |
| Dip to black | time passing, act change | `fadeblack` (0.3–0.6) | `fade()` with a black layer |
| Rack-focus blur cut | dreamy or emotional joins | `hblur` / `vblur` (0.2) | animate `filter: blur()` 0→18px out, 18→0 in |
| Whip pan | energy and direction changes, same direction both sides | `smoothleft` / `smoothright` (0.15) plus `whoosh_fast.wav` | `slide({direction:"from-right"})` with motion blur |
| Zoom-through | "go deeper": push into the eye or texture, emerge in the next shot | `zoomin` (0.25) | scale 1→3 exit, 0.4→1 entry, mirrored power4 easing |
| Light leak | warm, nostalgic, the luxury preset | — | `@remotion/light-leaks` over the cut, 0.4–0.8s |
| Luma wipe | rare stylised moment | `wipetl`, `radial` | `wipe()` |
| Glitch | hype/drill only, 2–4 frames | `pixelize` (0.1) | `rgbashift` plus displacement for 3 frames |

Budget: no more than 1 flash per drop, 1 whip per act change, and a light leak only in warm or dreamy edits.

```tsx
// Remotion TransitionSeries
import {TransitionSeries, linearTiming, springTiming} from "@remotion/transitions";
import {fade} from "@remotion/transitions/fade"; import {slide} from "@remotion/transitions/slide";
<TransitionSeries>
  <TransitionSeries.Sequence durationInFrames={69}><Shot src="c1.mp4"/></TransitionSeries.Sequence>
  <TransitionSeries.Transition presentation={slide({direction:"from-right"})} timing={linearTiming({durationInFrames:5})}/>
  <TransitionSeries.Sequence durationInFrames={60}><Shot src="c2.mp4"/></TransitionSeries.Sequence>
</TransitionSeries>
```

---

## 6. Animation recipes (Remotion)

**Easing**
- Arrivals: `Easing.bezier(0.16,1,0.3,1)` (expo-out).
- Exits: `Easing.bezier(0.7,0,0.84,0)` (expo-in).
- Physical pops: `spring({damping:200})`.
- Never use linear on type.

```tsx
const f = useCurrentFrame(); const {fps} = useVideoConfig();
// 1) Mask reveal (text rises from a clip line)
<div style={{overflow:"hidden"}}><div style={{transform:`translateY(${(1-p)*110}%)`}}>WORD</div></div>
// 2) Per-word / per-letter stagger (waterfall): start_i = base + i*0.08s
// 3) Tracking collapse: letterSpacing interpolate(f,[0,2*fps],[0.9,0.4]) em, with expo-out
// 4) Beat punch: scale 1.06 -> 1 over 6 frames on each beat in the hook
const beats: number[] = beatsJson.beats_frames;
const last = beats.filter(b => b <= f).pop() ?? -99;
const punch = interpolate(f - last, [0, 6], [1.06, 1], {extrapolateRight:"clamp", easing: Easing.out(Easing.cubic)});
// 5) Impact shake (restrained): +-6px for 5 frames on drops only, with noise2D from @remotion/noise
// 6) Motion blur on anything fast: <CameraMotionBlur shutterAngle={180} samples={6}>
// 7) Text BEHIND subject: background parallax -> title -> subject RGBA (tools/cutout.py) on top
// 8) Parallax layers: bg moves 0.4x, subject 1x, foreground particles 1.6x of the same camera vector
// 9) Lyric/caption pop: one phrase at a time, 2 sizes max, keyword in the accent colour or italic serif
```

Type rules:
- 2 families at most.
- Display type is huge (12–18% of the frame width) or tiny wide-tracked caps; never medium.
- Hold readable text for at least 0.8s (at least 1.5s for the date and CTA).
- Keep type clear of the bottom 20% in 9:16.

---

## 7. Seam rules (from hf-motion-doctrine)

1. **Vector law:**
   - Exit direction = entry direction, on the same axis.
   - Matched speed: an exit on `power4.in` meets an entry on `power4.out`.
   - Cut mid-motion on both sides.
2. **One dominant direction (the current)** for ordinary cuts. Reserve "up" for reveals and "Z-forward" for going deeper.
3. **No idle wobble.** Motion performs (a push, a reveal); it doesn't breathe in place.
4. **Stillness before climax.** Kill the motion for 2–4 beats before the drop.

---

## 8. Cut QC checklist (run it before delivering)

1. Every cut is within 1 frame of a beat or onset in `beats.json`. Spot-check 5.
2. The phrase lengths vary (no 4+ identical lengths in a row outside the intro).
3. The biggest visual hit lands on the drop.
4. There is a hold or stillness before the drop.
5. Transitions are within budget, and each has a reason.
6. Motion direction stays consistent across ordinary cuts.
7. No face distortion from parallax; check close-ups at 100%.
8. Text is readable on a phone and inside the safe area.
9. Audio: SFX sit 10–14 dB under the song, and a voiceover ducks the music by about 8 dB.
10. The first 1.5 seconds hook: strong image plus sound. The last frame lands on a downbeat with the title or CTA.
