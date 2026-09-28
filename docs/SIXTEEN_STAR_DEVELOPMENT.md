# Sixteen-star completion: evidence and remaining policy work

A fresh-save controller trajectory now collects **16 stars**, obtains both Bowser keys, passes the upstairs gates with backward long jumps, defeats the final Bowser, collects the Grand Star, and enters the ending. A separate fresh replay reproduced the **complete observation-history hash** while recording dashboard playback.

This is a completed **development trajectory**, not a verified autonomous full-game policy. GPT-6 Astra developed and tested the feedback skills, switched controllers during development, tried explicit controller inputs, and branched action-replay checkpoints. The first 15-star prefix ran autonomously. The complete sequence can be replayed from the normal fresh start using controller inputs alone, but that establishes reproducibility of this trajectory, not generalization of a frozen policy.

## Watch the result

Start the local dashboard with `make dashboard` if it is not already running.

- [Full trajectory](http://127.0.0.1:8765/#run=sixteen-star-complete-01&session=session-000&frame=0)
- [Final course, successful first wheel exit](http://127.0.0.1:8765/#run=sixteen-star-complete-01&session=session-000&frame=101715)
- [Final Bowser battle](http://127.0.0.1:8765/#run=sixteen-star-complete-01&session=session-000&frame=107400)
- [Grand Star](http://127.0.0.1:8765/#run=sixteen-star-complete-01&session=session-000&frame=110400)
- [Ending](http://127.0.0.1:8765/#run=sixteen-star-complete-01&session=session-000&frame=111180)

Playback samples the game and full oracle state every 10 physics frames. The inspector lists every controller decision between displayed states and labels the final action separately. Policy targets and reasoning were not recorded for this development trajectory; they are not reconstructed after the fact. The earlier first-Bowser recording retains its detailed controller diagnostics.

## Verified local evidence

`artifacts/sixteen-star-complete-01/session-000/result.json` records `verified=true`, `game_beaten=true`, and `autonomous_policy_validation=false`.

| Event | Physics frame |
| --- | ---: |
| Final Bowser defeated | 109998 |
| Grand Star cutscene begins | 110407 |
| Ending / credits active | 111172 |
| Recording ends | 113178 |

The ending begins at 61:45.7 of simulated game time. This includes exploration, failed attempts, and waiting during controller development; it is not a speedrun claim. The 113178-frame replay and recording took about 234 seconds on this host, which is a replay measurement, not policy-development throughput.

The observation-history SHA-256 is:

```
af370e5f0af507c24a30622b30fb7b3e9307ed341ea385f26baa68f4cae62901
```

The canonical checkpoint is retained in both the development directory and the self-contained playback bundle:

```
artifacts/sixteen-star-complete-01/session-000/checkpoint.json
```

Recreate the verification and dashboard recording in a new output directory:

```sh
PYTHONPATH=src python3 scripts/record_checkpoint.py \
  artifacts/sixteen-star-complete-01/session-000/checkpoint.json \
  --output artifacts/sixteen-star-reverified --record-every 10
```

The recorder rejects a different engine build, gameplay mod, spawn override, or observed history. A replay mismatch leaves artifacts explicitly unverified. Each replay starts a fresh process and save directory; it does not load native memory or write earned progress. ROMs, extracted assets, native binaries, saves, checkpoint bundles, and large rollout artifacts remain outside Git.

`SixteenStarCompletion` independently requires 16 unique saved star bits, evidence of both keys or their unlocked doors, final Bowser health reaching zero in level 34, the Grand Star action, and credits. It retains key evidence because ending code clears transient save flags. The progression-mode `died` signal is not a reliable death counter; no death-count claim is made.

## Route and technique

The method is **hierarchical code as policy with oracle-state feedback**. There are no learned weights and no RL training in these extensions. Controllers use position, velocity, action state, contact/platform identity, nearby object motion, dialog state, and save progress. Course landmarks are authored constants.

The stars are Chain Chomp's Gate; both Princess's Secret Slide stars; Secret Aquarium; Whomp King, fortress tower, owl cage, Wild Blue, and Blast Away the Wall; Lethal Lava Land red coins, Big Bully, bully trio, and Hot-Foot-It into the Volcano; basement Toad; Hazy Maze Cave's Swimming Beast; and Board Bowser's Sub. MIPS door clips bypass the 30-star gate. Backward long jumps pass the 50-star door and endless stairs.

The useful control improvements include:

- Timing repeated backward long jumps from distance to the next stair riser, rather than blindly alternating A.
- Predicting rotating-platform positions and waiting for an acceptable landing window.
- Centering Mario on a moving platform before accelerating for the next jump.
- Waiting for an approaching slider before jumping from a pole, then tracking it in flight.
- Chaining backflips at landing transitions to beat the timed staircase.
- Braking long jumps from position and forward velocity, and steering around hanging obstacles.
- A Bowser controller that circles to the tail, grabs, spins, releases toward a bomb, avoids fire, and collects the reward.

Selected source versions and their dependencies are retained in [`experiments/sixteen_star/`](../experiments/sixteen_star/README.md). They are separate from the supported first-Bowser policy. The source catalog names each tested entry point and its required starting state.

## Next autonomous-policy work

The main gaps are a reliable MIPS door-clip state machine, a robust moving-step entry in Bowser in the Sky, and one campaign scheduler that composes the skills with explicit entry, success, failure, and retry conditions. The endless-stairs helper currently assumes an already initiated backward long jump. DDD entry needs a guard against stale coordinates during area transitions.

Freeze that composed policy before running fresh-save evaluations across seeds and timing perturbations. Keep failures in the denominator. A successful replay or an isolated checkpoint test is not a replacement for that evaluation. Do not claim native determinism, arbitrary-state robustness, or an autonomous sixteen-star success rate from this result.

## Runtime changes and checks

`Action.start` now reaches the native controller and is preserved by version-2 compact action replays; version-1 A/B/Z replays remain readable. The dashboard displays Start and distinguishes sampled action sequences from held actions.

The native bridge performs multiple scene traversals per simulation frame. A pause-menu selection must remain latched until the level update consumes it; later traversals previously overwrote it with zero. A native pause-and-exit regression test covers the fix.

This runtime is the upstream native PC port, not an N64 emulator. Progression mode skips the intro and uses the port's normal course, dialog, death, and menu behavior, including “Exit to Castle.” Physics, star requirements, and Bowser health were not changed to complete the route.

Validation for this change: 50 Python tests passed with native checks enabled, three dashboard model tests passed, and the complete fresh-save replay matched its observation-history digest. Older experimental filenames may overstate results; use the verified result JSON, not checkpoint names, as evidence.
