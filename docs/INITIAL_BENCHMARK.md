# Initial native benchmark

Measured 2026-09-28 00:52 UTC on macOS-26.5.2-arm64-arm-64bit-Mach-O.
Python 3.14.4; native library; hidden OpenGL rendering at 128 × 72.

36 real gameplay sessions completed. Each used a fresh save and process,
1800 decisions × 4 frames = 7200 simulated frames (240 seconds at 30 Hz).

## Parallel throughput

| Workers | Observed overlap | Sessions | Wall time | Aggregate frames/s | Speedup |
|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 12/12 | 59.24 s | 1458.5 | 1.00× |
| 2 | 2 | 12/12 | 31.75 s | 2721.3 | 1.87× |
| 4 | 4 | 12/12 | 19.77 s | 4371.3 | 3.00× |

Each concurrency setting was measured once; these are initial measurements, not confidence intervals.
Aggregate throughput includes startup, neutral warmup, snapshots, trace logging, and worker teardown.
The suites ran sequentially so they did not compete with one another.

## Policy capability

Results below use the highest-concurrency suite (4 seeds per policy).

| Policy | Mean visited cells | Range | Mean max displacement | Deaths | Stars gained | Peak coins |
|---|---:|---:|---:|---:|---:|---:|
| noop | 1.00 | 1–1 | 0 | 0 | 0 | 0 |
| random | 57.75 | 32–78 | 4869 | 0 | 0 | 0 |
| explore | 52.00 | 49–53 | 9012 | 0 | 0 | 0 |

Cells are 400-unit XZ bins scoped by level/area; displacement is in game world units.
No baseline collected a star or coin. These policies do not yet solve a game objective.

## Limits and provenance

- Upstream's mod enters Bob-omb Battlefield, suppresses dialogue, and auto-respawns on death.
- Fresh-save startup skips the castle intro. Startup rejects the wrong level or a stuck intro action.
- Policy seeds are controlled; native-engine deterministic replay has not been established.
- There is no ending detector; game completion remains unknown, not a reported success.
- Initial smoke runs 001/002 were rejected after finding an intro-cutscene stall; they are excluded here.
- Synthetic fixture runs are also excluded.

Upstream commit: `fa88c37234af93372d454e7b2b28045931a727a2`.
Native library SHA-256: `4e00e9e75a86f5bf35d9f2c45468e29878f86358cbf666c944c05ccea0b46b1e`.

Raw results are in the local, Git-ignored `artifacts/baseline-*` directories:
`summary.json`, `manifest.json`, and per-session configurations, logs, traces, metrics, and PPM images.
See [CODE_POLICY.md](CODE_POLICY.md) for build/run commands and the policy interface.
