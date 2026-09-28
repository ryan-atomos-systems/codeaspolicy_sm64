# Experiment evidence

The page reports a continuous campaign from castle grounds with an empty save,
ending with eight unique saved stars and the first Bowser key. It uses a modified
native PC port, oracle observations, and Mario-relative controls. The intro is
skipped, and the API frame counter starts after the native startup warmup.

## Recorded runs

| Measurement | Original successful run | Instrumented rerun |
| --- | ---: | ---: |
| Run identifier | first-bowser-attempt-03 | first-bowser-debug-01 |
| Stars earned | 8 | 8 |
| Key first verified at frame | 26,540 | 26,540 |
| Recorded decisions | 26,600 | 26,600 |
| Recorded images | 8,868 | 8,868 |
| Deaths | 0 | 0 |
| Minimum health | 5/8 | 5/8 |
| Episode wall time | 142.046 s | 140.439 s |

Both episodes start with all 26 saved star masks and initial flags zero. Final
star masks are BOB 32, WF 23, Princess's Secret Slide 3, and Secret Aquarium 1;
other masks are zero. Final save flags are 27665 and include the first-key bit 16.
The evaluator counts unique saved bits independently of policy labels.

The rerun matches the initial observation and all 26,600 actions and resulting
observations. Decision diagnostics intentionally differ. This comparison is
scoped regression evidence, not a success-rate estimate or a claim about equality
of all hidden native memory. Whole-game completion remains unknown.

## Packaged data

- [Selected metrics from both runs](evidence.json).
- [55 consecutive recorded decisions](media/decision.json), outcomes 1437–1491.
- [Complete campaign video](media/campaign.mp4), 10 recorded images/s, no audio.
- [Python policy source](policy-source.zip), excluding the native engine.
- [Technical report source](paper.tex), standalone LaTeX with embedded references.
- [Export asset hashes](site-manifest.json).

The decision excerpt includes input observation 1436 before its first action.
For each subsequent record, the preceding observation is the input; that record's
observation is its outcome. Images are sparse and labeled with their own frame.
The final video endpoint is quantized to the 10-image/s cadence. Collection times
come from the state trace rather than video timestamps.

## Trace identities

Original trace SHA-256:
`21fde462e20538cf55ac27477cb25f01a0be673496155bf6b85321e3c1bcd364`

Instrumented trace SHA-256:
`0deabb1ab412bc02e6f3749cf83b479bfa4fadad6ac2e39e6d6c76aba98c7ee3`

Shared native library SHA-256:
`a4c81a7f00a50128acac502d0d909f9cf621708f90d2203aed679415a2de7638`

The raw trace hashes were checked during preparation of the publication. Raw
traces, ROMs, extracted assets, binaries, and saves are not included in this site.

## Limits of the record

The run manifests identify the upstream/base Git revision, with local changes,
rather than a complete frozen release. Their source digest covers an explicit
set of Python and native inputs, not the entire checkout. The campaign manifests
also retain a stale BOB/scaffold scope string; session configurations and traces
record the actual progression-mode campaign. Historical artifacts were not
rewritten. The technical report discusses these provenance limits.

Timing metadata identifies Apple Silicon macOS 26.5.2 and Python 3.14.4 but does
not record an exact chip model or controlled machine load. Episode execution
time does not measure development time, language-model latency, or training cost.
Human task direction and iterative source-informed development were part of the
process; total prompts, tokens, costs, and interventions were not instrumented.

GPT-6 Astra is credited as the development agent. The deployed Python policy has
no learned weights or per-frame language-model calls. No full-game result,
vision-only result, or comparison against RL is claimed.
