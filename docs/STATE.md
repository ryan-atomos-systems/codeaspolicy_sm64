# Oracle state and the path to learned perception

## What “state” means here

The engine's full internal state includes Mario, every object and its behavior program/timers, collision surfaces, camera internals, Lua globals, save progress, RNG, level scripts, and pending transitions. That full state determines subsequent simulation, subject to external timing/input. It is not exposed or serialized by `get_state()`.

`get_state()` returns an immutable **policy observation** sampled at the latest reset/step boundary. It does not advance simulation or query the engine again. The default `observation_mode="oracle"` reads a useful subset directly from native state. It is privileged information, including off-screen objects and hidden timers. It is not a promise of a complete Markov state or a native save-state.

The original flat fields remain available: `position`, `velocity`, `health`, `died`, `height_above_ground`, `stars`, `coins`, `level`, `area`, `act`, `mario_action`. New policies should also use the structured records below. Synthetic observations and `observation_mode="basic"` leave the rich records as `None`; absence is not equivalent to an empty world.

## Current schema

| Record | Information | Policy use |
| --- | --- | --- |
| `frame`, `last_action_frames`, `engine_frame` | Physics frames since reset, previous action duration, engine tick | Align images/actions, estimate motion, time skills |
| `mario` | Position/velocity, facing/angular velocity, forward speed, current/previous action, action arguments/state/timer, input/ability flags, health/lives, invulnerability/cap/jump timers | Steering, jump timing, recovery, attack and movement skills |
| `mario.floor/ceiling/wall` | Available engine collision references with normal, triangle vertices, surface type, flags, room, supporting object ID | Slopes, wall kicks, ceiling clearance, hazards, moving platforms |
| `mario` contact context | Floor/ceiling height, water level, quicksand depth, action-derived airborne/swimming/pole/hanging flags, held/ridden/platform/interacted object IDs | Distinguish air, ground, water, carrying and riding |
| `camera` | Render-camera position/focus, roll, control yaw, mode, cutscene, engine FOV, image size | Relate observations to frames; future perception labels |
| `geometry.rays` | 18 collision samples and hit triangles | Local obstacle, drop, and ceiling detection |
| `objects` | Nearest 64 eligible objects within 6,000 units, IDs, behavior names/IDs, transforms, motion, hit/hurt boxes, interaction flags, action/timer/health | Coins/stars, doors, enemies, platforms, manipulable objects |
| `progress` | Course/level/area/act, star/coin/life totals, per-course star masks, save/unlock flags, cannon unlock mask, last collected course/star, credits signal | Pick goals, avoid already completed stars, track route prerequisites |

Example (inside a guarded `main()`):

```python
with SM64Env() as env:
    state = env.reset(Level.BOB)
    state = env.step(Action(stick_y=64, a=True), n_frames=4)
    print(state.frame, state.mario.face_angle, state.mario.airborne)
    coins = [obj for obj in state.objects.items if "coin" in obj.affordances]
    first_star_done = state.progress.has_star(course=1, star=1)
    floor = state.mario.floor
    if floor is not None:
        print(floor.normal, floor.surface_type)
```

Run `PYTHONPATH=src python3 examples/inspect_state.py` for an actual JSON observation and corresponding rendered frame in `artifacts/oracle-example/`.

### Coordinates and semantics

- Positions are world coordinates in engine units, with Y up. Velocities are engine movement units per physics frame (30 Hz). `relative_position` is a world-axis displacement from Mario, not a camera or body rotation.
- Angles are signed SM64 units, 65,536 per turn, ordered pitch/yaw/roll. Yaw 0 points along +Z; +16,384 points along +X. Use sine/cosine for learned features to avoid the angle wrap discontinuity.
- `camera.control_yaw` uses the engine's control convention; it is not the camera viewing yaw. Derive a viewing direction from `focus - position`. This fork forces a camera behind Mario in its frame builder. The camera record is not calibrated pixel intrinsics: FOV overrides, shake, interpolation and raster aspect need separate validation before projecting labels into images.
- The contact surfaces are the engine's latest references. A wall/floor pointer alone does not mean ongoing contact. `near_floor` only means the sampled Mario Y is within four units of the stored floor height; use action flags, velocity and surface data together. The action-derived flags are overlapping booleans, not an exhaustive motion-mode classifier.
- `water_level` preserves the engine's raw sentinel where no water exists. Floor/ceiling references and ray hits use `None` for unavailable data. An absent ray hit means no hit within that ray segment, not traversable space everywhere.
- Object IDs combine pool slot and allocation generation. They persist across observations of a living object, change when the slot is reused, and are only meaningful within an episode. They are tracking labels, not features whose numeric values should determine an action. IDs are not native pointers and are not global across episodes.
- The object query includes active objects in the current loaded area, including dormant/off-screen/other-room objects; it excludes Mario and objects the engine marks unimportant (typically particles). It sorts by 3D distance. `total_in_radius`, `capacity`, and `truncated` reveal omissions. Referenced held/platform IDs may be outside the returned subset. There is no visibility/occlusion mask yet.
- `affordances` are decoded interaction bits, not a complete taxonomy or guarantee of availability. `intangible_timer`, action, active flags, and task context matter. Object health/damage fields are raw shared behavior fields and may be unused for noncombat objects. Behavior-specific puzzle counters are not yet decoded.
- Star masks are indexed by **course ID**, not level ID. Index 0 is castle secret stars; 1 is BOB, 2 is WF, etc. `has_star(course, star)` uses star numbers 1–7; star 7 represents 100 coins in main courses. Save flags retain the engine's key/door/cap-switch bits from `engine/src/game/save_file.h`. Credits being active is diagnostic, not a tested game-completion predicate.

### Local geometry coverage

Eight horizontal rays start 100 units above Mario and span 1,500 units, at 45-degree increments relative to facing. Nine downward rays form a **world-aligned** 3×3 patch with 300-unit spacing, starting 200 units above Mario and extending down 4,000 units. One upward ray starts 100 units above Mario and extends 2,000 units. Each provides origin, normalized direction, length, optional hit distance/position, and surface data.

The downward samples find the first available collision along that segment, which may be an overhang or a platform rather than ground under Mario. This is a sparse local sensor using the engine's collision ray query; it is not a full mesh, visibility test, walkability map, or proof that a gap can be jumped. Dynamic collision only exists where the engine has loaded it. Build a cached static mesh/navigation map and task-specific queries as route planning grows.

## Keep the task separate

The world tells us what exists and what has happened. A task tells the policy what to accomplish. A useful task contract is `TaskSpec(goal_kind, course, star, target, constraints)` plus policy-maintained skill/subgoal status. The environment should not invent a currently pursued star from `act`: act selection and the star the policy is trying to collect can differ.

Start with explicit task success predicates on progress changes, e.g. a previously absent star bit becoming present. Then add navigation and interaction subgoals. Track failure, timeout, death, and route completion separately from reward and exploration coverage. A credits flag alone is not the final completion detector.

The first implementation is now available: [FIRST_STAR.md](FIRST_STAR.md) describes
the working `StarGoal`/`StarTask` contract, feedback motor skills, saved-bit success
checks, and controller-only Chain Chomp star rollout. The broader roadmap remains:

1. Feedback-controlled movement: face a heading, reach a waypoint, jump, land, recover from a wall, and avoid hazardous floors.
2. One complete star task, with a success predicate and a reproducible start. Use objects/geometry to navigate and interact rather than relying on fixed frame scripts alone.
3. A task graph over stars, unlocks, cap switches, course entries/exits, and Bowser encounters. Add behavior-specific puzzle counters and warp destinations when those tasks need them.
4. A faithful end-to-end evaluation mode. Current sessions still inherit BOB entry, dialogue suppression, auto-respawn, and fresh-save resets; observation work has not removed those modifications.

## Learning the observation from images and history

Use the oracle as a teacher and preserve a policy-facing semantic contract:

```text
image_t + previous estimated belief + previous action/duration
                    ↓ state estimator
             estimated state + uncertainty
                    ↓ policy(state, task)
                 next action
```

In notation: `belief_t = estimator(belief_(t-1), action_(t-1), n_frames, image_t)`. The policy initially consumes oracle state; later it consumes a compatible estimated state. A **belief** may contain distributions, unknown fields, confidence and last-observed timestamps, not only point estimates.

Not every oracle field can be uniquely inferred from the current image. Off-screen enemies need object memory. Collected stars and unlocks need persistent progression memory or HUD/cutscene evidence. Internal timers/RNG cannot generally be recovered exactly. Prefer policy decisions based on task-relevant semantic state; retain extra oracle internals as debugging labels or privileged training targets. Do not force a vision model to regress meaningless pointer-like IDs or memorize arbitrary behavior/action numeric encodings.

Training data must be causal and aligned. At reset record `(state_0, image_0)`. Each step gives `(action_t, duration_t, state_(t+1), image_(t+1))`. In our JSONL trace, an entry's observation/frame is **after** its recorded action. Use the previous entry (or initial observation) as that action's input state; do not train the policy on the post-action state paired with the action that produced it. Current ABI 3 policy rendering selects the current interpolation endpoint, and `RGBFrame.frame` identifies the corresponding post-action frame. This is a timestamp/phase contract, not a claim of pixel-perfect camera calibration. Historical ABI 1/2 recordings used the previous interpolation endpoint and should not be silently mixed into new perception labels. `--record-every 1` records each decision boundary; larger cadences are sparse image supervision and should carry missing-image masks.

Train initially with oracle labels and history, then evaluate and train recurrent rollouts using the estimator's own past predictions. Always feeding past oracle states during training hides error accumulation and leaks a resource that won't exist at deployment. Collect data on policies with perception errors as well as expert trajectories. Split evaluation by episode/seed and later by route or environment conditions, not neighboring frames from the same rollout.

Next additions for this phase are per-object visibility/association labels, calibrated camera projection, task annotations, transition events with intra-step timestamps, and an explicit belief schema with missingness/uncertainty. The current typed records and frame indices establish the observation targets; they do not implement or train the estimator yet.

## Performance and compatibility

Progression mode also includes `ui`: `dialog_id`, `dialog_state`, `dialog_response`,
`menu_mode`, `transition_active`, `play_mode`, and `selected_act`. These are copied
through an additive native accessor, leaving ABI 3's fixed struct layouts intact.
The policy can distinguish a conversation, act-selection screen and warp from
ordinary movement. They are privileged labels for later temporal perception;
they do not contain text understanding or a learned dialogue policy.

Oracle mode is the default and requires native ABI 3 (`make build`). `SM64Env(observation_mode="basic")` or CLI `--observation-mode basic` retains the old compact observation and supports ABI 1/2 reference binaries. Oracle sensing, serialization, IPC, and trace storage cost more; hold observation mode constant in timing comparisons. Synthetic mode remains a harness fixture with no oracle claims.

Native records use fixed-width, pointer-free layouts with size/version checks. Bounds are explicit. All values are copied into immutable Python records so a later native read cannot mutate an old observation. Save/load checkpoints now include observation mode, and their history verification covers the selected observation schema. Full state dumps should never be confused with complete native memory snapshots.

## Local validation

The final ABI 3 build passed 14 tests, including native level/spawn resets, immutable oracle translation, layout rejection, object/ray consistency, frame timestamps, and rich-observation checkpoint replay with matching continuation.

- `artifacts/state-final-basic`: 12 native episodes × 1,800 decisions; all 21,600 basic action/state records and initial observations match the pre-oracle `artifacts/final-perf-fast` suite. Aggregate basic-mode throughput was 14,410 simulated frames/s on this run.
- `artifacts/state-final-oracle` and `artifacts/state-final-reference`: four native episodes × 300 decisions, random/explore seeds 0/1, four workers, 320×180 images every four decisions. All 1,200 rich action/state records and initial observations match between fast and fully rendered execution. These short recorded suites achieved 1,974 and 1,458 aggregate simulated frames/s respectively; their workload differs from the long basic benchmark.
- `artifacts/oracle-example/state.json` and `frame.png`: actual BOB observation after four frames, with 40 returned nearby objects and 18 geometry probes in this sample.

These checks establish scoped consistency for tested episodes, not general native determinism, pixel-perfect projection, or full-game completion. Oracle JSON is substantially larger than basic telemetry; the initial 12×600-decision oracle suite used approximately 271 MB of uncompressed traces. For large training corpora, add a compact columnar/tensor exporter rather than treating verbose JSON as the final dataset format.

Native game seeding is now opt-in (`game_seed`, scheme 1). Earlier artifacts and
runs without this option seed only Python policy randomness. Neither seeds nor
matching observation hashes capture hidden native memory; use verified action
replays scoped to the same build/runtime. A replay bundle includes the game seed,
settings and action durations as well as observed-history checks.
