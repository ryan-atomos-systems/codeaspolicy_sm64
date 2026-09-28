"""Verify a controller checkpoint from reset and publish local dashboard artifacts.

The engine build, mod, and entire observation history must match. Playback
samples contain the complete sequence of actions between displayed states;
they are not presented as one held action or reconstructed policy reasoning.
"""

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sm64_policy import Action, CheckpointMismatch, SM64Env
from sm64_policy.completion import SixteenStarCompletion
from sm64_policy.config import EpisodeConfig
from sm64_policy.environment import _mod_digest
from sm64_policy.metrics import EpisodeMetrics
from sm64_policy.paths import DEFAULT_LIBRARY
from sm64_policy.recording import FrameRecorder
from sm64_policy.storage import read_json, write_json


def record(checkpoint, output, library=DEFAULT_LIBRARY, every=10):
    if every < 1:
        raise ValueError("record interval must be positive")
    value = read_json(checkpoint)
    if value.get("format") != "sm64-replay-checkpoint" or value.get("version") != 2:
        raise ValueError("Expected a version 2 replay checkpoint")
    if (
        value["spawn_state"] is not None
        or value["level"] != 16
        or value["gameplay_mode"] != "progression"
    ):
        raise ValueError("Completion recording requires the normal fresh-save castle start")
    if hashlib.sha256(library.read_bytes()).hexdigest() != value["library_sha256"]:
        raise CheckpointMismatch("Checkpoint uses a different engine build")
    if _mod_digest() != value["mod_sha256"]:
        raise CheckpointMismatch("Checkpoint uses a different gameplay mod")
    output.mkdir(parents=True, exist_ok=False)
    session = output / "session-000"
    session.mkdir()
    shutil.copyfile(checkpoint, session / "checkpoint.json")
    total = sum(item["n_frames"] for item in value["history"])
    config = EpisodeConfig(
        str(session),
        str(library),
        policy="16-star development trajectory",
        steps=total,
        frame_skip=1,
        record_every=every,
        **{
            key: value[key]
            for key in (
                "width",
                "height",
                "level",
                "observation_mode",
                "gameplay_mode",
                "engine_mode",
                "game_seed",
            )
        },
    )
    write_json(session / "config.json", config.to_dict())
    write_json(
        output / "manifest.json", {**config.to_dict(), "workers": 1, "policies": [config.policy]}
    )
    result = {
        "status": "running",
        "verified": False,
        "autonomous_policy_validation": False,
        "source_checkpoint": str(checkpoint.resolve()),
        "source_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
    }
    write_json(session / "result.json", result)
    start = time.monotonic()
    recorder = None
    try:
        with SM64Env(
            library=library,
            **{
                key: value[key]
                for key in (
                    "width",
                    "height",
                    "observation_mode",
                    "gameplay_mode",
                    "engine_mode",
                    "game_seed",
                )
            },
        ) as env:
            state = env.reset(16)
            task, metrics = SixteenStarCompletion(state), EpisodeMetrics(state)
            recorder = FrameRecorder(session, config, state)
            recorder.capture(env, 0, render=True)
            pending = []
            with (session / "trace.jsonl").open("w", buffering=1024 * 1024) as trace:
                for index, item in enumerate(value["history"]):
                    action = Action(**item["action"])
                    state = env._step(action, item["n_frames"], capture=item["capture"])
                    task.update(state)
                    metrics.update(state)
                    pending.append({"action": action.to_dict(), "n_frames": item["n_frames"]})
                    if (index + 1) % every == 0 or index == len(value["history"]) - 1:
                        row = {
                            "step": index,
                            "frame": state.frame,
                            "action": action.to_dict(),
                            "action_sequence": pending,
                            "observation": state.to_dict(),
                            "policy": {
                                "phase": "Recorded controller sequence",
                                "provenance": "development trajectory replay; no policy reasoning reconstructed",
                            },
                        }
                        trace.write(json.dumps(row, separators=(",", ":")) + "\n")
                        pending = []
                        recorder.capture(env, state.frame, render=True)
                    if index % 5000 == 0:
                        print(
                            f"{state.frame}/{total} frames · {state.stars} stars · level {state.level}",
                            flush=True,
                        )
            actual_digest = env.save_state()["observation_sha256"]
            if actual_digest != value["observation_sha256"]:
                raise CheckpointMismatch(
                    "Observation history diverged; dashboard images are unverified"
                )
            result.update(
                status="ok",
                verified=True,
                steps=total,
                simulated_frames=state.frame,
                wall_seconds=time.monotonic() - start,
                task=task.to_dict(),
                **metrics.to_dict(),
            )
            result["game_beaten"] = task.success_frame is not None
            result["deaths"] = None
            result["death_count_note"] = (
                "The progression-mode died signal is not a reliable death counter. No death-count claim is made."
            )
            result["observation_history_sha256"] = actual_digest
            recorder.metadata.update(
                events=task.events,
                task=task.to_dict(),
                verified=True,
                provenance="development trajectory; verified action replay, not an autonomous policy evaluation",
            )
    except Exception as exc:
        result.update(status="error", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        if recorder:
            recorder.finish()
        write_json(session / "result.json", result)
        write_json(
            output / "summary.json",
            {
                "status": result["status"],
                "total_sessions": 1,
                "verified": result["verified"],
                "sessions": [result],
            },
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--record-every", type=int, default=10)
    args = parser.parse_args()
    print(
        json.dumps(record(args.checkpoint, args.output, args.library, args.record_every), indent=2)
    )


if __name__ == "__main__":
    main()
