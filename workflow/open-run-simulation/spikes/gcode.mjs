// Deliberately narrow instruction ADAPTER. The mechanical Engine stays generic.
// Supported language: G90, G91, G1 with X/Y and a positive feed in mm/min;
// semicolon comments. No G0, arcs, extrusion, acceleration, homing or firmware.
export class Program {
  constructor(engine, source, axes) {
    this.e = engine; this.source = source; this.axes = structuredClone(axes);
    this.lines = source.split('\n').map(s => s.split(';')[0].trim()).filter(Boolean);
    this.cursor = 0; this.absolute = true; this.feed = null; this.active = null; this.paused = false;
  }
  startNext() {
    while (this.cursor < this.lines.length && !this.active) {
      const line = this.lines[this.cursor], compact = line.replace(/\s/g, '').toUpperCase();
      const words = [...compact.matchAll(/([A-Z])([+-]?(?:\d+(?:\.\d*)?|\.\d+))/g)];
      if (words.map(x => x[0]).join('') !== compact) throw new Error(`unsupported G-code syntax at line ${this.cursor+1}`);
      const fields = {};
      for (const [, letter, raw] of words) {
        if (letter in fields) throw new Error(`duplicate G-code word: ${letter}`);
        fields[letter] = Number(raw);
      }
      if (![1, 90, 91].includes(fields.G)) throw new Error('unsupported G-code command');
      if (fields.G !== 1) {
        if (Object.keys(fields).length !== 1) throw new Error('mode line must contain only G90/G91');
        this.absolute = fields.G === 90; this.cursor++; continue;
      }
      for (const k of Object.keys(fields)) if (!['G', 'F', ...Object.keys(this.axes)].includes(k)) throw new Error(`unsupported G-code axis: ${k}`);
      const feed = fields.F ?? this.feed;
      if (!Number.isFinite(feed) || feed <= 0) throw new Error('positive feed required');
      const deltas = {}; let squaredDistance = 0;
      for (const [letter, axis] of Object.entries(this.axes)) if (letter in fields) {
        const mm = this.absolute ? fields[letter] - this.e.q[axis.position] : fields[letter];
        deltas[axis.input] = mm / axis.mmPerInput; squaredDistance += mm*mm;
      }
      if (!Object.keys(deltas).length) throw new Error('move needs a declared axis');
      const ticks = Math.max(1, Math.ceil(Math.sqrt(squaredDistance) / (feed/60) / this.e.dt));
      const group = `gcode-${this.cursor}`;
      this.e.move(group, deltas, ticks);
      this.active = group; this.feed = feed; this.cursor++;
    }
  }
  advance(ticks) {
    if (!Number.isInteger(ticks) || ticks < 0) throw new Error('integer ticks required');
    for (let n = 0; n < ticks; n++) {
      const before = this.snapshot();
      try {
        if (!this.paused) this.startNext();
        this.e.advance(1);
        if (this.active && this.e.moves[this.active].status === 'completed') this.active = null;
        if (this.active && this.e.moves[this.active].status === 'blocked') this.paused = true;
      } catch (error) { this.restore(before); throw error; }
    }
    return this.snapshot();
  }
  pause(paused = true) {
    if (this.active) this.e.pause(this.active, paused);
    this.paused = paused;
  }
  snapshot() {
    return {source: this.source, axes: structuredClone(this.axes), cursor: this.cursor,
      absolute: this.absolute, feed: this.feed, active: this.active, paused: this.paused,
      mechanical: this.e.snapshot()};
  }
  restore(snap) {
    if (snap.source !== this.source || JSON.stringify(snap.axes) !== JSON.stringify(this.axes)) throw new Error('incompatible program checkpoint');
    this.e.restore(snap.mechanical);
    for (const k of ['cursor', 'absolute', 'feed', 'active', 'paused']) this[k] = structuredClone(snap[k]);
  }
}
