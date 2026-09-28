"""Fresh-save first-Bowser success/timing statistics over reproducible RNG seeds.

Game seeds change native RNG streams, not arbitrary positions or saved progress.
The policy/engine are frozen for the suite; failed runs remain in the denominator.
"""

import argparse
import json
import math
import random
import secrets
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sm64_policy.config import SuiteConfig
from sm64_policy.paths import DEFAULT_LIBRARY
from sm64_policy.storage import read_json, write_json
from sm64_policy.suite import run_suite


def describe(values):
    if not values:
        return None
    values = sorted(values)

    def percentile(p):
        x = (len(values) - 1) * p
        lo, hi = math.floor(x), math.ceil(x)
        return values[lo] + (values[hi] - values[lo]) * (x - lo)

    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "min": values[0],
        "max": values[-1],
        "p10": percentile(0.1),
        "p90": percentile(0.9),
        "stddev": statistics.pstdev(values),
    }


def summarize(summary, output, experiment_seed):
    sessions = summary["sessions"]
    n = len(sessions)
    successes = [
        r for r in sessions if r.get("status") == "ok" and (r.get("task") or {}).get("success")
    ]
    if not n:
        raise ValueError("No episodes ran; inspect summary blockers")
    k = len(successes)
    z = 1.959963984540054
    fraction = k / n
    denominator = 1 + z * z / n
    center = (fraction + z * z / (2 * n)) / denominator
    margin = z * math.sqrt(fraction * (1 - fraction) / n + z * z / (4 * n * n)) / denominator
    rollouts = [read_json(p) for p in output.glob("session-*/rollout.json")]
    replays = [read_json(p) for p in output.glob("session-*/replay.json")]
    configurations = {str(p.parent): read_json(p) for p in output.glob("session-*/config.json")}
    stats = {
        "experiment_seed": experiment_seed,
        "distribution": "Normal fresh-save castle grounds; unique uniform uint32 game and Python seeds; no spawn/delay perturbations",
        "policy": "first-bowser",
        "game_seed_scheme": 1,
        "episodes": n,
        "successes": k,
        "success_rate": fraction,
        "success_rate_wilson_95_percent": [max(0, center - margin), min(1, center + margin)],
        "execution_statuses": dict(Counter(r["status"] for r in sessions)),
        "termination_reasons": dict(Counter(r.get("termination", r["status"]) for r in sessions)),
        "unique_initial_observations": len({r["initial_observation_sha256"] for r in rollouts}),
        "unique_trace_hashes": len(
            {r.get("trace_sha256") for r in sessions if r.get("trace_sha256")}
        ),
        "unique_observation_histories": len({r["observation_history_sha256"] for r in replays}),
        "replay_bundles": len(replays),
        "recorded_physics_frames_per_second_including_errors": sum(
            sum(a[3] for a in r["actions"]) for r in replays
        )
        / summary["wall_seconds"],
        "completion_game_seconds_successes_only": describe(
            [r["task"]["success_frame"] / 30 for r in successes]
        ),
        "completion_wall_seconds_successes_only": describe(
            [r["task_completion_seconds"] for r in successes]
        ),
        "episode_wall_seconds": describe(
            [r["finished_at"] - r["started_at"] for r in sessions if "finished_at" in r]
        ),
        "suite_wall_seconds": summary["wall_seconds"],
        "aggregate_physics_frames_per_second": summary[
            "aggregate_frames_per_second_including_startup"
        ],
        "failure_progress": [
            {
                "seed": r["seed"],
                "game_seed": configurations.get(r["session_dir"], {}).get(
                    "game_seed", r.get("game_seed")
                ),
                "status": r["status"],
                "termination": r.get("termination"),
                "earned_stars": (r.get("task") or {}).get("earned_stars"),
                "deaths": r.get("deaths"),
                "session_dir": r["session_dir"],
            }
            for r in sessions
            if r not in successes
        ],
        "limits": "Conditional on this RNG distribution, build, normal start, policy, and step budget. Budget failures are censored at the budget and policy errors terminate early; completion-time summaries include successes only. No claim of arbitrary-state robustness or full-game completion.",
    }
    experiment_path = output / "experiment.json"
    experiment = read_json(experiment_path) if experiment_path.exists() else {}
    if experiment.get("seed_suite"):
        stats["distribution"] = (
            "Recorded seed pairs; regression evaluation, not independent unseen seeds"
        )
        stats["seed_suite"] = experiment["seed_suite"]
        stats["selected_indices"] = experiment.get("indices")
    write_json(output / "statistics.json", stats)
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=64)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--steps", type=int, default=36000)
    parser.add_argument("--experiment-seed", type=int)
    parser.add_argument("--seed-suite", type=Path)
    parser.add_argument("--indices", type=int, nargs="+")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("runs must be positive")
    experiment_seed = (
        args.experiment_seed if args.experiment_seed is not None else secrets.randbits(64)
    )
    rng = random.Random(experiment_seed)
    python_seeds = tuple(rng.sample(range(2**32), args.runs))
    game_seeds = tuple(rng.sample(range(2**32), args.runs))
    if args.seed_suite:
        source = read_json(args.seed_suite / "manifest.json")
        indices = (
            args.indices
            if args.indices is not None
            else range(min(args.runs, len(source["seeds"])))
        )
        python_seeds = tuple(source["seeds"][i] for i in indices)
        game_seeds = tuple(source["game_seeds"][i] for i in indices)
        experiment_seed = None
    elif args.indices is not None:
        parser.error("indices requires seed-suite")
    output = args.output.resolve()
    if output.exists():
        parser.error("output must be a new directory")
    config = SuiteConfig(
        output,
        DEFAULT_LIBRARY,
        policies=("first-bowser",),
        seeds=python_seeds,
        game_seeds=game_seeds,
        workers=args.workers,
        steps=args.steps,
        frame_skip=1,
        gameplay_mode="progression",
        level=16,
        trace_mode="compact",
        record_every=0,
        width=480,
        height=270,
        timeout=1800,
    )
    # run_suite creates the output atomically; seed pairs are recorded in its manifest
    # before dispatch. The master seed is saved even if interrupted.
    try:
        summary = run_suite(config)
    finally:
        if output.exists():
            write_json(
                output / "experiment.json",
                {
                    "experiment_seed": experiment_seed,
                    "seed_suite": str(args.seed_suite) if args.seed_suite else None,
                    "indices": args.indices,
                    "python_seeds": python_seeds,
                    "game_seeds": game_seeds,
                    "distribution": "normal fresh-save start; RNG seed diversity",
                },
            )
    stats = summarize(summary, output, experiment_seed)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
