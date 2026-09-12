import * as THREE from '/three/build/three.module.js';

const corpus = await (await fetch('../evidence/corpus.json')).json();
const worker = new Worker('./worker.mjs', {type: 'module'});
let seq = 0; const pending = new Map();
worker.onmessage = ({data}) => {
  const callback = pending.get(data.id); pending.delete(data.id);
  if (data.error) callback.reject(new Error(data.error)); else callback.resolve(data.result);
};
function request(op, extra = {}) {
  return new Promise((resolve, reject) => {
    const id = ++seq; pending.set(id, {resolve, reject});
    worker.postMessage({id, op, ...extra});
  });
}

const scene = new THREE.Scene(); scene.background = new THREE.Color('#182638');
const renderer = new THREE.WebGLRenderer({antialias: true, preserveDrawingBuffer: true});
renderer.setSize(1100, 480); renderer.setPixelRatio(1);
document.querySelector('#view').appendChild(renderer.domElement);
const camera = new THREE.PerspectiveCamera(40, 1100 / 480, .1, 100);
camera.position.set(0, -.25, 10); camera.lookAt(0, -.25, 0);
scene.add(new THREE.HemisphereLight(0xdaf2ff, 0x303040, 2.4));
const light = new THREE.DirectionalLight(0xffffff, 3); light.position.set(4, 7, 10); scene.add(light);
const brass = new THREE.MeshStandardMaterial({color: '#cdaa62', metalness: .65, roughness: .3});
const dark = new THREE.MeshStandardMaterial({color: '#274d64', metalness: .35, roughness: .45});
const orange = new THREE.MeshStandardMaterial({color: '#fba85a'});
const grey = new THREE.MeshStandardMaterial({color: '#647b8d'});

function label(text, width = 1.3, height = .5, color = '#f3f6fa') {
  const c = document.createElement('canvas'); c.width = text.length === 1 ? 128 : 256; c.height = 128;
  const ctx = c.getContext('2d'); ctx.clearRect(0, 0, 256, 100);
  ctx.fillStyle = color; ctx.font = 'bold 104px monospace'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(text, c.width/2, 68);
  return new THREE.Mesh(new THREE.PlaneGeometry(width, height), new THREE.MeshBasicMaterial({map: new THREE.CanvasTexture(c), transparent: true}));
}
function box(w, h, d, material, x, y, z) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
  mesh.position.set(x, y, z); scene.add(mesh); return mesh;
}
const wheels = [], shafts = [], levers = [];
for (let i = 0; i < 3; i++) {
  const x = (1-i)*3.8, g = new THREE.Group(); g.position.set(x, .65, 0); scene.add(g);
  const body = new THREE.Mesh(new THREE.CylinderGeometry(1.55, 1.55, .48, 80), brass);
  body.rotation.x = Math.PI / 2; g.add(body);
  for (let j = 0; j < 10; j++) {
    const a = -j * Math.PI / 5, glyph = label(String(j), .48, .48, '#101924');
    glyph.position.set(-Math.sin(a)*1.18, Math.cos(a)*1.18, .255); glyph.rotation.z = a; g.add(glyph);
  }
  wheels.push(g);
  const hub = new THREE.Mesh(new THREE.BoxGeometry(.15, 1, .12), dark); hub.position.z = .36; g.add(hub);
  box(.07, .35, .12, new THREE.MeshBasicMaterial({color: 'white'}), x, 2.4, .35);
  const caption = label(`W${i}`, 1, .35); caption.position.set(x, -1.32, .1); scene.add(caption);
  const shaft = box(1.2, .13, .14, grey, x, -2, .2); shafts.push(shaft);
  if (i) {
    const lever = box(.16, .8, .16, orange, x+1.7, -1.9, .25); levers.push(lever);
  }
}
const crank = box(1.1, .12, .15, orange, 0, -3, .2);
let running = false, busy = false, last = performance.now(), accumulator = 0;
function pose(state) {
  window.lastState = state;
  const radians = Math.PI / 180;
  wheels.forEach((mesh, i) => { mesh.rotation.z = state.q[`wheel${i}`] * radians; });
  shafts.forEach((mesh, i) => { mesh.rotation.z = state.q[`shaft${i}`] * radians; });
  levers.forEach((mesh, i) => { mesh.position.y = state.m[`latched${i+1}`] ? -2.25 : -1.9; });
  crank.rotation.z = state.q.crank * radians;
  document.querySelector('#state').textContent = `Elapsed ${(state.tick * state.dt).toFixed(3)} s   |   crank ${state.q.crank.toFixed(3)}° (unwrapped)\nWheel coordinates: ${[2, 1, 0].map(i => `W${i} ${state.q[`wheel${i}`].toFixed(3)}°`).join('   ')}\nCarry latches: ${[1, 2].map(i => `L${i} ${state.m[`latched${i}`] ? 'down / retained' : 'upper detent'}`).join('   ')}   |   events ${Object.values(state.counts).reduce((a, b) => a+b, 0)}`;
  renderer.render(scene, camera);
  return state;
}
async function init() {
  running = false; accumulator = 0;
  pose(await request('init', {program: corpus.programs.curta, dt: 1 / 240}));
  await request('rate', {args: ['crank', 180]});
}
document.querySelector('#run').onclick = () => { running = true; last = performance.now(); };
document.querySelector('#pause').onclick = () => { running = false; accumulator = 0; };
document.querySelector('#reset').onclick = () => init();
document.querySelector('#step').onclick = async () => { running = false; pose(await request('advance', {args: [240]})); };
document.addEventListener('visibilitychange', () => { if (document.hidden) running = false; });
function frame(now) {
  if (running && !busy) {
    accumulator += Math.min((now-last)/1000, .1); // No hidden-page catch-up.
    const ticks = Math.min(120, Math.floor(accumulator * 240));
    if (ticks) {
      accumulator -= ticks / 240; busy = true;
      request('advance', {args: [ticks]}).then(pose).catch(e => { running = false; document.querySelector('#state').textContent = e.message; }).finally(() => { busy = false; });
    }
  }
  last = now; requestAnimationFrame(frame);
}
await init();
window.probe = {
  suite: () => request('suite', {corpus}),
  gcode: () => request('gcode-probe', {program: corpus.programs.concurrent}),
  reset: init,
  advance: async ticks => pose(await request('advance', {args: [ticks]})),
  snapshot: () => request('snapshot'),
  restore: async snap => pose(await request('restore', {args: [snap]})),
  renderOnly: () => renderer.render(scene, camera),
  longRun: ticks => request('advance', {args: [ticks]}),
  revision: THREE.REVISION,
};
window.ready = true; requestAnimationFrame(frame);
