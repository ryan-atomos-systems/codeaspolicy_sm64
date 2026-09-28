"""Run with: PYTHONPATH=src python3 examples/environment.py"""

from pathlib import Path

from sm64_policy import Action, Level, SM64Env, SpawnState


def main() -> None:
    output = Path("artifacts/api-example")
    output.mkdir(parents=True, exist_ok=True)
    with SM64Env(width=320, height=180) as env:
        state = env.reset(Level.BOB, SpawnState((-6558.0, 200.0, 6464.0)))
        for step in range(60):
            state = env.step(Action(stick_y=64, a=step % 24 < 3), n_frames=4)
        checkpoint = env.save_state(output / "checkpoint.json")
        env.render().save(output / "before.png")
        future = [env.step(Action(stick_y=64), n_frames=4) for _ in range(20)]
        assert env.load_state(checkpoint) == state
        assert [env.step(Action(stick_y=64), n_frames=4) for _ in range(20)] == future
        env.render().save(output / "after.png")
        print(f"Restored checkpoint and matched continuation; files: {output.resolve()}")


if __name__ == "__main__":
    main()
