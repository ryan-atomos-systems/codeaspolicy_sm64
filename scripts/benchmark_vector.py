"""Measure batched RL stepping; export validation traces after the timed rollout.

One fresh process/save per lane. No pixels, checkpoint history, trace serialization,
metrics or decision diagnostics in the timed rollout. Report this separately from
end-to-end benchmark suite throughput. Retaining observations costs bounded RAM.
"""

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sm64_policy import SM64VectorEnv
from sm64_policy.diagnostics import source_identity
from sm64_policy.paths import DEFAULT_LIBRARY
from sm64_policy.policies import Random
from sm64_policy.storage import OBSERVATION_HASH, TraceWriter, observation_hash, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-envs", type=int, default=4)
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--frame-skip", type=int, default=1)
    parser.add_argument("--observation-mode", choices=["oracle", "basic"], default="oracle")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.num_envs <= 32 or not 1 <= args.steps <= 10000:
        parser.error("num-envs must be 1..32 and steps 1..10000 (observations retained in RAM)")
    if not 1 <= args.frame_skip <= 120:
        parser.error("frame-skip must be 1..120")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        **vars(args),
        "output": str(output),
        "backend": "native",
        "engine_mode": "fast",
        "gameplay_mode": "scaffold",
        "level": 9,
        "width": 128,
        "height": 72,
        "policy": "random",
        "seeds": list(range(args.num_envs)),
        "trace_mode": "compact",
        "record_every": None,
        "checkpoint_history": False,
        "scope": "BOB RL batch stepping; no images; policy RNG seeds only",
        "timing_scope": "rollout includes policy and retained observations; excludes startup and artifact export",
        "library_sha256": hashlib.sha256(DEFAULT_LIBRARY.read_bytes()).hexdigest(),
        **source_identity(),
    }
    write_json(output / "manifest.json", manifest)
    # Native stdout/stderr from every lane is preserved in the shared worker log.
    stdout, stderr = os.dup(1), os.dup(2)
    began = time.perf_counter()
    try:
        with (output / "worker.log").open("w") as log:
            os.dup2(log.fileno(), 1)
            os.dup2(log.fileno(), 2)
            with SM64VectorEnv(
                args.num_envs, observation_mode=args.observation_mode, workspace=output / "runtime"
            ) as env:
                initial = states = env.reset()
                policies = [Random(seed=i) for i in range(args.num_envs)]
                records = []
                start = time.perf_counter()
                for step in range(args.steps):
                    actions = tuple(
                        policy.act(state, step) for policy, state in zip(policies, states)
                    )
                    states = env.step(actions, args.frame_skip)
                    records.append((actions, states))
                rollout_seconds = time.perf_counter() - start
    finally:
        os.dup2(stdout, 1)
        os.dup2(stderr, 2)
        os.close(stdout)
        os.close(stderr)
    sessions = []
    for lane in range(args.num_envs):
        folder = output / f"session-{lane:03d}"
        folder.mkdir()
        write_json(folder / "config.json", {**manifest, "policy": "random", "seed": lane})
        with TraceWriter(folder / "trace.jsonl", "compact") as trace:
            for step, (actions, states) in enumerate(records):
                trace.append(step, (step + 1) * args.frame_skip, actions[lane], states[lane])
        write_json(
            folder / "rollout.json",
            {
                "schema_version": 3,
                "initial_observation": initial[lane].to_dict(),
                "initial_observation_sha256": observation_hash(initial[lane]),
                "observation_hash_algorithm": OBSERVATION_HASH,
                "trace_mode": "compact",
                "observation_mode": args.observation_mode,
                "observation_timing": "after_recorded_action",
                "frames": [],
                "record_every": 0,
                "game_fps": 30,
                "frame_skip": args.frame_skip,
                "visual_playback": False,
            },
        )
        result = {
            "status": "ok",
            "steps": args.steps,
            "seed": lane,
            "policy": "random",
            "simulated_frames": args.steps * args.frame_skip,
            "trace_sha256": trace.digest.hexdigest(),
            "game_beaten": None,
        }
        write_json(folder / "result.json", result)
        sessions.append(result)
    frames = args.num_envs * args.steps * args.frame_skip
    wall = time.perf_counter() - began
    summary = {
        **manifest,
        "status": "ok",
        "sessions": sessions,
        "total_sessions": args.num_envs,
        "successful_sessions": args.num_envs,
        "rollout_seconds": rollout_seconds,
        "wall_seconds_including_export": wall,
        "aggregate_rollout_frames_per_second": frames / rollout_seconds,
        "aggregate_frames_per_second_including_export": frames / wall,
    }
    write_json(output / "summary.json", summary)
    print(
        f"{frames / rollout_seconds:.1f} aggregate rollout frames/s; "
        f"{rollout_seconds:.3f}s rollout, {wall:.3f}s including startup/export; {output}"
    )


if __name__ == "__main__":
    main()
