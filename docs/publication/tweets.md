# Tweet drafts

Drafts only. Each quoted post is below 280 characters, including numbering. Attach media separately; the notes are not part of the posts. Local dashboard addresses will not work for readers, so no placeholder public links are included.

## Nine-post thread

### 1 — Result

> 1/9 I used GPT-6 Astra to develop a code-as-policy player for Super Mario 64. From an empty save: 8 stars, first Bowser defeated, basement key collected, zero deaths. This runs on oracle state in a modified native PC port, with the intro skipped.

Attach a clip ending in the Bowser key celebration. Keep the eight-star HUD visible.

### 2 — Agent versus policy

> 2/9 GPT-6 Astra was the development agent: inspect mechanics, write skills, run experiments, debug failures. I set the goals. During gameplay, Python code chooses the inputs every physics frame. No per-frame LLM calls or RL training.

### 3 — Architecture

> 3/9 The technique: hierarchical code-as-policy with feedback control. A campaign controller composes navigation, ground pounds, sliding, swimming, platform timing, cannon aiming, and Bowser skills. Authored routes guide it; observed state drives corrections.

### 4 — A concrete decision

> 4/9 One ground-pound decision: Mario is airborne, 28.77 units from the post's center, and 46.62 units above its top. The alignment and height gates pass. Action: Z. Those are actual logged conditions, so we can inspect why the code took the branch.

Attach `decision-debugger.png`.

### 5 — The debugger

> 5/9 The dashboard pairs gameplay with an interactive 3D state view: Mario, objects, collision samples, velocity, targets, and route. Scrub a frame and inspect input state -> evaluated conditions -> action -> outcome. Unknown geometry stays unknown.

Attach `state-debugger.png` or a short screen recording of orbiting and scrubbing.

### 6 — Timing

> 6/9 The eighth star arrives at 10:37.10 of simulated game time; the first Bowser key at 14:44.67. The original recorded episode took about 142 seconds of wall time. That is rollout execution time, not the agent's development time or training cost.

### 7 — Evidence

> 7/9 Success is verified from eight unique saved star bits and the key flag. An instrumented fresh-save rerun matched all 26,600 actions and observations, plus the initial state. Useful regression evidence; not a measured success rate across varied starts.

### 8 — Prior work

> 8/9 This builds on Gumbo64/sm64-AI and connects to Code as Policies, Voyager's executable skills, and programmatic policies. Our route is fixed and human-directed. The contribution is a working, inspectable SM64 milestone, not a claim to invent the idea.

Add public source links in a separate reply if desired: [Gumbo64](https://github.com/Gumbo64/sm64-AI), [Code as Policies](https://arxiv.org/abs/2209.07753), [Voyager](https://arxiv.org/abs/2305.16291).

### 9 — Next step

> 9/9 Next: test robustness, extend the campaign, then estimate state from frames and action history. Oracle traces can supervise that estimator, but it must use its own estimates at inference. First Bowser is working. Full-game and vision-only play remain ahead.

## Standalone alternatives

### A — Result first

> GPT-6 Astra helped me build a Python policy that gets 8 stars and the first Bowser key from an empty SM64 save, with zero deaths. It uses oracle state in a modified native port, with the intro skipped. The policy runs without per-frame LLM calls.

### B — Debugger first

> My favorite part of this SM64 project is the debugger: gameplay beside a 3D oracle-state view, with targets, velocity, collision samples, and the exact conditions behind each action. GPT-6 Astra developed the code-as-policy controller under my direction.

### C — Method first

> An AI coding agent can build the player itself. With GPT-6 Astra, we made a code-as-policy SM64 controller that composes feedback skills to earn 8 stars and the first Bowser key. Oracle access, authored routes, modified native port. A milestone toward the full game.

## Media and editing notes

- Screenshots are under `artifacts/first-bowser-debug-01/`; keep their image/state frame labels when cropping.
- A useful video edit is: a star collection, the rotating platforms, the Bowser throw, then the key. Label excerpts and playback speed so the edit is not mistaken for continuous real-time footage.
- These drafts deliberately distinguish the coding agent from the runtime policy, and the first Bowser from beating the whole game.
- If adding a public paper/blog link, recheck the final post's character count. No project publication URL exists in these drafts.
