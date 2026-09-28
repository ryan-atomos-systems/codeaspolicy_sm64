# MacBook versus 5090 host throughput (2026-09-28)

The Ryzen 9 9950X / RTX 5090 desktop delivered **12,058 aggregate physics
frames/s** at 32 workers, versus **2,933 frames/s** for the M3 MacBook Air at
8 workers: **4.11×** the best tested median throughput. Single-worker throughput
was **1.22×** faster. These are native oracle-rollout measurements, not RTX GPU
inference, visual recording, or full-game completion speed.

## Repeated results

Each entry is three sequential batches. Ranges are observed minima/maxima,
not confidence intervals. Machines ran independently; no benchmark batches
competed on the same host. Alternate sweeps reversed the worker-count order.

| Host | Workers | Median frames/s | Range | Average CPU cores, median | Batch time, median |
| --- | ---: | ---: | ---: | ---: | ---: |
| MacBook Air M3 | 1 | 885 | 885–887 | 1.00 | 22.59 s |
| MacBook Air M3 | 4 | 2,699 | 2,371–2,866 | 3.94 | 29.64 s |
| MacBook Air M3 | 8 | 2,933 | 2,432–3,125 | 6.36 | 54.55 s |
| 9950X / RTX 5090 box | 1 | 1,077 | 1,057–1,103 | 1.00 | 18.56 s |
| 9950X / RTX 5090 box | 4 | 3,797 | 3,779–3,834 | 3.98 | 21.07 s |
| 9950X / RTX 5090 box | 8 | 6,773 | 6,537–6,919 | 7.91 | 23.62 s |
| 9950X / RTX 5090 box | 16 | 10,687 | 9,283–10,706 | 15.88 | 29.94 s |
| 9950X / RTX 5090 box | 32 | 12,058 | 11,154–14,025 | 30.29 | 53.08 s |

Use **32 workers for bulk throughput** on the desktop. They used about 30.3 of
32 logical CPUs on average (95%). Use **16 workers for shorter batch latency**:
median 29.9 seconds instead of 53.1 seconds, at 89% of the aggregate throughput.
The desktop has 16 physical cores with two hardware threads each. On the Mac,
8 workers had the best tested median, only 9% ahead of 4, with overlapping ranges.
Higher counts than 8 on Mac or 32 on Linux were not tested in this study.

## Workload and timing

- Same source commit: `49bd1b26cdc1ed13fd17c40f84a20d438f0cdee3`.
- Each fresh process/save simulates 20,000 frames with one decision per frame.
- Native fast mode, full oracle observations, BOB (level 9), scaffold mode.
- Random baseline; Python policy seed 0 and native game seed 0 in every session.
  Identical seeds deliberately control the work, rather than produce diverse data.
- Compact traces retain every action and full-state hash. Resolution 480×270;
  images only at the two endpoints. This is not continuous dashboard recording.
- Rate = sum of simulated frames / complete CLI wall time, including startup,
  warmup, policy, IPC, observation extraction, tracing, endpoint images, and teardown.
- CPU cores = child-process user + system CPU seconds / CLI wall seconds, including
  waited engine descendants. External display-server CPU time is excluded.
- Mac: M3 Air, 4 performance + 4 efficiency cores, 16 GiB RAM, macOS 26.5.2,
  Python 3.14.4, Apple OpenGL. Desktop: Ryzen 9950X, 16 cores / 32 threads,
  approximately 60 GiB usable RAM, Ubuntu 24.04, Python 3.12.3.
- Linux ran under Xvfb with Mesa llvmpipe and `LP_NUM_THREADS=1` to avoid multiplying
  software-rendering threads across workers. The RTX 5090 was not used for this
  workload. This compares the configured machines and software stacks, not CPU
  architectures in isolation. Normal background applications remained running.

There is meaningful run-to-run variation, especially at high concurrency.
The 32-worker desktop runs ranged from 11,154 to 14,025 frames/s. Three batches
are enough to show the broad scaling result, not a precise thermal or latency model.

## Correctness and portability

All **222 fixed-length native sessions / 4,440,000 frames** completed: 39 sessions
on Mac and 183 on Linux. Every trace file was independently SHA-256 checked
against its recorded digest. Within each host all repeated runs and worker counts
produced the same complete trace and initial observation. Both hosts produced the
same 20,000 controller actions and initial observation.

Cross-platform oracle state hashes differ starting at frame 1; the compact Mario
state first differs in velocity at frame 58. We do not claim cross-build trajectory
equivalence. The throughput test exercises the same inputs and API settings but
can follow different physical trajectories. It is not evidence of a policy win.

An initial eight-star + first-Bowser campaign pilot succeeded on Mac in 26,769
frames. Linux reached the 36,000-frame budget with five stars and no task success.
The campaign pilot and an interrupted Mac four-worker campaign were excluded
from the throughput table. The tower-controller dead-zone failure was subsequently fixed and the campaign
passed on both hosts; see [Linux compatibility](LINUX_COMPATIBILITY.md). The
throughput table preserves the measurements from before that fix.

## Reproduce and inspect

The stdlib-only driver is `scripts/benchmark_scaling.py`. It creates new output
directories, preserves CLI logs, manifests, session results and traces, and writes
`scaling.json` after each completed batch. It fails if a session is incomplete.

Mac:

```sh
python3 scripts/benchmark_scaling.py --workers 1 4 8 --repeats 3 \
  --output artifacts/hardware-fixed-mac-NEW
```

Linux, from `/home/ryan/code/codex/sm64_ai`:

```sh
xvfb-run -a env LP_NUM_THREADS=1 python3 scripts/benchmark_scaling.py \
  --workers 1 4 8 16 32 --repeats 3 --output artifacts/hardware-fixed-5090-NEW
```

Raw data stays outside Git:

- Mac: `artifacts/hardware-fixed-mac-20260928/` (scaling and validation JSON,
  nine suites and their complete recordings).
- Desktop: `artifacts/hardware-fixed-5090-20260928/` (scaling and validation JSON,
  fifteen suites and their complete recordings).
- Mac consolidated metadata: `artifacts/hardware-comparison-20260928/`
  contains comparison JSON, Linux measurements and validation, hardware metadata,
  and the canonical Linux trace. Full desktop artifacts remain on the desktop.
- Campaign pilot evidence: `artifacts/hardware-scaling-{mac,5090}-20260928/`
  on the respective host.

All benchmark workers exited after the measurements.
