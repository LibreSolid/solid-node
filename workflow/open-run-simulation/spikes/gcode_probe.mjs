import {Engine} from './kernel.mjs';
import {Program} from './gcode.mjs';

export function probe(program) {
  const e = new Engine(program, .01);
  const axes = {X: {input: 'x_motor', position: 'x', mmPerInput: 2/360},
    Y: {input: 'y_motor', position: 'y', mmPerInput: 2/360}};
  const source = 'G90\nG1 X10 Y0 F600\nG91\nG1 X0 Y5 F300';
  const p = new Program(e, source, axes);
  const assert = (condition, message) => { if (!condition) throw new Error(message); };
  const near = (x, y) => Math.abs(x-y) < 1e-8;
  e.rate('motor', 720); e.rate('steering', 10);
  p.advance(40); p.pause(); const mid = p.snapshot();
  assert(near(e.q.x, 4) && near(e.q.y, 0), 'first line partial physical travel');
  p.advance(50);
  assert(near(e.q.x, 4) && near(e.q.cam, 324), 'program pause must not pause independent motor');
  p.pause(false); p.advance(160); const final = p.snapshot();
  assert(near(e.q.x, 10) && near(e.q.y, 5), 'two coordinated instructions must finish at requested physical pose');
  assert(final.cursor === 4 && !final.active, 'cursor completed without repeating line');
  p.restore(mid); p.advance(50); p.pause(false); p.advance(160);
  assert(JSON.stringify(p.snapshot()) === JSON.stringify(final), 'program plus mechanism checkpoint replay');
  let rejected = false;
  try { new Program(new Engine(program), 'G2 X10 F100', axes).advance(1); } catch { rejected = true; }
  assert(rejected, 'unknown commands must be refused');
  const bad = structuredClone(program);
  bad.relations.push({id: 'jammed-screw', a: 'x_motor', b: 'x', ratio: 1});
  const failing = new Program(new Engine(bad, .01), source, axes);
  const beforeFailure = failing.snapshot();
  let refused = false;
  try { failing.advance(1); } catch { refused = true; }
  assert(refused, 'inconsistent mechanics must fail');
  assert(JSON.stringify(failing.snapshot()) === JSON.stringify(beforeFailure), 'failed tick must roll back program cursor AND mechanics');
  return {dialect: 'G90/G91/G1 X/Y F only', source,
    paused: {x: mid.mechanical.q.x, remaining_ticks: mid.mechanical.moves[mid.active].remaining},
    final: {x: final.mechanical.q.x, y: final.mechanical.q.y, cam: final.mechanical.q.cam, rack: final.mechanical.q.rack},
    program_and_mechanical_replay_identical: true, unsupported_command_refused: true,
    failure_rolls_back_program_and_mechanics: true};
}
