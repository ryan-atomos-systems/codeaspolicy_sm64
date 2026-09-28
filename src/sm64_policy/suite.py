"""Bounded worker scheduling. Every episode owns a fresh engine process."""

import hashlib
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .config import EpisodeConfig, SuiteConfig
from .diagnostics import doctor, source_identity
from .paths import ROOT
from .storage import SCHEMA_VERSION, read_json, write_json


class WorkerPool:
    def __init__(self):
        self.processes = set()
        self.lock = threading.Lock()
        self.cancelled = False

    @staticmethod
    def stop(process):
        if process.poll() is None:
            try:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
            except ProcessLookupError:
                pass
            process.wait()

    def cancel(self):
        with self.lock:
            self.cancelled = True
            for process in self.processes:
                self.stop(process)

    def run(self, config: EpisodeConfig, timeout: int) -> dict:
        directory = config.directory
        write_json(directory / "config.json", config.to_dict())
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
        env["SM64_PROJECT_ROOT"] = str(ROOT)
        with (directory / "worker.log").open("w") as log:
            with self.lock:
                if self.cancelled:
                    return self._failure(config, "cancelled", "Suite cancelled")
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "sm64_policy",
                        "_worker",
                        str(directory / "config.json"),
                    ],
                    cwd=ROOT,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=os.name == "posix",
                )
                self.processes.add(process)
            try:
                code = process.wait(timeout=timeout)
                if code == 0 and (directory / "result.json").is_file():
                    return read_json(directory / "result.json") | {"session_dir": str(directory)}
                return self._failure(config, "error", f"Worker exited {code}; see worker.log")
            except subprocess.TimeoutExpired:
                self.stop(process)
                return self._failure(
                    config, "timeout", f"Worker exceeded {timeout}s; see worker.log"
                )
            finally:
                with self.lock:
                    self.processes.discard(process)

    @staticmethod
    def _failure(config, status, error):
        result = {
            "status": status,
            "backend": config.backend,
            "policy": config.policy,
            "seed": config.seed,
            "error": error,
            "session_dir": config.session_dir,
        }
        write_json(config.directory / "result.json", result)
        return result


def _jobs(config):
    jobs, sockets = [], []
    try:
        for policy in config.policies:
            for index, seed in enumerate(config.seeds):
                folder = config.output / f"session-{len(jobs):03d}"
                folder.mkdir()
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(("127.0.0.1", 0))
                sockets.append(sock)
                jobs.append(
                    config.episode(
                        folder,
                        sock.getsockname()[1],
                        policy,
                        seed,
                        config.game_seeds[index] if config.game_seeds else None,
                    )
                )
    finally:
        for sock in sockets:
            sock.close()
    return jobs


def run_suite(config: SuiteConfig) -> dict:
    config.output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "backend": config.backend,
        "engine_mode": config.engine_mode,
        "observation_mode": config.observation_mode if config.backend == "native" else "synthetic",
        "workers": config.workers,
        "steps": config.steps,
        "frame_skip": config.frame_skip,
        "policies": config.policies,
        "seeds": config.seeds,
        "game_seeds": config.game_seeds,
        "game_seed_scheme": 1 if config.game_seeds is not None else None,
        "record_every": config.record_every,
        "trace_mode": config.trace_mode,
        "gameplay_mode": config.gameplay_mode,
        "level": config.level,
        "width": config.width,
        "height": config.height,
        "seed_scope": "Python and native RNG streams; seed scheme 1; replay verification required"
        if config.game_seeds is not None
        else "Python policy only; engine determinism unverified",
        "doctor": doctor(config.library),
        **source_identity(),
        "game_beaten": None,
        "scope": "Progression; fresh save, normal course exits, intro skipped"
        if config.gameplay_mode == "progression"
        else "Scaffold; dialogue suppression, auto-respawn, intro skipped",
        "synthetic_warning": "HARNESS TEST ONLY; NOT GAMEPLAY"
        if config.backend == "synthetic"
        else None,
    }
    if config.library.is_file():
        manifest["library_sha256"] = hashlib.sha256(config.library.read_bytes()).hexdigest()
    write_json(config.output / "manifest.json", manifest)
    if config.backend == "native" and manifest["doctor"]["blockers"]:
        summary = {
            **manifest,
            "status": "blocked",
            "sessions": [],
            "total_sessions": 0,
            "error": "; ".join(manifest["doctor"]["blockers"]),
        }
        write_json(config.output / "summary.json", summary)
        return summary
    jobs = _jobs(config)
    results = {}
    started = time.perf_counter()
    pool = WorkerPool()
    executor = ThreadPoolExecutor(max_workers=config.workers)
    futures = {executor.submit(pool.run, job, config.timeout): i for i, job in enumerate(jobs)}
    try:
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    finally:
        pool.cancel()
        executor.shutdown(wait=True, cancel_futures=True)
    sessions = [results[i] for i in range(len(jobs))]
    elapsed = time.perf_counter() - started
    ok = [r for r in sessions if r["status"] == "ok"]
    summary = {
        **manifest,
        "status": "ok" if len(ok) == len(jobs) else "failed",
        "sessions": sessions,
        "successful_sessions": len(ok),
        "task_successes": sum(bool((r.get("task") or {}).get("success")) for r in sessions),
        "task_sessions": sum(r.get("task") is not None for r in sessions),
        "total_sessions": len(jobs),
        "wall_seconds": elapsed,
        "aggregate_frames_per_second_including_startup": sum(r["simulated_frames"] for r in ok)
        / elapsed,
    }
    write_json(config.output / "summary.json", summary)
    _report(config.output, summary)
    return summary


def _report(directory: Path, summary: dict):
    title = (
        "Synthetic harness test — NOT gameplay"
        if summary["backend"] == "synthetic"
        else "Native policy benchmark"
    )
    lines = [
        f"# {title}",
        "",
        f"{summary['successful_sessions']}/{summary['total_sessions']} sessions completed.",
        f"Mode: {summary['engine_mode']}; record every {summary['record_every']} decisions (0 = endpoints only).",
        "",
        "| Policy | Seed | Status | Steps/s | Cells | Deaths | Stars | Task success |",
        "|---|---:|---|---:|---:|---:|---:|---|",
    ]
    for r in summary["sessions"]:
        lines.append(
            f"| {r['policy']} | {r['seed']} | {r['status']} | {r.get('steps_per_second', 0):.1f} | "
            f"{r.get('visited_xz_cells_400', '—')} | {r.get('deaths', '—')} | {r.get('stars_gained', '—')} | "
            f"{(r.get('task') or {}).get('success', '—')} |"
        )
    lines += ["", "Game completion is unknown. Coverage is not task success."]
    (directory / "report.md").write_text("\n".join(lines) + "\n")
