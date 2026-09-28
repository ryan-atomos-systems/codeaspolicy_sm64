"""Task graph for a fresh-save eight-star route and the first Bowser key.

Only Action values leave this policy. No resets, checkpoint loads, save edits,
position writes, or engine calls are available to its movement skills.
"""

from ..api import Action, Observation
from ..first_star import FirstStar
from ..tasks import CampaignGoal
from .aquarium import Aquarium
from .cannon import Cannon
from .fight import Fight
from .navigation import Route
from .owl import Owl
from .slide import Slide
from .tower import Tower
from .whomp_climb import Whomp


class FirstBowser:
    goal = CampaignGoal()
    max_action_frames = 1

    def __init__(self, seed: int = 0):
        self.level = None
        self.route = self.skill = None
        self.target_star = None
        self.phase = "start"
        self.events = []
        self.course_attempts = 0
        self.retry_until = 0

    def enter(self, s):
        previous = self.level
        self.level = s.level
        self.events.append({"frame": s.frame, "kind": "level", "label": f"Enter level {s.level}"})
        if s.level == 16:
            self.route = Route(
                [(-1300, 3100), (0, 2000), (0, 200), (0, -1100), (0, -1700), (-76, -3350)]
            )
        elif s.level == 6:
            if s.stars == 0:
                points = [
                    (-1024, 1000),
                    (-2200, 800),
                    (-2450, 500),
                    (-2770, 100),
                    (-2900, -793),
                    (-3400, -793),
                    (-3900, -461),
                    (-4900, -461),
                    (-6000, -461, 1),
                ]
                if previous == 9:
                    points = [(-6000, -461, 1)]
            elif s.stars == 1:
                points = [
                    (-3900, -461),
                    (-3400, -793),
                    (-2850, -793),
                    (-2700, 0),
                    (-2200, 700),
                    (-1024, 600),
                    (-1024, 0),
                    (-1024, -750),
                    (-500, -750),
                    (200, -1200),
                    (1000, -1830),
                    (2013, -2014, 1),
                ]
            elif s.stars == 2:
                points = [
                    (-1024, 400),
                    (-1024, -750),
                    (-500, -750),
                    (200, -1200),
                    (1000, -1830),
                    (2013, -2014, 1),
                ]
            elif s.stars == 3:
                points = [
                    (-1024, 400),
                    (200, 700),
                    (500, 450),
                    (850, 50),
                    (1700, -230),
                    (2500, -230),
                    (2300, 900),
                    (1963, 1280, 2),
                ]
            elif s.stars < 8:
                points = (
                    [
                        (2500, -230),
                        (1700, -230),
                        (850, -230),
                        (550, 450),
                        (-400, 500),
                        (-400, 0),
                        (256, -600),
                        (256, -1500),
                        (256, -3800, 1),
                        (256, -5100, 1),
                    ]
                    if previous == 20
                    else [(256, -5100, 1)]
                )
            else:
                points = (
                    [(-5513, -4324)]
                    if previous == 17
                    else [
                        (-1024, 600),
                        (-1024, -750),
                        (-1700, -750),
                        (-2300, -1100),
                        (-2750, -1550),
                        (-3700, -2600),
                        (-4600, -3400),
                        (-5513, -4324),
                    ]
                    if previous == 16
                    else [
                        (256, -3800),
                        (900, -3800),
                        (900, -2300),
                        (256, -2300),
                        (256, -1800, 1),
                        (256, -500),
                        (-400, 0),
                        (-1024, 600),
                        (-1024, -750),
                        (-1700, -750),
                        (-2300, -1100),
                        (-2750, -1550),
                        (-3700, -2600),
                        (-4600, -3400),
                        (-5513, -4324),
                    ]
                )
            self.route = Route(points)
        elif s.level == 9:
            self.skill = FirstStar()
            self.skill.phase_start = s.frame
        elif s.level == 27:
            self.skill = Slide()
        elif s.level == 20:
            self.skill = Aquarium()
        elif s.level == 24:
            if not s.progress.has_star(2, 1):
                self.skill, self.target_star = Whomp(), 1
            elif not s.progress.has_star(2, 2):
                self.skill, self.target_star = Whomp(), 2
                self.skill.fight = Tower()
            elif not s.progress.has_star(2, 5):
                self.skill, self.target_star = Owl(), 5
            else:
                self.skill, self.target_star = Cannon(), 3
        elif s.level == 17:
            from .dark_world import DarkWorld

            self.skill = DarkWorld()
            if previous != 30:
                self.course_attempts += 1
                # A fixed restart can repeat the same enemy/platform collision.
                self.retry_until = s.frame + 37 * (self.course_attempts - 1)
            if previous == 30:
                # Battle death returns at the pipe checkpoint, not course entry.
                self.skill.upper_ready = True
                self.skill.finish.phase = "switch"
                self.skill.finish.stairs.phase = "pipe"
        elif s.level == 30:
            self.skill = Fight()

    def act(self, s: Observation, step: int) -> Action:
        if any(value is None for value in (s.mario, s.objects, s.progress, s.ui)):
            raise ValueError("first-bowser requires native oracle observations")
        if s.last_action_frames > 1:
            raise ValueError("first-bowser requires --frame-skip 1")
        if s.health <= 0:
            return Action()
        if self.level != s.level:
            self.enter(s)
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0 or (s.level in (9, 24) and s.area == 2):
            self.phase = "dialog or act selection"
            return Action(a=s.frame % 8 == 0)
        if s.level == 17 and s.frame < self.retry_until:
            return Action()
        if s.level in (16, 6):
            self.phase = "castle navigation"
            return self.route.act(s)
        if s.level == 9:
            self.phase = "Chain Chomp"
            return self.skill.act(s, step)
        if s.level == 24:
            self.phase = f"Whomp’s Fortress star {self.target_star}"
            if s.progress.has_star(2, self.target_star):
                return Action(a=s.frame % 8 == 0)
        elif s.level == 27:
            self.phase = "Princess’s Secret Slide"
        elif s.level == 20:
            self.phase = "Secret Aquarium red coins"
        elif s.level == 17:
            self.phase = "Bowser in the Dark World"
        elif s.level == 30:
            self.phase = "Bowser battle"
            return self.skill.act(s, s.frame)
        else:
            return Action()
        return self.skill.act(s)

    def diagnostics(self):
        return {
            "phase": self.phase,
            "skill": getattr(self.skill, "phase", None),
            "waypoint": getattr(self.skill, "i", None),
            "castle_waypoint": self.route.index if self.route else None,
        }
