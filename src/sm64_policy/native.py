"""Own one native engine in a disposable worker. Never instantiate two per process."""

import ctypes as ct
import math
import os
import shutil
from pathlib import Path

from .api import Action, Observation
from .config import EpisodeConfig
from .native_abi import GameState, Input
from .native_state import OracleReader
from .paths import ENGINE
from .state import UIState


class Native:
    def __init__(self, config: EpisodeConfig):
        self.config = config
        os.environ["SM64_POLICY_HIDDEN"] = "1"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        self.dll = ct.CDLL(str(Path(config.library).resolve()))
        self._bind()
        self.oracle = OracleReader(self.dll) if config.observation_mode == "oracle" else None
        self.frame, self.last_action_frames = 0, 0
        self._ready = False
        self.inputs = (Input * 1)()
        self.progress = (ct.c_int * 6)()
        self.ui_buffer = (ct.c_int * 7)()
        self.state = None
        self._captured = False
        user_dir = config.directory / "save"
        user_dir.mkdir()
        shutil.copytree(ENGINE / "mods/compass", user_dir / "mods/compass")
        mod = user_dir / "mods/compass/main.lua"
        mod.write_text(
            mod.read_text().replace(
                "gLevelValues.entryLevel = LEVEL_BOB", f"gLevelValues.entryLevel = {config.level}"
            )
        )
        shutil.copytree(ENGINE / "lang", user_dir / "lang")
        if config.gameplay_mode == "progression":
            # Restore normal dialogs, deaths, and course exits. No gameplay hooks.
            mod.write_text(
                "-- name: Policy progression\n"
                f"gLevelValues.entryLevel = {config.level}\n"
                "gLevelValues.disableActs = false\n"
            )
            try:
                self.dll.sm64_policy_set_progression.argtypes = [ct.c_bool]
                self.dll.sm64_policy_set_progression.restype = None
                self.dll.sm64_policy_set_progression(True)
                self.dll.sm64_policy_read_ui.argtypes = [ct.POINTER(ct.c_int)]
                self.dll.sm64_policy_read_ui.restype = None
            except AttributeError as exc:
                raise RuntimeError("Progression mode requires a rebuilt native library") from exc
        self.dll.sm64_policy_configure(config.port)
        if config.game_seed is not None:
            try:
                self.dll.sm64_policy_seed_version.restype = ct.c_int
                if self.dll.sm64_policy_seed_version() != 1:
                    raise RuntimeError("Unsupported native seed scheme")
                self.dll.sm64_policy_set_seed.argtypes = [ct.c_uint32]
                self.dll.sm64_policy_set_seed.restype = None
                self.dll.sm64_policy_set_seed(config.game_seed)
            except AttributeError as exc:
                raise RuntimeError("Game seeding requires a rebuilt native library") from exc
        self.dll.main_func(
            os.fsencode(ENGINE),
            os.fsencode(user_dir),
            True,
            0,
            False,
            False,
            config.width,
            config.height,
            False,
            b"English",
        )
        # Preserve the baseline warmup exactly, independent of recording cadence.
        for step in range(30):
            self.step(Action(), capture=step == 29)
        initial = self.observe()
        if initial.level != config.level or initial.mario_action == 0x04001301:
            raise RuntimeError("Startup failed: wrong level or stuck castle intro")
        if config.spawn_state:
            if self.api_version < 2:
                raise RuntimeError("Custom spawns require ABI v2; run make build")
            self.dll.sm64_policy_spawn(
                *config.spawn_state["position"], config.spawn_state.get("yaw", 0)
            )
        self.frame, self.last_action_frames = 0, 0
        self._ready = True

    def _bind(self) -> None:
        try:
            self.dll.sm64_policy_api_version.restype = ct.c_int
            self.api_version = self.dll.sm64_policy_api_version()
        except AttributeError as exc:
            raise RuntimeError("Missing native policy ABI; run make build") from exc
        if self.api_version not in (1, 2, 3):
            raise RuntimeError(f"Unsupported native ABI {self.api_version}")
        if self.config.observation_mode == "oracle" and self.api_version < 3:
            raise RuntimeError(
                "Oracle observations require ABI v3; run make build or use observation_mode='basic'"
            )
        if self.config.engine_mode == "fast" and self.api_version < 2:
            raise RuntimeError("Fast stepping requires ABI v2; run make build")
        self.dll.max_players_reminder.restype = ct.c_int
        if self.dll.max_players_reminder() != 1:
            raise RuntimeError("Independent episodes require a clean MAX_PLAYERS=1 build")
        self.dll.sm64_policy_configure.argtypes = [ct.c_int]
        self.dll.sm64_policy_configure.restype = None
        self.dll.main_func.argtypes = [
            ct.c_char_p,
            ct.c_char_p,
            ct.c_bool,
            ct.c_int,
            ct.c_bool,
            ct.c_bool,
            ct.c_int,
            ct.c_int,
            ct.c_bool,
            ct.c_char_p,
        ]
        self.dll.main_func.restype = None
        self._set_start = getattr(self.dll, "sm64_policy_set_start", None)
        if self._set_start is not None:
            self._set_start.argtypes = [ct.c_bool]
            self._set_start.restype = None
        self.dll.step_pixels.argtypes = [ct.POINTER(Input), ct.c_int]
        self.dll.step_pixels.restype = ct.POINTER(ct.POINTER(GameState))
        self.dll.sm64_policy_progress.argtypes = [ct.c_int]
        self.dll.sm64_policy_progress.restype = ct.c_int
        if self.api_version >= 2:
            self.dll.sm64_policy_step.argtypes = [ct.POINTER(Input), ct.c_int, ct.c_bool]
            self.dll.sm64_policy_step.restype = ct.POINTER(ct.POINTER(GameState))
            self.dll.sm64_policy_read_progress.argtypes = [ct.POINTER(ct.c_int)]
            self.dll.sm64_policy_read_progress.restype = None
            self.dll.sm64_policy_render.argtypes = []
            self.dll.sm64_policy_render.restype = ct.POINTER(GameState)
            self.dll.sm64_policy_free_image.argtypes = [ct.POINTER(GameState)]
            self.dll.sm64_policy_free_image.restype = None
            self.dll.sm64_policy_spawn.argtypes = [ct.c_float, ct.c_float, ct.c_float, ct.c_int]
            self.dll.sm64_policy_spawn.restype = None

    def observe(self) -> Observation:
        if self.state is None:
            raise RuntimeError("Engine has not produced a state")
        state = self.state
        if self.api_version >= 2:
            self.dll.sm64_policy_read_progress(self.progress)
            progress = self.progress
        else:
            progress = [self.dll.sm64_policy_progress(i) for i in range(6)]
        ui = None
        if self.config.gameplay_mode == "progression" and self._ready:
            self.dll.sm64_policy_read_ui(self.ui_buffer)
            ui = UIState(*self.ui_buffer[:4], bool(self.ui_buffer[4]), *self.ui_buffer[5:])
        return Observation(
            (state.x, state.y, state.z),
            (state.vx, state.vy, state.vz),
            state.health,
            bool(state.died),
            state.height_above_ground,
            *progress,
            frame=self.frame,
            last_action_frames=self.last_action_frames,
            ui=ui,
            **(
                self.oracle.read(
                    (state.x, state.y, state.z),
                    (state.vx, state.vy, state.vz),
                    self.config.width,
                    self.config.height,
                )
                if self.oracle is not None and self._ready
                else {}
            ),
        )

    def step(
        self, action: Action, n_frames: int | None = None, *, capture: bool = False
    ) -> Observation:
        frames = self.config.frame_skip if n_frames is None else n_frames
        if type(frames) is not int or not 1 <= frames <= 120:
            raise ValueError("n_frames must be an integer in [1, 120]")
        if self._set_start is not None:
            self._set_start(action.start)
        elif action.start:
            raise RuntimeError("Start input requires a rebuilt native library")
        value = self.inputs[0]
        value.stick_x, value.stick_y = action.stick_x, action.stick_y
        value.buttons[:] = (action.a, action.b, action.z)
        if self.config.engine_mode == "fast":
            states = self.dll.sm64_policy_step(self.inputs, frames, capture)
        else:
            states = self.dll.step_pixels(self.inputs, frames)
        if not states or not states[0]:
            raise RuntimeError("Native step returned a null state")
        self.state = states[0].contents
        self.frame += frames
        self.last_action_frames = frames
        self._captured = capture or self.config.engine_mode == "reference"
        observation = self.observe()
        if not all(math.isfinite(v) for v in (*observation.position, *observation.velocity)):
            raise RuntimeError("Non-finite native state")
        return observation

    def pixels(self) -> tuple[int, int, bytes]:
        if not self._captured:
            raise RuntimeError("Pixels were not requested for the latest step")
        return self._copy_pixels(self.state)

    def render(self) -> tuple[int, int, bytes]:
        if self.api_version < 2:
            return self.pixels()
        image = self.dll.sm64_policy_render()
        if not image:
            raise RuntimeError("Native render returned null")
        try:
            return self._copy_pixels(image.contents)
        finally:
            self.dll.sm64_policy_free_image(image)

    def _copy_pixels(self, state) -> tuple[int, int, bytes]:
        if not state.pixels or (state.width, state.height) != (
            self.config.width,
            self.config.height,
        ):
            raise RuntimeError("Invalid native pixel buffer dimensions")
        stride = state.width * 3
        data = ct.string_at(state.pixels, stride * state.height)
        rgb = b"".join(data[y : y + stride] for y in range(len(data) - stride, -1, -stride))
        return state.width, state.height, rgb

    def close(self) -> None:
        # Engine teardown is process exit. Calling upstream game_deinit is unsafe
        # for this fork's partly disabled audio/network loop.
        pass
