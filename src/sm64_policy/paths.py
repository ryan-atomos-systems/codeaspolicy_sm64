"""Resolve repository assets without depending on the caller's working directory."""

import os
from pathlib import Path


def project_root() -> Path:
    override = os.environ.get("SM64_PROJECT_ROOT")
    candidates = [Path(override)] if override else Path(__file__).resolve().parents
    for directory in candidates:
        if (directory / "engine/Makefile").is_file() and (directory / "pyproject.toml").is_file():
            return directory.resolve()
    raise RuntimeError("Cannot find engine/; set SM64_PROJECT_ROOT to the repository root")


ROOT = project_root()
ENGINE = ROOT / "engine"
DEFAULT_LIBRARY = ENGINE / "build/us_pc" / ("sm64.dll" if os.name == "nt" else "sm64")
