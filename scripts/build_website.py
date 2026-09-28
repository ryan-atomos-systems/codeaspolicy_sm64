"""Export a self-contained GitHub Pages site from the verified campaign.

Python uses only the standard library. FFmpeg is needed once to encode the MP4.
The output stays in ignored artifacts/: no raw trace, ROM, save, or engine binary
is copied. Rebuilding reuses a video with the same recording identity.
"""

import argparse
import hashlib
import html
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "website"
FIRST, LAST = 1437, 1491


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, separators=(",", ":")) + "\n")


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def export_code(output):
    paths = sorted((ROOT / "src/sm64_policy").rglob("*.py"))
    with zipfile.ZipFile(output / "policy-source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, path.relative_to(ROOT))
        archive.writestr(
            "README.txt",
            "Selected Python source for the SM64 Policy Lab experiment.\n"
            "This archive excludes the native engine and game assets.\n"
            "It is a source supplement, not a standalone game distribution.\n",
        )
    parts = []
    for anchor, name in (
        ("campaign", "campaign/policy.py"),
        ("control", "control.py"),
        ("bowser", "campaign/fight.py"),
        ("verification", "tasks.py"),
    ):
        source = (ROOT / "src/sm64_policy" / name).read_text()
        parts.append(
            f'<section id="{anchor}"><h2>{html.escape(name)}</h2>'
            f'<pre class="source-code"><code>{html.escape(source)}</code></pre></section>'
        )
    (output / "code.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Policy source · SM64 Policy Lab</title><link rel="stylesheet" href="style.css">'
        '</head><body><main class="source-page"><a href="index.html">← Project page</a>'
        "<h1>Policy source</h1><p>The campaign controller, shared movement skills, "
        "Bowser controller, and independent success check.</p><p>"
        '<a class="button" href="policy-source.zip" download>Download Python source</a></p>'
        '<p class="figure-caption">This source supplement excludes the native engine and game assets. '
        "The code below is copied from the local implementation at export time.</p>"
        '<nav aria-label="Source files"><a href="#campaign">Campaign</a> · '
        '<a href="#control">Movement</a> · <a href="#bowser">Bowser</a> · '
        '<a href="#verification">Success check</a></nav>'
        + "".join(parts)
        + "</main></body></html>\n"
    )


def export_excerpt(session, output):
    records, previous = [], None
    with (session / "trace.jsonl").open() as stream:
        for line in stream:
            record = json.loads(line)
            if record["frame"] == FIRST - 1:
                previous = record["observation"]
            if FIRST <= record["frame"] <= LAST:
                records.append(record)
            if record["frame"] >= LAST:
                break
    if previous is None or [r["frame"] for r in records] != list(range(FIRST, LAST + 1)):
        raise ValueError("The expected consecutive oracle decisions are missing")
    for record in records:
        if record.get("policy", {}).get("decision", {}).get("input_frame") != record["frame"] - 1:
            raise ValueError("Decision timing metadata does not match the preceding frame")
    write_json(
        output / "media/decision.json", {"initial_observation": previous, "records": records}
    )
    for frame in range((FIRST - 1) // 3 * 3, LAST + 1, 3):
        name = f"{frame:08d}.png"
        copy(session / "frames" / name, output / "media/decision" / name)


def export_video(session, result, output):
    video = output / "media/campaign.mp4"
    cache = output / "media/video-identity.json"
    identity = {
        "trace_sha256": result["trace_sha256"],
        "recorded_frames": result["recorded_frames"],
        "fps": 10,
        "encoding": "h264-crf24-v1",
    }
    if video.exists() and cache.exists() and read_json(cache) == identity:
        print("Reusing the encoded campaign video", flush=True)
        return
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg is required to encode the recording; install it before exporting"
        )
    print("Encoding the complete campaign at the recorded 10 images/s…", flush=True)
    temporary = output / "media/campaign.encoding.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-framerate",
            "10",
            "-pattern_type",
            "glob",
            "-i",
            str(session / "frames/*.png"),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "24",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(temporary),
        ],
        check=True,
    )
    temporary.replace(video)
    write_json(cache, identity)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/project-site")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error(
            "Export inside artifacts/ so generated media stays out of the source repository"
        )
    session = ROOT / "artifacts/first-bowser-debug-01/session-000"
    result = read_json(session / "result.json")
    if not (
        result["task"]["success"]
        and result["task"]["success_frame"] == 26540
        and result["task"]["earned_stars"] == 8
    ):
        raise ValueError("The publication requires the verified first-Bowser recording")
    output.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "style.css", "site.js", "favicon.svg", "LICENSE.md"):
        copy(SOURCE / name, output / name)
    (output / ".nojekyll").touch()
    copy(SOURCE / "github-pages.yml", output / ".github/workflows/pages.yml")
    copy(ROOT / "scripts/preview_website.py", output / "preview.py")
    copy(ROOT / "docs/publication/paper.tex", output / "paper.tex")
    copy(SOURCE / "evidence.md", output / "evidence.md")
    viewer = ROOT / "src/sm64_policy/dashboard/static"
    for name in ("state-view.js", "debug-model.js"):
        copy(viewer / name, output / "viewer" / name)
    for path in (viewer / "vendor").iterdir():
        if path.is_file():
            copy(path, output / "viewer/vendor" / path.name)
    copy(session / "frames/00026568.png", output / "media/poster.png")
    export_excerpt(session, output)
    export_video(session, result, output)
    export_code(output)
    safe_fields = (
        "policy",
        "backend",
        "gameplay_mode",
        "observation_mode",
        "steps",
        "simulated_frames",
        "loop_seconds",
        "recorded_frames",
        "task",
        "termination",
        "deaths",
        "minimum_health",
        "game_beaten",
        "trace_sha256",
    )
    original = read_json(ROOT / "artifacts/first-bowser-attempt-03/session-000/result.json")
    write_json(
        output / "evidence.json",
        {
            "run": "first-bowser-debug-01",
            "session": "session-000",
            "result": {key: result[key] for key in safe_fields},
            "original_successful_run": {key: original[key] for key in safe_fields},
            "episode_wall_seconds": {
                "original": original["finished_at"] - original["started_at"],
                "instrumented": result["finished_at"] - result["started_at"],
            },
            "video": {
                "fps": 10,
                "note": "Sparse frames presented at 10 images/s; final endpoint quantized to the video cadence.",
            },
            "decision_excerpt": {
                "first_outcome": FIRST,
                "last_outcome": LAST,
                "initial_input": FIRST - 1,
            },
        },
    )
    (output / "README.md").write_text(
        "# SM64 Policy Lab project page\n\n"
        "This directory is a standalone static website. Copy its contents, including "
        ".nojekyll and .github, to a GitHub repository you own.\n\n"
        "In Settings → Pages, select GitHub Actions. Run the Deploy project page "
        "workflow manually from the Actions tab. It publishes this folder as the "
        "site root. Alternatively, use Pages' Deploy from a branch option with "
        "main and /(root). No build step, ROM, server API, or secret is required.\n\n"
        "Preview locally: python3 preview.py\n"
        "This loopback-only helper supports byte-range video seeking.\n\n"
        "The included video is a continuous recording. The small decision excerpt "
        "powers the 3D viewer without executing the game or policy.\n"
    )
    # Hash every exported asset, excluding the manifest itself. This is separate
    # from experiment provenance: assets may be regenerated after a copy edit.
    hashes = {
        str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.rglob("*"))
        if p.is_file() and p.name != "site-manifest.json"
    }
    write_json(output / "site-manifest.json", {"files": hashes})
    bundle = shutil.make_archive(str(output) + "-github-pages", "zip", output)
    total = sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
    print(f"Exported {output} ({total / 1024**2:.1f} MiB)")
    print(f"GitHub Pages bundle: {bundle}")


if __name__ == "__main__":
    main()
