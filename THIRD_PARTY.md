# Third-party material

The vendored skills in `.claude/skills/` come from the repos below. Each keeps its upstream licence, and a LICENSE file sits in the skill folder where the upstream repo has one. The `om-*` skills are AGPL-3.0, so keep their LICENSE files and source. The Remotion skills are **not** included: setup downloads them from remotion-dev/skills. Remotion itself needs a paid company licence for companies of 4+ people.

| Prefix / skill | Source | License |
|---|---|---|
| `remotion-*` (downloaded at setup, not in this repo) | github.com/remotion-dev/skills | none stated; Remotion License applies |
| `hf-*` | github.com/heygen-com/hyperframes | Apache-2.0 |
| `ds-*` | github.com/digitalsamba/claude-code-video-toolkit | MIT |
| `om-*` | github.com/calesthio/OpenMontage | AGPL-3.0 |
| `cv-*` | github.com/agricidaniel/claude-video | MIT |
| `ecc-video-editing` | github.com/affaan-m/everything-claude-code | MIT |
| `mc-video-editing` | github.com/6missedcalls/video-editing-skill | MIT |
| `projects/hf-launch/vendor/gsap.min.js` | GSAP (npm `gsap`) | GSAP Standard License |
| `fonts/` | Google Fonts | SIL OFL 1.1 / Apache-2.0 |
| `models/` (not in git; downloaded by setup.sh) | Depth-Anything-V2 via fabio-sim/Depth-Anything-ONNX | Small model Apache-2.0; Base model CC-BY-NC-4.0 (non-commercial) |

Original to this repo: `tools/`, `luts/` (generated), `sfx/` (synthesised), `createvid` skill, templates.
