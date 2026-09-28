# Environment API

Import `SM64Env`, `Action`, `Observation`, `Level`, `SpawnState`, `RGBFrame`, and `CheckpointMismatch` from `sm64_policy`. The executable example is `examples/environment.py`.

## Lifecycle

```python
with SM64Env(width=320, height=180, timeout=30) as env:
    observation = env.reset(Level.BOB)
```

Use a normal Python script with an `if __name__ == "__main__":` entry guard. The engine uses multiprocessing **spawn**; an unguarded script, stdin snippet, or notebook function is not a supported launch pattern.

Policy workers are silent: SDL uses its dummy audio driver and BASS uses its no-sound device, including character voices. This requires the current native build.

Construction does not start the engine. Each `reset()` stops the previous worker and starts a fresh native process with a fresh save directory. Multiple environments can coexist because their native state is isolated. Always close the environment, preferably with a context manager. `close()` is idempotent. A closed environment cannot reset.

Constructor options:

| Argument | Default | Meaning |
| --- | --- | --- |
| `library` | `engine/build/us_pc/sm64` | Compiled library path |
| `width`, `height` | `128`, `72` | RGB image size, each 1–1024 |
| `engine_mode` | `"fast"` | Skip unnecessary GPU work; `"reference"` renders every step |
| `observation_mode` | `"oracle"` | Rich oracle state (ABI 3); `"basic"` keeps compact telemetry |
| `timeout` | `30` | Maximum seconds to wait for an engine response |
| `workspace` | temporary directory | Parent of fresh episode/save directories; explicit directories persist for inspection |

## `reset(level=Level.BOB, spawn_state=None) -> Observation`

Accepts a `Level` enum or its numeric engine ID. It runs the normal startup warmup (120 physics frames), verifies the selected level and that the castle intro has ended, then applies an optional spawn:

```python
from sm64_policy import Level, SpawnState

state = env.reset(Level.BOB, SpawnState(position=(-6558, 200, 6464), yaw=16384))
```

`SpawnState` sets `(x, y, z)`, zeroes velocity, and sets signed 16-bit yaw and idle action. Coordinates are engine units, with Y up. It does not restore health, objects, camera, RNG, act, or area. Choose a valid location in the selected level. BOB and WF resets are integration-tested; all enumerated levels have not been validated.

The bundled Lua mod suppresses dialogue and auto-respawns. Native benchmark runs start in BOB and skip the intro; this is not an unmodified full-game progression environment.

## `step(action, n_frames=4) -> Observation`

Hold an `Action` for 1–120 integer physics frames. SM64 game time is 30 physics frames per second. The call runs as fast as possible, without wall-clock pacing.

```python
state = env.step(Action(stick_x=20, stick_y=64, a=True), n_frames=4)
```

- Stick axes are integers in `[-80, 80]`; buttons `a`, `b`, `z`, and `start` are booleans. Older native builds without Start support reject `start=True` explicitly.
- An omitted axis/button is neutral/released. Holding A across calls keeps it pressed; release it before the next jump.
- This fork interprets stick direction relative to Mario's facing. Do not assume stock camera-relative semantics.
- The return is a state observation, not a Gym `(state, reward, terminated, truncated, info)` tuple. Objectives, rewards, and episode stopping conditions belong in the policy/evaluation layer.
- The mod auto-respawns; death does not close an episode. Observations are sampled at decision boundaries, so transient events inside a frame batch may not appear in telemetry.

## `get_state() -> Observation`

Returns the latest immutable observation without advancing the engine or making an IPC round trip. Call `reset()` first. The flat summary includes position, velocity, health (0–8), died, height above ground, stars, coins, level, area, act, and numeric Mario action. Default oracle mode also returns `mario`, `camera`, `geometry`, `objects`, `progress`, `frame`, `last_action_frames`, and `engine_frame`. These are structured policy observations, not all hidden engine state. See [the state contract and perception roadmap](STATE.md) for field semantics, limits, and examples.

The policy protocol is `act(observation: Observation, step: int) -> Action`, where `step` is the zero-based decision index. The CLI instantiates each policy as `PolicyClass(seed=seed)` in a fresh episode process.

## `render() -> RGBFrame`

Returns top-down, row-major RGB bytes with `width`, `height`, and the associated post-action `frame` number. ABI 3 policy rendering selects the current interpolation endpoint. It renders the current display list and does not advance physics. Repeated rendering may cost GPU work; state-only `step()` avoids it.

```python
image = env.render()
image.save("frame.png")  # Standard-library PNG encoder
assert len(image.rgb) == image.width * image.height * 3
```

The process still requires SDL/OpenGL even when its window is hidden. There is no software-only headless backend yet.

## `save_state(path=None) -> dict` / `load_state(checkpoint) -> Observation`

```python
checkpoint = env.save_state()             # Independent JSON-compatible dictionary
checkpoint = env.save_state("state.json") # Also writes atomically to disk
restored = env.load_state(checkpoint)      # Dictionary or JSON file path
```

These are **verified replay checkpoints**, not native memory snapshots. A checkpoint records level, spawn, renderer settings, native build/mod fingerprints, controller actions/frame batches, and a hash of the entire observed state history. Loading creates a fresh episode, replays all actions, and checks the observed history. Build/settings mismatches are rejected before reset; replay divergence discards the candidate environment and raises `CheckpointMismatch`. After divergence, call `reset()` to recover.

Restoration costs O(number of past decisions); there is no constant-time branching yet. Checkpoints do not include Python policy state/RNG, camera/object memory, or proof of hidden native equivalence. Matching observations are useful validation, not a general deterministic-engine guarantee. Restore policy state separately when continuing an adaptive policy. These checkpoints are intended for local experiments using the same build and settings.

## Errors and recovery

Invalid actions, frame counts, and level IDs fail before stepping. A crashed or unresponsive native worker raises `RuntimeError` or `TimeoutError` and is stopped. The caller can `reset()` to create a clean replacement. Each CLI episode also has a suite-level timeout; failed sessions keep logs and error results rather than silently counting as success.

## Progression episodes

Use `SM64Env(gameplay_mode="progression")` and `reset(Level.CASTLE_GROUNDS)` for
a fresh-save campaign. The default `scaffold` mode keeps the previous benchmark
behavior. Progression restores normal act selection, dialogue/NPC interaction,
camera/HUD, deaths and course exits. It advances local object/course clocks by
physics frames instead of wall-clock time. The intro cinematic is still skipped.
See [campaign fidelity and controls](FIRST_BOWSER.md).

`get_state().ui` exposes dialogue ID/state/response, menu mode, warp transition,
play mode and selected act in progression mode. This record describes the current
interface, not an instruction to advance it. `-1` denotes no dialogue/menu.
Checkpoints include gameplay mode and reject loading into a different mode.
The CLI exposes the same configuration as `--gameplay-mode` and `--level`.

## Parallel RL collection

`SM64VectorEnv` owns independent `SM64Env` lanes and dispatches every action
before waiting for any result. It requires the same guarded script entry point:

```python
from sm64_policy import Action, SM64VectorEnv


def main():
    with SM64VectorEnv(4, gameplay_mode="progression") as envs:
        states = envs.reset(levels=16)
        for _ in range(1000):
            actions = [Action(stick_y=64) for state in states]
            states = envs.step(actions, n_frames=1)
        states_for_one_lane = envs.reset_at(0, level=16)


if __name__ == "__main__":
    main()
```

The result is a tuple of immutable observations in lane order. `levels` can be
one level or a sequence of levels; `spawn_states` is an optional sequence.
`n_frames` can be one duration or a duration per lane. All batch inputs are
validated before sending actions. Each reset creates a fresh native process and
save; there is no automatic reset, reward, done flag, tensor conversion, Gym
adapter, or RL algorithm. The learner defines rewards and stopping rules using
the observations, preserves terminal observations, then calls `reset_at()` for
finished lanes. `envs.envs[i].render()` can capture a selected lane between steps.

For overlap with learner work, use `step_async(actions, n_frames)` followed by
`step_wait()`, or `reset_async()` followed by `reset_wait()`. Only one operation
may be pending. These methods also exist on `SM64Env`. `get_state()` during a
pending step returns the **previous** observation; rendering/checkpoint operations
must wait. Timeouts are measured from dispatch. If a vector operation fails, all
lanes are stopped so an incomplete batch cannot be mistaken for a valid result;
call `reset()` to recover. Context-manager exit stops pending workers as well.

Vector environments default to `checkpoint_history=False`: they do not retain an
unbounded action history or serialize every observation for checkpoint hashing.
The same option is available on `SM64Env`; its default remains `True` for backward
compatibility. `save_state()` and `load_state()` explicitly reject disabled
history. Choose `checkpoint_history=True` at construction when replay checkpoints
are needed. This does not change observations or engine simulation.

Direct environment/vector calls write no rollout traces or images unless asked.
For policy evaluation with small, verifiable artifacts, add `--trace-mode compact`
to `benchmark`. Policies still receive the complete selected observation mode.

## Seeded campaigns and action-only replay

`SM64Env(game_seed=123)` opts into native seed scheme 1. `None` preserves the
legacy initialization. A uint32 seed controls the global SM64 RNG, initial
per-object and position-derived RNG streams, libc and Lua initialization.
`benchmark --seeds 1 2 --game-seeds 101 102` pairs Python and game seeds by index.
The runner seeds Python's module RNG before constructing the policy and also
passes the Python seed to its constructor. Custom external RNGs need their own
seeding. A game seed changes randomness, not spawn position, save progress, act,
or area. Initial visible observations can match while later outcomes differ.

Native compact episodes write `replay.json`: seeds, exact controller actions and
frame durations, settings, engine/mod fingerprints, and initial/history hashes.
No policy code is executed during replay. Python seeds are provenance; recorded
actions already incorporate policy randomness. Preserve the matching engine,
its adjacent runtime libraries, and gameplay mod. This is an action replay, not
a native snapshot or a cross-build/platform determinism promise. Replay rejects
fingerprint mismatches and observed drift. Rendering is optional:

```sh
PYTHONPATH=src python3 -m sm64_policy replay artifacts/RUN/session-000/replay.json \
  --output artifacts/REPLAY --record-every 30
```

The output contains PNGs and `replay-result.json`; images are verified only when
the entire observation history matches. `--record-every 1` extracts every decision
frame (every physics frame for one-frame actions); omit it to verify without
images. Original runs retain compact telemetry for inspection, but only the
replay bundle and matching runtime are needed to reconstruct observations/images.
