# SM64 Policy Lab

A code-as-policy workspace for Super Mario 64: isolated native environments, parallel benchmarks, and a local rollout dashboard. Python policies consume game state and return controller actions. The Python runtime uses only the standard library. The build-free dashboard bundles Three.js locally for 3D debugging.

This is a modified native PC port from [Gumbo64/sm64-AI](https://github.com/Gumbo64/sm64-AI), not an N64 emulator. The `first-star` feedback policy collects **Behind Chain Chomp's Gate**. The [`first-bowser` campaign](docs/FIRST_BOWSER.md) combines eight star skills, castle navigation, the Bowser course, and the key battle. A [16-star development trajectory](docs/SIXTEEN_STAR_DEVELOPMENT.md) now reaches the final Bowser, Grand Star, and ending, with a verified fresh-save controller replay. It includes development interventions and is not an autonomous full-game policy evaluation. The random/exploration baselines do not collect stars.

## Quick start

Python 3.11+ is required. The native build has been verified on Apple Silicon macOS with Xcode command-line tools and Homebrew:

```sh
brew install make sdl2 glew pkgconf x86_64-elf-binutils
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Place your US ROM at `engine/baserom.us.z64`, then:

```sh
make build                     # Validates ROM; builds MAX_PLAYERS=1
make doctor
make test                      # No ROM needed for harness tests
SM64_NATIVE_TESTS=1 make test   # Also exercises the real engine/API
make demo                      # Four recorded native rollouts
make first-star                # Collect a real star; record 30 fps playback
make first-bowser              # Fresh-save eight-star campaign and first Bowser key
make dashboard                 # http://127.0.0.1:8765
```

The build helper downloads checksum-verified Lua 5.3.6 sources into ignored `artifacts/deps/`. The ROM, extracted game assets, builds, saves, and run artifacts stay local. Hidden rendering still needs a working OpenGL display context. Other platforms are not yet validated by this scaffold.

`make` sets `PYTHONPATH=src`, so its commands also work without an editable install. Direct `python -m sm64_policy` commands require that install or `PYTHONPATH=src`.

## Environment API

```python
from sm64_policy import Action, Level, SM64Env


def main():
    with SM64Env(width=320, height=180) as env:
        state = env.reset(Level.BOB)
        state = env.step(Action(stick_y=64, a=True), n_frames=4)
        state = env.get_state()
        checkpoint = env.save_state()
        env.step(Action(stick_x=40), n_frames=20)
        state = env.load_state(checkpoint)
        env.render().save("frame.png")


if __name__ == "__main__":
    main()
```

Each `reset()` creates a fresh engine process and save directory. `render()` does not advance physics. `save_state()`/`load_state()` use **verified action replay**, not native memory snapshots; restoration is linear in history length and rejects observed replay drift. See [API contract](docs/API.md) and the runnable [example](examples/environment.py).

`get_state()` now includes structured Mario/contact, camera, local collision geometry, nearby object, and saved-progress records by default. Read the [oracle state contract and perception roadmap](docs/STATE.md). Use `SM64Env(observation_mode="basic")` for the old lightweight telemetry. `examples/inspect_state.py` writes a real state JSON and frame.

## Benchmarks and playback

```sh
sm64-policy benchmark --workers 4 --output artifacts/my-benchmark
sm64-policy benchmark --policies random explore --seeds 0 1 --steps 600 \
  --workers 4 --record-every 1 --width 320 --height 180 --output artifacts/my-playback
sm64-policy dashboard
```

Output directories must be new. Every session produces a controller/state trace, metrics, and initial/final images. `--record-every 1` records each decision for visual playback; the default records endpoints only for faster benchmarks. The dashboard supports session selection, scrubbing, play/pause, speed controls, keyboard stepping, trajectories, and controller/state inspection.

The [3D state and decision debugger](docs/STATE_DEBUGGER.md) shows the game beside an interactive oracle scene, with object inspection, contact/ray geometry, policy targets, and a causal input → action → outcome inspector.

The [first-Bowser publication drafts](docs/publication/README.md) include a technical paper, blog post, tweet thread, and an evidence guide covering GPT-6 Astra's development role and the code-as-policy result. The [project website](website/README.md) exports to GitHub Pages with the full recording and an interactive 3D decision example.

For a custom policy, implement `MyPolicy(seed=...)` with `act(observation, step) -> Action`, then pass `--policies my_module:MyPolicy`. See [policy guide](docs/CODE_POLICY.md).

Read [the first-star controller, evidence, and extension guide](docs/FIRST_STAR.md).
It uses hierarchical code-as-policy and model-based movement feedback, with an
independent saved-star-bit success check. The dashboard shows skill milestones
and lets you jump directly to star collection.

## Repository map

| Path | Purpose |
| --- | --- |
| `src/sm64_policy/` | Public API, policies, workers, metrics, recording, dashboard |
| `engine/` | Native port, gameplay mod, and small C policy bridge |
| `scripts/` | Reproducible native build and trace comparison |
| `tests/` | Harness tests and opt-in native integration tests |
| `examples/` | Executable public API usage |
| `docs/` | Architecture, API semantics, performance evidence, policy workflow |
| `legacy/` | Original RL experiments, wrappers, models, and media; reference only |
| `artifacts/` | Ignored run data, recordings, logs, and local dependencies |

Start future changes with [AGENTS.md](AGENTS.md), [architecture](docs/ARCHITECTURE.md), and [performance notes](docs/PERFORMANCE.md). The [initial benchmark](docs/INITIAL_BENCHMARK.md) records the pre-refactor exploration baseline.

For Python linting/formatting, install the optional development tools with `python -m pip install -e '.[dev]'`, then run `make lint` in the activated virtual environment. These tools are not runtime dependencies.

## Faster collection for RL

Use `SM64VectorEnv(4)` to step independent native environments as a batch. It
returns the existing full observations, with no automatic recording or checkpoint
history. The learner owns rewards, tensor conversion, and explicit episode resets.
See [parallel API and failure semantics](docs/API.md#parallel-rl-collection).

For parallel policy evaluation, keep full policy observations but write small
traces with actions and full-state verification hashes:

```sh
PYTHONPATH=src python3 -m sm64_policy benchmark \
  --policies first-bowser --gameplay-mode progression --level 16 \
  --seeds 0 1 2 3 --workers 4 --steps 36000 --frame-skip 1 \
  --record-every 0 --trace-mode compact --width 480 --height 270 --timeout 1800 \
  --output artifacts/campaign-compact-new
```

`--trace-mode full` remains the default for complete oracle/debugger recordings.
See [measured throughput and benchmark scopes](docs/PERFORMANCE.md).

For normal-start RNG diversity and success/timing statistics, run
`PYTHONPATH=src python3 scripts/evaluate_campaign.py --runs 64 --workers 4 --output artifacts/NEW-RUN`.
Native compact runs save action replay bundles with game/Python seeds and drift
checks; see [seeded replay](docs/API.md#seeded-campaigns-and-action-only-replay).
