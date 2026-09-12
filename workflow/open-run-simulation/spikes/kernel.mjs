// Browser/Node interpreter of the SAME numeric mechanical program as kernel.py.
// Experimental, intentionally small piecewise-affine scope. No machine dispatch.
const EPS = 1e-8, TIME_EPS = 1e-12;
const clone = x => structuredClone(x);
const sorted = o => Object.keys(o).sort();
const fail = message => { throw new Error(message); };

export function value(expr, q, m) {
  if (!Array.isArray(expr)) return expr;
  const [op, ...operands] = expr;
  if (op === 'q') return q[operands[0]];
  if (op === 'm') return m[operands[0]];
  const a = operands.map(x => value(x, q, m));
  if (op === 'and') return a.every(Boolean);
  if (op === 'not') return !a[0];
  if (op === '+') return a[0] + a[1];
  if (op === '-') return a[0] - a[1];
  if (op === '*') return a[0] * a[1];
  if (op === 'floor') return Math.floor(a[0]);
  if (op === 'phase-aligned') return Math.abs(a[0] - Math.round(a[0] / a[1]) * a[1]) <= EPS;
  if (op === '==') return Math.abs(a[0] - a[1]) <= EPS;
  fail(`unsupported expression: ${op}`);
}

export class Engine {
  constructor(program, dt = 1 / 240) {
    if (program.version !== 'open-run-spike/1') fail('unsupported program version');
    if (!Number.isFinite(dt) || dt <= 0) fail('positive finite dt required');
    this.p = clone(program); this.dt = dt; this.tick = 0;
    this.q = clone(program.q); this.m = clone(program.m);
    this.rates = {}; this.moves = {}; this.blocked = []; this.counts = {}; this.trace = [];
    this.checkInitial();
  }
  ev(expr) { return value(expr, this.q, this.m); }
  checkInitial() {
    const ids = ['relations', 'events', 'stops'].flatMap(k => this.p[k].map(r => r.id));
    if (new Set(ids).size !== ids.length) fail('duplicate mechanism identity');
    for (const r of this.p.relations) {
      if (!Number.isFinite(r.ratio) || !r.ratio) fail('nonzero finite affine ratio required');
      if (!(r.a in this.q) || !(r.b in this.q)) fail('unknown coordinate');
      this.ev(r.when ?? true);
    }
    for (const e of this.p.events) {
      if (!(e.coord in this.q) || ![-1, 1].includes(e.direction)) fail('invalid event surface');
      if ((e.period ?? 0) < 0) fail('negative event period');
      this.ev(e.when ?? true);
      this.ev(e.require ?? true);
      for (const [k, v] of Object.entries(e.writes)) {
        if (!(k in this.m)) fail('unknown state slot');
        this.ev(v);
      }
    }
    for (const s of this.p.stops) if (this.ev(s.when ?? true)) {
      if (this.q[s.coord] < this.ev(s.lo ?? -Infinity) - EPS) fail('initial state below stop');
      if (this.q[s.coord] > this.ev(s.hi ?? Infinity) + EPS) fail('initial state above stop');
    }
  }
  rate(coord, rate) {
    if (!this.p.inputs.includes(coord) || !Number.isFinite(rate)) fail('finite rate on declared input required');
    if (Object.values(this.moves).some(g => g.remaining && coord in g.rates)) fail('actuator already owned by motion group');
    if (!rate) delete this.rates[coord]; else this.rates[coord] = rate;
  }
  move(group, deltas, ticks) {
    const active = Object.fromEntries(Object.entries(this.moves).filter(([, g]) => g.remaining));
    if (!Object.keys(deltas).length || !Number.isInteger(ticks) || ticks <= 0 || group in active) fail('new group and positive integer duration required');
    const owned = new Set(Object.keys(this.rates));
    Object.values(this.moves).filter(g => g.remaining).forEach(g => Object.keys(g.rates).forEach(k => owned.add(k)));
    if (Object.keys(deltas).some(k => owned.has(k) || !this.p.inputs.includes(k))) fail('actuator ownership conflict');
    if (!Object.values(deltas).every(Number.isFinite)) fail('finite travel required');
    this.moves = active;
    this.moves[group] = {rates: Object.fromEntries(Object.entries(deltas).map(([k, v]) => [k, v / (ticks * this.dt)])),
      remaining: ticks, paused: false, status: 'running'};
  }
  pause(group, paused = true) {
    if (!paused && this.moves[group].status === 'blocked') fail('blocked move needs explicit replan in this spike');
    this.moves[group].paused = paused;
  }
  snapshot() {
    return clone({program: this.p.id, dt: this.dt, tick: this.tick, q: this.q, m: this.m,
      rates: this.rates, moves: this.moves, blocked: this.blocked, counts: this.counts, trace: this.trace});
  }
  restore(snap) {
    if (snap.program !== this.p.id || snap.dt !== this.dt) fail('incompatible checkpoint');
    for (const k of ['tick', 'q', 'm', 'rates', 'moves', 'blocked', 'counts', 'trace']) this[k] = clone(snap[k]);
  }
  velocities() {
    const adj = Object.fromEntries(Object.keys(this.q).map(k => [k, []]));
    for (const r of this.p.relations) if (this.ev(r.when ?? true)) {
      adj[r.a].push([r.b, r.ratio]); adj[r.b].push([r.a, 1 / r.ratio]);
    }
    const requested = {...this.rates};
    for (const g of Object.values(this.moves)) if (g.remaining && !g.paused) Object.assign(requested, g.rates);
    const v = {}, components = [];
    for (const start of sorted(this.q)) {
      if (start in v) continue;
      const members = new Set(), stack = [start];
      while (stack.length) {
        const x = stack.pop();
        if (!members.has(x)) { members.add(x); stack.push(...adj[x].map(([y]) => y)); }
      }
      const seeds = [...members].filter(x => x in requested).sort();
      const root = seeds[0] ?? start;
      v[root] = requested[root] ?? 0; stack.push(root);
      while (stack.length) {
        const x = stack.pop();
        for (const [y, ratio] of adj[x]) {
          const expected = v[x] * ratio;
          if (y in v) { if (Math.abs(v[y] - expected) > EPS) fail(`inconsistent closed relation at ${y}`); }
          else { v[y] = expected; stack.push(y); }
        }
      }
      for (const x of seeds) if (Math.abs(v[x] - requested[x]) > EPS) fail(`incompatible prescribed motion at ${x}`);
      components.push([members, seeds]);
    }
    const blocked = new Set();
    for (const s of this.p.stops) if (this.ev(s.when ?? true)) {
      const c = s.coord, lo = this.ev(s.lo ?? -Infinity), hi = this.ev(s.hi ?? Infinity);
      if ((v[c] < 0 && this.q[c] <= lo + EPS) || (v[c] > 0 && this.q[c] >= hi - EPS)) blocked.add(c);
    }
    for (const [members, seeds] of components) if ([...members].some(x => blocked.has(x))) {
      seeds.forEach(x => { if (!this.blocked.includes(x)) this.blocked.push(x); });
      members.forEach(x => { v[x] = 0; });
    }
    return v;
  }
  eventDistance(e, v) {
    const speed = v[e.coord];
    if (speed * e.direction <= 0) return Infinity;
    const x = this.q[e.coord], period = e.period ?? 0;
    let level = e.phase;
    if (period) level += (speed > 0 ? Math.floor((x - e.phase + EPS) / period) + 1 : Math.ceil((x - e.phase - EPS) / period) - 1) * period;
    const t = (level - x) / speed;
    return t > TIME_EPS ? t : Infinity;
  }
  onSurface(e) {
    let d = this.q[e.coord] - e.phase;
    if (e.period) d -= Math.round(d / e.period) * e.period;
    return Math.abs(d) <= EPS;
  }
  settle(arrivalVelocity) {
    const fired = new Set();
    for (let n = 0; n < 64; n++) {
      const batch = this.p.events.filter(e => !fired.has(e.id) && arrivalVelocity[e.coord] * e.direction > 0 && this.onSurface(e) && this.ev(e.when ?? true));
      if (!batch.length) return;
      batch.sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
      const writes = {};
      for (const e of batch) {
        if (!this.ev(e.require ?? true)) fail(`inadmissible engagement: ${e.id}`);
        for (const [k, expr] of Object.entries(e.writes)) {
          const next = this.ev(expr);
          if (k in writes && writes[k] !== next) fail(`conflicting event writes: ${k}`);
          writes[k] = next;
        }
        fired.add(e.id);
      }
      Object.assign(this.m, writes);
      for (const e of batch) {
        this.counts[e.id] = (this.counts[e.id] ?? 0) + 1;
        this.trace.push({id: e.id, at: this.q[e.coord]});
      }
      this.trace = this.trace.slice(-64);
    }
    fail('same-instant event settlement limit');
  }
  step() {
    let remaining = this.dt, n = 0;
    this.blocked = [];
    for (; n < 1000; n++) {
      if (remaining <= TIME_EPS) break;
      const v = this.velocities(); let interval = remaining;
      for (const e of this.p.events) interval = Math.min(interval, this.eventDistance(e, v));
      for (const s of this.p.stops) if (this.ev(s.when ?? true)) {
        const c = s.coord;
        if (v[c]) {
          const edge = this.ev(v[c] > 0 ? s.hi ?? Infinity : s.lo ?? -Infinity);
          const t = (edge - this.q[c]) / v[c];
          if (t > TIME_EPS) interval = Math.min(interval, t);
        }
      }
      for (const c of Object.keys(this.q)) this.q[c] += v[c] * interval;
      this.settle(v); remaining -= interval;
    }
    if (n === 1000) fail('event subdivision limit');
    this.velocities(); this.blocked.sort();
    for (const g of Object.values(this.moves)) if (g.remaining && !g.paused) {
      if (Object.keys(g.rates).some(k => this.blocked.includes(k))) { g.paused = true; g.status = 'blocked'; }
      else { g.remaining--; if (!g.remaining) g.status = 'completed'; }
    }
    this.tick++;
  }
  advance(ticks) {
    if (!Number.isInteger(ticks) || ticks < 0) fail('nonnegative integer ticks required');
    for (let n = 0; n < ticks; n++) {
      const before = this.snapshot();
      try { this.step(); } catch (e) { this.restore(before); throw e; }
    }
    return this.snapshot();
  }
}
