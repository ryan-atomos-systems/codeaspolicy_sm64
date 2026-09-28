# Linux tower-climb deadlock and fix

The eight-star + first-Bowser policy now completes on both the M3 Mac and the
9950X Linux host. The failed Linux benchmark exposed a controller dead-zone bug;
no native physics, compiler flags, observation schema, or checkpoint checks were
changed to make the campaign pass.

## Cause

The tower controller waits until its heading error is below 0.18 radians before
jumping. While turning, it calls `steer(..., magnitude=24)` to avoid walking off
the platform. At an observed 11.334° heading error this produces raw stick
`(-5, 24)`. The native `adjust_analog_stick` in `engine/src/game/game_init.c`
ignores raw axis values from -7 through 7, and subtracts/adds 6 from accepted
values. Thus the intended sideways turn becomes zero while forward walking
continues. Mario cannot satisfy the alignment gate at that pose.

The recorded Linux failure was on the diagonal tower platform while targeting
the north platform at XZ `(0, -704)`. Mario was at
`(264, 4185, -527.193115234375)`, facing yaw `-24576`, with an 11.334° error.
The original policy exhausted 36,000 frames with five saved stars. Cross-platform
trajectory differences brought Linux into this failure case; the controller
assumption was unsafe on either platform.

## Change

`steer` now accepts `ensure_turn=True` for heading-alignment gates. It raises a
nonzero lateral command inside the dead zone to signed magnitude 8, leaving the
forward input unchanged. Both tower alignment gates use this option: the next
platform jump and the backflip onto the top. Ordinary steering retains its
existing response. The decision trace records the actual corrected action and
whether the option was enabled.

This is intentionally a local controller fix. It does not promise bit-identical
floating-point state across Linux/x86 and macOS/ARM, and does not bypass replay
fingerprints or force the Linux state to match a Mac checkpoint.

## Validation

All campaign runs start from castle grounds with an empty save, use progression
mode and full oracle state, and issue one controller action per physics frame.
They use only normal controller inputs, with no intermediate reset or save edits.

| Run | Saved stars + first key | Final frame |
| --- | --- | ---: |
| Original Linux pilot | 5 stars, task failed | 36,000 budget |
| Fixed Linux, single campaign | 8 stars + key | 27,852 |
| Fixed Linux, four parallel campaigns | 4/4 succeeded | 27,852 each |
| Fixed Mac, single campaign | 8 stars + key | 26,520 |

The four Linux parallel trace hashes match the fixed single campaign:

```
5d24bcded1b5016eb0d064447465c840460c310314325d973b1b81e33349b5ee
```

The task verifier checks eight unique saved star bits plus the first key, rather
than inferring success from process exit. The key is earned at frame 27,792 on
Linux and 26,460 on Mac; the recorder then retains 60 ending frames.

All 52 tests passed with `SM64_NATIVE_TESTS=1` on each host. Added regression tests
recreate the observed tower pose and exercise both turn directions, checking that
the selected action survives the native dead-zone threshold while preserving the
forward command and the alignment-before-jump gate. Ruff and formatting pass.

This validates the eight-star campaign that failed during hardware benchmarking.
It is not a new validation of the full sixteen-star development trajectory on
Linux, and the two platforms still have different state histories.

## Local evidence

- Linux original campaign: `artifacts/hardware-scaling-5090-20260928/w01-r1/`.
- Linux full oracle/controller diagnostic: `artifacts/linux-compat-diagnostic-01/`.
- Linux fixed single: `artifacts/linux-compat-fix-01/`.
- Linux fixed parallel: `artifacts/linux-compat-fixed-parallel-01/`.
- Mac fixed campaign: `artifacts/mac-compat-fix-01/`.
- Mac consolidated diagnostics/results: `artifacts/linux-compat/`.

Raw recordings remain ignored. The native test suites include rendering,
checkpoint replay, first-star collection, and process lifecycle validation.
