"""Seeded curriculum probes, explicitly separate from continuous campaigns.

Controller-only after reset. BOB starts on grounds; other tasks reset directly
inside the target course, with optional pose/timing variation for the pipe.
"""

import argparse
import random
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sm64_policy import Action, SM64Env, SpawnState
from sm64_policy.campaign.policy import FirstBowser
from sm64_policy.campaign.stairs import Stairs
from sm64_policy.config import EpisodeConfig
from sm64_policy.diagnostics import source_identity
from sm64_policy.paths import DEFAULT_LIBRARY
from sm64_policy.replay import save_replay
from sm64_policy.storage import TraceWriter, observation_hash, read_json, write_json


def evaluate(case, args):
    index, seed, game_seed = case
    directory = args.output / f"session-{index:03d}"
    directory.mkdir()
    rng = random.Random(seed)
    spawn = (
        SpawnState((5700, 2860, rng.uniform(-60, 60)), rng.randrange(-32768, 32768))
        if args.task == "pipe"
        else None
    )
    level = {"bob": 16, "dark-world": 17, "pipe": 17, "fight": 30}[args.task]
    delay = rng.randrange(args.max_delay + 1)
    config = EpisodeConfig(
        str(directory),
        str(DEFAULT_LIBRARY),
        policy=f"curriculum:{args.task}",
        seed=seed,
        game_seed=game_seed,
        level=level,
        frame_skip=1,
        steps=args.steps,
        trace_mode="compact",
        gameplay_mode="progression",
        spawn_state={"position": spawn.position, "yaw": spawn.yaw} if spawn else None,
    )
    write_json(directory / "config.json", config.to_dict())
    policy = Stairs() if args.task == "pipe" else FirstBowser(seed)
    if args.task == "pipe":
        policy.phase = "pipe"
    result = {
        "seed": seed,
        "game_seed": game_seed,
        "success": False,
        "delay": delay,
        "task": args.task,
        "scope": "curriculum",
        "status": "ok",
    }
    started = time.perf_counter()
    trace = None
    try:
        with SM64Env(
            game_seed=game_seed,
            gameplay_mode="progression",
            checkpoint_history=False,
            workspace=directory / "runtime",
        ) as env:
            s = env.reset(level, spawn)
            initial = observation_hash(s)
            events = []
            previous = None
            with TraceWriter(directory / "trace.jsonl", "compact") as trace:
                for step in range(args.steps):
                    a = (
                        Action()
                        if step < delay
                        else policy.act(s)
                        if args.task == "pipe"
                        else policy.act(s, step)
                    )
                    diag = {
                        "level": s.level,
                        "phase": policy.phase,
                        "skill": getattr(getattr(policy, "skill", None), "phase", None),
                        "waypoint": getattr(getattr(policy, "skill", None), "waypoint", None),
                        "upper": getattr(
                            getattr(getattr(policy, "skill", None), "finish", None), "phase", None
                        ),
                    }
                    if diag != previous:
                        events.append({"frame": s.frame, **diag})
                        previous = diag
                    s = env.step(a, 1)
                    trace.append(step, s.frame, a, s)
                    success = (
                        s.progress.has_star(1, 6)
                        if args.task == "bob"
                        else bool(s.progress.save_flags & 16)
                        if args.task == "fight"
                        else s.level == 30
                    )
                    if success:
                        result["success"] = True
                        break
                    if args.task in ("dark-world", "pipe") and s.level not in (17, 30):
                        break
            result.update(
                frames=s.frame,
                position=s.position,
                level=s.level,
                events=events,
                last_diagnostics=diag,
            )
            env.render().save(directory / "final.png")
    except (OSError, RuntimeError, ValueError) as exc:
        result.update(status="error", error=f"{type(exc).__name__}: {exc}")
        (directory / "worker.log").write_text(traceback.format_exc())
    finally:
        if trace is not None:
            save_replay(config, initial, trace, directory / "replay.json")
    result["wall_seconds"] = time.perf_counter() - started
    write_json(directory / "result.json", result)
    print(f"{directory.name}: {'PASS' if result['success'] else 'FAIL'}", flush=True)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--task", choices=("bob", "dark-world", "pipe", "fight"), required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--runs", type=int, default=64)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--steps", type=int, default=9000)
    p.add_argument("--experiment-seed", type=int, default=20260928)
    p.add_argument("--seed-suite", type=Path)
    p.add_argument("--indices", type=int, nargs="+")
    p.add_argument("--max-delay", type=int, default=0)
    args = p.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    if args.seed_suite:
        m = read_json(args.seed_suite / "manifest.json")
        pairs = (
            m["seeds"]
            if isinstance(m["seeds"][0], list)
            else list(zip(m["seeds"], m["game_seeds"]))
        )
        seeds = [pairs[i] for i in args.indices] if args.indices else pairs[: args.runs]
    else:
        rng = random.Random(args.experiment_seed)
        seeds = list(zip(rng.sample(range(2**32), args.runs), rng.sample(range(2**32), args.runs)))
    write_json(
        args.output / "manifest.json",
        {
            "scope": "curriculum; not continuous campaign",
            "task": args.task,
            "seeds": seeds,
            "max_delay": args.max_delay,
            "steps": args.steps,
            **source_identity(),
        },
    )
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(
            pool.map(
                lambda case: evaluate(case, args), [(i, *pair) for i, pair in enumerate(seeds)]
            )
        )
    summary = {
        "scope": "curriculum",
        "task": args.task,
        "successes": sum(r["success"] for r in results),
        "episodes": len(results),
        "wall_seconds": time.perf_counter() - started,
        "sessions": results,
    }
    write_json(args.output / "summary.json", summary)
    print(f"{summary['successes']}/{len(results)} successes", flush=True)


if __name__ == "__main__":
    main()
