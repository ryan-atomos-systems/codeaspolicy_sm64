# 5090 handoff

Source: https://github.com/ryan-atomos-systems/codeaspolicy_sm64
Upstream: https://github.com/Gumbo64/sm64-AI

The Linux checkout is `/home/ryan/code/codex/sm64_ai` on SSH host
`rboesch-5090`. Read `AGENTS.md` and `docs/SIXTEEN_STAR_DEVELOPMENT.md` first.
The completed sixteen-star result is a verified development trajectory, not yet
a frozen autonomous campaign. The approach is hierarchical code as policy using
oracle feedback; there is no RL training or neural inference in this controller.

## Build on Ubuntu 24.04

Supply your own US ROM at `engine/baserom.us.z64`. It is intentionally excluded
from Git, along with extracted assets, builds, saves, and recordings.

```sh
sudo apt-get install build-essential pkg-config libsdl2-dev libglew-dev \
  libaudiofile-dev libreadline-dev zlib1g-dev python3-venv xvfb xauth mesa-utils
python3 -m venv .venv
.venv/bin/pip install -e .
python3 scripts/build_native.py --jobs 4
PYTHONPATH=src python3 -m unittest discover -s tests -v
xvfb-run -a env SM64_NATIVE_TESTS=1 PYTHONPATH=src \
  python3 -m unittest discover -s tests -v
```

Each engine requires a fresh process and save directory. Hidden rendering still
needs an OpenGL display; Xvfb provides one for SSH sessions. Xvfb may use software
Mesa. This does not imply the 5090 accelerates simulation: game logic and the
current controllers run on the CPU. Profile CPU stepping, state extraction,
rendering, recording, and worker contention separately before changing them.

## Data copied directly over SSH

- `engine/baserom.us.z64`: user-supplied ROM.
- `artifacts/sixteen-star-complete-01/`: self-contained verified Mac playback,
  result, complete action checkpoint, and sampled oracle observations.
- `artifacts/sixteen-dev/`: development checkpoints, probes, and historical data.

Mac binaries in development artifacts are reference files, not Linux libraries.
The new Linux library must be built locally. Action checkpoints fingerprint the
native build and gameplay mod and check observation history; the Mac checkpoint
is **not a portable Linux snapshot**. Preserve it unchanged. Establish and record
a new Linux baseline before claiming replay equivalence or optimization gains.
Do not disable fingerprint checks to declare a replay verified.

## Dashboard over SSH

On the 5090:

```sh
cd /home/ryan/code/codex/sm64_ai
PYTHONPATH=src python3 -m sm64_policy dashboard
```

On your workstation (local port 8766 avoids the existing Mac dashboard):

```sh
ssh -N -L 8766:127.0.0.1:8765 rboesch-5090
```

Open http://127.0.0.1:8766/#run=sixteen-star-complete-01&session=session-000 .
Playback needs neither a running engine nor Xvfb. Keep the server on loopback.

## Optimization starting point

Use `experiments/sixteen_star/README.md` to locate the tested route skills and
required starting states. Integrate the remaining manually directed transitions
before treating the full run as an autonomous policy. Keep the existing replay
as development evidence, separate from new policy evaluations.

Benchmark fresh output directories with identical policy, seeds, observation
mode, resolution, recording cadence, and workers. Run reference and candidate
suites sequentially. Check actions and observations with
`scripts/compare_rollouts.py`; faster execution alone does not establish preserved
behavior. Scene traversal and animation callbacks have gameplay side effects.
