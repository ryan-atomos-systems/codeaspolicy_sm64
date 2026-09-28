"""Measure repeated, end-to-end native rollout throughput and process CPU time."""

import argparse
import json
import os
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, nargs="+", required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.repeats < 1 or any(n < 1 for n in args.workers):
        parser.error("workers and repeats must be positive")
    args.output.mkdir(parents=True, exist_ok=False)
    report = {
        "platform": platform.platform(),
        "python": sys.version,
        "logical_cpus": os.cpu_count(),
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "cpu_scope": "benchmark subprocess and waited descendants; excludes external X server",
        "runs": [],
    }
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    for repeat in range(args.repeats):
        # Reverse alternate sweeps to reduce a consistent thermal/order bias.
        order = args.workers if repeat % 2 == 0 else list(reversed(args.workers))
        for workers in order:
            output = args.output / f"w{workers:02d}-r{repeat + 1}"
            command = [
                sys.executable,
                "-m",
                "sm64_policy",
                "benchmark",
                "--policies",
                "random",
                "--gameplay-mode",
                "scaffold",
                "--level",
                "9",
                "--observation-mode",
                "oracle",
                "--engine-mode",
                "fast",
                "--trace-mode",
                "compact",
                "--steps",
                "20000",
                "--frame-skip",
                "1",
                "--record-every",
                "0",
                "--width",
                "480",
                "--height",
                "270",
                "--timeout",
                "1800",
                "--workers",
                str(workers),
                "--seeds",
                *(["0"] * workers),
                "--game-seeds",
                *(["0"] * workers),
                "--output",
                str(output.resolve()),
            ]
            print(f"START repeat={repeat + 1} workers={workers}", flush=True)
            before = resource.getrusage(resource.RUSAGE_CHILDREN)
            started = time.perf_counter()
            with (args.output / f"{output.name}.log").open("w") as log:
                run = subprocess.run(
                    command, cwd=ROOT, env=env, stdout=log, stderr=log, check=False
                )
            wall = time.perf_counter() - started
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            cpu = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
            summary = json.loads((output / "summary.json").read_text())
            row = {
                "workers": workers,
                "repeat": repeat + 1,
                "directory": output.name,
                "command": command,
                "returncode": run.returncode,
                "wall_seconds": wall,
                "cpu_seconds": cpu,
                "average_cpu_cores": cpu / wall,
                "suite_wall_seconds": summary.get("wall_seconds"),
                "frames": sum(s.get("simulated_frames", 0) for s in summary["sessions"]),
                "task_successes": summary.get("task_successes"),
                "sessions": summary["total_sessions"],
                "session_frames": [s.get("simulated_frames") for s in summary["sessions"]],
                "trace_sha256": [s.get("trace_sha256") for s in summary["sessions"]],
            }
            row["frames_per_second"] = row["frames"] / wall
            report["runs"].append(row)
            (args.output / "scaling.json").write_text(json.dumps(report, indent=2) + "\n")
            print(
                json.dumps(
                    {
                        k: v
                        for k, v in row.items()
                        if k not in {"command", "trace_sha256", "session_frames"}
                    }
                ),
                flush=True,
            )
            if run.returncode or row["session_frames"] != [20000] * workers:
                raise SystemExit("Rollout failed; inspect artifacts before comparing throughput")


if __name__ == "__main__":
    main()
