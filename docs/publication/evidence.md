# Evidence and editorial notes

Prepared September 28, 2026. This file is the fact-checking companion to the paper, blog, and tweet drafts. It records local evidence, not a public artifact release. Historical experiment files have not been rewritten.

## What was achieved

**GPT-6 Astra, acting as the coding/development agent under human task-level direction, developed an executable Python policy that starts with an empty save on castle grounds, earns eight unique stars, and obtains the first Bowser key in one continuous episode.**

The runtime technique is hierarchical code-as-policy with model-based feedback control. The demonstration uses oracle observations in a modified native PC port. It has no per-frame language-model calls, RL training, or learned policy weights. Full-game completion and state estimation from images have not been demonstrated.

“Fresh save” describes the saved-progress starting condition. It does not include the opening cinematic, which is skipped. The environment performs 30 warmup steps of four physics frames before resetting its public frame counter to zero. Public frame times therefore exclude this warmup and the intro.

The model name is the attribution supplied for this development session. Model version comparisons, total model calls/tokens/cost, total development time, and the precise division of every individual human/agent contribution were not instrumented. Do not infer them from episode metrics.

## Claim-to-evidence map

All paths below are relative to the repository root.

| Claim | Primary local evidence | Interpretation |
| --- | --- | --- |
| Empty save; 8 unique stars; first key | `artifacts/first-bowser-attempt-03/session-000/result.json`, `task` | 26 initial masks zero; initial flags zero; 8 final star bits; final flags include bit 16 |
| Starts on castle grounds, without custom spawn | Same session's `config.json` and `rollout.json` initial observation | Level 16, `spawn_state: null`, progression mode |
| Continuous controller-only campaign | `src/sm64_policy/episode.py`, `campaign/policy.py`, controller sources, full trace | Policy returns actions; no policy calls to resets, save edits, spawn writes, or checkpoint restores; ordinary in-game warps are used |
| Key at frame 26,540; 0 deaths; minimum health 5/8 | Session `result.json` | Recorded outcome in the tested episode; does not establish recovery under different conditions |
| Route and collection frames | Session `rollout.json`, `events` | Saved-bit collection events and level transitions |
| Instrumented rerun matches 26,600 action/observation pairs | `artifacts/first-bowser-debug-01/debug-validation.json`; both runs' traces and initial observations | Diagnostics differ intentionally; not an arbitrary-start or seed sweep |
| Ground-pound example | Debug run `trace.jsonl`, row with outcome frame 1,467; preceding observation | Input frame 1,466; horizontal error 28.766644; height above top 46.623901; final action neutral stick + Z |
| Bowser release logic | `src/sm64_policy/campaign/fight.py` | Speed and angle conditions in actual code; not a learned controller |
| Oracle query limits | `docs/STATE.md`, `engine/src/pc/policy_state.c`, `src/sm64_policy/native_state.py` | Bounded privileged observations; no full local collision mesh |
| API/process/checkpoint semantics | `src/sm64_policy/environment.py`, `native.py`, `docs/API.md` | Fresh native process per reset; replay checkpoints; render does not advance physics |
| Debugger's timing and geometry meaning | `docs/STATE_DEBUGGER.md`, recorded decision diagnostics, dashboard modules | Input precedes action; row observation is the outcome; proxies and samples are labeled |
| Earlier 3.30x basic-mode throughput improvement | `artifacts/final-perf-reference/summary.json`, `artifacts/final-perf-fast/summary.json`, `docs/PERFORMANCE.md` | Separate workload and earlier binaries; not the campaign throughput |

## Core measurements

| Metric | `first-bowser-attempt-03` | `first-bowser-debug-01` |
| --- | ---: | ---: |
| Saved stars earned | 8 | 8 |
| Success frame | 26,540 | 26,540 |
| Recorded physics frames / decisions | 26,600 | 26,600 |
| Recorded images | 8,868 | 8,868 |
| Episode wall seconds (`finished_at - started_at`) | 142.046194 | 140.439035 |
| Loop wall seconds | 141.530956 | 139.855165 |
| Physics frames / loop second | 187.944749 | 190.196765 |
| Time inside policy calls, seconds | 0.273380 | 0.443051 |
| Deaths | 0 | 0 |
| Minimum health, out of 8 | 5 | 5 |

Both runs use one worker, oracle observations, one-frame decisions, 480×270 recording every three frames, and a 36,000-frame maximum budget. Successful verification stops the run after a 60-frame recording tail. `26,540 / 30 = 884.6667` seconds to success; `26,600 / 30 = 886.6667` seconds including the tail. Recording includes endpoint images. Wall time is not development time, model latency, or training cost. The small difference between the two wall times is not a measured instrumentation speedup.

The manifest records macOS 26.5.2 on arm64 and Python 3.14.4. It does not record an exact Apple chip model, thermal state, or controlled background load. Do not invent a hardware-specific performance claim.

## Artifact identities

The raw trace SHA-256 hashes were recomputed during preparation of these drafts and matched the recorded values.

| Item | SHA-256 |
| --- | --- |
| Original successful trace | `21fde462e20538cf55ac27477cb25f01a0be673496155bf6b85321e3c1bcd364` |
| Instrumented successful trace | `0deabb1ab412bc02e6f3749cf83b479bfa4fadad6ac2e39e6d6c76aba98c7ee3` |
| Shared campaign native library | `a4c81a7f00a50128acac502d0d909f9cf621708f90d2203aed679415a2de7638` |
| Original run's recorded source digest | `32c6018807144957c222709952cab5d233bf67f31d744ae11e81644d67d290a1` |
| Instrumented run's recorded source digest | `0000ff5eeb5569e75e2af046daf4e01c5def6c1605cd6aca82f9b6ce7ad5bbb8` |

The different trace hashes are expected: the instrumented trace includes extra diagnostics. Comparison of **actions and observations** must exclude those intentionally different diagnostic fields.

The recorded Git revision is `fa88c37234af93372d454e7b2b28045931a727a2`. It identifies the base checkout, with extensive local changes, rather than a frozen release of this implementation. The source digest covers the Python modules and an explicit list of native/build inputs in `diagnostics.source_identity()`; it is not an archive of the entire checkout or all dashboard files. A public reproducibility release needs an actual reviewed source revision or source archive.

The campaign manifests retain the stale `scope` string “Bob-omb Battlefield; dialogue suppression, auto-respawn, intro skipped.” It describes scaffold mode. Per-session configurations specify **progression** mode, and observations/results record the multi-level campaign. Do not quote the stale manifest string as the experiment setup. The paper discloses this discrepancy; no historical artifact was silently corrected.

## What the evidence does not establish

- No general success rate. Earlier attempts changed code; they are not iid trials of a frozen controller. Do not advertise “100% success” or divide successes by development attempts.
- No full-game result. `game_beaten` is null; the campaign evaluator checks eight stars and the first key.
- No pixel-only or blind exploration result. Exact oracle state and source-informed landmarks are central inputs.
- No retail-console equivalence. The native port changes input coordinates and startup behavior and restores progression relative to a training fork.
- No autonomous research benchmark. Human goal-setting and iterative agent development were part of the process, without a complete intervention log.
- No guarantee that all engine memory matched. Trace equality compares exported observations and actions.
- No scalability curve, cross-game generalization result, or comparison against RL. The interface supports further experiments; those outcomes are unmeasured.
- No complete geometry reconstruction. The viewer draws observed surfaces and ray samples, with unknown regions left unknown.

## Reproduce and inspect

See [FIRST_BOWSER.md](../FIRST_BOWSER.md) for the run command and [STATE_DEBUGGER.md](../STATE_DEBUGGER.md) for viewer semantics. Start the dashboard with `make dashboard`.

- [Continuous instrumented campaign](http://127.0.0.1:8765/#run=first-bowser-debug-01&session=session-000).
- [Ground-pound decision](http://127.0.0.1:8765/#run=first-bowser-debug-01&session=session-000&frame=1467).
- [Eighth-star collection](http://127.0.0.1:8765/#run=first-bowser-debug-01&session=session-000&frame=19113).
- [First-key collection](http://127.0.0.1:8765/#run=first-bowser-debug-01&session=session-000&frame=26540).

These are local URLs, not shareable public endpoints. The recording is sparse at 10 images/s. Preserve the dashboard's actual image-frame labels when illustrating a decision between recorded images.

The generic `scripts/compare_rollouts.py` compares whole rows and expects budget-length traces. It is unsuitable for these two early-stopped runs with intentionally different diagnostics. A campaign comparison should instead assert identical initial observations, equal trace lengths, and equality of each row's `frame`, `action`, and `observation`, while verifying task success independently.

## Sources used in the drafts

Primary sources checked on September 28, 2026. The arXiv entries are cited by their original preprint year; the drafts do not require a claim about later publication venues.

| Source | Relevance |
| --- | --- |
| [Liang et al., Code as Policies (2022)](https://arxiv.org/abs/2209.07753) | Language-model-generated programs for embodied control |
| [Wang et al., Voyager (2023)](https://arxiv.org/abs/2305.16291) | Executable game skills improved using feedback |
| [Verma et al., Programmatically Interpretable Reinforcement Learning (2018)](https://proceedings.mlr.press/v80/verma18a.html) | Readable program policies; a different synthesis/training procedure |
| [Sutton, Precup, and Singh, options framework (1999)](https://people.cs.umass.edu/~barto/courses/cs687/Sutton-Precup-Singh-AIJ99.pdf) | Temporally extended closed-loop skills |
| [Ma et al., Eureka (2023)](https://arxiv.org/abs/2310.12931) | Generated reward code followed by RL, contrasted with direct policy code |
| [Gumbo64/sm64-AI](https://github.com/Gumbo64/sm64-AI) | Direct native-interface foundation and upstream attribution |

No quantitative performance comparison against these projects is supported by this experiment.

## Media and publication preparation

The project website now includes the full recorded campaign and a bounded interactive decision excerpt; [website/README.md](../../website/README.md) documents the GitHub Pages export. The text edition was rewritten to match that page. These original screenshots remain available as optional publication media:

- [Game/state view](../../artifacts/first-bowser-debug-01/state-debugger.png).
- [Decision inspector](../../artifacts/first-bowser-debug-01/decision-debugger.png).
- [Earlier campaign completion dashboard](../../artifacts/first-bowser-attempt-03/dashboard.png).

The standalone paper uses a vector system diagram and tables, so it needs no external image files or BibTeX database. Its source is opened in the Codex LaTeX editor with a compiled PDF preview. The website currently links the LaTeX source, explicitly labeled; a PDF can be added after exporting the preview. The prepared static bundle includes selected media but has not been published. Do not redistribute the ROM, extracted assets, native binaries, or saves as part of these materials.

The tweet file contains nine thread posts and three alternatives, all plain ASCII within the quoted post text and all below 280 characters including numbering. Captions, suggested media, and source notes are outside the posts. Adding a URL or changing text requires another length check.
