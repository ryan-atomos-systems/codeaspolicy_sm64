"""Conservative evidence for a fresh-save sixteen-star completion.

Credits alone are not sufficient: retain the earned star bits, both keys,
the final Bowser defeat, and the Grand Star cutscene seen before credits.
This measures a trajectory, not policy autonomy or robustness.
"""

from .tasks import CampaignGoal, CampaignTask


class SixteenStarCompletion:
    def __init__(self, initial):
        self.campaign = CampaignTask(CampaignGoal(stars=16), initial)
        self.flags_seen = initial.progress.save_flags
        self.bowser_defeated_frame = None
        self.grand_star_frame = None
        self.credits_frame = None
        self.success_frame = None
        self.events = self.campaign.events

    def update(self, state):
        self.campaign.update(state)
        self.flags_seen |= state.progress.save_flags
        if state.level == 34:
            if (
                state.objects
                and any(
                    obj.behavior_name == "bhvBowser" and obj.health <= 0
                    for obj in state.objects.items
                )
                and self.bowser_defeated_frame is None
            ):
                self.bowser_defeated_frame = state.frame
                self.events.append(
                    {"frame": state.frame, "kind": "boss", "label": "Final Bowser defeated"}
                )
            if state.mario and state.mario.action == 0x00001909 and self.grand_star_frame is None:
                self.grand_star_frame = state.frame
                self.events.append(
                    {"frame": state.frame, "kind": "grand_star", "label": "Grand Star collected"}
                )
        if state.progress.credits_active and self.credits_frame is None:
            self.credits_frame = state.frame
            self.events.append(
                {"frame": state.frame, "kind": "credits", "label": "Ending / credits"}
            )
        complete = (
            self.campaign.earned_stars == 16
            and bool(self.flags_seen & (16 | 64))
            and bool(self.flags_seen & (32 | 128))
            and self.bowser_defeated_frame is not None
            and self.grand_star_frame is not None
            and self.credits_frame is not None
        )
        if complete and self.success_frame is None:
            self.success_frame = state.frame
            return True
        return False

    def to_dict(self):
        return {
            "id": "sixteen-star-completion",
            "name": "16 stars, final Bowser, and Grand Star",
            "kind": "campaign",
            "success": self.success_frame is not None,
            "success_frame": self.success_frame,
            "earned_stars": self.campaign.earned_stars,
            "initial_masks": self.campaign.initial_masks,
            "final_masks": self.campaign.final_masks,
            "flags_seen": self.flags_seen,
            "bowser_defeated_frame": self.bowser_defeated_frame,
            "grand_star_frame": self.grand_star_frame,
            "credits_frame": self.credits_frame,
            "evidence": "fresh_save_16_unique_star_bits_both_keys_final_bowser_grand_star_and_credits",
            "autonomous_policy_validation": False,
        }
