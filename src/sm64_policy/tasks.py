"""Objectives and measured outcomes, independent of movement policy and engine."""

from dataclasses import asdict, dataclass

from .api import Observation


@dataclass(frozen=True, slots=True)
class StarGoal:
    id: str
    name: str
    course: int
    star: int

    def __post_init__(self):
        if not 0 <= self.course <= 25 or not 1 <= self.star <= 7:
            raise ValueError("Invalid course or star")


class StarTask:
    """Prove collection by an absent-to-present transition in the saved bit."""

    def __init__(self, goal: StarGoal, initial: Observation):
        if initial.progress is None:
            raise ValueError("Star tasks require native oracle progress")
        if initial.progress.has_star(goal.course, goal.star):
            raise ValueError("The target star is already present in the initial save")
        self.goal = goal
        self.initial_mask = initial.progress.collected_star_masks[goal.course]
        self.final_mask = self.initial_mask
        self.success_frame = None

    def update(self, observation: Observation) -> bool:
        if observation.progress is None:
            raise ValueError("Missing progress during a star task")
        self.final_mask = observation.progress.collected_star_masks[self.goal.course]
        if self.success_frame is None and observation.progress.has_star(
            self.goal.course, self.goal.star
        ):
            self.success_frame = observation.frame
            return True
        return False

    def to_dict(self) -> dict:
        return {
            **asdict(self.goal),
            "success": self.success_frame is not None,
            "success_frame": self.success_frame,
            "initial_mask": self.initial_mask,
            "final_mask": self.final_mask,
            "evidence": "saved_star_bit_0_to_1",
        }


@dataclass(frozen=True, slots=True)
class CampaignGoal:
    id: str = "first-bowser"
    name: str = "Eight stars and the first Bowser key"
    stars: int = 8
    key_flag: int = 16


class CampaignTask:
    """Verify earned save bits and the key in one uninterrupted fresh-save episode."""

    def __init__(self, goal: CampaignGoal, initial: Observation):
        if initial.progress is None:
            raise ValueError("Campaign tasks require oracle progress")
        self.goal = goal
        self.initial_masks = initial.progress.collected_star_masks
        self.final_masks = self.initial_masks
        self.initial_flags = self.final_flags = initial.progress.save_flags
        if any(self.initial_masks) or self.initial_flags & goal.key_flag:
            raise ValueError("Campaign verification requires an empty save")
        if initial.level != 16:
            raise ValueError("Campaign verification must start on castle grounds (level 16)")
        self.success_frame = None
        self.events = []

    def update(self, observation: Observation) -> bool:
        if observation.progress is None:
            raise ValueError("Missing campaign progress")
        progress = observation.progress
        for course, (old, new) in enumerate(zip(self.final_masks, progress.collected_star_masks)):
            for star in range(1, 8):
                bit = 1 << (star - 1)
                if new & bit and not old & bit:
                    self.events.append(
                        {
                            "frame": observation.frame,
                            "kind": "star_collected",
                            "label": f"Course {course} · Star {star}",
                            "course": course,
                            "star": star,
                        }
                    )
        self.final_masks = progress.collected_star_masks
        self.final_flags = progress.save_flags
        if (
            self.success_frame is None
            and self.earned_stars >= self.goal.stars
            and self.final_flags & self.goal.key_flag
        ):
            self.success_frame = observation.frame
            return True
        return False

    @property
    def earned_stars(self) -> int:
        return sum((mask & 0x7F).bit_count() for mask in self.final_masks)

    def to_dict(self) -> dict:
        return {
            **asdict(self.goal),
            "kind": "campaign",
            "success": self.success_frame is not None,
            "success_frame": self.success_frame,
            "earned_stars": self.earned_stars,
            "initial_masks": self.initial_masks,
            "final_masks": self.final_masks,
            "initial_flags": self.initial_flags,
            "final_flags": self.final_flags,
            "evidence": "fresh_save_unique_star_bits_and_first_bowser_key",
        }


def make_task(goal: StarGoal | CampaignGoal, initial: Observation):
    return (
        CampaignTask(goal, initial) if isinstance(goal, CampaignGoal) else StarTask(goal, initial)
    )
