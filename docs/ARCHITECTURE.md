# Architecture and artifact format

## Boundaries

```text
CLI / custom Python caller
  ├─ SM64Env → private Pipe → fresh engine process → Native → C policy bridge
  └─ suite scheduler → episode process → SM64Env → fresh engine process

recorded artifacts → loopback HTTP server → static rollout dashboard
```

The extra episode process in a benchmark isolates arbitrary policy code and its failures. The native process isolates the port's global C/Lua state and makes reset reliable. A bounded thread pool schedules subprocesses; it does not run native engines in threads. Every episode gets its own save/mod directory and UDP port. Workers have process groups so suite timeouts/cancellation can stop the entire episode tree. Normal close uses a Pipe command; stuck native processes are killed after a bounded join.

## Python modules

| Module | Responsibility |
| --- | --- |
| `api.py`, `state.py` | Immutable action/observation records, oracle schema, and policy protocol |
| `environment.py` | Public API, reset/process lifetime, replay checkpoints |
| `native_abi.py`, `native_state.py`, `native.py` | ctypes layouts, ABI validation, oracle translation, native calls, pixel copying |
| `config.py`, `paths.py` | Validated serializable config and checkout location |
| `policies.py` | Baselines and `module:Class` loading |
| `control.py`, `first_star.py`, `tasks.py` | Feedback skills, BOB star task, independent saved-star-bit success evaluation |
| `episode.py` | Policy/engine loop and instrumentation |
| `suite.py` | Bounded scheduling, failure isolation, manifests and reports |
| `metrics.py` | Coverage, progress, health, distance and death measurements |
| `storage.py`, `recording.py` | Atomic metadata, buffered JSONL traces, PNG frames |
| `diagnostics.py` | Prerequisite checks and source/binary provenance |
| `dashboard/server.py` | Read-only artifact API, loopback binding, constrained paths |
| `dashboard/static/` | Plain HTML/CSS/JavaScript viewer; no build tool or CDN |

The maintained package is editable-installable from `src/`. Runtime assets remain in the checkout. `SM64_PROJECT_ROOT` can point to a checkout when discovery is unavailable; a wheel alone is not a self-contained game distribution.

## Native boundary

`engine/src/pc/policy_bridge.{h,c}` exports ABI version 3: configuration, progress reads, optional-capture stepping, rendering, image release, and spawn positioning. `pc_main.c` retains the upstream update loop and legacy ABI. Python verifies ABI and `MAX_PLAYERS=1` before startup. ABI 1/2 can be used with `observation_mode="basic"`; fast stepping and custom spawn require ABI 2. ABI 3 adds `policy_state.{h,c}` for bounded, read-only oracle observations and a small allocation hook in `spawn_object.c` for lifetime IDs. The reader checks all C/ctypes record sizes. See [STATE.md](STATE.md).

State-only stepping retains CPU scene traversal and animation updates but skips GPU submission, readback, and image allocation. Those CPU callbacks influence gameplay. `render()` submits the prepared display list; it must not traverse/update the scene again. See `docs/PERFORMANCE.md` before optimizing further.

The existing Lua mod is copied into each save tree because the engine discovers mods there. Its entry-level setting is changed in that isolated copy for `reset(level)`. The original mod files remain the source of truth. The intro skip is gated by policy configuration. See `engine/UPSTREAM.md` for upstream and patch history.

## Artifacts (schema version 3)

```text
artifacts/my-run/
  manifest.json           # Configuration, scope, source/build fingerprints
  summary.json            # Overall status, wall-clock throughput, session metrics
  report.md               # Human-readable table
  session-000/
    config.json
    result.json           # Success metrics or failure/timeout details
    worker.log            # Native stdout/stderr and Python errors
    trace.jsonl           # {step, frame, action, observation} per decision
    rollout.json          # Initial observation, image index, recording metadata
    frames/00000000.png   # Physics frame number, top-down RGB PNG
    frames/00000004.png
    runtime/episode-*/    # Separate native save/mod tree per reset
```

Schema 3 adds rich oracle observations and observation-mode provenance. Basic traces retain the prior flat observation keys; the dashboard still reads older artifacts. Traces are buffered during the loop. Metadata/results use atomic replacement. The trace hash covers serialized trace records, not native hidden memory. `game_beaten` is null because no completion detector exists. Coverage bins are 400-unit XZ cells keyed by level/area; path distance excludes death and level/area transitions. These are exploration diagnostics, not task reward or progress proofs.

`--record-every N` captures every N decisions plus initial/final frames. The trace observation is sampled after its recorded action; ABI 3 images use the current interpolation endpoint. Historical ABI 1/2 images need alignment review before use as perception labels. With `N=0`, the dashboard explicitly labels endpoint snapshots and plays the state trajectory. Image recording adds GPU, IPC, compression, and disk cost. A captured image shows the most recent image at or before the selected trace frame; sparse captures are not interpolated.

## Dashboard

Task policies can declare a `StarGoal` and a maximum action duration. The episode
loop validates them, checks the goal independently, and records 60 celebration
frames before stopping on success. Results distinguish actual `steps` from
`step_budget`; `task.success` distinguishes gameplay success from `status=ok`.
`rollout.json` adds task evidence and frame-indexed skill/collection events.
Optional trace `policy` diagnostics describe the input decision; observations
remain post-action. See [FIRST_STAR.md](FIRST_STAR.md) for the implemented task.

`make dashboard` serves `http://127.0.0.1:8765`. The server provides `/api/runs`, `/api/sessions?run=...`, `/api/rollout?run=...&session=...`, and indexed PNG routes. It has no execution, upload, deletion, or external publishing endpoint. Paths are constrained to the artifact root; arbitrary native files and ROMs are not served. It rejects foreign Host headers and supplies a self-only content policy.

The frontend selects runs/sessions, renders a trajectory and height chart, displays recorded game frames and controller/state telemetry, and supports play/pause, speed selection, timeline scrubbing, and arrow-key decision stepping. Hash links preserve run/session selection. Refresh discovers newly finished runs. Older trace-only artifacts remain viewable; synthetic and invalid-startup runs carry explicit labels.

The [3D debugger](STATE_DEBUGGER.md) adds bounded `/api/states` observation pages, a byte-offset trace index, locally vendored Three.js, and a context-local decision recorder. Full oracle data stays on disk; the browser fetches small windows. `policy.decision` is an additive diagnostic record, not a change to oracle ABI or action semantics.

## Throughput and compact evaluation traces

`SM64VectorEnv` sends a batch through independent environment Pipes before
collecting replies, allowing native simulation to overlap across processes.
Initialization is also dispatched as a batch. The learner remains in its own
process. There are no shared native globals, Python engine threads, automatic
resets, or weakened failure isolation. Immutable state records use positional
pickle construction to avoid the generic dataclass field-restoration loop.

Benchmark episodes disable unused in-memory replay-checkpoint history. Full
JSONL traces remain the default. `--trace-mode compact` retains each action,
`n_frames`, frame number, flat outcome telemetry, and `observation_sha256` for the
**entire** oracle observation. It omits rich observation dumps and policy decision
diagnostics. `rollout.json` retains the full initial observation and records
`trace_mode`, `initial_observation_sha256`, and `observation_hash_algorithm`.
The schema-3 extension is additive; the dashboard can show compact trajectories
and any captured images, while subsequent oracle geometry and decision details
are unavailable. Policy observation mode and stored trace detail are distinct.

Hash algorithm `sm64-observation-positional-json-v1` is SHA-256 over compact JSON
arrays in the declared dataclass field order, recursively, including all optional
records, frame timing, and UI state. It avoids constructing dictionaries and
repeating field names for each state. A change to that field schema must version
the algorithm. This hash verifies the observed state, not unobserved native memory.
Compact traces support validating action replay, but are not native snapshots or
a substitute for retaining matching engine/mod settings and binaries. No automatic
trace-to-video command is included.

`compare_rollouts.py` compares full traces directly or checks full/compact state
hashes and controller timing. It validates actual completed step counts, including
early task success, and ignores non-semantic policy diagnostics. Compact mode does
not change the policy, action cadence, physics, oracle sensing, or image cadence.

Opt-in native seed scheme 1 is initialized once before engine startup in each
fresh owned process. Unseeded calls preserve legacy RNG initialization. Compact
native episodes additionally export an action replay bundle; replay executes
through `SM64Env` and validates the complete observed history. Seed diversity is
RNG diversity at the normal start, not arbitrary engine-state randomization.
