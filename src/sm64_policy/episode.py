"""Execute a policy episode. Called only inside a fresh worker process."""

import math
import os
import random
import time
from contextlib import nullcontext

from .api import Action
from .config import EpisodeConfig
from .decision_trace import capture_decision
from .environment import SM64Env, SpawnState
from .metrics import EpisodeMetrics
from .policies import load_policy
from .recording import FrameRecorder
from .replay import save_replay
from .storage import OBSERVATION_HASH, SCHEMA_VERSION, TraceWriter, observation_hash, write_json
from .synthetic import Synthetic
from .tasks import CampaignGoal, make_task


def run_episode(config: EpisodeConfig) -> dict:
    started = time.time()
    if config.backend == "native":
        env = SM64Env(
            library=config.library,
            width=config.width,
            height=config.height,
            engine_mode=config.engine_mode,
            observation_mode=config.observation_mode,
            gameplay_mode=config.gameplay_mode,
            workspace=config.directory / "runtime",
            checkpoint_history=False,
            game_seed=config.game_seed,
        )
    else:
        env = Synthetic(frame_skip=config.frame_skip)
    recording = task = policy = trace = None
    events = []
    try:
        spawn = config.spawn_state
        observation = (
            env.reset(
                config.level,
                SpawnState(tuple(spawn["position"]), spawn.get("yaw", 0)) if spawn else None,
            )
            if config.backend == "native"
            else env.observe()
        )
        random.seed(config.seed)
        policy = load_policy(config.policy, config.seed)
        if config.frame_skip > getattr(policy, "max_action_frames", 120):
            raise ValueError(f"{config.policy} requires --frame-skip {policy.max_action_frames}")
        goal = getattr(policy, "goal", None)
        if isinstance(goal, CampaignGoal) and config.gameplay_mode != "progression":
            raise ValueError("Campaigns require --gameplay-mode progression")
        task = make_task(goal, observation) if goal is not None else None
        metrics = EpisodeMetrics(observation)
        recording = FrameRecorder(config.directory, config, observation)
        recording.metadata["trace_mode"] = config.trace_mode
        recording.metadata["observation_hash_algorithm"] = OBSERVATION_HASH
        recording.metadata["initial_observation_sha256"] = observation_hash(observation)
        recording.capture(env, 0)
        latencies = []
        policy_time = engine_time = 0.0
        loop_start = time.perf_counter()
        task_completion_seconds = None
        with TraceWriter(config.directory / "trace.jsonl", config.trace_mode) as trace:
            for step in range(config.steps):
                capture = config.record_every > 0 and (step + 1) % config.record_every == 0
                capture = capture or step == config.steps - 1
                tick = time.perf_counter()
                with (
                    capture_decision(observation.frame)
                    if config.trace_mode == "full"
                    else nullcontext(None)
                ) as decision:
                    action = policy.act(observation, step)
                    diagnostics = (
                        policy.diagnostics()
                        if decision is not None and hasattr(policy, "diagnostics")
                        else {}
                    )
                diagnostics = {**(diagnostics or {}), "decision": decision} if decision else None
                if not isinstance(action, Action):
                    raise TypeError("Policy.act() must return sm64_policy.api.Action")
                decision_end = time.perf_counter()
                observation = (
                    env._step(action, config.frame_skip, capture=capture)
                    if config.backend == "native"
                    else env.step(action, capture=capture)
                )
                engine_end = time.perf_counter()
                policy_time += decision_end - tick
                engine_time += engine_end - decision_end
                latencies.append(engine_end - tick)
                metrics.update(observation)
                if task and task.update(observation):
                    task_completion_seconds = time.perf_counter() - loop_start
                    events.append(
                        {
                            "frame": observation.frame,
                            "kind": "campaign_complete"
                            if isinstance(goal, CampaignGoal)
                            else "star_collected",
                            "label": task.goal.name,
                        }
                    )
                frame = (step + 1) * config.frame_skip
                trace.append(step, frame, action, observation, diagnostics)
                if capture:
                    recording.capture(env, frame)
                # Include two seconds of the real collection animation in playback.
                if task and task.success_frame is not None and frame >= task.success_frame + 60:
                    break
        elapsed = time.perf_counter() - loop_start
        steps = len(latencies)
        if not recording.frames or recording.frames[-1]["frame"] != frame:
            recording.capture(env, frame, render=True)
        ordered = sorted(latencies)
        result = {
            "schema_version": SCHEMA_VERSION,
            "status": "ok",
            "backend": config.backend,
            "engine_mode": config.engine_mode,
            "gameplay_mode": config.gameplay_mode,
            "observation_mode": config.observation_mode
            if config.backend == "native"
            else "synthetic",
            "policy": config.policy,
            "seed": config.seed,
            "game_seed": config.game_seed,
            "pid": os.getpid(),
            "port": getattr(env, "port", config.port),
            "started_at": started,
            "finished_at": time.time(),
            "steps": steps,
            "step_budget": config.steps,
            "simulated_frames": steps * config.frame_skip,
            "loop_seconds": elapsed,
            "steps_per_second": steps / elapsed,
            "frames_per_second": steps * config.frame_skip / elapsed,
            "policy_seconds": policy_time,
            "engine_seconds": engine_time,
            "instrumentation_seconds": elapsed - policy_time - engine_time,
            "step_latency_p50_ms": ordered[len(ordered) // 2] * 1000,
            "step_latency_p95_ms": ordered[math.ceil(len(ordered) * 0.95) - 1] * 1000,
            "recorded_frames": len(recording.frames),
            "trace_sha256": trace.digest.hexdigest(),
            "trace_mode": config.trace_mode,
            "task": task.to_dict() if task else None,
            "termination": "task_success"
            if task and task.success_frame is not None
            else "budget_exhausted",
            "task_completion_seconds": task_completion_seconds,
            **metrics.to_dict(),
        }
        write_json(config.directory / "result.json", result)
        return result
    finally:
        try:
            if recording is not None:
                recording.metadata["events"] = sorted(
                    events + getattr(task, "events", []) + getattr(policy, "events", []),
                    key=lambda event: event["frame"],
                )
                recording.metadata["task"] = task.to_dict() if task else None
                recording.finish()
                if (
                    config.backend == "native"
                    and config.trace_mode == "compact"
                    and trace is not None
                ):
                    save_replay(
                        config,
                        recording.metadata["initial_observation_sha256"],
                        trace,
                        config.directory / "replay.json",
                    )
        finally:
            env.close()
