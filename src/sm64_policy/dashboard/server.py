"""Serve saved artifacts on loopback. No shell execution or arbitrary file serving."""

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from ..storage import read_json
from .traces import TraceCache, debug_events

STATIC = Path(__file__).with_name("static")


class ArtifactStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.traces = TraceCache()

    def path(self, *parts: str) -> Path:
        if any(not re.fullmatch(r"[a-zA-Z0-9_.-]+", part) or part in {".", ".."} for part in parts):
            raise ValueError("Invalid artifact identifier")
        path = self.root.joinpath(*parts).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Artifact is outside the configured directory")
        return path

    def runs(self) -> list[dict]:
        results = []
        for manifest_path in self.root.glob("*/manifest.json"):
            try:
                run = self.path(manifest_path.parent.name)
                data = read_json(self.path(run.name, "manifest.json"))
                summary = (
                    read_json(self.path(run.name, "summary.json"))
                    if (run / "summary.json").exists()
                    else {}
                )
                results.append(
                    {
                        "id": run.name,
                        "backend": data["backend"],
                        "status": summary.get("status", "running"),
                        "workers": data["workers"],
                        "policies": data["policies"],
                        "steps": data["steps"],
                        "record_every": data.get("record_every", 0),
                        "fps": summary.get("aggregate_frames_per_second_including_startup"),
                        "sessions": summary.get("total_sessions", 0),
                        "updated": manifest_path.stat().st_mtime,
                    }
                )
            except (OSError, ValueError, KeyError):
                continue
        return sorted(results, key=lambda r: r["updated"], reverse=True)

    def sessions(self, run: str) -> dict:
        directory = self.path(run)
        manifest = read_json(self.path(run, "manifest.json"))
        sessions = []
        for config_path in sorted(directory.glob("session-*/config.json")):
            config = read_json(self.path(run, config_path.parent.name, "config.json"))
            result_path = self.path(run, config_path.parent.name, "result.json")
            result = read_json(result_path) if result_path.exists() else {"status": "running"}
            sessions.append(
                {
                    **result,
                    "id": config_path.parent.name,
                    "policy": config["policy"],
                    "seed": config["seed"],
                    "steps": result.get("steps", config["steps"]),
                    "record_every": config.get("record_every", 0),
                }
            )
        return {"manifest": manifest, "sessions": sessions}

    def rollout(self, run: str, session: str) -> dict:
        config = read_json(self.path(run, session, "config.json"))
        result = (
            read_json(self.path(run, session, "result.json"))
            if self.path(run, session, "result.json").exists()
            else {}
        )
        metadata = (
            read_json(self.path(run, session, "rollout.json"))
            if self.path(run, session, "rollout.json").exists()
            else {}
        )
        records = self.traces.get(self.path(run, session, "trace.jsonl")).records
        frames = [
            {
                "frame": item["frame"],
                "url": f"/frames/{quote(run)}/{quote(session)}/{Path(item['path']).name}",
            }
            for item in metadata.get("frames", [])
        ]
        return {
            "config": config,
            "result": result,
            "records": records,
            "frames": frames,
            "initial_observation": metadata.get("initial_observation"),
            "visual_playback": metadata.get("visual_playback", False),
            "events": metadata.get("events", []),
            "debug_events": debug_events(records, metadata.get("initial_observation")),
            "task": result.get("task") or metadata.get("task"),
        }

    def states(self, run: str, session: str, start: int, count: int) -> dict:
        metadata_path = self.path(run, session, "rollout.json")
        initial = (
            read_json(metadata_path).get("initial_observation") if metadata_path.exists() else None
        )
        return self.traces.observations(
            self.path(run, session, "trace.jsonl"), initial, start, count
        )


def create_server(root: Path, port: int = 8765) -> ThreadingHTTPServer:
    store = ArtifactStore(root)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            host = self.headers.get("Host", "").split(":")[0]
            if host not in {"localhost", "127.0.0.1"}:
                self.send_error(403)
                return
            url = urlparse(self.path)
            query = parse_qs(url.query)
            try:
                if url.path == "/api/runs":
                    self.json({"runs": store.runs()})
                elif url.path == "/api/sessions":
                    self.json(store.sessions(query["run"][0]))
                elif url.path == "/api/rollout":
                    self.json(store.rollout(query["run"][0], query["session"][0]))
                elif url.path == "/api/states":
                    self.json(
                        store.states(
                            query["run"][0],
                            query["session"][0],
                            int(query["start"][0]),
                            int(query.get("count", ["24"])[0]),
                        )
                    )
                elif url.path.startswith("/frames/"):
                    parts = url.path.split("/")
                    if len(parts) != 5 or not re.fullmatch(r"\d{8}\.png", parts[-1]):
                        raise ValueError("Invalid frame path")
                    path = store.path(parts[2], parts[3], "frames", parts[4])
                    self.send_bytes(path.read_bytes(), "image/png")
                elif url.path in {
                    "/",
                    "/app.js",
                    "/style.css",
                    "/state-view.js",
                    "/decision-view.js",
                    "/oracle-data.js",
                    "/debug-model.js",
                    "/vendor/three.module.min.js",
                    "/vendor/three.core.min.js",
                    "/vendor/OrbitControls.js",
                }:
                    name = "index.html" if url.path == "/" else url.path[1:]
                    mime = (
                        "text/javascript"
                        if name.endswith(".js")
                        else "text/css"
                        if name.endswith(".css")
                        else "text/html"
                    )
                    self.send_bytes((STATIC / name).read_bytes(), mime)
                else:
                    self.json({"error": "Not found"}, 404)
            except (KeyError, ValueError):
                self.json({"error": "Invalid artifact request"}, 400)
            except FileNotFoundError:
                self.json({"error": "Artifact not available yet"}, 404)
            except OSError:
                self.json({"error": "Could not read artifact"}, 500)

        def json(self, value, status=200):
            self.send_bytes(json.dumps(value, allow_nan=False).encode(), "application/json", status)

        def send_bytes(self, data, mime, status=200):
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self'; img-src 'self'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(root: Path, port: int) -> None:
    with create_server(root, port) as server:
        print(f"Rollout dashboard: http://127.0.0.1:{server.server_port}", flush=True)
        server.serve_forever()
