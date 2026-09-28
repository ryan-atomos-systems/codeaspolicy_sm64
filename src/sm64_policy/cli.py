"""CLI boundary: parse input, dispatch, and report exit status."""

import argparse
import json
import sys
from pathlib import Path

from .config import EpisodeConfig, SuiteConfig
from .diagnostics import doctor
from .paths import DEFAULT_LIBRARY, ROOT
from .storage import read_json


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Must be positive")
    return number


def parser():
    cli = argparse.ArgumentParser(
        description="SM64 code policies, benchmarks, and rollout playback"
    )
    commands = cli.add_subparsers(dest="command", required=True)
    check = commands.add_parser("doctor", help="Check native prerequisites")
    check.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    run = commands.add_parser("benchmark", help="Run isolated policy episodes")
    run.add_argument("--backend", choices=["native", "synthetic"], default="native")
    run.add_argument("--engine-mode", choices=["fast", "reference"], default="fast")
    run.add_argument("--gameplay-mode", choices=["scaffold", "progression"], default="scaffold")
    run.add_argument("--level", type=int, default=9, help="Starting level ID; 16 is castle grounds")
    run.add_argument(
        "--observation-mode",
        choices=["oracle", "basic"],
        default="oracle",
        help="Oracle adds Mario, camera, local geometry, objects, and progress",
    )
    run.add_argument("--policies", nargs="+", default=["noop", "random", "explore"])
    run.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3])
    run.add_argument(
        "--game-seeds",
        nargs="+",
        type=int,
        help="Native uint32 seeds, paired one-to-one with --seeds; omitted keeps legacy startup",
    )
    run.add_argument("--workers", type=positive, default=4)
    run.add_argument(
        "--trace-mode",
        choices=["full", "compact"],
        default="full",
        help="Compact saves actions, flat telemetry, and full-state hashes; omits oracle dumps/diagnostics",
    )
    run.add_argument("--steps", type=positive, default=1800)
    run.add_argument("--frame-skip", type=positive, default=4)
    run.add_argument("--timeout", type=positive, default=300)
    run.add_argument(
        "--record-every",
        type=int,
        default=0,
        help="Capture every N decisions; 0 saves endpoints only",
    )
    run.add_argument("--width", type=positive, default=128)
    run.add_argument("--height", type=positive, default=72)
    run.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    run.add_argument("--output", type=Path, required=True)
    dashboard = commands.add_parser("dashboard", help="Serve the local rollout explorer")
    dashboard.add_argument("--artifacts", type=Path, default=ROOT / "artifacts")
    dashboard.add_argument("--port", type=int, default=8765)
    worker = commands.add_parser("_worker", help=argparse.SUPPRESS)
    worker.add_argument("config", type=Path)
    replay = commands.add_parser(
        "replay", help="Verify an action replay and optionally render images"
    )
    replay.add_argument("path", type=Path)
    replay.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    replay.add_argument("--output", type=Path)
    replay.add_argument("--record-every", type=int, default=0)
    return cli


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    try:
        if args.command == "doctor":
            result = doctor(args.library)
            print(json.dumps(result, indent=2))
            return int(bool(result["blockers"]))
        if args.command == "dashboard":
            from .dashboard.server import serve

            serve(args.artifacts.resolve(), args.port)
            return 0
        if args.command == "_worker":
            from .episode import run_episode

            run_episode(EpisodeConfig(**read_json(args.config)))
            return 0
        if args.command == "replay":
            from .replay import replay

            print(
                json.dumps(
                    replay(
                        args.path,
                        library=args.library,
                        output=args.output,
                        record_every=args.record_every,
                    ),
                    indent=2,
                )
            )
            return 0
        from .suite import run_suite

        values = vars(args).copy()
        values.pop("command")
        values.update(
            output=args.output.resolve(),
            library=args.library.resolve(),
            policies=tuple(args.policies),
            seeds=tuple(args.seeds),
        )
        summary = run_suite(SuiteConfig(**values))
        print(f"{summary['status']}: {args.output.resolve() / 'summary.json'}")
        return 0 if summary["status"] == "ok" else 1
    except (ValueError, FileExistsError) as exc:
        cli.error(str(exc))
    except KeyboardInterrupt:
        print("Cancelled; worker processes stopped.", file=sys.stderr)
        return 130
