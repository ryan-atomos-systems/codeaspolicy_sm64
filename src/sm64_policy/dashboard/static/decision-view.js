import { describeTransition } from "./debug-model.js";
const $ = (id) => document.getElementById(id);
const num = (value) =>
  typeof value === "number"
    ? Number(value.toFixed(2)).toLocaleString()
    : String(value ?? "Unknown");
const vec = (value) => value?.map(num).join(" / ") ?? "Not recorded";
function lines(node, entries) {
  node.replaceChildren();
  for (const [label, value] of entries) {
    const row = document.createElement("div"),
      dt = document.createElement("dt"),
      dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = value;
    row.append(dt, dd);
    node.append(row);
  }
}
export function showDecision(record, input, output) {
  const transition = describeTransition(record, input, output);
  if (!transition) {
    $("decision-caption").textContent =
      "No observation recorded at this frame.";
    return;
  }
  const p = record.policy || {},
    d = p.decision,
    controls = d?.controls || [];
  const sequence = record.action_sequence;
  $("decision-caption").textContent =
    record.step < 0
      ? "Initial observation · no action has been chosen yet."
      : sequence
        ? `Replay interval: F${input?.frame ?? "?"} → ${sequence.length} recorded controller decisions → F${transition.outputFrame}. The stick display shows the final action.`
        : `Decision ${record.step + 1}: input F${input?.frame ?? "?"} → action held ${transition.duration ?? "?"} frame(s) → outcome F${transition.outputFrame}`;
  const m = input?.mario;
  lines($("input-facts"), [
    ["Input frame", input?.frame ?? "Not recorded"],
    ["Position X / Y / Z", vec(input?.position)],
    ["Velocity X / Y / Z", vec(input?.velocity)],
    [
      "Motion flags",
      m
        ? [
            m.airborne && "airborne",
            m.swimming && "swimming",
            m.on_pole && "on pole",
            m.hanging && "hanging",
            !m.airborne && "not airborne",
          ]
            .filter(Boolean)
            .join(" · ")
        : "Not recorded",
    ],
    ["Support object", m?.platform_id ?? "None"],
  ]);
  lines($("policy-facts"), [
    [
      "Active phase",
      [p.phase, p.skill].filter(Boolean).join(" / ") || "Not recorded",
    ],
    [
      "Waypoint",
      p.waypoint ??
        (p.phase === "castle navigation" ? p.castle_waypoint : null) ??
        "Not recorded",
    ],
    [
      "Target",
      transition.intent
        ? vec(transition.intent.position) +
          (transition.intent.projected ? " (XZ; Y projected)" : "")
        : "Not recorded",
    ],
    [
      "Provenance",
      record.step < 0
        ? "Initial state; no decision yet"
        : d
          ? "Recorded during act(input)"
          : p.provenance || "No controller call trace recorded",
    ],
    ...(p.post_drop != null
      ? [["Post depressed", `${num(p.post_drop)} / 190 units`]]
      : []),
  ]);
  const a = record.action;
  const buttons = ["a", "b", "z", "start"]
    .filter((k) => a[k])
    .map((k) => k.toUpperCase())
    .join(" + ");
  const gate = d?.gates?.at(-1);
  const gateText = gate
    ? ` · ${gate.name}: ${Object.values(gate.conditions).filter(Boolean).length}/${Object.keys(gate.conditions).length} conditions met`
    : "";
  $("decision-preview").textContent =
    record.step < 0
      ? "Initial observation · no action yet"
      : `INPUT F${input?.frame ?? "?"} · ${p.skill || p.phase || "Policy"}${sequence ? ` (${sequence.length} decisions; final action shown)` : ""} → stick ${a.stick_x}/${a.stick_y}${buttons ? ` + ${buttons}` : ""} → OUTCOME F${transition.outputFrame}${gateText}`;
  lines($("action-facts"), [
    ["Raw stick X / Y", `${a.stick_x} / ${a.stick_y}`],
    [
      "Buttons",
      ["a", "b", "z", "start"]
        .filter((k) => a[k])
        .map((k) => k.toUpperCase())
        .join(" + ") || "Released",
    ],
    [sequence ? "Final action held for" : "Held for", `${sequence?.at(-1)?.n_frames ?? transition.duration ?? "—"} physics frame(s)`],
    ...(sequence ? [["Recorded sequence", sequence.map((item) => {
      const keys = ["a", "b", "z", "start"].filter((key) => item.action[key]).join("+") || "—";
      return `(${item.action.stick_x}, ${item.action.stick_y}; ${keys}) × ${item.n_frames}`;
    }).join(" → ")]] : []),
    ["Coordinates", "Mario-relative stick axes"],
  ]);
  lines($("outcome-facts"), [
    ["Result frame", transition.outputFrame],
    [
      "Displacement X / Y / Z",
      transition.delta
        ? vec(transition.delta)
        : "No local comparison across a warp / missing input",
    ],
    ["Result velocity", vec(output.velocity)],
    ["Health change", num(transition.healthDelta)],
    ["Stars", output.stars ?? "Not recorded"],
  ]);
  const calls = $("control-calls");
  calls.replaceChildren();
  if (!d) {
    const text = document.createElement("p");
    text.textContent =
      record.step < 0
        ? "Select the next decision to see how the policy uses this initial observation."
        : "This run did not record controller calculations. Targets appear only where its policy logged them; missing intent is not reconstructed.";
    calls.append(text);
  }
  for (const [i, c] of controls.entries()) {
    const article = document.createElement("article"),
      title = document.createElement("strong"),
      dl = document.createElement("dl");
    title.textContent = `${i + 1}. ${c.controller} · ${c.source}`;
    lines(
      dl,
      Object.entries(c)
        .filter(([key]) => !["controller", "source", "action"].includes(key))
        .map(([key, value]) => [
          key.replaceAll("_", " "),
          Array.isArray(value) ? vec(value) : num(value),
        ]),
    );
    const output = document.createElement("p");
    output.textContent = `Evaluated stick: ${c.action.stick_x} / ${c.action.stick_y}. Final policy action is shown above; later calls or button overrides may change this intermediate result.`;
    article.append(title, dl, output);
    calls.append(article);
  }
  if (d && !controls.length) {
    const text = document.createElement("p");
    text.textContent =
      "No shared steering controller was called. The policy returned a direct action; inspect its phase, conditions and recorded diagnostics.";
    calls.append(text);
  }
  const gates = $("decision-gates");
  gates.replaceChildren();
  for (const gate of d?.gates || []) {
    const item = document.createElement("article"),
      title = document.createElement("strong");
    title.textContent = gate.name;
    item.append(title);
    for (const [name, pass] of Object.entries(gate.conditions)) {
      const row = document.createElement("div");
      row.className = pass ? "gate-pass" : "gate-fail";
      row.textContent = `${pass ? "✓" : "○"} ${name}`;
      item.append(row);
    }
    const dl = document.createElement("dl");
    lines(
      dl,
      Object.entries(gate)
        .filter(([k]) => !["name", "conditions"].includes(k))
        .map(([k, v]) => [
          k.replaceAll("_", " "),
          Array.isArray(v) ? vec(v) : num(v),
        ]),
    );
    item.append(dl);
    gates.append(item);
  }
  $("diagnostic-json").textContent = JSON.stringify(p, null, 2);
}
