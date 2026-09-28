"""Validated configurations are the boundary between CLI, scheduler, and worker."""

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EpisodeConfig:
    session_dir: str
    library: str
    policy: str = "explore"
    seed: int = 0
    backend: str = "native"
    engine_mode: str = "fast"
    steps: int = 1800
    frame_skip: int = 4
    port: int = 7777
    record_every: int = 0
    width: int = 128
    height: int = 72
    level: int = 9
    spawn_state: dict | None = None
    observation_mode: str = "oracle"
    gameplay_mode: str = "scaffold"
    trace_mode: str = "full"
    game_seed: int | None = None

    def __post_init__(self) -> None:
        if self.game_seed is not None and (
            type(self.game_seed) is not int or not 0 <= self.game_seed <= 0xFFFFFFFF
        ):
            raise ValueError("game_seed must be None or a uint32 integer")
        if self.trace_mode not in {"full", "compact"}:
            raise ValueError("trace_mode must be full or compact")
        if self.gameplay_mode not in {"scaffold", "progression"}:
            raise ValueError("gameplay_mode must be scaffold or progression")
        if self.observation_mode not in {"oracle", "basic"}:
            raise ValueError("observation_mode must be oracle or basic")
        if self.backend not in {"native", "synthetic"}:
            raise ValueError("backend must be native or synthetic")
        if self.engine_mode not in {"fast", "reference"}:
            raise ValueError("engine_mode must be fast or reference")
        if self.steps < 1 or not 1 <= self.frame_skip <= 120:
            raise ValueError("steps must be positive; frame_skip must be in [1, 120]")
        if self.record_every < 0 or not 1 <= self.width <= 1024 or not 1 <= self.height <= 1024:
            raise ValueError(
                "record_every must be nonnegative; image dimensions must be in [1, 1024]"
            )
        if not 1024 <= self.port <= 65535:
            raise ValueError("port must be in [1024, 65535]")
        if self.level not in set(range(4, 37)) - {25, 32, 35}:
            raise ValueError("Unsupported playable level ID")

    @property
    def directory(self) -> Path:
        return Path(self.session_dir)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SuiteConfig:
    output: Path
    library: Path
    policies: tuple[str, ...] = ("noop", "random", "explore")
    seeds: tuple[int, ...] = (0, 1, 2, 3)
    workers: int = 4
    timeout: int = 300
    backend: str = "native"
    engine_mode: str = "fast"
    steps: int = 1800
    frame_skip: int = 4
    record_every: int = 0
    width: int = 128
    height: int = 72
    observation_mode: str = "oracle"
    gameplay_mode: str = "scaffold"
    level: int = 9
    trace_mode: str = "full"
    game_seeds: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if self.workers < 1 or self.timeout < 1 or not self.policies or not self.seeds:
            raise ValueError("workers, timeout, policies, and seeds must be nonempty/positive")
        if self.game_seeds is not None:
            if len(self.game_seeds) != len(self.seeds):
                raise ValueError("game_seeds must pair one-to-one with Python seeds")
            if any(
                type(seed) is not int or not 0 <= seed <= 0xFFFFFFFF for seed in self.game_seeds
            ):
                raise ValueError("game_seeds must contain uint32 integers")
        self.episode(self.output, 7777, self.policies[0], self.seeds[0])

    def episode(
        self, directory: Path, port: int, policy: str, seed: int, game_seed: int | None = None
    ) -> EpisodeConfig:
        return EpisodeConfig(
            str(directory),
            str(self.library),
            policy,
            seed,
            self.backend,
            self.engine_mode,
            self.steps,
            self.frame_skip,
            port,
            self.record_every,
            self.width,
            self.height,
            observation_mode=self.observation_mode,
            gameplay_mode=self.gameplay_mode,
            level=self.level,
            trace_mode=self.trace_mode,
            game_seed=game_seed,
        )
