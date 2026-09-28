# Native performance and validation

## Parallel rollout optimization (2026-09-28)

On the same development Mac, using the unchanged native binary and complete
oracle observations, one controller decision per physics frame:

| Workload | Before | After | Throughput change |
| --- | ---: | ---: | ---: |
| Four simultaneous eight-star + Bowser campaigns, endpoints only | 88.459 s / 1,203 aggregate frames/s | 37.410 s / 2,844 aggregate frames/s | **2.36×** |
| One eight-star + Bowser campaign, endpoints only | 67.205 s | 29.006–30.942 s (two runs) | **2.17–2.32×** |
| Four simultaneous first-star runs, full traces retained | 3.676 s / 901 aggregate frames/s | 2.588 s / 1,280 aggregate frames/s | **1.42×** |

Campaign comparisons use `--trace-mode full` before and `--trace-mode compact`
after; this deliberately reduces artifact detail while preserving full policy
observations and verification hashes. All other campaign settings match: 480×270,
fast engine, progression mode from castle grounds, seeds 0–3 for the four-worker
suite (seed 0 for the single), frame skip 1, image cadence 0 (two endpoints),
36,000-step ceiling. All campaigns stop at 26,600 frames after verified success.
The first-star comparison uses full traces on both sides, 128×72, scaffold, four
workers, seeds 0–3, frame skip 1, two endpoints, and a 2,400-step ceiling.

These wall times include startup, warmup, all trace writing, endpoint images,
and teardown. Four campaigns produced 4.22 GB of full JSONL before, versus
46.4 MB of compact JSONL after (**91× smaller**). These are small local samples,
not confidence intervals. Eight-star timings above include the Bowser course/key.

The four campaigns' initial observations and **all 106,400 actions and full-state
hashes match** their pre-change runs. All four earned eight unique star bits and
the first key at frame 26,540. The first-star comparison matched every initial
observation and all 3,312 actions/states, with four verified star successes.
Neither comparison establishes general native determinism.

Evidence (ignored local artifacts):

- `artifacts/rl-perf-before-source/`: preserved pre-change Python/docs/tests.
- `artifacts/rl-perf-before-campaign4/` and `rl-perf-after-campaign4-compact/`.
- `artifacts/first-bowser-no-record-20260928-01/`,
  `rl-perf-after-campaign1-compact/`, `rl-perf-after-campaign1-compact-repeat/`.
- `artifacts/rl-perf-before-star4/` and `rl-perf-after-star4-full/`.
- Native/unit validation logs: `artifacts/rl-native-tests-final.log`.

### Campaign scaling to 8 and 16 concurrent sessions

Follow-up measurements on the same Apple M3 MacBook Air (4 performance cores,
4 efficiency cores, 16 GB RAM), using the compact campaign settings above:

| Concurrent sessions | Total batch wall time | Aggregate physics frames/s | Campaigns/minute |
| ---: | ---: | ---: | ---: |
| 1 | 30.942 s | 860 | 1.94 |
| 4 | 37.410 s | 2,844 | 6.42 |
| 8 | 75.127 s | 2,833 | 6.39 |
| 16 | 168.532 s | 2,525 | 5.70 |

Each session simulates the same 26,600 frames and earns eight stars plus the key.
The 8- and 16-session suites ran sequentially, using seeds 0–7 and 0–15;
1/4 reuse the measurements above. This authored campaign does not use policy RNG.
All new sessions succeeded; their initial observations and entire compact trace
hashes match the four-session reference. Artifact files were independently
rehashed to verify the recorded trace digests. These are single batch samples,
not confidence intervals or a guarantee under different thermal/system load.

Four sessions remain the measured throughput choice for this workload/machine:
eight provide essentially unchanged throughput, and sixteen reduce it by about
11%. Extra workers largely time-share the available CPU capacity; increased
concurrency does not make an individual campaign faster. This is campaign
throughput, separate from the shorter RL batch API experiment below.

Evidence: `artifacts/rl-scaling-campaign8-20260928/`,
`artifacts/rl-scaling-campaign16-20260928/`, and the consolidated checks in
`artifacts/rl-campaign-scaling-20260928.json`.

### Where the improvement comes from

A parent-process cProfile sample attributed 1.925 of 3.464 instrumented seconds
to checkpoint-history hashing, principally conversion of rich records to JSON.
Generic frozen-dataclass unpickling cost another 0.441 seconds. These are profiling
measurements with profiler overhead, not unbiased benchmark timings.

- Benchmark episodes no longer build an unused in-memory replay checkpoint.
  Standalone `SM64Env` preserves checkpoint history by default; vector collectors
  disable it by default and reject checkpoint calls explicitly.
- State transport reconstructs immutable records through positional constructors,
  avoiding the generic dataclass field-restoration loop. Numeric tuples/matrices
  no longer get recursively copied for JSON serialization.
- Compact traces use positional JSON hashes covering the entire observation,
  plus small flat trajectory records. They skip detailed decision diagnostics.
- `SM64VectorEnv` dispatches resets/actions to every independent engine before
  waiting, permitting overlap without a thread pool or shared native instance.

No native game code, observation coverage, action frequency, physics ordering, or
rendering callbacks changed. Remaining costs include native simulation/oracle
queries, Python record construction, and process transport. Pixel-based RL still
pays for rendering; these measurements concern oracle state policies.

### RL batch stepping (different timing scope)

`python3 scripts/benchmark_vector.py --num-envs 4 --output artifacts/vector-new`
measures random-policy rollouts with no images, checkpoint history, metrics or
trace serialization in the timed loop. Observations are retained in bounded RAM
and compact validation artifacts are exported afterwards. It reports both rollout
rate and wall time including startup/export. It is not a training algorithm.

At 1,500 decisions per lane, frame skip 1, oracle mode, 128×72, scaffold BOB:

| Environments | Aggregate rollout frames/s | Rollout wall time | Wall time including startup/export |
| ---: | ---: | ---: | ---: |
| 1 | 1,415 | 1.060 s | 1.949 s |
| 4 | 2,685 | 2.234 s | 4.407 s |
| 8 | 2,425 | 4.948 s | 10.015 s |

These suites ran sequentially, once each. Four is the measured starting point
for this Mac; eight regressed. Parent-side Python conversion and CPU contention
limit scaling. Re-measure for different hardware, policy/inference costs, and
observation/image settings. Do not equate these rollout-only rates with the
end-to-end campaign rates above or the historical 14,284 basic-mode frames/s.
Raw runs are `artifacts/rl-vector-oracle{1,4,8}/`, with shared worker logs and
per-lane action/state-hash traces.

## Earlier measured result (basic observation mode)

Measured on Apple Silicon macOS 26.5.2, Python 3.14.4, on 2026-09-27 local time (2026-09-28 UTC). These measurements predate oracle observations and correspond to today's `--observation-mode basic`. Both suites used the public process-isolated API, four concurrent sessions, three policies (`noop`, `random`, `explore`), and seeds 0–3. Each of 12 sessions ran 1,800 decisions × 4 physics frames at 128 × 72, saving initial/final snapshots and all telemetry. The suites ran sequentially.

| Native path | Suite wall time | Aggregate physics frames/s | Relative throughput |
| --- | ---: | ---: | ---: |
| Pre-optimization binary, full rendering | 19.945 s | 4,331.9 | 1.00× |
| ABI 2, optional rendering and improved lifecycle | 6.049 s | 14,284.3 | **3.30×** |

Aggregate throughput includes startup, warmup, IPC, trace logging, endpoint images, and teardown. It is the sum of simulated frames across parallel episodes, not the wall-clock frame rate of one game window. These are single suite measurements, not confidence intervals or a hardware-independent promise.

**All 12 full traces matched: 21,600 controller decisions and observed states, plus initial observations.** This is scoped regression evidence for these policies/level/settings. It does not establish native determinism for every level or prove hidden state equivalence. No baseline collected a star or coin, and game completion remains unknown.

Local evidence (Git-ignored):

- `artifacts/final-perf-reference/{manifest,summary}.json`
- `artifacts/final-perf-fast/{manifest,summary}.json`
- Each suite's `session-*/trace.jsonl`, `result.json`, `worker.log`, and `rollout.json`.
- Reference binary SHA-256: `4e00e9e75a86f5bf35d9f2c45468e29878f86358cbf666c944c05ccea0b46b1e`.
- Optimized binary SHA-256: `38f0b08c28d8416731488b6465f573dfb7f5a4e918c5e33149d2410709c60738`.

The original worker-scaling study is preserved in [INITIAL_BENCHMARK.md](INITIAL_BENCHMARK.md). Intermediate experiments in `artifacts/perf-*` used an internal adapter before the public API was integrated; use the final suites above for the current end-to-end comparison.

## What changed

1. **Make pixels optional.** Ordinary `step()` skips GPU display-list submission, framebuffer readback, and image allocation. Recording requests pixels only on scheduled decisions; `render()` requests them explicitly.
2. **Preserve gameplay work.** CPU scene traversal, animation callbacks, and the original force-frame ordering remain. Removing those calls changed trajectories because they have side effects. Skipping visual output must not skip game logic.
3. **Reduce Python overhead.** Reuse ctypes input/progress buffers, read progress in one call, serialize small records directly, and buffer JSONL writes. No per-decision deep `dataclasses.asdict()` conversions.
4. **Bound process costs.** Fresh native workers still provide reliable reset. Normal shutdown now uses the worker protocol; the old SIGTERM/join path waited unnecessarily because SDL intercepted the signal while its event loop was idle. Stuck workers still have a bounded kill fallback.

The engine is a compiled PC port, not an emulator. Physics and gameplay remain native C; the public API adds a local Pipe round trip per decision.

## Reproduce a comparison

Keep a pre-change binary and its adjacent dynamic libraries in ignored storage before rebuilding. The retained reference in this checkout is `artifacts/reference-native/sm64`.

```sh
PYTHONPATH=src python3 -m sm64_policy benchmark \
  --observation-mode basic --engine-mode reference --library artifacts/reference-native/sm64 \
  --workers 4 --output artifacts/reference-new
PYTHONPATH=src python3 -m sm64_policy benchmark \
  --observation-mode basic --engine-mode fast --workers 4 --output artifacts/candidate-new
python3 scripts/compare_rollouts.py artifacts/reference-new artifacts/candidate-new
```

The current binary also supports `--engine-mode reference`, which is useful for isolating GPU capture cost. It does not replace retaining the old binary when changing CPU gameplay code. Hold policies, seeds, frame skip, resolution, capture cadence, and worker count constant. Compare parsed actions/states, not timing-bearing metadata. Use repeated sequential suites if a small timing difference matters.

A visual rollout benchmark is a different workload:

```sh
make demo
make dashboard
```

Recording every decision incurs GPU submission/readback, PNG encoding, Pipe transfers, and disk writes. Use `--record-every 4` or a smaller resolution to trade visual sampling density for speed. With the default `--record-every 0`, only endpoint images are available; the dashboard labels this accurately.

## Next optimization constraints

Profile before changing native update order. A software-only headless backend, fewer process crossings, and true serialized native snapshots could improve throughput, but each requires its own correctness validation. Do not claim constant-time save/load, arbitrary native determinism, or full-game progression from the current replay checkpoint and BOB benchmark.
