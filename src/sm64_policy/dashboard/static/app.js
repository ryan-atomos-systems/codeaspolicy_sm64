import { StateView } from "./state-view.js";
import { OracleData } from "./oracle-data.js";
import { showDecision } from "./decision-view.js";
import { nearestImage } from "./debug-model.js";
const $ = (id) => document.getElementById(id);
let oracleView = null,
  oracleData = null,
  oracleRequest = 0;
try {
  oracleView = new StateView();
} catch (error) {
  $("oracle-status").textContent =
    `3D renderer unavailable: ${error.message}. Decision inspection still works.`;
}
const state = {
  runs: [],
  run: null,
  session: null,
  records: [],
  frames: [],
  index: 0,
  playing: false,
  cursor: 0,
  lastTick: 0,
  generation: 0,
};
const number = (value) =>
  value == null ? "—" : Math.round(value).toLocaleString();
const clock = (frames) =>
  `${Math.floor(frames / 1800)}:${String(Math.floor(frames / 30) % 60).padStart(2, "0")}`;
const campaignStars = {
  "1:6": "Chain Chomp's Gate",
  "19:2": "Slide under 21 seconds",
  "19:1": "Slide box star",
  "24:1": "Secret Aquarium",
  "2:1": "Whomp King",
  "2:2": "Top of the Fortress",
  "2:5": "Caged Island",
  "2:3": "Wild Blue",
  "2:6": "Blast Away the Wall",
  "7:3": "8-Coin Puzzle with 15 Pieces",
  "7:1": "Boil the Big Bully",
  "7:2": "Bully the Bullies",
  "7:5": "Hot-Foot-It into the Volcano",
  "0:1": "Basement Toad",
  "6:1": "Swimming Beast in the Cavern",
  "9:1": "Board Bowser's Sub",
};
function eventLabel(event) {
  if (event.kind === "campaign_complete") return "Bowser key collected";
  if (event.label === "Enter level 17") return "Bowser course";
  if (event.label === "Enter level 30") return "Bowser battle";
  return (
    campaignStars[`${event.course}:${event.star}`] ||
    event.label.replaceAll("_", " ")
  );
}

async function request(url) {
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || `Request failed (${response.status})`);
  }
  return response.json();
}
function notice(message = "") {
  $("notice").textContent = message;
  $("notice").hidden = !message;
}
function pause(bookmark = false) {
  state.playing = false;
  $("play").textContent = "▶";
  $("play").setAttribute("aria-label", "Play rollout");
  if (bookmark && state.session && state.records.length) {
    const params = new URLSearchParams({
      run: state.run,
      session: state.session.id,
      frame: state.records[state.index].frame,
    });
    history.replaceState(null, "", `#${params}`);
  }
}
function fail(error) {
  clearSession(error.message);
}
function runNotice() {
  const run = state.runs.find((r) => r.id === state.run);
  if (run?.backend === "synthetic")
    notice(
      "SYNTHETIC FIXTURE — these trajectories test the harness and are not SM64 gameplay.",
    );
  else if (run?.status === "invalid_startup")
    notice(
      "INVALID STARTUP — this historical run was stuck in the intro and is excluded from benchmarks.",
    );
  else notice();
}
function togglePlay() {
  if (!state.records.length) return;
  if (state.playing) return pause(true);
  if (state.index === state.records.length - 1) seek(0);
  state.playing = true;
  state.lastTick = performance.now();
  $("play").textContent = "Ⅱ";
  $("play").setAttribute("aria-label", "Pause rollout");
}

async function loadRuns() {
  pause();
  const data = await request("/api/runs");
  state.runs = data.runs;
  $("run").replaceChildren(
    ...data.runs.map((run) => {
      const option = document.createElement("option");
      option.value = run.id;
      option.textContent = `${run.id}${run.backend === "synthetic" ? " [synthetic]" : ""}`;
      return option;
    }),
  );
  if (!data.runs.length) {
    $("run-meta").textContent = "No saved experiments";
    notice(
      "No rollouts found. Run make demo to record your first policy sessions, then refresh.",
    );
    return;
  }
  const hash = new URLSearchParams(location.hash.slice(1));
  const wanted = state.run || hash.get("run");
  const initial =
    data.runs.find((r) => r.id === wanted) ||
    data.runs.find(
      (r) => r.record_every > 0 && r.backend === "native" && r.status === "ok",
    ) ||
    data.runs[0];
  $("run").value = initial.id;
  await loadRun(initial.id, hash.get("session"));
}

async function loadRun(id, wantedSession) {
  pause();
  state.run = id;
  const generation = ++state.generation;
  const data = await request(`/api/sessions?run=${encodeURIComponent(id)}`);
  if (generation !== state.generation) return;
  const run = state.runs.find((r) => r.id === id);
  $("run-meta").textContent =
    `${data.sessions.length} sessions · ${run.workers} workers · ${number(run.fps)} frames/s`;
  $("sessions").replaceChildren(
    ...data.sessions.map((session) => {
      const button = document.createElement("button");
      button.className = "session";
      button.dataset.id = session.id;
      const text = document.createElement("span");
      const name = document.createElement("strong");
      name.textContent = session.policy;
      const info = document.createElement("small");
      info.textContent = `SEED ${session.seed} · ${session.status === "ok" ? `${session.steps.toLocaleString()} decisions` : session.status}`;
      text.append(name, info);
      const dot = document.createElement("span");
      dot.className = `dot${session.status === "ok" ? "" : " error"}`;
      button.append(text, dot);
      button.addEventListener("click", () => loadSession(session).catch(fail));
      return button;
    }),
  );
  runNotice();
  const selected =
    data.sessions.find((s) => s.id === wantedSession) ||
    data.sessions.find((s) => s.status === "ok") ||
    data.sessions[0];
  if (selected) await loadSession(selected);
  else clearSession("This experiment has no sessions yet.");
}

function clearSession(message) {
  pause();
  state.records = [];
  state.frames = [];
  oracleData?.close();
  oracleData = null;
  oracleRequest++;
  oracleView?.unavailable(message);
  for (const id of ["play", "previous", "next", "timeline"])
    $(id).disabled = true;
  $("game-frame").hidden = true;
  $("task-panel").hidden = true;
  $("frame-empty").hidden = false;
  notice(message);
}

async function loadSession(session) {
  pause();
  oracleView?.reset();
  oracleData?.close();
  oracleData = null;
  oracleRequest++;
  const generation = ++state.generation;
  document
    .querySelectorAll(".session")
    .forEach((button) =>
      button.classList.toggle("active", button.dataset.id === session.id),
    );
  $("title").textContent = session.policy;
  $("subtitle").textContent =
    `Seed ${session.seed} · ${session.id} · ${session.steps.toLocaleString()} decisions`;
  $("status").textContent = session.status.toUpperCase();
  if (session.status === "running") {
    clearSession(
      session.error ||
        "This session is still running. Refresh when it finishes.",
    );
    return;
  }
  const data = await request(
    `/api/rollout?run=${encodeURIComponent(state.run)}&session=${encodeURIComponent(session.id)}`,
  );
  if (generation !== state.generation) return;
  runNotice();
  if (session.status !== "ok")
    notice(`Partial recording · ${session.error || session.status}`);
  state.session = session;
  oracleData = new OracleData(state.run, session.id);
  state.frames = data.frames;
  state.records = data.records;
  if (data.initial_observation)
    state.records.unshift({
      step: -1,
      frame: 0,
      action: { stick_x: 0, stick_y: 0, a: false, b: false, z: false },
      observation: data.initial_observation,
    });
  if (!state.records.length) {
    clearSession("This session contains no state records.");
    return;
  }
  state.config = data.config;
  state.task = data.task;
  state.events = data.events || [];
  state.debugEvents = data.debug_events || [];
  populateDebugEvents();
  $("task-panel").hidden = !data.task;
  $("events").replaceChildren();
  if (data.task) {
    $("objective").textContent = data.task.name;
    $("task-result").textContent = data.task.success
      ? "OBJECTIVE VERIFIED"
      : "NOT COMPLETED";
    $("status").textContent = data.task.success
      ? "SUCCESS"
      : session.status === "ok"
        ? "BUDGET EXHAUSTED"
        : session.status.toUpperCase();
    $("footnote").textContent = data.task.success
      ? data.task.id === "sixteen-star-completion"
        ? "Verified fresh-save controller replay: 16 stars, both keys, final Bowser defeat, Grand Star, and ending. Development trajectory with interventions; not an autonomous policy evaluation."
        : data.task.kind === "campaign"
        ? `Verified ${data.task.earned_stars} unique stars and the first Bowser key from an empty save. This is the first Bowser milestone, not full-game completion.`
        : `Verified saved star bit: ${data.task.initial_mask} → ${data.task.final_mask}. Full-game completion is not measured.`
      : session.status === "ok"
        ? "The objective was not completed within this session's decision budget."
        : "The session failed. This partial recording contains the decisions saved before the failure.";
    for (const event of [{ frame: 0, label: "Start" }, ...state.events]) {
      if (event.label === "celebrate") continue;
      if (
        data.task.kind === "campaign" &&
        event.kind === "level" &&
        !["Enter level 17", "Enter level 30"].includes(event.label)
      )
        continue;
      const button = document.createElement("button");
      button.className = "quiet event";
      button.textContent = `${clock(event.frame)} · ${event.kind === "star_collected" ? "★ " : ""}${eventLabel(event)}`;
      button.addEventListener("click", () => {
        pause();
        seek(
          Math.max(
            0,
            state.records.findIndex((record) => record.frame >= event.frame),
          ),
        );
      });
      $("events").append(button);
    }
  } else {
    $("footnote").textContent =
      "Game completion is not measured. Exploration is a diagnostic, not a win condition.";
  }
  state.index = 0;
  state.cursor = 0;
  $("coverage").textContent = number(session.visited_xz_cells_400);
  $("distance").textContent = number(session.max_displacement);
  $("throughput").textContent = number(session.frames_per_second);
  $("stars").textContent = number(session.stars_gained);
  $("visual-mode").textContent = data.visual_playback
    ? `RECORDED · EVERY ${data.config.record_every} DECISION${data.config.record_every === 1 ? "" : "S"}`
    : data.frames.length
      ? "ENDPOINT SNAPSHOTS · TRAJECTORY PLAYBACK"
      : "TRAJECTORY ONLY · NO IMAGES RECORDED";
  if (data.config.trace_mode === "compact")
    $("visual-mode").textContent = "COMPACT TRACE · " + $("visual-mode").textContent;
  for (const id of ["play", "previous", "next", "timeline"])
    $(id).disabled = false;
  $("timeline").max = state.records.length - 1;
  const hash = new URLSearchParams(location.hash.slice(1));
  const wantedFrame =
    hash.get("run") === state.run && hash.get("session") === session.id
      ? Number(hash.get("frame") || 0)
      : 0;
  fitMap();
  const wantedIndex = state.records.findIndex((r) => r.frame >= wantedFrame);
  seek(wantedIndex < 0 ? state.records.length - 1 : wantedIndex);
}

function fitMap() {
  const positions = state.records.map((r) => r.observation.position);
  const xs = positions.map((p) => p[0]),
    zs = positions.map((p) => p[2]);
  const minX = Math.min(...xs),
    maxX = Math.max(...xs),
    minZ = Math.min(...zs),
    maxZ = Math.max(...zs);
  state.bounds = {
    cx: (minX + maxX) / 2,
    cz: (minZ + maxZ) / 2,
    span: Math.max(maxX - minX, maxZ - minZ, 1200) * 1.18,
  };
}
function canvas(id) {
  const element = $(id),
    ratio = devicePixelRatio || 1;
  const width = element.clientWidth,
    height = element.clientHeight;
  if (
    element.width !== Math.round(width * ratio) ||
    element.height !== Math.round(height * ratio)
  ) {
    element.width = Math.round(width * ratio);
    element.height = Math.round(height * ratio);
  }
  const ctx = element.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, width, height);
  return [ctx, width, height];
}
function drawMap() {
  if (!document.querySelector(".trajectory-overview").open) return;
  const [ctx, width, height] = canvas("map");
  if (!state.bounds) return;
  const { cx, cz, span } = state.bounds,
    scale = Math.min(width, height) / span;
  const point = (p) => [
    (p[0] - cx) * scale + width / 2,
    (p[2] - cz) * scale + height / 2,
  ];
  ctx.strokeStyle = "#283234";
  ctx.lineWidth = 1;
  for (
    let x = Math.floor((cx - width / scale / 2) / 400) * 400;
    x < cx + width / scale / 2;
    x += 400
  ) {
    const px = point([x, 0, cz])[0];
    ctx.beginPath();
    ctx.moveTo(px, 0);
    ctx.lineTo(px, height);
    ctx.stroke();
  }
  for (
    let z = Math.floor((cz - height / scale / 2) / 400) * 400;
    z < cz + height / scale / 2;
    z += 400
  ) {
    const py = point([cx, 0, z])[1];
    ctx.beginPath();
    ctx.moveTo(0, py);
    ctx.lineTo(width, py);
    ctx.stroke();
  }
  function path(end, color, lineWidth) {
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    for (let i = 0; i <= end; i++) {
      const r = state.records[i],
        [x, y] = point(r.observation.position),
        last = state.records[i - 1];
      if (
        !i ||
        r.observation.died ||
        r.observation.level !== last.observation.level ||
        r.observation.area !== last.observation.area
      )
        ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  path(state.records.length - 1, "#414c4e", 1.4);
  path(state.index, "#f6a36d", 2);
  const [sx, sy] = point(state.records[0].observation.position);
  ctx.fillStyle = "#9fbd99";
  ctx.beginPath();
  ctx.arc(sx, sy, 3.5, 0, Math.PI * 2);
  ctx.fill();
  const [x, y] = point(state.records[state.index].observation.position);
  ctx.fillStyle = "#f6a36d22";
  ctx.beginPath();
  ctx.arc(x, y, 12, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#f6a36d";
  ctx.beginPath();
  ctx.arc(x, y, 4, 0, Math.PI * 2);
  ctx.fill();
}
function drawController(action) {
  const [ctx, w, h] = canvas("stick");
  const cx = w / 2,
    cy = h / 2,
    radius = Math.min(w, h) * 0.38;
  ctx.strokeStyle = "#414d50";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(cx - radius, cy);
  ctx.lineTo(cx + radius, cy);
  ctx.moveTo(cx, cy - radius);
  ctx.lineTo(cx, cy + radius);
  ctx.stroke();
  const x = cx + (action.stick_x / 80) * radius,
    y = cy - (action.stick_y / 80) * radius;
  ctx.strokeStyle = "#f6a36d";
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(x, y);
  ctx.stroke();
  ctx.fillStyle = "#f6a36d";
  ctx.beginPath();
  ctx.arc(x, y, 5, 0, Math.PI * 2);
  ctx.fill();
  for (const button of ["a", "b", "z", "start"])
    $(`button-${button}`).classList.toggle("pressed", Boolean(action[button]));
  $("stick-value").textContent = `X ${action.stick_x} · Y ${action.stick_y}`;
}
function drawHeight() {
  const [ctx, w, h] = canvas("height-chart"),
    ys = state.records.map((r) => r.observation.position[1]);
  const low = Math.min(...ys),
    span = Math.max(100, Math.max(...ys) - low),
    px = (i) => 8 + (i / (ys.length - 1 || 1)) * (w - 16),
    py = (y) => h - 10 - ((y - low) / span) * (h - 24);
  ctx.beginPath();
  ys.forEach((y, i) =>
    i ? ctx.lineTo(px(i), py(y)) : ctx.moveTo(px(i), py(y)),
  );
  ctx.strokeStyle = "#829995";
  ctx.lineWidth = 1.2;
  ctx.stroke();
  ctx.strokeStyle = "#f6a36d";
  ctx.beginPath();
  ctx.moveTo(px(state.index), 4);
  ctx.lineTo(px(state.index), h - 4);
  ctx.stroke();
}
function seek(index, updateCursor = true) {
  state.index = Math.max(
    0,
    Math.min(state.records.length - 1, Math.round(index)),
  );
  const r = state.records[state.index];
  if (!r) return;
  if (updateCursor) state.cursor = r.frame;
  if (updateCursor && state.session) {
    const params = new URLSearchParams({
      run: state.run,
      session: state.session.id,
      frame: r.frame,
    });
    history.replaceState(null, "", `#${params}`);
  }
  $("timeline").value = state.index;
  $("time").textContent =
    `${clock(r.frame)} / ${clock(state.records.at(-1).frame)}`;
  $("decision").textContent =
    r.step < 0 ? "INITIAL STATE" : `DECISION ${r.step + 1}`;
  const o = r.observation;
  if (state.task) {
    const collected =
      state.task.success_frame != null && r.frame >= state.task.success_frame;
    const phase = r.policy?.phase?.replaceAll("_", " ") || "navigate";
    $("skill").textContent = collected
      ? `Objective completed · saved progress confirmed at frame ${state.task.success_frame}`
      : `Skill: ${phase} · ${o.stars ?? 0} stars${r.policy?.post_drop != null ? ` · post depressed ${number(r.policy.post_drop)} / 190 units` : ""}`;
  }
  $("position").textContent = o.position.map(number).join(" / ");
  $("velocity").textContent = o.velocity.map((v) => v.toFixed(1)).join(" / ");
  $("health").textContent = `${o.health} / 8 · ${o.coins ?? "—"} coins`;
  $("action").textContent =
    o.mario_action == null
      ? "—"
      : `0x${(o.mario_action >>> 0).toString(16).padStart(8, "0")}`;
  $("level").textContent = `LEVEL ${o.level ?? "—"} · AREA ${o.area ?? "—"}`;
  const displayFrame =
    $("state-basis").value === "input"
      ? state.records[state.index - 1]?.frame
      : r.frame;
  const image =
    displayFrame == null ? null : nearestImage(state.frames, displayFrame);
  $("frame-label").textContent = image
    ? `IMAGE F${image.frame}${image.frame !== displayFrame ? ` · STATE F${displayFrame} (sparse recording)` : ""}`
    : "NO IMAGE AT THIS STATE";
  $("game-frame").hidden = !image;
  $("frame-empty").hidden = Boolean(image);
  if (image && $("game-frame").getAttribute("src") !== image.url)
    $("game-frame").src = image.url;
  drawMap();
  drawController(r.action);
  drawHeight();
  updateOracle(r, image);
}

async function updateOracle(record, image) {
  if (!oracleData) return;
  const request = ++oracleRequest,
    basis = $("state-basis").value;
  oracleView?.setPending(
    basis === "input"
      ? (state.records[state.index - 1]?.frame ?? "?")
      : record.frame,
  );
  try {
    // Pages index displayed observations, which can be sampled from many decisions.
    const { input, output } = await oracleData.get(state.index);
    if (request !== oracleRequest) return;
    showDecision(record, input, output);
    oracleView?.update({
      record,
      input,
      output,
      basis,
      imageFrame: image?.frame,
      history: state.records.slice(
        Math.max(0, state.index - 150),
        state.index + 1,
      ),
    });
  } catch (error) {
    if (request === oracleRequest && error.name !== "AbortError") {
      oracleView?.unavailable(error.message);
      $("decision-caption").textContent = error.message;
    }
  }
}
function populateDebugEvents() {
  const kind = $("debug-event-kind").value;
  const events = (state.debugEvents || []).filter(
    (e) => kind === "all" || e.kind === kind,
  );
  $("debug-event").replaceChildren(
    ...events.map((e) => {
      const option = document.createElement("option");
      option.value = e.frame;
      option.textContent = `${clock(e.frame)} · ${e.label}`;
      return option;
    }),
  );
  $("jump-debug-event").disabled = !events.length;
}
$("debug-event-kind").addEventListener("change", populateDebugEvents);
$("jump-debug-event").addEventListener("click", () => {
  pause();
  const frame = Number($("debug-event").value);
  seek(state.records.findIndex((r) => r.frame >= frame));
});
$("align-image").addEventListener("click", () => {
  if (!state.records.length) return;
  const r = state.records[state.index],
    image = nearestImage(state.frames, r.frame);
  if (image) {
    pause();
    $("state-basis").value = "output";
    seek(state.records.findIndex((r) => r.frame >= image.frame));
  }
});
$("state-basis").addEventListener("change", () => {
  pause();
  if (state.records.length) seek(state.index);
});
document
  .querySelector(".trajectory-overview")
  .addEventListener("toggle", () => {
    if (state.records.length) drawMap();
  });
function animate(now) {
  if (state.playing && state.records.length) {
    state.cursor +=
      ((now - state.lastTick) / 1000) * 30 * Number($("speed").value);
    state.lastTick = now;
    let index = state.index;
    while (
      index + 1 < state.records.length &&
      state.records[index + 1].frame <= state.cursor
    )
      index++;
    if (index !== state.index) seek(index, false);
    if (state.cursor >= state.records.at(-1).frame) pause(true);
  }
  requestAnimationFrame(animate);
}
$("run").addEventListener("change", (event) =>
  loadRun(event.target.value).catch(fail),
);
$("refresh").addEventListener("click", () => loadRuns().catch(fail));
$("play").addEventListener("click", togglePlay);
$("previous").addEventListener("click", () => {
  pause();
  seek(state.index - 1);
});
$("next").addEventListener("click", () => {
  pause();
  seek(state.index + 1);
});
$("timeline").addEventListener("input", (event) => {
  pause();
  seek(Number(event.target.value));
});
$("game-frame").addEventListener("error", () =>
  notice(
    "A recorded image could not be loaded. The state trace is still available.",
  ),
);
document.addEventListener("keydown", (event) => {
  if (
    ["INPUT", "SELECT", "TEXTAREA", "BUTTON", "CANVAS", "SUMMARY"].includes(
      event.target.tagName,
    ) ||
    !state.records.length
  )
    return;
  if (event.code === "Space") {
    event.preventDefault();
    togglePlay();
  }
  if (event.code === "ArrowRight") {
    event.preventDefault();
    pause();
    seek(state.index + 1);
  }
  if (event.code === "ArrowLeft") {
    event.preventDefault();
    pause();
    seek(state.index - 1);
  }
});
window.addEventListener("resize", () => {
  if (state.records.length) seek(state.index);
});
window.addEventListener("hashchange", () => {
  const params = new URLSearchParams(location.hash.slice(1));
  const run = params.get("run"),
    session = params.get("session");
  if (!state.runs.some((item) => item.id === run)) return;
  if (run !== state.run || session !== state.session?.id) {
    $("run").value = run;
    loadRun(run, session).catch(fail);
  } else if (params.has("frame")) {
    pause();
    const index = state.records.findIndex(
      (r) => r.frame >= Number(params.get("frame")),
    );
    seek(index < 0 ? state.records.length - 1 : index);
  }
});
loadRuns().catch(fail);
requestAnimationFrame(animate);
