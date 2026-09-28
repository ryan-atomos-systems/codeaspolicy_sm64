"""Build prerequisites and source/binary provenance."""

import hashlib
import platform
import subprocess
import sys
from pathlib import Path

from .paths import DEFAULT_LIBRARY, ROOT


def doctor(library=None):
    library = Path(library) if library else DEFAULT_LIBRARY
    rom = ROOT / "engine/baserom.us.z64"
    expected = (ROOT / "engine/sm64.us.sha1").read_text().split()[0]
    rom_hash = hashlib.sha1(rom.read_bytes()).hexdigest() if rom.is_file() else None
    return {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "library": str(library),
        "library_exists": library.is_file(),
        "rom": str(rom),
        "rom_exists": rom.is_file(),
        "rom_sha1_matches": rom_hash == expected if rom_hash else None,
        "blockers": []
        if library.is_file()
        else [
            "Native library is missing; supply engine/baserom.us.z64 and run python3 scripts/build_native.py"
        ],
        "notes": [
            "Library ABI, MAX_PLAYERS=1, and graphics are validated by native workers",
            "Hidden rendering still requires a working OpenGL display/context",
        ],
    }


def source_identity():
    # Include uncommitted policy, harness, and engine changes in provenance.
    paths = sorted((ROOT / "src/sm64_policy").rglob("*.py")) + [
        ROOT / "engine/src/pc/pc_main.c",
        ROOT / "engine/src/bass_audio/bass_audio_helpers.c",
        ROOT / "engine/src/pc/gfx/gfx_opengl.c",
        ROOT / "engine/src/pc/gfx/gfx_sdl2.c",
        ROOT / "engine/mods/compass/main.lua",
        ROOT / "engine/src/pc/logfile.h",
        ROOT / "engine/src/pc/policy_bridge.c",
        ROOT / "engine/src/pc/policy_bridge.h",
        ROOT / "engine/src/pc/policy_state.c",
        ROOT / "engine/src/pc/policy_state.h",
        ROOT / "engine/src/game/spawn_object.c",
        ROOT / "engine/src/engine/behavior_script.c",
        ROOT / "engine/src/game/rng_position.c",
        ROOT / "engine/src/pc/network/sync_object.c",
        ROOT / "engine/src/pc/lua/smlua.c",
        ROOT / "engine/src/pc/mods/mods.c",
        ROOT / "engine/Makefile",
        ROOT / "scripts/build_native.py",
    ]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())
    git = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return {"git_commit": git.stdout.strip(), "source_sha256": digest.hexdigest()}
