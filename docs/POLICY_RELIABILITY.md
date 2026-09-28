# Policy reliability after seeded failure analysis

The final validation recovered all 20 previously failing campaign seeds and
completed 64/64 campaigns on unseen seed pairs. Success requires eight unique
saved star bits plus the first Bowser key. The campaign budget remains 36,000
physics frames (20 minutes of game time), starting normally on grounds with an
empty save. The policy uses ordinary controller inputs throughout.

## Results

| Evaluation | Successes | Evidence directory |
| --- | ---: | --- |
| Original baseline | 44/64 | `artifacts/campaign-seeded64-20260928` |
| Original failing seeds, final policy | **20/20** | `artifacts/reliability-original20-final` |
| Additional failures found during development | **2/2** | `artifacts/reliability-campaign-newfailures2` |
| Unseen seed pairs, final campaign validation | **64/64** | `artifacts/reliability-campaign-unseen64-final` |
| BOB from grounds, seeded task sweep | **256/256** | `artifacts/reliability-bob256-final` |
| Pipe entry, varied reset yaw/Z and startup timing | **64/64** | `artifacts/reliability-pipe64-v1` |
| Bowser fight, varied seeds and startup timing | **64/64** | `artifacts/reliability-fight64` |

The accepted validation contains **384 focused task runs and 86 full campaigns**.
There are 1,098 recorded session results across development and validation,
including rejected controller variants and the interrupted development batch.
The pipe and fight rows are curriculum tests, not continuous eight-star runs.

For the unseen campaign cohort (experiment seed `735122`), the observed success
rate is 100%; its Wilson 95% interval is **94.34–100%**. This is evidence under the
specified RNG distribution and budget, not a guarantee for arbitrary states.
All 64 observed histories differ. Regression cases are reported separately and
are not included in that confidence interval.

Successful game completion times: mean **15:06.13**, median **14:44.47**, range
**14:06.80–18:44.40**. 14 of the 64 campaigns entered the Bowser course more
than once: falls and retries can still occur, but all final campaigns finished.
Suites overlapped during validation; their wall times are not a controlled
performance comparison.

## Changes

- Bridge navigation attacks nearby Goombas and uses air steering. Falls into the
  trench select the appropriate north/south detour back to the ramp.
- Death animations no longer trigger missing-object errors. BOB re-entry uses
  the actual painting-room return point; scaffold auto-respawn clears old detours.
- Pipe entry stops pulsing jump at the rim and walks into the opening after the
  climb. Battle deaths resume at the pipe checkpoint.
- Game-over returns use the lobby route from grounds. Course retries vary their
  neutral-input delay by 37 frames per attempt, breaking repeated collision timing.
- The upper course clears a Goomba on the wide landing and excludes enemies on
  other floors. Its narrow route avoids steering into the supporting wall.

The attempted moving-platform rewrites did not improve measured reliability and
were discarded. Their development artifacts remain available. Recovery remains
part of the controller; the task evaluator and engine gameplay rules are unchanged.

## Reproduce and inspect

```sh
PYTHONPATH=src python3 scripts/evaluate_campaign.py --runs 64 \
  --experiment-seed 735122 --output artifacts/NEW-CAMPAIGN-EVAL

PYTHONPATH=src python3 scripts/evaluate_subtasks.py --task bob --runs 256 \
  --experiment-seed 735120 --steps 6000 --output artifacts/NEW-BOB-EVAL
```

`evaluate_campaign.py --seed-suite artifacts/PRIOR --indices ...` reruns selected
recorded seed pairs. Always use a new output directory. The final campaign
artifacts retain manifests, configs, worker logs, traces, results and replay
bundles. The exact evaluated policy source and silent native runtime are saved
under `artifacts/reliability-final-source`.

A recovered campaign with three Bowser-course entries was replayed independently:
**32,258 action/observation frames matched**, with **109 images** extracted.
See `artifacts/reliability-recovered-campaign-replay/replay-result.json`.

**46 tests passed with native integrations enabled; lint passed.** Tests include
wrong-floor enemy rejection, retry timing, battle checkpoint and game-over routes,
trench recovery, dying-Mario handling, and scaffold detour cleanup.
