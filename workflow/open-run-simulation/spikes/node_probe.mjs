import fs from 'node:fs';
import {performance} from 'node:perf_hooks';
import {Engine} from './kernel.mjs';
import {suite} from './conformance.mjs';

const corpus = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const results = suite(corpus);
const e = new Engine(corpus.programs.curta);
e.rate('crank', 360);
const memory = [];
let prior = 0;
const started = performance.now();
for (const ticks of [2000, 20000, 100000]) {
  e.advance(ticks - prior); prior = ticks;
  if (global.gc) global.gc();
  memory.push({ticks, heap_used_bytes: process.memoryUsage().heapUsed,
    snapshot_bytes: JSON.stringify(e.snapshot()).length, trace_length: e.trace.length,
    event_count_slots: Object.keys(e.counts).length});
}
console.log(JSON.stringify({runtime: process.version, results, memory,
  seconds_for_100000_ticks: (performance.now() - started) / 1000}));
