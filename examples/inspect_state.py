"""Inspect a real oracle observation: PYTHONPATH=src python3 examples/inspect_state.py."""

import json
from pathlib import Path

from sm64_policy import Action, Level, SM64Env


def main() -> None:
    output = Path("artifacts/oracle-example")
    output.mkdir(parents=True, exist_ok=True)
    with SM64Env(width=320, height=180) as env:
        state = env.reset(Level.BOB)
        state = env.step(Action(stick_y=64, a=True), n_frames=4)
        (output / "state.json").write_text(json.dumps(state.to_dict(), indent=2) + "\n")
        env.render().save(output / "frame.png")
        print(
            f"frame={state.frame}, yaw={state.mario.face_angle[1]}, airborne={state.mario.airborne}"
        )
        print(
            f"course={state.progress.course}, first star collected={state.progress.has_star(1, 1)}"
        )
        print(
            f"objects={len(state.objects.items)}/{state.objects.total_in_radius}, radius={state.objects.radius:g}"
        )
        for obj in state.objects.items[:8]:
            print(
                f"  {obj.id}: {obj.behavior_name} at {obj.position}, interactions={obj.affordances}"
            )
        print(f"State and aligned image: {output.resolve()}")


if __name__ == "__main__":
    main()
