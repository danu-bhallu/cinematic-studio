# Cinematic Studio: rules for Claude

This repo is a cinematic video studio: music launch teasers, reels, lyric videos and visualizers.

**For ANY video request, use the `/createvid` skill** (`.claude/skills/createvid/SKILL.md`). It is the director's brief and routes to every tool and specialist skill here.

Non-negotiables:
1. **Plan first.** Write `projects/<name>/PLAN.md` (Shot Plan template in `.claude/skills/createvid/reference/PLAYBOOK.md` §9). Name every tool, skill and repo used, and say why. Get an OK before rendering, unless told to just go.
2. **An MP3/WAV from the user is the soundtrack.** Run `tools/beats.py` on it first, and take every cut time from `beats.json`.
3. Grade once at the end. QC at full resolution before delivering.

First time in a fresh machine or container: run `bash setup.sh`. It rebuilds the venv, models, repos and node_modules, none of which are stored in git.
