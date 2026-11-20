#!/usr/bin/env bash
# Build the whole Cinematic Studio from this skill folder alone, without needing the GitHub repo.
# Usage: bash bootstrap.sh [STUDIO_DIR]   (default ~/cinematic-studio). Idempotent; ~10-15 min first time.
set -e
SK="$(cd "$(dirname "$0")" && pwd)"
ST="${1:-$HOME/cinematic-studio}"
mkdir -p "$ST"/{tools,luts,sfx,fonts,models,projects,repos}
cd "$ST"
echo "== studio: $ST"

# 1) If the full repo is reachable, prefer it (has the 44 specialist skills, fonts and templates)
if [ ! -f "$ST/.claude/skills/createvid/SKILL.md" ]; then
  git clone -q --depth 1 https://github.com/danu-bhallu/cinematic-studio "$ST.repo" 2>/dev/null && cp -rn "$ST.repo/." "$ST/" && rm -rf "${ST:?}.repo" && echo "== pulled full repo" || echo "== repo not reachable; building standalone"
fi
cp -n "$SK"/tools/*.py tools/ ; chmod +x tools/*.py

# 2) System packages
SUDO=""; [ "$(id -u)" != 0 ] && command -v sudo >/dev/null && SUDO=sudo
need=""; for b in ffmpeg convert sox blender xvfb-run; do command -v $b >/dev/null || need=1; done
if [ -n "$need" ] && command -v apt-get >/dev/null; then
  export DEBIAN_FRONTEND=noninteractive; $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq ffmpeg imagemagick blender sox libsox-fmt-all fonts-noto-core fonts-inter xvfb libegl1 libgl1-mesa-dri libosmesa6 >/dev/null
elif [ -n "$need" ] && command -v brew >/dev/null; then brew install ffmpeg imagemagick sox || true; fi

# 3) Python toolchain
[ -x venv/bin/python ] || python3 -m venv venv
venv/bin/python -c "import librosa, rembg, onnxruntime, depthflow, moviepy, cv2" 2>/dev/null || {
  venv/bin/pip install -q --upgrade pip
  venv/bin/pip install -q moviepy librosa opencv-python-headless scenedetect pillow numpy scipy soundfile "rembg[cpu]" onnxruntime depthflow pedalboard pydub; }

# 4) Models (GitHub releases; no Hugging Face needed)
for m in depth_anything_v2_vits depth_anything_v2_vitb; do
  [ -s models/$m.onnx ] || curl -sfL -o models/$m.onnx https://github.com/fabio-sim/Depth-Anything-ONNX/releases/download/v2.0.0/$m.onnx || echo "warn: $m download failed"
done
# Voiceover: Kokoro-82M (local, Apache-2.0)
venv/bin/python -c "import kokoro_onnx" 2>/dev/null || venv/bin/pip install -q kokoro-onnx || echo "warn: kokoro-onnx not installed"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do [ -s models/$f ] || curl -sfL -o models/$f https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f || echo "warn: $f download failed"; done
venv/bin/python -I -c "from rembg import new_session; new_session('u2net_human_seg'); new_session('isnet-general-use')" >/dev/null || true

# 5) Looks: LUTs (generated) + SFX (synthesised)
[ -f luts/print_film.cube ] || venv/bin/python -I tools/gen_luts.py luts
if command -v sox >/dev/null && [ ! -f sfx/impact_cinematic.wav ]; then (cd sfx
  sox -n -r 48000 -c 2 whoosh_fast.wav synth 0.6 pinknoise sinc 300-6000 fade q 0.25 0.6 0.3 tremolo 0.8 30 gain -n -3
  sox -n -r 48000 -c 2 whoosh_slow.wav synth 1.4 pinknoise lowpass 2500 fade h 0.8 1.4 0.6 gain -n -4
  sox -n -r 48000 -c 2 riser_4s.wav synth 4 sine 80-1200 synth 4 pinknoise mix vol 0.6 highpass 200 fade p 3.8 4 0.05 gain -n -3
  sox -n -r 48000 -c 2 riser_8s.wav synth 8 sine 60-1600 synth 8 pinknoise mix highpass 150 fade p 7.8 8 0.05 gain -n -3
  sox -n -r 48000 -c 2 sub_drop.wav synth 1.5 sine 90-28 fade 0 1.5 1.2 gain -n -1
  sox -n -r 48000 -c 2 impact_body.wav synth 1.2 sine 55-35 fade 0 1.2 1.0 gain -n -2
  sox -n -r 48000 -c 2 impact_crack.wav synth 0.25 whitenoise highpass 1500 fade 0 0.25 0.22 gain -n -6
  sox -m impact_body.wav impact_crack.wav impact_cinematic.wav reverb 40 gain -n -1
  sox -n -r 48000 -c 2 tape_hiss_loop.wav synth 10 brownnoise highpass 2000 vol 0.04
  sox -n -r 48000 -c 2 click_shutter.wav synth 0.03 whitenoise highpass 3000 fade 0 0.03 0.02 gain -n -8
  sox -n -r 48000 -c 2 reverse_swell.wav synth 2 pinknoise lowpass 4000 reverb 90 reverse fade p 1.9 2 0.05 gain -n -4
) 2>/dev/null; fi

# 6) Fonts (Google Fonts, OFL)
if [ -z "$(ls fonts 2>/dev/null)" ]; then
  for f in "Bodoni Moda" "Playfair Display" "Inter Tight" "Space Grotesk" "Syne" "Unbounded" "Anton" "Bebas Neue" "Fraunces" "Italiana" "Cormorant Garamond" "Manrope" "DM Serif Display" "Instrument Serif" "Oswald" "Cinzel" "Montserrat" "Outfit"; do
    q=$(echo "$f" | tr ' ' '+'); d=fonts/$(echo "$f" | tr -d ' '); mkdir -p "$d"; i=0
    for spec in ":wght@400;700" ""; do css=$(curl -s -A "Wget/1.0" "https://fonts.googleapis.com/css2?family=$q$spec"); echo "$css" | grep -q gstatic && break; done
    for u in $(echo "$css" | grep -o 'https://fonts.gstatic.com[^)]*' | sort -u); do i=$((i+1)); curl -s -o "$d/$(basename "$d")-$i.${u##*.}" "$u"; done
  done
fi
mkdir -p ~/.fonts && cp -r fonts/* ~/.fonts/ 2>/dev/null && (fc-cache -f >/dev/null 2>&1 || true)

# 7) Render engines: Remotion template + HyperFrames CLI
if [ ! -d projects/remotion-launch/node_modules ]; then
  [ -f projects/remotion-launch/package.json ] || (cd projects && npx --yes create-video@latest --yes --blank remotion-launch >/dev/null)
  (cd projects/remotion-launch && npm install --silent && V=$(node -p "require('remotion/package.json').version") && \
   npm install --silent zod @remotion/transitions@$V @remotion/google-fonts@$V @remotion/three@$V @remotion/lottie@$V @remotion/motion-blur@$V @remotion/noise@$V @remotion/paths@$V @remotion/shapes@$V @remotion/layout-utils@$V @remotion/media-utils@$V @remotion/media@$V @remotion/captions@$V @remotion/light-leaks@$V three @react-three/fiber @react-three/drei gsap)
  grep -q TitleCard projects/remotion-launch/src/Composition.tsx 2>/dev/null || cp "$SK/templates/remotion-Composition.tsx" projects/remotion-launch/src/Composition.tsx
fi
command -v hyperframes >/dev/null || npm install -g hyperframes >/dev/null 2>&1 || echo "warn: hyperframes not installed"
hyperframes telemetry disable >/dev/null 2>&1 || true
[ -d repos/remotion-dev_skills ] || git clone -q --depth 1 https://github.com/remotion-dev/skills repos/remotion-dev_skills || true
# Official Remotion skills (fetched, not redistributed)
for s in repos/remotion-dev_skills/skills/*/; do [ -d "$s" ] && [ ! -e ".claude/skills/$(basename $s)" ] && mkdir -p .claude/skills && cp -r "$s" ".claude/skills/$(basename $s)"; done
[ -d repos/heygen-com_hyperframes ] || git clone -q --depth 1 https://github.com/heygen-com/hyperframes repos/heygen-com_hyperframes || true

echo "$ST" > "$SK/../STUDIO_ROOT" 2>/dev/null || true
echo "== studio ready: $ST"
