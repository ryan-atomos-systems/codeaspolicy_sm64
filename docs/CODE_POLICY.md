# Working on a code policy

The maintained scaffold is now `src/sm64_policy/`. Start with [README](../README.md), [API semantics](API.md), and [architecture](ARCHITECTURE.md). Original RL scripts and wrappers live under `legacy/` for reference.

## Working star policy

`make first-star` runs the state-feedback Chain Chomp policy and records a full
30 fps rollout. Read [FIRST_STAR.md](FIRST_STAR.md) for the technique, validation,
task predicates, reusable control skills, and extension path. This goal requires
oracle observations and `--frame-skip 1`; the exploration baselines use larger
batches for exploration throughput.

## Write and evaluate a policy

A policy is ordinary Python, instantiated once per episode with its own RNG:

```python
# my_policy.py (on the Python import path)
import random
from sm64_policy import Action, Observation


class MyPolicy:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def act(self, observation: Observation, step: int) -> Action:
        return Action(stick_y=64, a=step % 30 < 3)
```

```sh
PYTHONPATH=src:. python3 -m sm64_policy benchmark \
  --policies my_policy:MyPolicy --seeds 0 1 2 3 --workers 4 \
  --steps 1800 --output artifacts/my-policy-v1
```

Built-in `noop`, `random`, and `explore` provide baseline policies. They are deliberately simple and do not plan star routes. `explore` has a stall-recovery heuristic and jump release; random sometimes covers more ground. Do not mistake coverage for star progress.

Use state feedback for named skills such as steering, jumping, recovering from stalls, and navigating a waypoint. Keep policy state explicit so checkpoints can be paired with the policy's RNG and internal memory. The environment's checkpoint does not save your Python objects.

For standalone experiments, use `SM64Env.reset/step/get_state/save_state/load_state/render`. Run the guarded example with `PYTHONPATH=src python3 examples/environment.py`. Avoid importing the archived Gym wrappers or loading native ctypes directly.

## Inspect failures

1. Read the session's `result.json` and `worker.log`.
2. Open the run in `make dashboard`. Existing state-only traces show trajectories; record a new run with `--record-every 1` for game-frame playback.
3. Inspect action, health, coordinates, level/area, and Mario action around the failure. A stationary trace can be a bad startup, held input, a wall, or a policy bug.
4. Compare native trajectories after engine changes with `scripts/compare_rollouts.py` before claiming a speed improvement. See [performance protocol](PERFORMANCE.md).

Synthetic mode (`--backend synthetic`) is a deterministic kinematic fixture for orchestration tests. It cannot validate gameplay, collision, stars, camera behavior, or native throughput.

## Known upstream findings

- The game is a native SM64 port with a shared-library entry point, not an emulator.
- `MAX_PLAYERS` is compiled into global arrays. Independent sessions require fresh processes, not repeated library instances or the original multiprocessing wrappers.
- The upstream wrapper's `main_func` declaration omitted the fullscreen argument and had a reversed pixel dimension layout. The new adapter has the correct ABI.
- Inputs previously latched buttons with bitwise OR, and rejected a stick if either axis was zero. The bridge assigns every input each step and accepts single-axis movement.
- The Compass mod forces BOB entry, suppresses dialogue, and auto-respawns. Intro skipping is enabled in policy mode; historical intro-stuck runs are marked invalid.
- Controls in this fork are Mario-relative. The old top-down render option changes conventions; it is not exposed in the current API.
- Scene traversal has side effects. Removing it to optimize state-only execution changed trajectories; the final fast path preserves it and skips only unnecessary GPU/image work.
- The library has no complete serialization boundary. Replay checkpoints are the current implementation of save/load; true constant-time native snapshots remain future work.

The scaffold makes experiments observable and repeatable enough to compare locally. Completing SM64 still requires task definitions, progression support, policies for stars/Bowser, and a completion detector.
