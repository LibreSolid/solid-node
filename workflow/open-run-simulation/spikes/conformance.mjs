import {Engine} from './kernel.mjs';

export function execute(programs, test) {
  const e = new Engine(programs[test.program], test.dt), marks = [], saved = {};
  for (const cmd of test.commands) {
    const [op, ...args] = cmd;
    if (op === 'save') saved[args[0]] = e.snapshot();
    else if (op === 'restore') e.restore(saved[args[0]]);
    else if (op === 'expect-error') {
      let error = null;
      try { e[args[0]](...args.slice(1)); } catch (err) { error = err.message; }
      if (!error) throw new Error('expected refusal did not occur');
      marks.push({error});
    } else if (op === 'mark') marks.push(e.snapshot());
    else e[op](...args);
  }
  marks.push(e.snapshot());
  return marks;
}

export function suite(corpus) {
  return Object.fromEntries(corpus.cases.map(c => [c.name, execute(corpus.programs, c)]));
}
