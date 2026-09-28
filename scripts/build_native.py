#!/usr/bin/env python3
"""Build a single-player library; verify the ROM before invoking upstream make."""

import argparse
import hashlib
import os
import platform
import re
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LUA_URL = "https://www.lua.org/ftp/lua-5.3.6.tar.gz"
LUA_SHA256 = "fc5fd69bb8736323f026672b1b7235da613d7177e72558893a0bdcd320466d60"


def require(name):
    path = shutil.which(name)
    if not path:
        raise SystemExit(
            f"Missing {name}; on macOS: brew install make sdl2 glew pkgconf x86_64-elf-binutils"
        )
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--clean", action="store_true", help="Clean engine objects before building")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    rom = ROOT / "engine/baserom.us.z64"
    if not rom.is_file():
        raise SystemExit(f"Place your US ROM at {rom}")
    expected = (ROOT / "engine/sm64.us.sha1").read_text().split()[0]
    if hashlib.sha1(rom.read_bytes()).hexdigest() != expected:
        raise SystemExit("ROM checksum does not match the upstream US release")
    mac = platform.system() == "Darwin"
    if mac:
        brew = require("brew")
        prefix = subprocess.check_output([brew, "--prefix"], text=True).strip()
        os.environ["PATH"] = f"{prefix}/bin:{prefix}/opt/make/libexec/gnubin:" + os.environ["PATH"]
        os.environ["PKG_CONFIG_PATH"] = f"{prefix}/lib/pkgconfig:" + os.environ.get(
            "PKG_CONFIG_PATH", ""
        )
    make = require("gmake" if mac else "make")
    version = subprocess.check_output([make, "--version"], text=True)
    match = re.search(r"GNU Make (\d+)", version)
    if not match or int(match[1]) < 4:
        raise SystemExit(
            "GNU Make >= 4 is required (macOS system make silently skips asset extraction)"
        )
    options = ["MAX_PLAYERS=1", "DISCORD_SDK=0", "COOPNET=0"]
    if mac:
        for name in ("clang", "pkg-config", "sdl2-config", "x86_64-elf-as", "x86_64-elf-objcopy"):
            require(name)
        lua_dir = ROOT / "artifacts/deps"
        lua_dir.mkdir(parents=True, exist_ok=True)
        lua_src = lua_dir / "lua-5.3.6"
        archive = lua_dir / "lua-5.3.6.tar.gz"
        if not archive.exists():
            urllib.request.urlretrieve(LUA_URL, archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != LUA_SHA256:
            raise SystemExit("Lua source archive checksum mismatch")
        if not lua_src.exists():
            with tarfile.open(archive) as tar:
                tar.extractall(lua_dir, filter="data")
        subprocess.run(
            [
                make,
                "-C",
                str(lua_src / "src"),
                f"-j{args.jobs}",
                "liblua.a",
                "MYCFLAGS=-DLUA_USE_MACOSX -fPIC",
            ],
            check=True,
        )
        shutil.copy2(lua_src / "src/liblua.a", lua_dir / "liblua53.a")
        options += [
            "OSX_BUILD=1",
            "COMPILER=clang",
            "CP=cp",
            "CPP=clang -E -P -x c",
            "USE_APP=0",
            "AS=x86_64-elf-as",
            "OBJCOPY=x86_64-elf-objcopy",
            f"LUA_LIB_DIR={lua_dir}",
        ]
    command = [make, "-C", str(ROOT / "engine")]
    if args.clean:
        subprocess.run(command + ["clean"] + options, check=True)
    subprocess.run(command + [f"-j{args.jobs}"] + options, check=True)


if __name__ == "__main__":
    main()
