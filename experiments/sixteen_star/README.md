# Sixteen-star development skills

These are the selected source versions used to develop the completed trajectory.
They have package-relative imports and standard formatting; workbench file logging
and module reloads were removed. Version suffixes preserve correspondence with the
local experiment checkpoints. Dependency modules are retained because their exact
movement behavior matters. This is an experimental skill library, not a single
validated autonomous sixteen-star policy.

Run with the repository root and `src` on Python's import path. Each skill consumes
the oracle observation and returns an `Action`; most use `act(state)`, while
`campaign.Campaign` uses `act(state, frame)`. Evaluate every physics frame. Do not
pass these directly to the benchmark loader without adapting the constructor,
goal, and method signature.

| Segment | Selected entry point | Evidence / precondition |
| --- | --- | --- |
| Fresh save to 15 stars and first key | `campaign.Campaign` | Autonomous development prefix; fixed route |
| Submarine star | `ddd_full.Submarine` | Enter normal DDD area 1; ignore stale positions during warps |
| Second Bowser course and key | `after_sub.Finish` | After collecting the Submarine star |
| 50-star staircase BLJ | `blj3.BLJ` | Correct staircase approach and alignment required |
| Endless stairs BLJ | `blj_endless2.BLJ` | Resume an already initiated backward long jump, facing yaw 0 |
| Sky moving step | `bits_start.Start`, `bits_steps3.Climb` | Timing-sensitive; not robust across approach phases |
| Sky lower route | `bits_cross4.Cross`, `bits_ramp.Ramp` | Course-specific waypoints |
| First rotating lift | `bits_wheel3.Wheel`, `bits_wheel_exit.Exit` | Wait for predicted platform position; recenter before takeoff |
| Left route and high gap | `bits_left2.Left`, `bits_back5.Back`, `bits_flip10.Jump` | Stop Back after the first backflip platform; diagonal sideflip then dive |
| Purple switch and timed steps | `bits_switch2.Switch`, `bits_stairs6.Up` | Chain landing-to-backflip transitions before timer expires |
| Upper ramp to arrow | `bits_roadrise2.Road`, `bits_loop2.Loop` | Stop on the arrow platform; do not chase the static final waypoint |
| Arrow obstacles | `bits_arrow_blocks6.Arrow` | Backflips over raised blocks; lateral long jump around final hanging obstacle |
| Octagons and poles | `bits_west2.West`, `bits_pole_exit.Exit`, `bits_sliders.Sliders`, `bits_pole2_exit2.Exit` | Second pole exit waits for the approaching platform and tracks its motion |
| Final rotating lifts | `bits_final_wheel2.Board`, `bits_final_transfer2.Transfer`, `bits_final_exit.Exit` | Position-aware boarding; center on platform before the next jump |
| Final staircase and pipe | `bits_pipe.Pipe` | Upper platform at Y=5833 |
| Final Bowser | `bowser_safe.Safe` | Circle to tail, grab, spin, aim at nearest bomb, avoid fire, collect Grand Star |

The MIPS and castle modules are controller primitives used with development
interventions. They do not form a reliable autonomous door-clip controller.
`mips_dddentry.Entry` also needs an area-transition guard before integration.

The replay bundle is the canonical record of the exact executed controller
sequence. Reusing a skill from a different starting state or platform phase can
fail even when a nearby checkpoint succeeded. See
[the evidence guide](../../docs/SIXTEEN_STAR_DEVELOPMENT.md) before reporting results.
