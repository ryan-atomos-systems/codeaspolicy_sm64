// Pure display transforms. No policy execution or invented explanations.
export function intentFor(record, input) {
  if (!input) return null;
  const p = record.policy || {},
    decision = p.decision || {};
  const control = decision.controls?.at(-1);
  const gate = decision.gates?.at(-1);
  if (gate?.target_position)
    return {
      position: gate.target_position,
      objectId: gate.object_id,
      label: gate.name,
      provenance: "Recorded condition target",
      projected: false,
    };
  const xz = control?.target_xz || p.target_xz;
  if (!xz) return null;
  return {
    position: [xz[0], input.position[1], xz[1]],
    label: control?.controller || p.phase || "Target",
    projected: true,
    provenance: control
      ? "Last evaluated controller target"
      : "Recorded policy target",
  };
}
export function sameArea(a, b) {
  return a && b && a.level === b.level && a.area === b.area;
}
export function describeTransition(record, input, output) {
  if (!output) return null;
  const local = sameArea(input, output);
  return {
    inputFrame: input?.frame ?? null,
    outputFrame: output.frame ?? record.frame,
    duration: input
      ? (output.frame ?? record.frame) - input.frame
      : output.last_action_frames,
    delta: local ? output.position.map((v, i) => v - input.position[i]) : null,
    healthDelta: input ? output.health - input.health : null,
    intent: intentFor(record, input),
    local,
  };
}
export function objectKind(object) {
  const name = object.behavior_name || "",
    a = object.affordances || [];
  if (/Star|Key/.test(name) || a.includes("star")) return "reward";
  if (/Coin/.test(name) || a.includes("coin")) return "coin";
  if (/Platform|Elevator|Ferris|Seesaw/.test(name)) return "platform";
  if (/Bowser|Whomp|Goomba|Chomp|Bobomb|Bully|Piranha|Amp/.test(name))
    return "enemy";
  if (/Door|Pipe|Warp|Teleport/.test(name)) return "portal";
  return "object";
}
export function nearestImage(frames, frame) {
  let low = 0,
    high = frames.length;
  while (low < high) {
    const mid = (low + high) >>> 1;
    if (frames[mid].frame <= frame) low = mid + 1;
    else high = mid;
  }
  return frames[low - 1] || null;
}
