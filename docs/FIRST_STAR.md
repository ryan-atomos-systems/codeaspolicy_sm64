# First star: Behind Chain Chomp's Gate

The `first-star` policy earns Bob-omb Battlefield star **6** from the normal fresh
BOB start. It crosses the first bridge, reaches Chain Chomp's post, pounds it three
times, waits for the gate to disappear, and jumps into the star. This is the first
star collected on an empty save, not the first mission in the course list.
The demonstrated episode uses controller inputs only after normal reset: no custom
spawn, teleport, progress edits, or altered enemy/puzzle logic.

## Run and watch

```sh
make first-star
make dashboard
```

Select the new `first-star-*` run in http://127.0.0.1:8765. Play from Start to see the
whole trajectory, or select **Star collected** to inspect the saved-progress
transition. Skill buttons jump to the post, gate, and collection phases. Images
are recorded at every physics frame (30 fps), at 640×360.

Equivalent explicit command, using a new output directory:

```sh
PYTHONPATH=src python3 -m sm64_policy benchmark \
  --policies first-star --seeds 0 --workers 1 --steps 2400 --frame-skip 1 \
  --record-every 1 --width 640 --height 360 --output artifacts/my-first-star
```

Oracle mode and **frame skip 1** are required. Larger batches are rejected because
holding Mario-relative steering while Mario turns changes the intended heading
within the batch. No training or extra Python dependencies are required.

## Technique

This is **hierarchical code-as-policy with model-based feedback control**. It does
not use RL or pretrained weights. A short authored waypoint route handles static
terrain; a skill state machine handles the puzzle. Every decision is recomputed
from the latest observation. Timers gate retries and detect stalls; they do not
substitute for observed task completion.

| Layer | Implementation | Inputs and decisions |
| --- | --- | --- |
| Goal/evaluation | `src/sm64_policy/tasks.py` | Target saved star bit must change from absent to present; rejects an already-collected target |
| Star task | `src/sm64_policy/first_star.py` | Navigate → pound post → wait for gate → collect star → celebrate; bounded phases and death restart |
| Walking | `src/sm64_policy/control.py:steer` | Position/yaw and waypoint; heading feedback and slower final approach |
| Jump alignment | `control.py:air_steer` | Position error, facing and velocity; inverse jump dynamics, lateral correction and braking |
| Ground pound | `control.py:GroundPoundObject` | Object position/top height; press Z only above its center, release A between jumps |
| Recording | `episode.py`, `storage.py`, `recording.py` | Task evidence, phase annotations, event timestamps, causal traces and images |

Ordinary SM64 jump control has two different axes: forward input changes forward
velocity, while sideways input sets lateral velocity. The air controller accounts
for this, the quadratic stick response, and controller dead zone. Ground pounding
cancels horizontal motion once Mario is centered above the post. The policy
confirms the post descended 190 units; it also requires the previously seen gate
to be absent for eight frames in a query that covers its known location. Truncation
or an out-of-range query is not treated as evidence that the gate opened.
The star is selected by behavior and star index. Engine object IDs are not route
constants. The post landmark, 205-unit collision-top offset, and route are
task-specific knowledge from the BOB/native source.

Success is independent of the policy's phase: `StarTask` reads
`progress.collected_star_masks[1]`, verifies bit 5 became set, and latches the first
observed frame. The harness records 60 further frames of the collection animation,
then stops. `result.steps` is the number actually executed; `step_budget` is the
limit. `status=ok` still means the episode ran correctly. Check `task.success` or
`termination=task_success` to assess the goal. Budget exhaustion is not a win.

Trace `policy` annotations describe the decision **before** its action. The trace's
`observation` describes the state **after** that action. Star events are measured
from the resulting observation; do not feed those labels backward into policy
training. `rollout.json` contains skill/star events, the image index and task
result. Existing traces without tasks still work in the dashboard.

## Measured local validation (2026-09-27)

- `artifacts/first-star-success`: normal start, controller-only collection at
  frame **768** / **25.6 game seconds**, no deaths, BOB saved mask **0 → 32**,
  one star gained. Full 30 fps 640×360 playback includes 60 celebration frames.
- `artifacts/first-star-repeat-01`: **4/4** fresh-process runs succeeded, each at
  frame 768 with no deaths. Seeds are labels here: this policy has no RNG, and
  seeds do not randomize the engine. This is repeatability evidence, not broad
  state-distribution coverage or a general determinism guarantee.
- `artifacts/first-star-robustness-01`: **8/8** cases succeeded without deaths:
  normal start; 45/90 neutral-frame delays; initial yaw ±45°; start X ±100 units;
  start Z −100 units. Collection frames ranged from **766–865**, including waits.
  Pose probes explicitly use `SpawnState` at reset; they are separately labeled
  and are not the demonstrated normal-start episode.
- `SM64_NATIVE_TESTS=1 make test`: **19 tests passed**, including target-bit
  validation, bounded query coverage, steering/braking, full native collection,
  and a recording cadence that does not divide the early-stop frame.

Reproduce the robustness probes with:

```sh
PYTHONPATH=src python3 scripts/evaluate_first_star.py \
  --workers 4 --output artifacts/new-first-star-robustness
```

This small suite is useful regression coverage, not a statistical claim of 100%
reliability. The policy can take damage; the demonstrated minimum health is 5/8.
Arbitrary spawns, all acts, other levels, and full-game progression are not
supported by this task. The harness still starts directly in BOB with the upstream
dialogue suppression, auto-respawn, and skipped intro.

## Extending toward the whole game

Keep goals, route planning, motor skills and perception separate. Add star tasks
that compose these skills and provide their own save-bit predicates. Expand the
route layer into a cached collision/navigation graph and add skills for moving
platforms, combat, carrying/throwing and course transitions. The authored route is
sufficient for this star; it is not an automatic all-level planner.

Use RL selectively for interactions or recoveries that resist compact controllers.
Give such a skill a bounded subgoal and termination rule; benchmark it against the
existing skill without changing star-success evaluation. Expert rollouts can also
train imitation or recurrent perception, but neither learner is implemented here.
Estimated observations will need missingness/confidence and robust feedback; this
policy currently assumes exact oracle positions and behavior labels.

An eventual game-level planner must manage star/key prerequisites and Bowser
encounters across a persistent save, and faithful evaluation must restore course
entry, dialogue and death handling. `game_beaten` remains unknown. This star
establishes a tested task/skill/evaluation pattern, not all-game generalization.

## Seeded recovery controller

The current controller punches nearby Goombas while navigating. If knocked below
the first bridge, it chooses a north or south detour around the trench walls
before returning to the ramp. It uses air steering during knockback/jumps and
waits through the normal death sequence instead of treating disappearing objects
as a missing-post error. In a campaign, a BOB death re-enters the painting from
its actual castle return location.

`evaluate_subtasks.py --task bob` starts on castle grounds, walks into BOB, and
stops only when its saved star bit is earned. It exercises actual native game
seeds and normal death/re-entry; it is a first-star probe, not an eight-star run.

```sh
PYTHONPATH=src python3 scripts/evaluate_subtasks.py --task bob --runs 256 \
  --experiment-seed 735120 --steps 6000 --output artifacts/NEW-BOB-SEEDS
```
