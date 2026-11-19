#!/usr/bin/env bash
# Build the heavy studio toolchain (not stored in git). Idempotent; safe to re-run. ~10 min first time.
# Linux (Debian/Ubuntu) with apt. On macOS: brew install ffmpeg imagemagick sox blender, then run the rest.
set -e
cd "$(dirname "$0")"
SUDO=""; [ "$(id -u)" != 0 ] && command -v sudo >/dev/null && SUDO=sudo
need=""; for b in ffmpeg convert sox blender xvfb-run; do command -v $b >/dev/null || need=1; done
if [ -n "$need" ] && command -v apt-get >/dev/null; then
  export DEBIAN_FRONTEND=noninteractive
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq ffmpeg imagemagick blender sox libsox-fmt-all fonts-noto-core fonts-inter fonts-liberation xvfb libegl1 libgl1-mesa-dri libosmesa6 >/dev/null
fi
# Python toolchain
[ -x venv/bin/python ] || python3 -m venv venv
if ! venv/bin/python -c "import librosa, rembg, onnxruntime, depthflow, moviepy, cv2" 2>/dev/null; then
  venv/bin/pip install -q --upgrade pip
  venv/bin/pip install -q moviepy librosa opencv-python-headless scenedetect pillow numpy scipy soundfile "rembg[cpu]" onnxruntime depthflow pedalboard pydub
fi
# Depth models (GitHub releases; Hugging Face not required)
mkdir -p models
for m in depth_anything_v2_vits depth_anything_v2_vitb; do
  [ -s models/$m.onnx ] || curl -sfL -o models/$m.onnx https://github.com/fabio-sim/Depth-Anything-ONNX/releases/download/v2.0.0/$m.onnx
done
# Cutout models (cached in ~/.u2net)
venv/bin/python -I -c "from rembg import new_session; new_session('u2net_human_seg'); new_session('isnet-general-use')" >/dev/null
# Reference repos (HyperFrames registry blocks, toolkits) for browsing/copying blocks
mkdir -p repos
for r in heygen-com/hyperframes remotion-dev/skills calesthio/OpenMontage digitalsamba/claude-code-video-toolkit agricidaniel/claude-video BrokenSource/DepthFlow; do
  d=repos/$(echo $r | tr / _); [ -d "$d" ] || git clone -q --depth 1 https://github.com/$r "$d" || echo "warn: could not clone $r"
done
# Official Remotion skills (fetched, not redistributed)
for s in repos/remotion-dev_skills/skills/*/; do [ -d "$s" ] && [ ! -e ".claude/skills/$(basename $s)" ] && mkdir -p .claude/skills && cp -r "$s" ".claude/skills/$(basename $s)"; done
# Node render engines
command -v hyperframes >/dev/null || npm install -g hyperframes >/dev/null 2>&1 || echo "warn: hyperframes CLI not installed"
hyperframes telemetry disable >/dev/null 2>&1 || true
[ -d projects/remotion-launch/node_modules ] || (cd projects/remotion-launch && npm install --silent)
# Fonts + LUTs
mkdir -p ~/.fonts && cp -r fonts/* ~/.fonts/ && (fc-cache -f >/dev/null 2>&1 || true)
[ -f luts/print_film.cube ] || venv/bin/python -I tools/gen_luts.py luts
echo "studio ready at $(pwd)"
