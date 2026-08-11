import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";

const viewport = document.querySelector("#viewport");
const annotationLayer = document.querySelector("#annotation-layer");
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setClearColor(0x101317);
viewport.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const root = new THREE.Group();
scene.add(root);
scene.add(new THREE.HemisphereLight(0xffffff, 0x26313d, 2.3));
const key = new THREE.DirectionalLight(0xffffff, 2.0);
key.position.set(4, -6, 8);
scene.add(key);

let perspective = false;
const cameras = {
  perspective: new THREE.PerspectiveCamera(42, 1, 0.01, 100000),
  orthographic: new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 100000),
};
let camera = cameras.orthographic;
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.screenSpacePanning = true;

const grid = new THREE.GridHelper(200, 40, 0x46617c, 0x293643);
grid.rotation.x = Math.PI / 2;
scene.add(grid);
const axes = new THREE.AxesHelper(30);
axes.visible = false;
scene.add(axes);

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const meshes = [];
const meshByName = new Map();
const annotationItems = [];
const measurePoints = [];
let measureMode = false;
let measureLine = null;
let markers = [];
let wireframe = false;
let transparent = false;
let annotationsVisible = true;
let bounds = new THREE.Box3();
let initialView = null;

function activeMaterial(mesh) {
  mesh.material.wireframe = wireframe;
  mesh.material.transparent = transparent;
  mesh.material.opacity = transparent ? 0.35 : 1;
  mesh.material.depthWrite = !transparent;
  mesh.material.needsUpdate = true;
}

function resize() {
  const width = viewport.clientWidth;
  const height = viewport.clientHeight;
  renderer.setSize(width, height, false);
  cameras.perspective.aspect = width / height;
  cameras.perspective.updateProjectionMatrix();
  updateOrtho(width / height);
}

function updateOrtho(aspect = viewport.clientWidth / viewport.clientHeight) {
  const size = initialView?.orthoSize || 100;
  cameras.orthographic.left = -size * aspect;
  cameras.orthographic.right = size * aspect;
  cameras.orthographic.top = size;
  cameras.orthographic.bottom = -size;
  cameras.orthographic.updateProjectionMatrix();
}

function fitView() {
  bounds.setFromObject(root);
  if (bounds.isEmpty()) return;
  const sphere = bounds.getBoundingSphere(new THREE.Sphere());
  const center = sphere.center;
  const radius = Math.max(sphere.radius, 1);
  const direction = new THREE.Vector3(1.3, -1.6, 1.1).normalize();
  const position = center.clone().add(direction.multiplyScalar(radius * 3.2));
  for (const item of Object.values(cameras)) {
    item.position.copy(position);
    item.up.set(0, 0, 1);
    item.lookAt(center);
  }
  controls.target.copy(center);
  cameras.perspective.near = Math.max(radius / 1000, 0.01);
  cameras.perspective.far = radius * 100;
  cameras.perspective.updateProjectionMatrix();
  initialView = { center: center.clone(), position: position.clone(), orthoSize: radius * 1.25 };
  updateOrtho();
  controls.update();
}

function resetView() {
  if (!initialView) return;
  camera.position.copy(initialView.position);
  controls.target.copy(initialView.center);
  controls.update();
}

function switchCamera() {
  const previous = camera;
  perspective = !perspective;
  camera = perspective ? cameras.perspective : cameras.orthographic;
  camera.position.copy(previous.position);
  camera.quaternion.copy(previous.quaternion);
  controls.object = camera;
  controls.update();
  document.querySelector("#camera").textContent = perspective ? "Perspective" : "Orthographic";
}

function clearMeasurement() {
  measurePoints.length = 0;
  markers.forEach((marker) => scene.remove(marker));
  markers = [];
  if (measureLine) scene.remove(measureLine);
  measureLine = null;
  document.querySelector("#measurement").textContent =
    "Select Measure, then click two surface points.";
}

function addMeasurePoint(point) {
  if (measurePoints.length === 2) clearMeasurement();
  measurePoints.push(point.clone());
  const marker = new THREE.Mesh(
    new THREE.SphereGeometry(
      Math.max(bounds.getBoundingSphere(new THREE.Sphere()).radius * 0.01, 0.15),
      16,
      12,
    ),
    new THREE.MeshBasicMaterial({ color: 0xffd166 }),
  );
  marker.position.copy(point);
  scene.add(marker);
  markers.push(marker);
  if (measurePoints.length === 2) {
    const geometry = new THREE.BufferGeometry().setFromPoints(measurePoints);
    measureLine = new THREE.Line(geometry, new THREE.LineBasicMaterial({ color: 0xffd166 }));
    scene.add(measureLine);
    const distance = measurePoints[0].distanceTo(measurePoints[1]);
    document.querySelector("#measurement").textContent = `${distance.toFixed(3)} mm`;
  } else {
    document.querySelector("#measurement").textContent = "Select the second point.";
  }
}

renderer.domElement.addEventListener("pointerdown", (event) => {
  if (!measureMode) return;
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObjects(
    meshes.filter((mesh) => mesh.visible),
    false,
  )[0];
  if (hit) addMeasurePoint(hit.point);
});

function bindButtons() {
  document.querySelector("#fit").onclick = fitView;
  document.querySelector("#reset").onclick = resetView;
  document.querySelector("#camera").onclick = switchCamera;
  document.querySelector("#wireframe").onclick = (event) => {
    wireframe = !wireframe;
    event.currentTarget.classList.toggle("active", wireframe);
    meshes.forEach(activeMaterial);
  };
  document.querySelector("#transparent").onclick = (event) => {
    transparent = !transparent;
    event.currentTarget.classList.toggle("active", transparent);
    meshes.forEach(activeMaterial);
  };
  document.querySelector("#grid").onclick = (event) => {
    grid.visible = !grid.visible;
    event.currentTarget.classList.toggle("active", grid.visible);
  };
  document.querySelector("#axes").onclick = (event) => {
    axes.visible = !axes.visible;
    event.currentTarget.classList.toggle("active", axes.visible);
  };
  document.querySelector("#annotations").onclick = (event) => {
    annotationsVisible = !annotationsVisible;
    event.currentTarget.classList.toggle("active", annotationsVisible);
    annotationLayer.hidden = !annotationsVisible;
  };
  document.querySelector("#measure").onclick = (event) => {
    measureMode = !measureMode;
    event.currentTarget.classList.toggle("active", measureMode);
    controls.enabled = !measureMode;
  };
  document.querySelector("#clear-measurement").onclick = clearMeasurement;
  document.querySelector("#explode").oninput = (event) => {
    const amount =
      Number(event.target.value) * Math.max(bounds.getSize(new THREE.Vector3()).x, 20) * 0.65;
    meshes.forEach((mesh, index) => {
      mesh.position.x = (index - (meshes.length - 1) / 2) * amount;
    });
  };
}

function formatNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  return Number.isInteger(number) ? number.toFixed(0) : number.toFixed(2);
}

function addReviewData(manifest) {
  const annotationList = document.querySelector("#annotation-list");
  const deltaList = document.querySelector("#delta-list");
  const annotations = manifest.annotations || [];
  const deltas = manifest.deltas || [];

  if (!annotations.length) {
    annotationList.innerHTML = '<p class="review-empty">No review annotations.</p>';
  }
  for (const annotation of annotations) {
    const label = document.createElement("div");
    label.className = "annotation-label";
    label.textContent = `${annotation.id}: ${annotation.label}`;
    label.style.setProperty("--annotation-color", annotation.color || "#ffd166");
    annotationLayer.appendChild(label);
    annotationItems.push({ annotation, label });

    const row = document.createElement("button");
    row.className = "review-item";
    row.style.setProperty("--annotation-color", annotation.color || "#ffd166");
    const title = document.createElement("strong");
    title.textContent = `${annotation.id}: ${annotation.label}`;
    const details = document.createElement("small");
    details.textContent = `${annotation.part || "assembly"} at (${annotation.position_mm.map(formatNumber).join(", ")}) mm${annotation.description ? ` — ${annotation.description}` : ""}`;
    row.append(title, details);
    row.onclick = () => {
      const target = new THREE.Vector3(...annotation.position_mm);
      const partMesh = annotation.part ? meshByName.get(annotation.part) : null;
      if (partMesh) target.add(partMesh.position);
      controls.target.copy(target);
      controls.update();
    };
    annotationList.appendChild(row);
  }

  if (!deltas.length) {
    deltaList.innerHTML = '<p class="review-empty">No position change is pending.</p>';
  }
  for (const delta of deltas) {
    const row = document.createElement("div");
    row.className = "review-item";
    const value = document.createElement("strong");
    const signedDelta = Number(delta.delta) >= 0 ? `+${formatNumber(delta.delta)}` : formatNumber(delta.delta);
    value.textContent = `${delta.annotation_id} · ${delta.parameter}: ${formatNumber(delta.before)} → ${formatNumber(delta.after)} ${delta.unit} (${signedDelta} ${delta.unit})`;
    const details = document.createElement("small");
    details.textContent = `${delta.direction}. ${delta.reason}`;
    const status = document.createElement("small");
    status.className = "delta-status";
    status.textContent = delta.review_status;
    row.append(value, details, status);
    deltaList.appendChild(row);
  }
}

function updateAnnotations() {
  if (!annotationsVisible) return;
  const width = viewport.clientWidth;
  const height = viewport.clientHeight;
  for (const item of annotationItems) {
    const point = new THREE.Vector3(...item.annotation.position_mm);
    const partMesh = item.annotation.part ? meshByName.get(item.annotation.part) : null;
    if (partMesh) point.add(partMesh.position);
    point.project(camera);
    const visible = point.z >= -1 && point.z <= 1;
    item.label.hidden = !visible;
    if (!visible) continue;
    item.label.style.left = `${(point.x * 0.5 + 0.5) * width}px`;
    item.label.style.top = `${(-point.y * 0.5 + 0.5) * height}px`;
  }
}

async function load() {
  bindButtons();
  const manifest = await fetch("manifest.json").then((response) => response.json());
  document.querySelector("#title").textContent = manifest.title;
  document.title = manifest.title;
  const loader = new STLLoader();
  const partList = document.querySelector("#parts");
  await Promise.all(
    manifest.parts.map(async (part, index) => {
      const geometry = await loader.loadAsync(part.file);
      geometry.computeVertexNormals();
      const material = new THREE.MeshStandardMaterial({
        color: part.color,
        roughness: 0.72,
        metalness: 0.02,
        side: THREE.DoubleSide,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.name = part.name;
      mesh.userData.baseX = 0;
      root.add(mesh);
      meshes[index] = mesh;
      meshByName.set(part.name, mesh);
      const row = document.createElement("label");
      row.className = "part";
      row.innerHTML = `<input type="checkbox" checked><span class="swatch" style="background:${part.color}"></span><span>${part.name}</span>`;
      row.querySelector("input").onchange = (event) => {
        mesh.visible = event.target.checked;
      };
      partList.appendChild(row);
    }),
  );
  addReviewData(manifest);
  fitView();
  document.querySelector("#status").textContent =
    `${meshes.length} component${meshes.length === 1 ? "" : "s"} loaded. Units: mm.`;
}

function animate() {
  controls.update();
  updateAnnotations();
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

new ResizeObserver(resize).observe(viewport);
resize();
load().catch((error) => {
  document.querySelector("#status").textContent = `Preview error: ${error.message}`;
  console.error(error);
});
animate();
