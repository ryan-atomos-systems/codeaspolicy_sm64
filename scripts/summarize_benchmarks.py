#!/usr/bin/env python3
"""Write a Markdown comparison of completed native benchmark directories."""

import argparse
import json
import statistics
from datetime import UTC, datetime
from pathlib import Path


def concurrency(sessions):
    events = sorted(
        [(s["started_at"], 1) for s in sessions] + [(s["finished_at"], -1) for s in sessions]
    )
    current = peak = 0
    for _, delta in events:
        current += delta
        peak = max(peak, current)
    return peak


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runs = [json.loads((path / "summary.json").read_text()) for path in args.runs]
    if any(r["backend"] != "native" or r["status"] != "ok" for r in runs):
        parser.error("Only completed native suites can be compared")
    for key in ("steps", "frame_skip", "policies", "seeds", "library_sha256"):
        if any(r[key] != runs[0][key] for r in runs):
            parser.error(f"Suite configurations differ: {key}")
    runs.sort(key=lambda r: r["workers"])
    baseline = runs[0]["aggregate_frames_per_second_including_startup"]
    reference = runs[-1]
    date = datetime.fromtimestamp(min(s["started_at"] for r in runs for s in r["sessions"]), UTC)
    rows = [
        "# Initial native benchmark",
        "",
        f"Measured {date:%Y-%m-%d %H:%M UTC} on {reference['doctor']['platform']}.",
        f"Python {reference['doctor']['python']}; native library; hidden OpenGL rendering at 128 × 72.",
        "",
        f"{sum(r['total_sessions'] for r in runs)} real gameplay sessions completed. Each used a fresh save and process,",
        (
            f"{reference['steps']} decisions × {reference['frame_skip']} frames = "
            f"{reference['steps'] * reference['frame_skip']} simulated frames "
            f"({reference['steps'] * reference['frame_skip'] / 30:g} seconds at 30 Hz)."
        ),
        "",
        "## Parallel throughput",
        "",
        "| Workers | Observed overlap | Sessions | Wall time | Aggregate frames/s | Speedup |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for r in runs:
        fps = r["aggregate_frames_per_second_including_startup"]
        rows.append(
            f"| {r['workers']} | {concurrency(r['sessions'])} | {r['successful_sessions']}/{r['total_sessions']} | "
            f"{r['wall_seconds']:.2f} s | {fps:.1f} | {fps / baseline:.2f}× |"
        )
    rows += [
        "",
        "Each concurrency setting was measured once; these are initial measurements, not confidence intervals.",
        "Aggregate throughput includes startup, neutral warmup, snapshots, trace logging, and worker teardown.",
        "The suites ran sequentially so they did not compete with one another.",
        "",
        "## Policy capability",
        "",
        f"Results below use the highest-concurrency suite ({len(reference['seeds'])} seeds per policy).",
        "",
        "| Policy | Mean visited cells | Range | Mean max displacement | Deaths | Stars gained | Peak coins |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for policy in reference["policies"]:
        sessions = [s for s in reference["sessions"] if s["policy"] == policy]
        cells = [s["visited_xz_cells_400"] for s in sessions]
        rows.append(
            f"| {policy} | {statistics.mean(cells):.2f} | {min(cells)}–{max(cells)} | "
            f"{statistics.mean(s['max_displacement'] for s in sessions):.0f} | "
            f"{sum(s['deaths'] for s in sessions)} | {sum(s['stars_gained'] for s in sessions)} | "
            f"{max(s['peak_coins'] for s in sessions)} |"
        )
    rows += [
        "",
        "Cells are 400-unit XZ bins scoped by level/area; displacement is in game world units.",
    ]
    if all(s["stars_gained"] == 0 and s["peak_coins"] == 0 for s in reference["sessions"]):
        rows += [
            "No baseline collected a star or coin. These policies do not yet solve a game objective."
        ]
    rows += [
        "",
        "## Limits and provenance",
        "",
        "- Upstream's mod enters Bob-omb Battlefield, suppresses dialogue, and auto-respawns on death.",
        "- Fresh-save startup skips the castle intro. Startup rejects the wrong level or a stuck intro action.",
        "- Policy seeds are controlled; native-engine deterministic replay has not been established.",
        "- There is no ending detector; game completion remains unknown, not a reported success.",
        "- Initial smoke runs 001/002 were rejected after finding an intro-cutscene stall; they are excluded here.",
        "- Synthetic fixture runs are also excluded.",
        "",
        f"Upstream commit: `{reference['git_commit']}`.",
        f"Native library SHA-256: `{reference['library_sha256']}`.",
        "",
        "Raw results are in the local, Git-ignored `artifacts/baseline-*` directories:",
        "`summary.json`, `manifest.json`, and per-session configurations, logs, traces, metrics, and PPM images.",
        "See [CODE_POLICY.md](CODE_POLICY.md) for build/run commands and the policy interface.",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(rows) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
