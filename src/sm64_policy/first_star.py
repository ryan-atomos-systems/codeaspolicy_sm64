"""BOB star 6: hierarchical code-as-policy with model-based feedback skills."""

import math
from dataclasses import replace

from .api import Action, Observation
from .control import GroundPoundObject, air_steer, horizontal_distance, query_covers, steer
from .decision_trace import record_route
from .tasks import StarGoal


class FirstStar:
    goal = StarGoal("bob-chain-chomp", "Behind Chain Chomp's Gate", course=1, star=6)
    max_action_frames = 1
    # A small authored route graph around static terrain, not timed inputs.
    # The final target is resolved from the observed post, not its object ID.
    route = ((-4000, 6000), (-1800, 5600), (900, 5600), (2300, 4400), (1700, 3600))
    post_landmark = (260, 768, 1920)

    def __init__(self, seed: int = 0):
        self.phase = "navigate"
        self.phase_start = 0
        self.waypoint = 0
        self.pound = GroundPoundObject(top_offset=205)
        self.post_initial_y = None
        self.post_drop = 0.0
        self.gate_id = None
        self.gate_position = None
        self.gate_absent_since = None
        self.star_position = None
        self.recoveries = 0
        self.target = None
        self.events = []
        self.last_star_jump = -100
        self.bridge_recovery = None
        self.recovery_route = ()

    def transition(self, phase, frame):
        self.phase = phase
        self.phase_start = frame
        self.events.append({"frame": frame, "kind": "skill", "label": phase})

    def diagnostics(self) -> dict:
        return {
            "phase": self.phase,
            "waypoint": self.waypoint,
            "target_xz": self.target,
            "post_drop": round(self.post_drop, 2),
            "recoveries": self.recoveries,
        }

    def act(self, state: Observation, step: int) -> Action:
        if state.mario is None or state.objects is None or state.progress is None:
            raise ValueError("first-star requires oracle observations")
        if state.level != 9:
            raise ValueError("first-star currently supports Bob-omb Battlefield only")
        if state.last_action_frames > self.max_action_frames:
            raise ValueError("first-star requires --frame-skip 1")
        if state.progress.has_star(self.goal.course, self.goal.star):
            if self.phase != "celebrate":
                self.transition("celebrate", state.frame)
            return Action()
        if state.health <= 0:
            return Action()  # Wait for the normal death/exit sequence.
        if state.died:
            self.bridge_recovery = None
            self.recoveries += 1
            self.waypoint = 0
            self.transition("navigate", state.frame)
            self.pound = GroundPoundObject(top_offset=205)
        if state.frame - self.phase_start > 1800:
            raise RuntimeError(f"first-star stalled in {self.phase}; inspect its trace")

        objects = state.objects.items
        posts = [o for o in objects if o.behavior_name == "bhvWoodenPost"]
        post = min(posts, key=lambda o: math.dist(o.position, self.post_landmark), default=None)
        if post and math.dist(post.position, self.post_landmark) > 500:
            post = None
        if post:
            if self.post_initial_y is None:
                self.post_initial_y = post.position[1]
            self.post_drop = self.post_initial_y - post.position[1]
        gate = next((o for o in objects if o.behavior_name == "bhvChainChompGate"), None)
        if gate:
            self.gate_id, self.gate_position = gate.id, gate.position
            self.gate_absent_since = None
        elif self.gate_position and query_covers(state, self.gate_position):
            if self.gate_absent_since is None:
                self.gate_absent_since = state.frame
        else:
            self.gate_absent_since = None
        star = next(
            (
                o
                for o in objects
                if o.behavior_name == "bhvStar"
                and (o.behavior_params >> 24) & 0xFF == self.goal.star - 1
            ),
            None,
        )
        if star:
            self.star_position = star.position

        if self.phase == "navigate":
            # Enemy knockback can drop Mario into the trench below the bridge.
            # Both side walls are too high to walk up: go around the south end
            # before approaching the ramp again.
            if self.waypoint >= 2 and -1700 < state.position[0] < 1500 and state.position[1] < 100:
                self.waypoint = 1
                self.bridge_recovery = 0
                self.recovery_route = (
                    ((-1400, 4500), (-2600, 4500), (-2600, 5600), (-1900, 5600))
                    if state.position[2] < 5376
                    else ((-500, 6650), (-1900, 6650), (-1900, 5600))
                )
                self.recoveries += 1
            if self.bridge_recovery is not None:
                detour = self.recovery_route
                self.target = detour[self.bridge_recovery]
                if horizontal_distance(state, self.target) < 100:
                    self.bridge_recovery += 1
                    if self.bridge_recovery == len(detour):
                        self.bridge_recovery = None
                    return Action()
                return (
                    air_steer(state, self.target, 30)
                    if state.mario.airborne
                    else steer(state, self.target)
                )
            record_route(self.route, self.waypoint)
            if self.waypoint < len(self.route):
                self.target = self.route[self.waypoint]
            elif post:
                self.target = post.position[0], post.position[2]
            else:
                raise RuntimeError("Expected post is missing at the route endpoint")
            distance = horizontal_distance(state, self.target)
            if distance < 100:
                self.waypoint += 1
                if self.waypoint > len(self.route):
                    self.transition("pound_post", state.frame)
                elif self.waypoint == len(self.route) and post:
                    self.target = post.position[0], post.position[2]
                else:
                    self.target = self.route[self.waypoint]
            magnitude = 32 if self.waypoint >= len(self.route) and distance < 350 else 64
            if state.mario.airborne:
                return air_steer(state, self.target, 30)
            action = steer(state, self.target, magnitude)
            nearby_goomba = any(
                o.behavior_name == "bhvGoomba"
                and o.action < 100
                and o.distance < 220
                and abs(o.position[1] - state.position[1]) < 100
                for o in objects
            )
            return replace(action, b=nearby_goomba and state.frame % 8 < 4)

        if self.phase == "pound_post":
            if post is None:
                raise RuntimeError("Lost the post during ground-pound skill")
            if self.post_drop >= 189:
                self.transition("wait_for_gate", state.frame)
                return Action()
            self.target = post.position[0], post.position[2]
            return self.pound.act(state, post)

        if self.phase == "wait_for_gate":
            # Absence is only evidence if the known gate location is in query coverage.
            if self.gate_absent_since is not None and state.frame - self.gate_absent_since >= 8:
                self.transition("collect_star", state.frame)
            return Action()

        if self.phase == "collect_star":
            if self.star_position is None:
                raise RuntimeError("Target star was not observed")
            self.target = self.star_position[0], self.star_position[2]
            distance = horizontal_distance(state, self.target)
            if state.mario.airborne:
                return air_steer(state, self.target)
            action = steer(state, self.target)
            if distance < 180 and state.frame - self.last_star_jump > 40:
                self.last_star_jump = state.frame
                return replace(action, a=True)
            return action
        raise RuntimeError(f"Unknown policy phase: {self.phase}")
