import * as THREE from "./vendor/three.module.min.js";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { intentFor, objectKind, sameArea } from "./debug-model.js";

const $ = (id) => document.getElementById(id);
const COLORS = {
  mario: 0xf6a36d,
  ghost: 0x77cbe6,
  floor: 0x75c9ac,
  wall: 0xf5827d,
  ceiling: 0xb29ae7,
  ray: 0x598497,
  reward: 0xffd15d,
  coin: 0xffd15d,
  platform: 0x60b9c3,
  enemy: 0xf17e76,
  portal: 0xad96e3,
  object: 0x9baabb,
  intent: 0xffd15d,
};
const vec = (p) => new THREE.Vector3(...p);
const textVec = (p) =>
  p?.map((v) => Number(v.toFixed(1))).join(" / ") ?? "Unknown";
const angle = (a) => (a * Math.PI * 2) / 65536;

export class StateView {
  constructor() {
    this.canvas = $("oracle-canvas");
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x10191f);
    this.camera = new THREE.PerspectiveCamera(48, 1, 5, 70000);
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
    });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.controls = new OrbitControls(this.camera, this.canvas);
    this.controls.minDistance = 180;
    this.controls.maxDistance = 20000;
    this.controls.maxPolarAngle = Math.PI * 0.95;
    this.controls.addEventListener("change", () => this.render());
    this.mode = "follow";
    this.focus = null;
    this.lastArea = null;
    this.selected = "mario";
    this.layers = {};
    this.pickables = [];
    this.materials = new Map();
    this.labels = [];
    for (const name of [
      "mario",
      "ghost",
      "geometry",
      "objects",
      "hitboxes",
      "rays",
      "camera",
      "intent",
      "trail",
      "grid",
    ]) {
      const group = new THREE.Group();
      this.layers[name] = group;
      this.scene.add(group);
    }
    this.shapes = {
      capsule: new THREE.CapsuleGeometry(35, 90, 4, 10),
      sphere: new THREE.SphereGeometry(1, 12, 8),
      box: new THREE.BoxGeometry(1, 1, 1),
      cylinder: new THREE.CylinderGeometry(1, 1, 1, 16, 1, true),
      diamond: new THREE.OctahedronGeometry(1),
    };
    const grid = new THREE.GridHelper(6000, 30, 0x3b5660, 0x20353e);
    grid.material.transparent = true;
    grid.material.opacity = 0.6;
    this.layers.grid.add(grid);
    this.grid = grid;
    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.controls.target.set(0, 70, 0);
    this.camera.position.set(1200, 1050, 1450);
    this.controls.update();
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(this.canvas.parentElement);
    let down;
    this.canvas.addEventListener("pointerdown", (e) => {
      down = [e.clientX, e.clientY];
    });
    this.canvas.addEventListener("pointerup", (e) => {
      if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 5)
        return;
      this.pick(e);
      down = null;
    });
    this.canvas.addEventListener("keydown", (e) => {
      if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key))
        return;
      e.preventDefault();
      e.stopPropagation();
      const offset = this.camera.position.clone().sub(this.controls.target);
      const spherical = new THREE.Spherical().setFromVector3(offset);
      spherical.theta +=
        e.key === "ArrowLeft" ? 0.12 : e.key === "ArrowRight" ? -0.12 : 0;
      spherical.phi = Math.max(
        0.05,
        Math.min(
          Math.PI - 0.05,
          spherical.phi +
            (e.key === "ArrowUp" ? -0.12 : e.key === "ArrowDown" ? 0.12 : 0),
        ),
      );
      this.camera.position
        .copy(this.controls.target)
        .add(new THREE.Vector3().setFromSpherical(spherical));
      this.controls.update();
    });
    document
      .querySelectorAll("[data-view]")
      .forEach((button) =>
        button.addEventListener("click", () =>
          this.setMode(button.dataset.view),
        ),
      );
    document.querySelectorAll("[data-layer]").forEach((input) => {
      this.layers[input.dataset.layer].visible = input.checked;
      input.addEventListener("change", () => {
        this.layers[input.dataset.layer].visible = input.checked;
        this.render();
      });
    });
    $("object-picker").addEventListener("change", (e) => {
      this.selected = e.target.value;
      this.inspect();
      this.highlight();
      this.render();
    });
    $("focus-object").addEventListener("click", () => {
      const o = this.selectedObject();
      if (!o) return;
      this.mode = "orbit";
      this.setButtons();
      const target = vec(o.position).add(new THREE.Vector3(0, 60, 0));
      this.camera.position.add(target.clone().sub(this.controls.target));
      this.controls.target.copy(target);
      this.controls.update();
    });
    $("expand-state").addEventListener("click", () => {
      const expanded = $("state-panel").classList.toggle("expanded");
      $("expand-state").textContent = expanded
        ? "Close expanded view"
        : "Expand";
      this.resize();
    });
  }
  material(color, opacity = 1, wireframe = false) {
    const key = [color, opacity, wireframe].join(":");
    if (!this.materials.has(key))
      this.materials.set(
        key,
        new THREE.MeshBasicMaterial({
          color,
          opacity,
          transparent: opacity < 1,
          side: THREE.DoubleSide,
          depthWrite: opacity === 1,
          wireframe,
        }),
      );
    return this.materials.get(key);
  }
  mesh(shape, color, opacity = 1, wireframe = false) {
    return new THREE.Mesh(
      this.shapes[shape],
      this.material(color, opacity, wireframe),
    );
  }
  line(points, color, opacity = 1, group = "intent") {
    const geometry = new THREE.BufferGeometry().setFromPoints(
      points.map((p) => (Array.isArray(p) ? vec(p) : p)),
    );
    const material = new THREE.LineBasicMaterial({
      color,
      transparent: opacity < 1,
      opacity,
    });
    const line = new THREE.Line(geometry, material);
    line.userData.transient = true;
    this.layers[group].add(line);
    return line;
  }
  arrow(origin, direction, color, group) {
    const length = direction.length();
    if (length < 1) return;
    // Lines + a small cone make the vector direction readable without a lighting dependency.
    this.line([origin, origin.clone().add(direction)], color, 1, group);
    const cone = new THREE.Mesh(
      new THREE.ConeGeometry(
        Math.min(15, length * 0.13),
        Math.min(40, length * 0.3),
        8,
      ),
      this.material(color),
    );
    cone.position
      .copy(origin)
      .addScaledVector(
        direction,
        1 - Math.min(40, length * 0.3) / (2 * length),
      );
    cone.quaternion.setFromUnitVectors(
      new THREE.Vector3(0, 1, 0),
      direction.clone().normalize(),
    );
    cone.userData.ownGeometry = true;
    this.layers[group].add(cone);
  }
  clear() {
    this.labels = [];
    $("scene-labels").replaceChildren();
    this.pickables = [];
    for (const [name, group] of Object.entries(this.layers)) {
      if (name === "grid") continue;
      group.traverse((node) => {
        if (node.userData.transient) {
          node.geometry.dispose();
          node.material.dispose();
        } else if (node.userData.ownGeometry) node.geometry.dispose();
      });
      group.clear();
    }
    this.marker = null;
  }
  setPending(frame) {
    $("oracle-status").textContent = `Loading observation F${frame}…`;
    this.canvas.classList.add("loading-state");
  }
  reset() {
    this.selected = "mario";
    this.observation = null;
    this.lastArea = null;
    this.unavailable("Loading session observations…");
  }
  unavailable(message) {
    this.clear();
    this.data = null;
    this.layers.grid.visible = false;
    this.render();
    this.canvas.classList.remove("loading-state");
    $("oracle-status").textContent = message;
    $("oracle-coverage").textContent =
      "Rich state not available. Flat telemetry and playback remain usable.";
    $("object-picker").replaceChildren();
    $("contact-badge").textContent = "";
    $("object-inspector").textContent = "No oracle objects recorded.";
  }
  setMode(mode) {
    this.mode = mode;
    this.setButtons();
    if (!this.observation) return;
    const target = vec(this.observation.position).add(
      new THREE.Vector3(0, 70, 0),
    );
    if (mode === "top") {
      this.controls.target.copy(target);
      this.camera.position.copy(target).add(new THREE.Vector3(0, 2200, 1));
    } else if (mode === "follow" || mode === "orbit") {
      this.controls.target.copy(target);
      this.camera.position
        .copy(target)
        .add(new THREE.Vector3(1200, 1050, 1450));
    }
    this.camera.fov = 48;
    this.camera.updateProjectionMatrix();
    this.controls.update();
    if (mode === "camera") this.gameCamera();
    this.render();
  }
  setButtons() {
    document
      .querySelectorAll("[data-view]")
      .forEach((b) =>
        b.setAttribute("aria-pressed", String(b.dataset.view === this.mode)),
      );
  }
  gameCamera() {
    const c = this.observation?.camera;
    if (!c) return;
    this.camera.position.copy(vec(c.position));
    this.controls.target.copy(vec(c.focus));
    this.camera.fov = c.fov_degrees || 48;
    this.camera.updateProjectionMatrix();
    this.controls.update();
  }
  update({ record, input, output, history, basis = "output", imageFrame }) {
    this.data = { record, input, output };
    this.observation = basis === "input" ? input : output;
    const o = this.observation;
    if (!o?.mario) {
      this.unavailable("No rich oracle observation at this frame.");
      return;
    }
    this.clear();
    this.canvas.classList.remove("loading-state");
    const area = `${o.level}:${o.area}`,
      reset = this.lastArea !== area;
    const focus = vec(o.position).add(new THREE.Vector3(0, 70, 0));
    if (reset || !this.focus || this.mode === "follow" || this.mode === "top") {
      const change = focus.clone().sub(this.controls.target);
      this.camera.position.add(change);
      this.controls.target.copy(focus);
    }
    this.focus = focus;
    this.lastArea = area;
    this.camera.fov = 48;
    this.camera.updateProjectionMatrix();
    this.grid.position.set(
      Math.round(o.position[0] / 200) * 200,
      (o.mario.floor_height ?? o.position[1]) - 4,
      Math.round(o.position[2] / 200) * 200,
    );
    this.layers.grid.visible = document.querySelector(
      '[data-layer="grid"]',
    ).checked;
    this.addMario(o, "mario");
    if (sameArea(input, output) && input?.mario && basis === "output")
      this.addMario(input, "ghost");
    this.addGeometry(o);
    this.addObjects(o);
    this.addCamera(o);
    if (sameArea(input, o)) this.addIntent(record, input);
    this.addTrail(history, o);
    this.refreshPicker();
    this.inspect();
    this.highlight();
    if (this.mode === "camera") this.gameCamera();
    else this.controls.update();
    const imageLabel =
      imageFrame == null
        ? "no recorded image"
        : `image F${imageFrame}${imageFrame === o.frame ? " · aligned" : ` · ${o.frame - imageFrame} frame offset`}`;
    $("oracle-status").textContent =
      `${basis === "input" ? "POLICY INPUT" : "OUTCOME"} F${o.frame} · ${imageLabel}`;
    const motion = o.mario.swimming
      ? "Swimming"
      : o.mario.on_pole
        ? "On pole"
        : o.mario.hanging
          ? "Hanging"
          : o.mario.airborne
            ? "Airborne"
            : "Not airborne";
    const floor =
      o.mario.floor_height == null
        ? "no floor reference"
        : `${Math.round(o.position[1] - o.mario.floor_height)} above floor reference`;
    $("contact-badge").textContent = `${motion} · ${floor}`;
    const q = o.objects;
    $("oracle-coverage").textContent =
      `${q?.items.length ?? 0} / ${q?.total_in_radius ?? "?"} objects in ${q?.radius ?? "?"} units${q?.truncated ? " · QUERY TRUNCATED" : ""}. ${o.geometry?.rays.length ?? 0} rays. Only returned contact / ray-hit triangles are known; the grid is a ruler, not terrain.`;
    this.render();
  }
  addMario(o, group) {
    const ghost = group === "ghost",
      color = ghost ? COLORS.ghost : COLORS.mario;
    const body = this.mesh("capsule", color, ghost ? 0.25 : 1, ghost);
    body.position.copy(vec(o.position)).add(new THREE.Vector3(0, 80, 0));
    this.layers[group].add(body);
    if (!ghost) {
      body.userData.selection = "mario";
      this.pickables.push(body);
      this.label(
        "Mario",
        vec(o.position).add(new THREE.Vector3(0, 220, 0)),
        "#f6a36d",
        "mario",
      );
    }
    const yaw = angle(o.mario.face_angle[1]),
      origin = vec(o.position).add(new THREE.Vector3(0, 105, 0));
    this.arrow(
      origin,
      new THREE.Vector3(Math.sin(yaw) * 240, 0, Math.cos(yaw) * 240),
      ghost ? color : 0xeef4ee,
      group,
    );
    if (!ghost)
      this.arrow(origin, vec(o.velocity).multiplyScalar(6), 0x77cbe6, group);
  }
  addGeometry(o) {
    const seen = new Set();
    const surface = (s, color, label) => {
      if (!s) return;
      const key = JSON.stringify([s.object_id, s.vertices]);
      if (seen.has(key)) return;
      seen.add(key);
      const g = new THREE.BufferGeometry();
      g.setAttribute(
        "position",
        new THREE.Float32BufferAttribute(s.vertices.flat(), 3),
      );
      const mesh = new THREE.Mesh(g, this.material(color, 0.22));
      mesh.userData.ownGeometry = true;
      mesh.userData.surface = { label, ...s };
      this.layers.geometry.add(mesh);
      this.pickables.push(mesh);
      this.line([...s.vertices, s.vertices[0]], color, 0.6, "geometry");
    };
    for (const name of ["floor", "wall", "ceiling"])
      surface(o.mario[name], COLORS[name], `${name} reference`);
    for (const ray of o.geometry?.rays || []) {
      surface(ray.surface, COLORS.ray, `${ray.kind} ray hit`);
      const end =
        ray.hit_position ||
        vec(ray.origin)
          .addScaledVector(vec(ray.direction), ray.length)
          .toArray();
      this.line(
        [ray.origin, end],
        ray.hit_position ? 0x72bdb6 : 0x54616c,
        ray.hit_position ? 0.7 : 0.3,
        "rays",
      );
      if (ray.hit_position) {
        const dot = this.mesh("sphere", 0x8cddd0);
        dot.scale.setScalar(9);
        dot.position.copy(vec(end));
        this.layers.rays.add(dot);
      }
    }
  }
  addObjects(o) {
    for (const object of o.objects?.items || []) {
      const kind = objectKind(object),
        color = COLORS[kind];
      const radius = Math.max(20, Math.min(130, object.hitbox_radius || 40));
      const shape =
        kind === "platform" ? "box" : kind === "reward" ? "diamond" : "sphere";
      const mesh = this.mesh(shape, color, 0.9);
      if (kind === "platform") mesh.scale.set(230, 55, 180);
      else mesh.scale.setScalar(radius);
      mesh.position
        .copy(vec(object.position))
        .add(new THREE.Vector3(0, kind === "platform" ? 35 : radius, 0));
      mesh.userData.selection = String(object.id);
      this.layers.objects.add(mesh);
      this.pickables.push(mesh);
      if (object.hitbox_radius > 0 && object.hitbox_height > 0) {
        const bound = this.mesh("cylinder", color, 0.45, true);
        bound.scale.set(
          object.hitbox_radius,
          object.hitbox_height,
          object.hitbox_radius,
        );
        bound.position
          .copy(vec(object.position))
          .add(
            new THREE.Vector3(
              0,
              object.hitbox_height / 2 - object.hitbox_down_offset,
              0,
            ),
          );
        this.layers.hitboxes.add(bound);
      }
    }
  }
  addCamera(o) {
    const c = o.camera;
    if (!c) return;
    const origin = vec(c.position),
      forward = vec(c.focus).sub(origin).normalize();
    if (forward.length() < 0.1) return;
    let right = new THREE.Vector3()
      .crossVectors(forward, new THREE.Vector3(0, 1, 0))
      .normalize();
    if (right.length() < 0.1) right = new THREE.Vector3(1, 0, 0);
    const up = new THREE.Vector3().crossVectors(right, forward).normalize();
    right.applyAxisAngle(forward, angle(c.roll || 0));
    up.applyAxisAngle(forward, angle(c.roll || 0));
    const depth = Math.min(700, Math.max(150, origin.distanceTo(vec(c.focus))));
    const half = depth * Math.tan(((c.fov_degrees || 48) * Math.PI) / 360),
      aspect = c.image_size[0] / c.image_size[1];
    const center = origin.clone().addScaledVector(forward, depth);
    const corners = [
      [-1, -1],
      [1, -1],
      [1, 1],
      [-1, 1],
    ].map(([x, y]) =>
      center
        .clone()
        .addScaledVector(right, x * half * aspect)
        .addScaledVector(up, y * half),
    );
    for (const p of corners) this.line([origin, p], 0xa394dc, 0.6, "camera");
    this.line([...corners, corners[0]], 0xa394dc, 0.8, "camera");
    const icon = this.mesh("box", 0xa394dc);
    icon.scale.set(70, 45, 55);
    icon.position.copy(origin);
    this.layers.camera.add(icon);
  }
  addIntent(record, input) {
    const intent = intentFor(record, input);
    if (intent) {
      const point = vec(intent.position);
      this.line([input.position, point], COLORS.intent, 0.85, "intent");
      this.label(
        intent.projected ? "XZ target" : "Condition target",
        point.clone().add(new THREE.Vector3(0, 130, 0)),
        "#ffd15d",
        "intent",
      );
      const cross = 70;
      this.line(
        [
          point.clone().add(new THREE.Vector3(-cross, 0, 0)),
          point.clone().add(new THREE.Vector3(cross, 0, 0)),
        ],
        COLORS.intent,
        1,
        "intent",
      );
      this.line(
        [
          point.clone().add(new THREE.Vector3(0, 0, -cross)),
          point.clone().add(new THREE.Vector3(0, 0, cross)),
        ],
        COLORS.intent,
        1,
        "intent",
      );
      const marker = this.mesh("diamond", COLORS.intent, 0.9, true);
      marker.scale.setScalar(55);
      marker.position.copy(point).add(new THREE.Vector3(0, 70, 0));
      this.layers.intent.add(marker);
    }
    const route = record.policy?.decision?.route;
    if (route?.points_xz?.length > 1) {
      const points = route.points_xz.map((p) => [
        p[0],
        input.position[1] + 8,
        p[1],
      ]);
      this.line(points, 0xc4b16f, 0.5, "intent");
      for (let i = 0; i < points.length; i++) {
        const dot = this.mesh(
          "sphere",
          i === route.index ? 0xffd15d : 0x93815b,
        );
        dot.scale.setScalar(i === route.index ? 28 : 13);
        dot.position.copy(vec(points[i]));
        this.layers.intent.add(dot);
      }
    }
  }
  addTrail(history, o) {
    const tail = [];
    for (let i = history.length - 1; i >= 0; i--) {
      const p = history[i].observation;
      if (p.frame > o.frame) continue;
      if (!sameArea(p, o)) break;
      if (tail.length && vec(p.position).distanceTo(vec(tail.at(-1))) > 1800)
        break;
      tail.push(p.position);
      if (tail.length >= 120) break;
    }
    if (tail.length > 1) this.line(tail, 0xf6a36d, 0.6, "trail");
  }
  selectedObject() {
    if (this.selected === "mario") return this.observation?.mario;
    return this.observation?.objects?.items.find(
      (o) => String(o.id) === this.selected,
    );
  }
  refreshPicker() {
    const picker = $("object-picker"),
      entries = [
        ["mario", "Mario · pose and contacts"],
        ...(this.observation.objects?.items || []).map((o) => [
          String(o.id),
          `${o.behavior_name || "Unknown"} #${o.id} · ${Math.round(o.distance)} units`,
        ]),
      ];
    picker.replaceChildren(
      ...entries.map(([value, label]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        return option;
      }),
    );
    if (!entries.some(([id]) => id === this.selected)) {
      const option = document.createElement("option");
      option.value = this.selected;
      option.textContent = `#${this.selected} · not returned`;
      picker.append(option);
    }
    picker.value = this.selected;
  }
  inspect(surface = null) {
    const panel = $("object-inspector");
    panel.replaceChildren();
    const o = surface || this.selectedObject();
    if (!o) {
      panel.textContent =
        "Object not returned in this observation. It may be outside the radius, omitted by capacity, or inactive; absence alone does not prove removal.";
      return;
    }
    const title = document.createElement("strong");
    title.textContent = surface
      ? surface.label
      : this.selected === "mario"
        ? "Mario"
        : `${o.behavior_name || "Object"} #${o.id}`;
    panel.append(title);
    const entries = surface
      ? [
          ["Surface type", o.surface_type],
          ["Normal", textVec(o.normal)],
          ["Object ID", o.object_id ?? "Static"],
        ]
      : this.selected === "mario"
        ? [
            ["Position", textVec(o.position)],
            ["Velocity", textVec(o.velocity)],
            ["Forward speed", o.forward_velocity.toFixed(2)],
            ["Motion", o.airborne ? "Airborne" : "Not airborne"],
            [
              "Floor / wall reference",
              `${Boolean(o.floor)} / ${Boolean(o.wall)} (references ≠ guaranteed contact)`,
            ],
            ["Platform ID", o.platform_id ?? "None"],
          ]
        : [
            ["Position", textVec(o.position)],
            ["Velocity", textVec(o.velocity)],
            ["Action / sub-action", `${o.action} / ${o.sub_action}`],
            ["Health / timer", `${o.health} / ${o.timer}`],
            ["Hit radius / height", `${o.hitbox_radius} / ${o.hitbox_height}`],
            ["Hitbox down offset", o.hitbox_down_offset],
            ["Affordances", o.affordances.join(", ") || "None decoded"],
          ];
    const dl = document.createElement("dl");
    for (const [key, value] of entries) {
      const row = document.createElement("div"),
        dt = document.createElement("dt"),
        dd = document.createElement("dd");
      dt.textContent = key;
      dd.textContent = value;
      row.append(dt, dd);
      dl.append(row);
    }
    panel.append(dl);
    const details = document.createElement("details"),
      summary = document.createElement("summary"),
      pre = document.createElement("pre");
    summary.textContent = "Raw observed fields";
    pre.textContent = JSON.stringify(o, null, 2);
    details.append(summary, pre);
    panel.append(details);
  }
  highlight() {
    if (this.marker) {
      this.layers.objects.remove(this.marker);
      this.marker = null;
    }
    const o = this.selectedObject();
    if (!o || this.selected === "mario") return;
    const marker = this.mesh("sphere", 0xffffff, 0.6, true);
    marker.position.copy(vec(o.position)).add(new THREE.Vector3(0, 50, 0));
    marker.scale.setScalar(Math.max(65, Math.min(200, o.hitbox_radius || 65)));
    this.layers.objects.add(marker);
    this.marker = marker;
  }
  pick(event) {
    const r = this.canvas.getBoundingClientRect();
    this.pointer.set(
      ((event.clientX - r.left) / r.width) * 2 - 1,
      (-(event.clientY - r.top) / r.height) * 2 + 1,
    );
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hit = this.raycaster.intersectObjects(
      this.pickables.filter((o) => o.parent.visible),
      false,
    )[0];
    if (!hit) return;
    if (hit.object.userData.surface) {
      this.inspect(hit.object.userData.surface);
      return;
    }
    this.selected = hit.object.userData.selection;
    this.refreshPicker();
    this.inspect();
    this.highlight();
    this.render();
  }
  resize() {
    const w = this.canvas.parentElement.clientWidth,
      h = this.canvas.parentElement.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.render();
  }
  label(text, position, color, layer) {
    const node = document.createElement("span");
    node.textContent = text;
    node.style.color = color;
    $("scene-labels").append(node);
    this.labels.push({ node, position, layer });
  }
  render() {
    this.renderer.render(this.scene, this.camera);
    for (const { node, position, layer } of this.labels) {
      const p = position.clone().project(this.camera);
      node.hidden =
        !this.layers[layer].visible ||
        Math.abs(p.x) > 1 ||
        Math.abs(p.y) > 1 ||
        p.z < -1 ||
        p.z > 1;
      node.style.left = `${(p.x * 0.5 + 0.5) * this.canvas.clientWidth}px`;
      node.style.top = `${(-p.y * 0.5 + 0.5) * this.canvas.clientHeight}px`;
    }
  }
}
