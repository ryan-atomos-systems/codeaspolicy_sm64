# Working on SM64 Policy Lab

## Start here

- Read `README.md`, `docs/API.md`, `docs/STATE.md`, and `docs/ARCHITECTURE.md` before changing the harness.
- Maintained Python lives in `src/sm64_policy/`; native code in `engine/`.
- `legacy/` preserves upstream experiments for reference. Do not import those wrappers into the new API.
- The runtime has no third-party Python dependencies. Keep the dashboard build-free and local unless requirements change.
- Use `make test`, or `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
- Optional development tools: `python3 -m pip install -e '.[dev]'`; `make lint` checks Python style. Run `node --check src/sm64_policy/dashboard/static/app.js` after JavaScript changes, and verify behavior in the browser.
- Use `SM64_NATIVE_TESTS=1 make test` for engine, process lifecycle, rendering, level, spawn, and checkpoint changes.
- Build with `python3 scripts/build_native.py --jobs 4`. Use `--clean` after compile-option changes. Build with `MAX_PLAYERS=1`.

## Engine invariants

- One engine instance per fresh process and save directory. `SM64Env` owns this lifecycle; never load a second ctypes library instance in a process.
- Use the public `SM64Env` API in new callers. The CLI scheduler isolates policy failures separately from the owned engine process.
- The fork has global C/Lua state. Killing a failed process is safer than invoking its partly disabled `game_deinit`.
- Oracle observations require ABI 3. Keep `policy_state.h` and `native_state.py` synchronized; maintain record size checks. IDs are allocation generations plus slots, never pointers. Sensing must not change game logic, RNG, or Lua state. Use basic mode with ABI 1/2 reference binaries.
- The C/ctypes struct layouts and ten-argument `main_func` must stay synchronized. Width precedes height in `GameState`.
- Policy sticks are Mario-relative in this fork, not conventional camera-relative controls. Buttons are assigned on every step so jump releases work.
- The fast path skips GPU submission and pixel readback when no image is requested. Preserve scene traversal, animation callbacks, and frame ordering: they have gameplay side effects. Do not simply remove `force_make_frame*` calls.
- State/image labels must use the same post-action frame. ABI 3 uses interpolation endpoint 1; old ABI 1/2 recordings used endpoint 0. Do not train on a trace's resulting observation as input for that same trace's recorded action.
- `render()` submits the prepared display list without advancing physics. Validate state and continuation when changing it.
- `reset(level, spawn_state)` currently supports a level plus optional position/yaw, not arbitrary engine object state or act/area selection.
- Checkpoints are JSON action replays. Never call them instantaneous native snapshots. Check build/mod fingerprints and observation history; fail on drift. They do not save Python policy RNG or hidden native memory.

## Validation and reporting

- Run parallel native episodes with `PYTHONPATH=src python3 -m sm64_policy benchmark --workers 4 --output artifacts/NEW-RUN`.
- Use a new output directory for every run. Preserve `manifest.json`, per-session traces/results, worker logs, and summary.
- Compare performance with identical policies, seeds, frame skip, resolution, recording cadence, observation mode, and worker count. Run reference and fast suites sequentially to avoid CPU contention.
- `--engine-mode reference` retains full GPU rendering per decision. For a true pre-change comparison, retain the old binary and adjacent dynamic libraries in ignored `artifacts/` and supply `--library`.
- Run `python3 scripts/compare_rollouts.py artifacts/REFERENCE artifacts/CANDIDATE` to check every action and observed state, including initial observations when available.
- Report aggregate wall-clock throughput separately from per-session stepping rate; recording, process startup, and teardown cost time.
- Synthetic mode tests harness mechanics only. Never report synthetic results as gameplay capability.
- Policy seeds control the policy RNG; `game_seed` separately seeds the engine. Matching traces are scoped evidence, not a promise of cross-build determinism or game completion.
- Default `scaffold` native benchmarks inherit the upstream BOB entry, suppressed dialogue, auto-respawn, and skipped intro. `progression` restores normal act selection, dialogues/NPCs, deaths/exits, camera/HUD and physics-frame area clocks; the intro remains skipped. Generic benchmarks leave `game_beaten` unknown; the sixteen-star completion verifier has separate ending evidence. Verify startup level/action before interpreting results.
- Test the dashboard in a browser against actual recorded frames, plus old trajectory-only artifacts. Keep synthetic/invalid-startup labels visible.
- `make first-star` records the controller-only BOB star-6 task. Read `docs/FIRST_STAR.md` before changing its skills. Oracle mode and one-frame decisions are required. Check `task.success` and saved-mask transitions; process `status=ok` alone is not a gameplay win. Native tests include a full star run. Use `scripts/evaluate_first_star.py` for separately labeled pose/timing perturbations.
- Read `docs/FIRST_BOWSER.md` for the campaign. `make first-bowser` starts from grounds with an empty save and progression mode. Its evaluator requires eight unique saved star bits plus the first key. Develop skills with separately labeled curriculum probes, then rerun from the beginning; isolated skill successes are not a continuous-run result.

- Read `docs/STATE_DEBUGGER.md` before editing the 3D viewer or decision diagnostics. Run `node --test tests/debug_model.test.mjs` and syntax-check edited JS modules. Preserve input/action/outcome timing, bounded state paging, and explicit unknown geometry. Vendor licenses and pinned sources belong in Git.
- The publication site lives in `website/`; read its `README.md` before editing it. `python3 scripts/build_website.py` exports a standalone GitHub Pages bundle into ignored `artifacts/project-site/`. Use `python3 scripts/preview_website.py` for local preview with byte-range video seeking. The site copies the existing 3D viewer and a bounded recorded excerpt; it never executes the game or policy. Preserve template attribution and the distinction between agent development, runtime policy, and measured results.

## Data and ownership

- Keep ROMs, extracted assets, generated native binaries, save files, and artifacts out of Git. Upstream-supplied runtime libraries and custom art already belong to the source tree; do not remove them accidentally.
- Never fetch a ROM. The user supplies `engine/baserom.us.z64`; the build verifies its checksum.
- Keep the dashboard bound to loopback and serving only known artifact routes. Do not expose arbitrary filesystem paths or policy execution over HTTP.
- Update docs alongside API, artifact schema, directory, or benchmark protocol changes.

- Read `docs/5090_HANDOFF.md` for Linux setup and `docs/SIXTEEN_STAR_DEVELOPMENT.md` for the verified development trajectory. The completed sixteen-star trajectory is not yet an autonomous campaign policy.
