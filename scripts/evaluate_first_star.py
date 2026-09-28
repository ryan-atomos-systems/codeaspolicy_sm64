"""Native robustness probes with pose/timing perturbations, not seed diversity.

Run with PYTHONPATH=src python3 scripts/evaluate_first_star.py --output artifacts/NEW.
Normal-start capability is measured separately by the benchmark CLI. These are
explicit curriculum resets; no positions/progress are written after reset.
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sm64_policy import Action, SM64Env, SpawnState
from sm64_policy.first_star import FirstStar
from sm64_policy.storage import write_json
from sm64_policy.tasks import StarTask

CASES = (
    ("normal", None, 0),
    ("wait-45", None, 45),
    ("wait-90", None, 90),
    ("yaw-minus-45", ((-6558, 0, 6464), 16384), 0),
    ("yaw-plus-45", ((-6558, 0, 6464), -32768), 0),
    ("west-100", ((-6658, 0, 6464), 24576), 0),
    ("east-100", ((-6458, 0, 6464), 24576), 0),
    ("north-100", ((-6558, 0, 6364), 24576), 0),
)


def evaluate(case, output):
    name, spawn, wait = case
    directory = output / name
    directory.mkdir()
    result = {"case": name, "spawn": spawn, "wait_frames": wait, "success": False}
    try:
        with SM64Env(workspace=directory / "runtime") as env:
            state = env.reset(spawn_state=SpawnState(*spawn) if spawn else None)
            task, policy = StarTask(FirstStar.goal, state), FirstStar()
            deaths = 0
            with (directory / "actions.jsonl").open("w") as trace:
                for step in range(2400):
                    action = Action() if step < wait else policy.act(state, step)
                    state = env.step(action, 1)
                    deaths += int(state.died)
                    trace.write(
                        json.dumps(
                            {
                                "frame": state.frame,
                                "action": action.to_dict(),
                                "position": state.position,
                                "policy": policy.diagnostics(),
                            }
                        )
                        + "\n"
                    )
                    if task.update(state):
                        break
            env.render().save(directory / "final.png")
            result.update(task.to_dict(), deaths=deaths, steps=state.frame)
    except (OSError, RuntimeError, ValueError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    write_json(directory / "result.json", result)
    print(f"{name}: {'PASS' if result['success'] else 'FAIL'}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda case: evaluate(case, args.output.resolve()), CASES))
    write_json(
        args.output / "summary.json",
        {"cases": results, "successes": sum(r["success"] for r in results), "total": len(results)},
    )
    return int(not all(r["success"] for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
