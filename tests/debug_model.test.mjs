import test from "node:test";
import assert from "node:assert/strict";
import {
  intentFor,
  describeTransition,
  nearestImage,
  sameArea,
} from "../src/sm64_policy/dashboard/static/debug-model.js";
import { OracleData } from "../src/sm64_policy/dashboard/static/oracle-data.js";
const input = {
  frame: 40,
  level: 9,
  area: 1,
  position: [10, 20, 30],
  health: 8,
};
const output = { ...input, frame: 44, position: [14, 22, 31], health: 7 };
test("intent uses recorded input height and does not invent legacy targets", () => {
  assert.equal(intentFor({ policy: { phase: "navigate" } }, input), null);
  const record = {
    policy: {
      decision: { controls: [{ controller: "steer", target_xz: [100, 200] }] },
    },
  };
  assert.deepEqual(intentFor(record, input).position, [100, 20, 200]);
  const t = describeTransition(record, input, output);
  assert.equal(t.duration, 4);
  assert.deepEqual(t.delta, [4, 2, 1]);
  assert.equal(t.healthDelta, -1);
  assert.equal(
    describeTransition(record, input, { ...output, level: 6 }).delta,
    null,
  );
  assert.equal(sameArea(input, { ...output, area: 2 }), false);
});
test("sparse image lookup never silently chooses a future image", () => {
  const frames = [{ frame: 0 }, { frame: 3 }, { frame: 6 }];
  assert.equal(nearestImage(frames, 5).frame, 3);
  assert.equal(nearestImage(frames, -1), null);
  assert.equal(nearestImage([], 10), null);
});
test("state pages include causal input at chunk boundaries and deduplicate requests", async () => {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async (url) => {
    calls++;
    const start = Number(
      new URL(url, "http://local").searchParams.get("start"),
    );
    const first = Math.max(0, start - 1);
    return {
      ok: true,
      json: async () => ({
        start: first,
        total: 72,
        observations: Array.from({ length: 25 }, (_, i) => ({
          frame: (first + i) * 4,
        })),
      }),
    };
  };
  try {
    const data = new OracleData("run", "session");
    const [a, b] = await Promise.all([data.get(24), data.get(24)]);
    assert.equal(a.input.frame, 92);
    assert.equal(a.output.frame, 96);
    assert.deepEqual(a, b);
    assert.equal(calls, 1);
    data.close();
  } finally {
    globalThis.fetch = original;
  }
});
