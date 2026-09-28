"""Batched controller stepping over independent, process-isolated environments."""

from .environment import Level, SM64Env, SpawnState


class SM64VectorEnv:
    """Dispatch the entire batch before collecting results, without a Python thread pool.

    Returns tuples of ordinary Observation records, in environment order. Rewards,
    termination, tensor conversion and policy inference belong to the learner.
    Reset is explicit: no terminal observation is lost to automatic reset. Each
    reset still creates a fresh native process/save. No third-party dependency.
    """

    def __init__(self, num_envs: int, **env_options):
        if type(num_envs) is not int or num_envs < 1:
            raise ValueError("num_envs must be a positive integer")
        env_options.setdefault("checkpoint_history", False)
        self.envs = []
        self._pending = None
        self._closed = False
        try:
            for _ in range(num_envs):
                self.envs.append(SM64Env(**env_options))
        except BaseException:
            self.close()
            raise
        self.envs = tuple(self.envs)

    def __len__(self):
        return len(self.envs)

    def _idle(self):
        if self._closed:
            raise RuntimeError("Vector environment is closed")
        if self._pending is not None:
            raise RuntimeError("A vector operation is pending; wait for it first")

    def _batch(self, values, name):
        values = tuple(values)
        if len(values) != len(self):
            raise ValueError(f"{name} must contain exactly {len(self)} items")
        return values

    def reset_async(self, levels=Level.BOB, spawn_states=None):
        self._idle()
        levels = (levels,) * len(self) if isinstance(levels, int) else self._batch(levels, "levels")
        levels = tuple(Level(level) for level in levels)
        spawns = (
            (None,) * len(self)
            if spawn_states is None
            else self._batch(spawn_states, "spawn_states")
        )
        if any(spawn is not None and not isinstance(spawn, SpawnState) for spawn in spawns):
            raise TypeError("spawn_states must contain SpawnState or None")
        try:
            for env, level, spawn in zip(self.envs, levels, spawns):
                env.reset_async(level, spawn)
            self._pending = "reset"
        except BaseException:
            self._abort()
            raise

    def reset_wait(self):
        return self._wait("reset")

    def reset(self, levels=Level.BOB, spawn_states=None):
        self.reset_async(levels, spawn_states)
        return self.reset_wait()

    def reset_at(self, index: int, level=Level.BOB, spawn_state=None):
        """Reset a finished/failed lane, preserving the other environments."""
        self._idle()
        if type(index) is not int or not 0 <= index < len(self):
            raise IndexError("Invalid environment index")
        return self.envs[index].reset(level, spawn_state)

    def step_async(self, actions, n_frames=4):
        self._idle()
        actions = self._batch(actions, "actions")
        frames = (
            (n_frames,) * len(self)
            if isinstance(n_frames, int)
            else self._batch(n_frames, "n_frames")
        )
        # Validate the whole batch before any engine advances.
        for env, action, count in zip(self.envs, actions, frames):
            env._idle()
            env.get_state()
            env._validate_step(action, count)
        try:
            for env, action, count in zip(self.envs, actions, frames):
                env.step_async(action, count)
            self._pending = "step"
        except BaseException:
            self._abort()
            raise

    def step_wait(self):
        return self._wait("step")

    def step(self, actions, n_frames=4):
        self.step_async(actions, n_frames)
        return self.step_wait()

    def _wait(self, operation):
        if self._pending != operation:
            raise RuntimeError(f"No vector {operation} is pending")
        try:
            return tuple(getattr(env, f"{operation}_wait")() for env in self.envs)
        except BaseException:
            # Never leave unread replies or a partly advanced batch in use.
            self._abort()
            raise
        finally:
            self._pending = None

    def _abort(self):
        for env in self.envs:
            env._stop()
        self._pending = None

    def close(self):
        for env in self.envs:
            env.close()
        self._pending = None
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
