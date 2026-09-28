"""Public process-isolated environment API and verified replay checkpoints."""

import hashlib
import json
import math
import multiprocessing as mp
import socket
import tempfile
import time
import traceback
from dataclasses import asdict, dataclass
from enum import IntEnum
from pathlib import Path

from .api import Action, Observation
from .config import EpisodeConfig
from .native import Native
from .paths import DEFAULT_LIBRARY, ENGINE
from .storage import read_json, write_json


class Level(IntEnum):
    BBH = 4
    CCM = 5
    CASTLE = 6
    HMC = 7
    SSL = 8
    BOB = 9
    SL = 10
    WDW = 11
    JRB = 12
    THI = 13
    TTC = 14
    RR = 15
    CASTLE_GROUNDS = 16
    BITDW = 17
    VCUTM = 18
    BITFS = 19
    SA = 20
    BITS = 21
    LLL = 22
    DDD = 23
    WF = 24
    CASTLE_COURTYARD = 26
    PSS = 27
    COTMC = 28
    TOTWC = 29
    BOWSER_1 = 30
    WMOTR = 31
    BOWSER_2 = 33
    BOWSER_3 = 34
    TTM = 36


@dataclass(frozen=True, slots=True)
class SpawnState:
    position: tuple[float, float, float]
    yaw: int = 0

    def __post_init__(self):
        if len(self.position) != 3 or not all(math.isfinite(v) for v in self.position):
            raise ValueError("position must contain three finite coordinates")
        if type(self.yaw) is not int or not -32768 <= self.yaw <= 32767:
            raise ValueError("yaw must be a signed 16-bit SM64 angle")


@dataclass(frozen=True, slots=True)
class RGBFrame:
    width: int
    height: int
    rgb: bytes
    frame: int | None = None

    def save(self, path: str | Path) -> None:
        from .recording import encode_png

        Path(path).write_bytes(encode_png(self.width, self.height, self.rgb))


class CheckpointMismatch(RuntimeError):
    """A replay diverged from its recorded state history; restoration is rejected."""


def _mod_digest() -> str:
    digest = hashlib.sha256()
    root = ENGINE / "mods/compass"
    for path in sorted(root.rglob("*.lua")):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _engine_worker(connection, config: EpisodeConfig):
    """Only this process loads the native library. No untrusted RPC endpoints."""
    try:
        env = Native(config)
        connection.send((True, env.observe()))
        while True:
            command, payload = connection.recv()
            if command == "close":
                break
            try:
                if command == "step":
                    action, frames, capture = payload
                    value = env.step(action, frames, capture=capture)
                elif command == "render":
                    value = RGBFrame(*env.render(), frame=env.frame)
                elif command == "pixels":
                    value = RGBFrame(*env.pixels(), frame=env.frame)
                else:
                    raise ValueError(f"Unknown command {command}")
                connection.send((True, value))
            except Exception:  # noqa: BLE001 — forward worker errors across the process boundary
                connection.send((False, traceback.format_exc()))
    except EOFError:
        pass
    except Exception:  # noqa: BLE001 — report startup failures to the owner
        connection.send((False, traceback.format_exc()))
    finally:
        connection.close()


class SM64Env:
    """reset / step / get_state / save_state / load_state / render.

    Checkpoints store actions and verify observation-history replay; they are not
    native memory snapshots. Use as a context manager and protect script entry
    with ``if __name__ == '__main__'`` for multiprocessing spawn.
    """

    def __init__(
        self,
        *,
        library: str | Path = DEFAULT_LIBRARY,
        width: int = 128,
        height: int = 72,
        engine_mode: str = "fast",
        observation_mode: str = "oracle",
        gameplay_mode: str = "scaffold",
        timeout: float = 30,
        workspace: str | Path | None = None,
        checkpoint_history: bool = True,
        game_seed: int | None = None,
    ):
        self.library = Path(library).resolve()
        if game_seed is not None and (
            type(game_seed) is not int or not 0 <= game_seed <= 0xFFFFFFFF
        ):
            raise ValueError("game_seed must be None or a uint32 integer")
        self.game_seed = game_seed
        if type(checkpoint_history) is not bool:
            raise ValueError("checkpoint_history must be bool")
        self.checkpoint_history = checkpoint_history
        self._pending = None
        self._deadline = None
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        self.width, self.height = width, height
        self.engine_mode, self.timeout = engine_mode, timeout
        if observation_mode not in {"oracle", "basic"}:
            raise ValueError("observation_mode must be oracle or basic")
        self.observation_mode = observation_mode
        if gameplay_mode not in {"scaffold", "progression"}:
            raise ValueError("gameplay_mode must be scaffold or progression")
        self.gameplay_mode = gameplay_mode
        self._temporary = tempfile.TemporaryDirectory(prefix="sm64-") if workspace is None else None
        self.workspace = Path(self._temporary.name if self._temporary else workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._process = self._connection = self._state = None
        self._history = []
        self._digest = hashlib.sha256()
        self._closed = False

    def reset(
        self, level: Level | int = Level.BOB, spawn_state: SpawnState | None = None
    ) -> Observation:
        self.reset_async(level, spawn_state)
        return self.reset_wait()

    def reset_async(
        self, level: Level | int = Level.BOB, spawn_state: SpawnState | None = None
    ) -> None:
        """Start a fresh process; collect its initial observation with reset_wait()."""
        if self._closed:
            raise RuntimeError("Environment is closed")
        level = Level(level)
        if spawn_state is not None and not isinstance(spawn_state, SpawnState):
            raise TypeError("spawn_state must be SpawnState or None")
        self._stop()
        self._level, self._spawn = level, spawn_state
        self._history, self._digest = [], hashlib.sha256()
        directory = Path(tempfile.mkdtemp(prefix="episode-", dir=self.workspace))
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.port = port
        config = EpisodeConfig(
            str(directory),
            str(self.library),
            port=port,
            engine_mode=self.engine_mode,
            width=self.width,
            height=self.height,
            level=int(level),
            spawn_state=asdict(spawn_state) if spawn_state else None,
            observation_mode=self.observation_mode,
            gameplay_mode=self.gameplay_mode,
            game_seed=self.game_seed,
        )
        context = mp.get_context("spawn")
        self._connection, child = context.Pipe()
        self._process = context.Process(target=_engine_worker, args=(child, config), daemon=True)
        try:
            self._process.start()
        except Exception:
            child.close()
            self._connection.close()
            self._process = self._connection = None
            raise
        child.close()
        self._pending = ("reset", None)
        self._deadline = time.monotonic() + self.timeout

    def reset_wait(self) -> Observation:
        if self._pending is None or self._pending[0] != "reset":
            raise RuntimeError("No reset is pending")
        self._state = self._receive()
        self._pending = None
        if self.checkpoint_history:
            self._hash_state()
        return self._state

    def step(self, action: Action, n_frames: int = 4) -> Observation:
        return self._step(action, n_frames, capture=False)

    @staticmethod
    def _validate_step(action, n_frames):
        if not isinstance(action, Action):
            raise TypeError("action must be an Action")
        if type(n_frames) is not int or not 1 <= n_frames <= 120:
            raise ValueError("n_frames must be an integer in [1, 120]")

    def _idle(self):
        if self._pending is not None:
            raise RuntimeError("An environment operation is pending; wait for it first")

    def step_async(self, action: Action, n_frames: int = 4) -> None:
        """Dispatch without waiting. Only one operation may be pending per engine."""
        self._send_step(action, n_frames, capture=False)

    def _send_step(self, action, n_frames, *, capture):
        self._idle()
        self.get_state()
        self._validate_step(action, n_frames)
        try:
            self._connection.send(("step", (action, n_frames, capture)))
        except OSError as exc:
            self._stop()
            raise RuntimeError("Native worker exited before accepting the step") from exc
        self._pending = ("step", (action, n_frames, capture))
        self._deadline = time.monotonic() + self.timeout

    def step_wait(self) -> Observation:
        if self._pending is None or self._pending[0] != "step":
            raise RuntimeError("No step is pending")
        action, n_frames, capture = self._pending[1]
        self._state = self._receive()
        self._pending = None
        if self.checkpoint_history:
            self._history.append(
                {"action": action.to_dict(), "n_frames": n_frames, "capture": capture}
            )
            self._hash_state()
        return self._state

    def _step(self, action: Action, n_frames: int, *, capture: bool) -> Observation:
        self._send_step(action, n_frames, capture=capture)
        return self.step_wait()

    def get_state(self) -> Observation:
        if self._state is None:
            raise RuntimeError("Call reset() before using the environment")
        return self._state

    def render(self) -> RGBFrame:
        self._idle()
        self.get_state()
        self._connection.send(("render", None))
        self._deadline = time.monotonic() + self.timeout
        return self._receive()

    def _pixels(self) -> RGBFrame:
        self._idle()
        self.get_state()
        self._connection.send(("pixels", None))
        self._deadline = time.monotonic() + self.timeout
        return self._receive()

    def _hash_state(self):
        self._digest.update(json.dumps(self._state.to_dict(), sort_keys=True).encode())

    def save_state(self, path: str | Path | None = None) -> dict:
        self._idle()
        if not self.checkpoint_history:
            raise RuntimeError("Checkpoints require checkpoint_history=True from reset")
        self.get_state()
        checkpoint = {
            "format": "sm64-replay-checkpoint",
            "version": 2,
            "game_seed": self.game_seed,
            "observation_mode": self.observation_mode,
            "gameplay_mode": self.gameplay_mode,
            "level": int(self._level),
            "spawn_state": asdict(self._spawn) if self._spawn else None,
            "width": self.width,
            "height": self.height,
            "engine_mode": self.engine_mode,
            "library_sha256": hashlib.sha256(self.library.read_bytes()).hexdigest(),
            "mod_sha256": _mod_digest(),
            "observation_sha256": self._digest.hexdigest(),
            "history": self._history,
        }
        # JSON roundtrip gives callers an independent, portable value.
        checkpoint = json.loads(json.dumps(checkpoint))
        if path is not None:
            write_json(Path(path), checkpoint)
        return checkpoint

    def load_state(self, checkpoint: dict | str | Path) -> Observation:
        self._idle()
        if not self.checkpoint_history:
            raise RuntimeError("Checkpoints require checkpoint_history=True from reset")
        value = read_json(Path(checkpoint)) if isinstance(checkpoint, (str, Path)) else checkpoint
        if value.get("format") != "sm64-replay-checkpoint" or value.get("version") not in (1, 2):
            raise ValueError("Unsupported checkpoint format")
        if value.get("observation_mode", "basic") != self.observation_mode:
            raise CheckpointMismatch("Checkpoint observation mode differs")
        if value.get("gameplay_mode", "scaffold") != self.gameplay_mode:
            raise CheckpointMismatch("Checkpoint gameplay mode differs")
        if value.get("game_seed") != self.game_seed:
            raise CheckpointMismatch("Checkpoint game seed differs")
        if value["library_sha256"] != hashlib.sha256(self.library.read_bytes()).hexdigest():
            raise CheckpointMismatch("Checkpoint uses a different engine build")
        if value.get("mod_sha256") != _mod_digest():
            raise CheckpointMismatch("Checkpoint uses a different gameplay mod")
        if (value["width"], value["height"], value["engine_mode"]) != (
            self.width,
            self.height,
            self.engine_mode,
        ):
            raise CheckpointMismatch("Checkpoint renderer settings differ")
        spawn = value["spawn_state"]
        self.reset(
            value["level"], SpawnState(tuple(spawn["position"]), spawn["yaw"]) if spawn else None
        )
        for item in value["history"]:
            self._step(Action(**item["action"]), item["n_frames"], capture=item["capture"])
        if self._digest.hexdigest() != value["observation_sha256"]:
            self._stop()
            raise CheckpointMismatch("Replay diverged; restored state was discarded")
        return self.get_state()

    def _receive(self):
        remaining = max(0.0, self._deadline - time.monotonic())
        if not self._connection.poll(remaining):
            self._stop()
            raise TimeoutError("Native worker did not respond before the timeout")
        try:
            success, value = self._connection.recv()
        except (EOFError, OSError) as exc:
            self._stop()
            raise RuntimeError("Native worker exited unexpectedly") from exc
        if not success:
            self._stop()
            raise RuntimeError(value)
        return value

    def _stop(self):
        self._pending = None
        self._deadline = None
        if self._process is not None:
            if self._process.is_alive():
                try:
                    self._connection.send(("close", None))
                except (BrokenPipeError, OSError):
                    pass
            # SDL handles SIGTERM without exiting while its event loop is idle.
            # Let the worker finish normally, then kill a stuck native process.
            self._process.join(timeout=1)
            if self._process.is_alive():
                self._process.kill()
                self._process.join()
            self._process.close()
        if self._connection is not None:
            self._connection.close()
        self._process = self._connection = self._state = None

    def close(self):
        self._stop()
        if self._temporary is not None:
            self._temporary.cleanup()
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
