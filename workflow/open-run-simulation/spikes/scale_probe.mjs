// Model-size experiment, not a performance forecast for complete Curta contact.
import {performance} from 'node:perf_hooks';
import {Engine} from './kernel.mjs';

const samples = [];
for (const size of [8, 500, 5000]) {
  const p = {version: 'open-run-spike/1', id: `synthetic-${size}`, q: {}, m: {}, inputs: ['q0'], relations: [], events: [], stops: []};
  for (let i = 0; i < size; i++) {
    p.q[`q${i}`] = 0;
    if (i) p.relations.push({id: `mesh-${i}`, a: 'q0', b: `q${i}`, ratio: i%2 ? -1 : 1});
  }
  const e = new Engine(p); e.rate('q0', 360); e.advance(50);
  const times = [];
  for (let n = 0; n < 250; n++) {
    const t = performance.now(); e.advance(1); times.push(performance.now()-t);
  }
  times.sort((a,b) => a-b);
  samples.push({coordinates: size, relations: size-1, program_bytes: JSON.stringify(p).length,
    snapshot_bytes: JSON.stringify(e.snapshot()).length, measured_steps: times.length,
    step_ms_median: times[125], step_ms_p95: times[237],
    note: 'linear permanently engaged star; no contact events, geometry or rendering'});
}
console.log(JSON.stringify({runtime: process.version, samples}, null, 2));
