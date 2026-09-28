# Fresh-save campaign: eight stars and the first Bowser

The `first-bowser` policy starts on castle grounds with an empty save, earns eight
unique stars, opens the eight-star door, traverses Bowser in the Dark World, and
fights Bowser for the basement key. The final objective is verified from saved
star bits and the key flag. HUD counts and a policy's phase are not proof of success.

## Run and watch

```sh
make build
make first-bowser
make dashboard
```

Select the new run at http://127.0.0.1:8765. Event buttons seek to each collection.
The full trace includes every physics-frame action and oracle observation; images
are recorded every three frames (10 fps) at 480×270. The dashboard serves compact
telemetry, keeping the complete oracle training data on disk.

```sh
PYTHONPATH=src python3 -m sm64_policy benchmark \
  --policies first-bowser --seeds 0 --workers 1 \
  --gameplay-mode progression --level 16 --steps 36000 --frame-skip 1 \
  --timeout 1800 --record-every 3 --width 480 --height 270 \
  --output artifacts/my-first-bowser
```

Use a new output directory. The budget is a ceiling; verified success stops the
run after 60 additional frames. `status=ok` means execution completed normally;
check `task.success` and `termination=task_success` for the gameplay result.
A missing module, crash, timeout, or exhausted budget is not success.

## Verified run

`artifacts/first-bowser-attempt-03/session-000/result.json` records a successful
continuous native run from castle grounds with all 26 initial star masks and
initial save flags zero. No custom spawn or checkpoint was used.

- Eighth star: frame 19,113 (10:37.10 at 30 game frames/second).
- First Bowser key: frame 26,540 (14:44.67); the recording continues to frame 26,600.
- Eight unique saved stars, zero deaths, minimum health 5/8.
- Saved star masks: BOB `32`, WF `23`, PSS `3`, Secret Aquarium `1`.
- Final save flags `27665` include the basement-key bit `16`.
- 8,868 images; 26,600 action/observation records; about 142 seconds wall time
  including startup on the development machine, with recording enabled.
- Trace SHA-256: `21fde462e20538cf55ac27477cb25f01a0be673496155bf6b85321e3c1bcd364`.

[Open the verified playback](http://127.0.0.1:8765/#run=first-bowser-attempt-03&session=session-000).
Use the star and level event buttons to skip ahead. This is one complete
successful run, supported by two isolated course-and-battle probes with different
entry delays; it is not a measured general success rate. The earlier full attempts
remain available as failed or incomplete runs.

## Technique and route

This is **hierarchical code-as-policy with model-based feedback control**, with
no RL training or learned weights. The task graph chooses the next skill using
saved progression. Each skill reads the current state and produces ordinary
controller inputs. There are no resets, checkpoint restores, custom spawns,
teleports invoked by the policy, or save modifications during a campaign.

| Order | Star | Controller |
| --- | --- | --- |
| 1 | BOB: Behind Chain Chomp's Gate | Post alignment and three ground pounds |
| 2 | Princess's Secret Slide, under 21 seconds | Position and velocity feedback on the slide |
| 3 | Princess's Secret Slide, box | Same route, then break the box and collect its star |
| 4 | The Secret Aquarium | Steer swimming yaw/pitch and gate strokes while turning |
| 5 | WF: Chip Off Whomp's Block | Bait a slam, evade, jump onto the back and pound |
| 6 | WF: To the Top of the Fortress | Track moving platforms, ride the elevator, recover falls |
| 7 | WF: Fall onto the Caged Island | Wake and catch Hoot, steer flight, release above the cage |
| 8 | WF: Shoot into the Wild Blue | Talk to the buddy, aim a simulated ballistic arc, slide down the pole |

The Bowser course composes walking, long jumps, moving-platform boarding, a narrow
path, seesaw tilt control, and a timed staircase. The battle circles behind Bowser,
grabs his tail, builds angular velocity, releases toward an observed bomb, and
collects the spawned key after the defeat dialogue.

Static landmarks and geometry knowledge are authored from the native level
sources. Dynamic object positions, velocities, contact, actions, health, UI,
and saved progress come from the oracle. This is a route-specific controller,
not a general navigation solver or a policy proven across arbitrary spawn states.
The structure allows replacing an individual skill with search, MPC, or RL while
retaining the same observation/action and evaluation contracts.

## Where to work

- `src/sm64_policy/campaign/policy.py`: campaign graph and castle routes.
- `campaign/slide.py`, `aquarium.py`, `owl.py`, `cannon.py`: specialized controls.
- `campaign/whomp_climb.py`, `whomp_fight.py`, `tower.py`: shared WF access and tasks.
- `campaign/dark_world.py`, `upper_bitdw.py`, `stairs.py`, `fight.py`: Bowser route.
- `control.py`: Mario-relative heading control and inverse ordinary-jump dynamics.
- `tasks.py`: evaluator independent of policy phases; rejects nonempty campaign starts.

Decisions must run every physics frame. During ordinary jumps the facing is
locked: forward input accelerates, lateral input directly changes side velocity.
A world-facing steering command cannot instantly turn a jump. Release A between
jumps; hold Z before pressing A for a long jump or backflip. Moving-platform IDs
may persist during takeoff, so boarding checks must also require ground contact.
The native stick dead zone matters when using tiny inputs to turn in place.

Development checkpoints are action replays, not native snapshots. Curriculum
probes may start inside a level or replay a checkpoint; label those separately.
A final capability claim needs a new full run from grounds with an empty save.
Do not infer success from a stitched collection of isolated skill tests.

## Progression mode and fidelity

Default `scaffold` mode preserves the earlier BOB benchmark's shortcuts.
`progression` mode restores act selection, dialogues and NPC interactions, the
normal camera and HUD, normal deaths and course exits, and local network object
updates. The local area clock advances once per physics frame, including course
timers and moving-object updates. This avoids wall-clock-dependent timers in an
accelerated simulation.

The intro cinematic is still skipped. This remains the modified native PC port,
with Mario-relative controls and `MAX_PLAYERS=1`, rather than retail N64 emulation.
The objective is the first Bowser milestone; the evaluator does not claim the
whole game was beaten. Earlier unseeded runs controlled policy RNG only; this authored policy has no
Python RNG. Explicit game seeds now vary native randomness. A repeated trace is
scoped repeatability evidence, not a guarantee of native determinism or success
from untested states.

For future vision training, preserve pre-action observations and image timing.
Trace observations are post-action; shift them correctly when making examples.
Oracle targets include UI state, but an image-only agent must infer dialogues,
menus, object motion and progress from its own history instead of using save bits
as inputs. Keep task verification separate from inferred policy state.

## Normal-start seeded evaluation

```sh
PYTHONPATH=src python3 scripts/evaluate_campaign.py \
  --runs 64 --workers 4 --output artifacts/NEW-SEEDED-EVALUATION
```

This freezes the current policy, samples distinct uint32 Python/game seeds, and
uses the normal empty-save castle-grounds start without spawn or delay changes.
Each run has a 36,000-frame budget. The experiment and manifest preserve the seed
pairs; compact traces and action replay bundles are saved, without intermediate
images. `statistics.json` reports successes over all attempted runs, a Wilson
95% interval, and game/wall completion-time distributions for successful runs.
Budget failures are censored, not silently removed from success-rate statistics.
Four workers are the measured throughput optimum on the development M3 machine.

## Failure-focused probes

`python3 scripts/evaluate_subtasks.py` (with `PYTHONPATH=src`) supports `bob`,
`pipe`, `fight`, and `dark-world`. Each probe saves seed/configuration, actions,
observation hashes, phase events, a final image, and a checked replay bundle.
`--max-delay` varies the number of neutral startup frames. Pipe probes additionally
vary reset yaw and Z position; they are explicitly labeled curriculum cases.
These resets are never used by the continuous campaign policy.

The pipe controller finishes climbing the rim before walking into the opening.
A Bowser battle death resumes at the pipe checkpoint. A game-over return uses
the lobby route from grounds rather than the fortress-exit route. The narrow
upper-course approach clears the Goomba while Mario is on the broad landing.

To rerun recorded campaign seed pairs, pass `--seed-suite artifacts/PRIOR-RUN`
to `evaluate_campaign.py`; optionally select original session numbers with
`--indices 4 6 10`. Each evaluation must use a new output directory. Evaluate
new seeds separately from cases used while developing the controller.

Course retries now wait an additional 37 physics frames per attempt. The first
attempt has no extra delay; later attempts change timing to avoid repeating an
identical collision indefinitely. This is ordinary neutral controller input and
counts against the same episode frame budget. Enemy checks use position and
floor height so a Goomba beneath the route cannot keep the controller engaged.

See [seeded failure analysis and final validation](POLICY_RELIABILITY.md) for the
latest measured success rates, recovered cases, and reproducible evaluation commands.
