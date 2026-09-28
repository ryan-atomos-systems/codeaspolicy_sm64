"""Small action replays with seed/settings fingerprints and observed-history checks."""

import hashlib
import json
from pathlib import Path

from .api import Action
from .environment import CheckpointMismatch, SM64Env, SpawnState, _mod_digest
from .paths import DEFAULT_LIBRARY
from .storage import OBSERVATION_HASH, observation_hash, write_json


def save_replay(config, initial_hash, trace, path):
    write_json(
        path,
        {
            "format": "sm64-action-replay",
            "version": 2,
            "game_seed_scheme": 1 if config.game_seed is not None else None,
            "python_seed": config.seed,
            "game_seed": config.game_seed,
            "policy": config.policy,
            "library_sha256": hashlib.sha256(Path(config.library).read_bytes()).hexdigest(),
            "mod_sha256": _mod_digest(),
            "settings": {
                key: getattr(config, key)
                for key in (
                    "width",
                    "height",
                    "level",
                    "spawn_state",
                    "engine_mode",
                    "observation_mode",
                    "gameplay_mode",
                )
            },
            "observation_hash_algorithm": OBSERVATION_HASH,
            "initial_observation_sha256": initial_hash,
            "observation_history_sha256": trace.observation_digest.hexdigest(),
            "action_encoding": "stick_x, stick_y, buttons (A=1 B=2 Z=4 Start=8), n_frames",
            "actions": trace.actions,
        },
    )


def replay(path, *, library=DEFAULT_LIBRARY, output=None, record_every=0):
    """Replay controller actions without invoking the policy. Fail on observed drift.

    Rendering is optional. Images stay explicitly unverified until all recorded
    observations match the cumulative digest. This is a linear action replay,
    not a native snapshot or a cross-build determinism guarantee.
    """
    value = json.loads(Path(path).read_text())
    if value.get("format") != "sm64-action-replay" or value.get("version") not in (1, 2):
        raise ValueError("Unsupported action replay")
    if value.get("observation_hash_algorithm") != OBSERVATION_HASH:
        raise ValueError("Unsupported observation hash algorithm")
    if value.get("game_seed_scheme") != (1 if value.get("game_seed") is not None else None):
        raise ValueError("Unsupported game seed scheme")
    library = Path(library)
    if hashlib.sha256(library.read_bytes()).hexdigest() != value["library_sha256"]:
        raise CheckpointMismatch("Replay uses a different engine build")
    if _mod_digest() != value["mod_sha256"]:
        raise CheckpointMismatch("Replay uses a different gameplay mod")
    if type(record_every) is not int or record_every < 0:
        raise ValueError("record_every must be nonnegative")
    if record_every and output is None:
        raise ValueError("Frame recording requires an output directory")
    actions = []
    for item in value["actions"]:
        x, y, buttons, frames = item
        if type(buttons) is not int or not 0 <= buttons <= (7 if value["version"] == 1 else 15):
            raise ValueError("Invalid replay buttons")
        action = Action(
            x, y, bool(buttons & 1), bool(buttons & 2), bool(buttons & 4), start=bool(buttons & 8)
        )
        SM64Env._validate_step(action, frames)
        actions.append((action, frames))
    settings = dict(value["settings"])
    level, spawn = settings.pop("level"), settings.pop("spawn_state")
    output = Path(output) if output is not None else None
    report = {"verified": False, "source": str(Path(path).resolve()), "recorded_frames": 0}
    if output is not None:
        output.mkdir(parents=True, exist_ok=False)
        write_json(output / "replay-result.json", report)
    digest = hashlib.sha256()
    try:
        with SM64Env(
            library=library, checkpoint_history=False, game_seed=value.get("game_seed"), **settings
        ) as env:
            state = env.reset(
                level, SpawnState(tuple(spawn["position"]), spawn.get("yaw", 0)) if spawn else None
            )
            if observation_hash(state) != value["initial_observation_sha256"]:
                raise CheckpointMismatch("Replay initial observation differs")
            if record_every:
                env.render().save(output / "00000000.png")
                report["recorded_frames"] += 1
            for step, (action, frames) in enumerate(actions):
                state = env.step(action, frames)
                digest.update(bytes.fromhex(observation_hash(state)))
                if record_every and ((step + 1) % record_every == 0 or step == len(actions) - 1):
                    env.render().save(output / f"{state.frame:08d}.png")
                    report["recorded_frames"] += 1
            if digest.hexdigest() != value["observation_history_sha256"]:
                raise CheckpointMismatch(
                    "Replay observation history diverged; images are unverified"
                )
            report.update(
                verified=True,
                decisions=len(actions),
                simulated_frames=state.frame,
                observation_history_sha256=digest.hexdigest(),
            )
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if output is not None:
            write_json(output / "replay-result.json", report)
    return report
