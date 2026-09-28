# 3D state and decision debugger

Open `make dashboard`, choose a recorded session, and scrub the shared timeline.
The game image and interactive oracle scene appear side by side. On narrow phone
widths they stack; **Expand** gives the scene its own full-window workspace.

Try the instrumented successful campaign:
[ground-pound decision](http://127.0.0.1:8765/#run=first-bowser-debug-01&session=session-000&frame=1467).
The URL retains a selected frame, so you can bookmark a specific decision.

## Read a decision causally

The four panels show **input observation → policy intent → chosen action → observed
outcome**. Trace row `t` contains the action and its *resulting* observation. Its
input is the preceding observation (or the initial observation for the first
row). The viewer never pairs an action with its outcome as though that outcome
were the input. Frame batches retain their actual duration; stepping means one
recorded decision, which may span multiple physics frames in older runs.

**Show: Policy input / Outcome** selects the 3D observation. The input ghost in
outcome mode shows Mario before the action. Ghosts, displacement comparisons,
and local trails stop across level/area changes. Long teleport discontinuities
also break trails. Camera modes include follow Mario, free orbit, top down, and
the approximate recorded game camera. Drag to orbit, right-drag to pan, and use
the wheel to zoom. Arrow keys rotate the focused 3D canvas; outside controls they
step decisions. Every mode and layer is also available through labeled controls.

Images may be sparse. Their **actual** frame is shown, alongside any offset from
the selected observation. No image is synthesized or silently treated as current.
**Align to recorded image** seeks to the last recorded image frame. This is useful
when investigating exact state/image pairs; `--record-every 1` gives an image at
every decision boundary. The state view dims and says “Loading” during a cache
miss instead of labeling a stale scene as the new frame.

## What the scene means

| Layer | Meaning and limits |
| --- | --- |
| Orange capsule, white arrow | Mario's position and facing yaw; capsule is a proxy, not animation or exact collision bounds |
| Blue arrow | Observed velocity multiplied by six frames for visibility; not a predicted collision-aware path |
| Cyan ghost | Mario in the preceding input observation |
| Green/red/purple triangles | Recorded floor/wall/ceiling references; a reference alone does not prove contact |
| Blue-gray triangles | Unique triangles returned by the recorded ray hits |
| Rays and endpoints | Hit segment or full no-hit query length; a miss says nothing about unsampled space |
| Colored object proxies | Returned objects: gold rewards/coins, coral enemies, teal platforms, purple doors/warps, gray other behaviors |
| Optional wire cylinders | Recorded interaction hitbox radius, height and down offset; these are not an object's collision mesh |
| Purple camera frustum | Recorded pose/FOV/aspect; approximate because rendering overrides and shake are not calibrated |
| Yellow target and route | Recorded condition target or last evaluated steering target; XZ-only targets/routes project to input Mario height, not inferred terrain |
| Orange trail | Up to 120 recent observations in the same area, excluding large jumps and warps |
| Grid | A 200-unit measurement guide near the sampled floor height; never evidence of a floor |

Click an object or choose it from **Observed object** to inspect position,
velocity, behavior/action, health, timer, affordances and raw fields. **Focus**
centers the camera on it. Selecting a surface displays its normal, source object
and vertices in raw fields. An object that disappears from the bounded query
stays labeled “not returned”; absence is not assumed to mean destruction.

The coverage line shows returned/eligible object counts, radius, truncation, and
ray count. This version draws **only the geometry already present in the oracle**.
It does not load a hidden full-level map or invent surfaces between sampled rays.
A future bounded triangle query or separately labeled reference mesh can expand
coverage without changing the meaning of today's observations.

## Recorded intent, not reconstructed reasoning

`decision_trace.py` adds a context-local recorder around `policy.act()`.
`steer()` and `air_steer()` log target, errors, control terms, returned intermediate
stick values and caller file/line. `Route` records its authored XZ waypoints.
`GroundPoundObject` records its actual alignment/height conditions; the Bowser
fight records spin-speed and aim conditions before a throw. These additions do
not influence control outputs or mutate the engine.

Evaluated calls are displayed in order. A later call or button override can
replace an earlier result, so the UI explicitly distinguishes **intermediate
controller outputs** from the **final chosen action**. A direct action without
instrumented conditions remains a direct action; the viewer does not invent an
explanation. Older artifacts expose their original diagnostics and targets when
available and explicitly label missing controller details. Nothing re-executes
old policy code to explain a historical recording.

To add more debugging, call `record_gate(name, conditions, **facts)` at a branch,
`record_control(name, **facts)` from a shared controller, or
`record_route(points_xz, active_index)` at a route decision. They are no-ops
outside a capture context. Keep values JSON-compatible and bounded. Logs should
name observed quantities and actual conditions, rather than generated prose
about what the policy might have considered.

Debug event navigation includes recorded skill changes and observed health,
held-object and airborne-action transitions. These describe sampled changes;
a health decrease can also be swimming air loss, and a release is not proof of a
successful throw. An airborne action ending can mean landing, swimming, pole contact or a cutscene; the event label does not assert ground contact. Success remains the independent saved-progress evaluator.

## Implementation and performance

- `dashboard/traces.py`: scans JSONL once, caches compact telemetry and byte
  offsets for at most two sessions; file size/mtime/inode changes invalidate it.
  An incomplete trailing line is excluded until it is complete.
- `GET /api/states?run=...&session=...&start=N&count=24`: returns a bounded page,
  plus its previous input observation. Index 0 is reset state, index N>0 is trace
  row N-1's outcome. Missing historical reset states remain null. Count is 1–48.
- `oracle-data.js`: six-page browser LRU, duplicate request sharing, prefetch,
  cancellation on session change and stale-response protection.
- `state-view.js`: Three.js scene, camera controls, picking and layer rendering.
  Three.js 0.184.0 and OrbitControls are pinned, vendored locally with MIT license;
  no CDN, network dependency, bundler or Python runtime dependency is required.
  See `static/vendor/README.md` for source and integrity information.
- `debug-model.js` and `decision-view.js`: causal display transforms and recorded
  calculation inspector. UI text uses `textContent`, never artifact HTML.
- The HTTP server remains read-only, loopback-only, with explicit static routes.
  WebGL2 is required for the 3D canvas; flat telemetry and decision inspection
  remain available when a renderer cannot be created.

## Validation

`artifacts/first-bowser-debug-01` is a new continuous campaign with the recorder
enabled. It earns eight stars and the key at frame 26,540. Its initial observation
and **all 26,600 actions and resulting observations exactly match**
`first-bowser-attempt-03`; only diagnostics differ. This is scoped regression
validation, not a general native-determinism claim.

```sh
make test
SM64_NATIVE_TESTS=1 make test
node --test tests/debug_model.test.mjs
node --check src/sm64_policy/dashboard/static/app.js
make lint
```

Tests cover causal page boundaries, byte offsets with UTF-8, partial files,
cache eviction, legacy missing frames/initial state, endpoint bounds, controller
instrumentation and sparse-image alignment. Also inspect a real run in the
browser: play, scrub, switch input/outcome, pick objects, orbit, toggle layers,
follow debug events, and load an older basic/synthetic recording.
