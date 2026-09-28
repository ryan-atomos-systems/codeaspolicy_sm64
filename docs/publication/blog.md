# Code as Policy in Super Mario 64

**From an empty save to eight stars and the first Bowser key.**

GPT-6 Astra · Development agent
SM64 Policy Lab · September 2026

This is the text edition of the [project website](../../website/README.md). The website includes the complete recording, chapter navigation, and an interactive 3D decision example.

## Overview

We use GPT-6 Astra to develop a controller for Super Mario 64. Given a gameplay objective and access to the game's source and state, the agent writes Python skills, tests them in the environment, and revises them from execution feedback. The resulting program collects eight stars and the first Bowser key in one continuous run from an empty save.

The policy combines a fixed campaign route with feedback control. It reads Mario's motion, nearby objects, collision samples, and saved progress, then chooses a controller input every physics frame. The run uses oracle observations in a modified native PC port, with the opening cinematic skipped. Human direction sets the development goals; the deployed program runs without language-model calls or RL training.

## From code to control

The campaign is a hierarchy of small programs. A task controller selects the course and objective. Skills handle interactions such as boarding a platform or grabbing Bowser's tail. Shared movement controllers convert target positions and current velocity into stick inputs.

Different movement modes need different controllers. On the ground, the policy steers toward a target heading. In an ordinary jump, Mario's facing is locked, so the controller adjusts forward acceleration and lateral motion separately. Sliding, swimming, cannon aiming, and the Bowser fight each have their own skill.

Routes and thresholds are authored using the level source. Dynamic decisions use the current observation: wait for a platform to descend, line up over a post, or release Bowser when the spin speed and angle are sufficient. Replay checkpoints support development; the final campaign is rerun from the beginning.

## Inside one decision

To free Chain Chomp, Mario must ground-pound the post. The policy presses Z when he is airborne, within 32 units of the post's center, and more than five units above its top.

At input frame 1,466, the horizontal error is **28.77 units** and the clearance is **46.62 units**. All three conditions hold. The final action is a neutral stick with Z pressed.

```python
# GroundPoundObject.act(), abbreviated
if state.mario.airborne:
    if distance < 32 and feet_y > post_top_y + 5:
        return Action(z=True)
    return air_steer(state, post_center)
```

The dashboard pairs the game image with an interactive rendering of the observation. It shows Mario, nearby objects, contact surfaces, sampled rays, and the current target. The decision inspector displays the conditions logged during execution and the resulting action. Each action uses the preceding observation; the image is labeled with its actual frame.

The scene contains only the geometry returned by the oracle. The grid is a ruler, and unsampled space remains unknown.

## Eight stars and the first key

The route combines four courses, castle travel, Bowser in the Dark World, and the boss encounter. The evaluator checks saved progress independently of the policy: eight distinct star bits and the first-key flag, starting from an empty save.

| Star | Objective | Game time |
| --- | --- | ---: |
| 1 | BOB · Behind Chain Chomp's Gate | 0:58.97 |
| 2 | Secret Slide · Under 21 seconds | 2:13.50 |
| 3 | Secret Slide · Box star | 3:09.80 |
| 4 | Secret Aquarium · Red coins | 5:03.50 |
| 5 | WF · Chip Off Whomp's Block | 7:09.73 |
| 6 | WF · To the Top of the Fortress | 9:01.53 |
| 7 | WF · Fall onto the Caged Island | 9:33.93 |
| 8 | WF · Shoot into the Wild Blue | 10:37.10 |
| Key | First Bowser · Basement key | 14:44.67 |

Times start at the first API observation and use 30 physics frames/s. The intro and startup warmup are excluded. BOB denotes Bob-omb Battlefield; WF denotes Whomp's Fortress.

The run records zero deaths and a minimum health of 5/8. A second campaign with decision logging matches the initial observation and all 26,600 recorded actions and observations, including the 60-frame tail after success. These matching runs establish repeatability for this setup; robustness to varied starts and disturbances remains unmeasured.

The original recorded episode took 142.05 seconds of wall time, including startup and recording. This measures execution, not agent development.

## From oracle state to perception

This experiment separates control from perception. The current policy uses exact state, object behavior IDs, saved progress, and source-informed landmarks. It completes one route through the first Bowser; the later game remains unsolved.

Next, we plan to test the fixed policy under timing and state perturbations, extend the skill library, and train a recurrent state estimator from frames and action history. Oracle traces provide supervision. At deployment, the estimator will use its own history, and the policy will need to tolerate uncertainty and accumulated error.

## Related work

[Code as Policies](https://code-as-policies.github.io/) uses language models to write programs that combine perception and control. [Voyager](https://voyager.minedojo.org/) develops reusable code skills through feedback in Minecraft. Our experiment applies these ideas to a fixed, human-directed SM64 objective.

[Programmatically Interpretable Reinforcement Learning](https://proceedings.mlr.press/v80/verma18a.html) studies readable program policies through a different synthesis procedure. [Eureka](https://eureka-research.github.io/) generates reward code for RL; here, code specifies the action policy directly.

The environment builds on [Gumbo64/sm64-AI](https://github.com/Gumbo64/sm64-AI) and its native-port contributors. The website adapts the [Nerfies project-page template](https://nerfies.github.io/), with attribution and its CC BY-SA 4.0 license retained for the adapted design.

Read the [technical report](paper.tex) and [evidence guide](evidence.md) for the controller details, configuration, and artifact identities.
