# Native source provenance

Moved from `env/` in [Gumbo64/sm64-AI](https://github.com/Gumbo64/sm64-AI), upstream `coop` commit `fa88c37234af93372d454e7b2b28045931a727a2`. This is the repository's modified sm64ex-coop PC port. Preserve upstream notices and source organization so native changes can be reviewed against it.

The maintained Python interface is outside this tree in `src/sm64_policy/`. Original Gym wrappers moved to `legacy/env/`. Build scripts and native tooling remain here.

Local patches:

- `Makefile`: modern macOS linking, GLEW include flags, configurable Lua library directory, and relocatable BASS library loading.
- `src/pc/logfile.h`: remove packing that misaligns file pointers on modern Apple Silicon toolchains.
- `src/pc/gfx/gfx_sdl2.c`: hidden SDL window controlled by `SM64_POLICY_HIDDEN`.
- `src/pc/gfx/gfx_opengl.c`: RGB readback pack alignment of one byte.
- `src/pc/pc_main.c`: correct per-step inputs, isolated network port, policy-mode intro skip, optional GPU/image work while preserving CPU frame order.
- `src/pc/policy_state.{h,c}` and `src/game/spawn_object.c`: pointer-free oracle records and allocation-generation object IDs.
- `src/pc/policy_bridge.{h,c}`: ABI version, batched progress read, fast step, no-physics render, image release, and spawn positioning.

Use `python3 scripts/build_native.py --jobs 4` from the repository root. It fixes build flags to `MAX_PLAYERS=1`, `DISCORD_SDK=0`, and `COOPNET=0`. Changing compile options requires `--clean`.

ROMs, extracted assets, build products, and runtime saves are ignored. Upstream already includes some prebuilt dependency libraries and custom game art; preserve those source dependencies. New generated binaries must stay untracked.
