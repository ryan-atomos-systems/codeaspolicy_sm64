const $ = (id) => document.getElementById(id);
const video = $("rollout-video");
const rate = $("playback-rate");
const setRate = () => { video.playbackRate = Number(rate.value); };
rate.addEventListener("change", setRate);
video.addEventListener("loadedmetadata", setRate);
const chapters = [...document.querySelectorAll(".chapters [data-seek]")];
document.querySelectorAll("[data-seek]").forEach((button) => {
  button.addEventListener("click", async () => {
    const target = Number(button.dataset.seek) / 30;
    if (video.readyState < 1) {
      await new Promise((resolve) => video.addEventListener("loadedmetadata", resolve, { once: true }));
    }
    video.currentTime = Math.min(target, video.duration);
    if (button.classList.contains("time-link")) $("rollout").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
    try { await video.play(); } catch { $("video-status").textContent = "Chapter selected. Press play to start the recording."; }
  });
});
video.addEventListener("timeupdate", () => {
  const active = chapters.filter((b) => Number(b.dataset.seek) <= video.currentTime * 30).at(-1);
  chapters.forEach((b) => { b.classList.toggle("active", b === active); b.setAttribute("aria-pressed", String(b === active)); });
});
video.addEventListener("error", () => { $("video-status").textContent = "The recording could not be loaded. Download the MP4 or reload the page."; });

let excerpt, view, index = 0;
const slider = $("decision-frame");
function showDecision() {
  const record = excerpt.records[index];
  const input = index ? excerpt.records[index - 1].observation : excerpt.initial_observation;
  const output = record.observation;
  const gate = record.policy.decision?.gates?.find((g) => g.name === "Ground-pound window");
  const basis = $("state-basis").value;
  const observation = basis === "input" ? input : output;
  const imageFrame = Math.floor(observation.frame / 3) * 3;
  const padded = String(imageFrame).padStart(8, "0");
  $("decision-image").src = `media/decision/${padded}.png`;
  $("decision-image").alt = `Mario at recorded game frame ${imageFrame}`;
  $("image-frame").textContent = `F${imageFrame}`;
  $("image-caption").textContent = `Image F${imageFrame} · ${basis === "input" ? "input" : "outcome"} F${observation.frame}${imageFrame === observation.frame ? " · aligned" : ` · ${observation.frame - imageFrame} frame offset`}`;
  $("frame-number").textContent = record.frame;
  slider.value = record.frame;
  $("previous-decision").disabled = index === 0;
  $("next-decision").disabled = index === excerpt.records.length - 1;
  $("decision-timing").textContent = `Input F${input.frame} → action held 1 frame → outcome F${output.frame}`;
  function measurement(id, value) {
    $(id).replaceChildren(document.createTextNode(Number.isFinite(value) ? value.toFixed(2) + " " : "— "));
    const unit = document.createElement("small"); unit.textContent = "units"; $(id).append(unit);
  }
  measurement("horizontal-error", gate?.horizontal_error);
  measurement("height-error", gate?.height_above_top);
  $("motion-state").textContent = input.mario.airborne ? "Airborne" : "Grounded";
  const conditions = gate?.conditions || {};
  [["horizontal-gate", "horizontal error < 32", "< 32"], ["height-gate", "feet above post top + 5", "> 5"], ["airborne-gate", "airborne", "Required"]].forEach(([id, key, label]) => {
    const result = conditions[key]; $(id).textContent = result == null ? "Not recorded" : `${label} ${result ? "✓" : "✕"}`;
    $(id).className = `gate ${result ? "pass" : "fail"}`;
  });
  const buttons = ["a", "b", "z"].filter((b) => record.action[b]).map((b) => b.toUpperCase());
  $("chosen-action").textContent = buttons.join(" + ") || "Released";
  $("chosen-stick").textContent = `stick ${record.action.stick_x} / ${record.action.stick_y}`;
  view?.update({ record, input, output, history: excerpt.records.slice(0, index + 1), basis, imageFrame });
}
async function loadDecision() {
  try {
    const response = await fetch("media/decision.json");
    if (!response.ok) throw new Error("Recorded excerpt unavailable");
    excerpt = await response.json();
    slider.min = excerpt.records[0].frame;
    slider.max = excerpt.records.at(-1).frame;
    index = excerpt.records.findIndex((r) => r.frame === 1467);
    if (index < 0) index = 0;
    try {
      const { StateView } = await import("./viewer/state-view.js");
      view = new StateView();
    } catch (error) {
      $("scene-fallback").hidden = false;
      document.querySelectorAll("[data-view], [data-layer], #expand-state, #object-picker, #focus-object").forEach((control) => { control.disabled = true; });
      console.warn("3D view unavailable:", error.message);
      $("demo-status").textContent = "Recorded values loaded. 3D rendering is unavailable in this browser.";
    }
    showDecision();
    slider.disabled = false;
    slider.addEventListener("input", () => { index = Number(slider.value) - Number(slider.min); showDecision(); });
    $("previous-decision").addEventListener("click", () => { index = Math.max(0, index - 1); showDecision(); });
    $("next-decision").addEventListener("click", () => { index = Math.min(excerpt.records.length - 1, index + 1); showDecision(); });
    $("state-basis").addEventListener("change", showDecision);
    if (view) $("demo-status").textContent = "Recorded excerpt · 55 consecutive decisions · no policy code executes in the browser.";
  } catch (error) {
    $("demo-status").textContent = "The interactive excerpt could not load. The example above shows the recorded frame 1467; reload to try again.";
    console.warn(error.message);
  } finally { document.querySelector(".decision-demo").setAttribute("aria-busy", "false"); }
}
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) { observer.disconnect(); loadDecision(); }
  }, { rootMargin: "400px" });
  observer.observe($("decision"));
} else loadDecision();
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && $("state-panel").classList.contains("expanded")) $("expand-state").click();
});
