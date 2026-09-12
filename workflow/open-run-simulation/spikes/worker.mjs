import {Engine} from './kernel.mjs';
import {suite} from './conformance.mjs';
import {probe as gcodeProbe} from './gcode_probe.mjs';

let engine;
self.onmessage = ({data}) => {
  try {
    let result;
    if (data.op === 'suite') result = suite(data.corpus);
    else if (data.op === 'gcode-probe') result = gcodeProbe(data.program);
    else if (data.op === 'init') {
      engine = new Engine(data.program, data.dt);
      result = engine.snapshot();
    } else {
      result = engine[data.op](...(data.args ?? []));
      if (result === undefined) result = engine.snapshot();
    }
    self.postMessage({id: data.id, result});
  } catch (error) { self.postMessage({id: data.id, error: error.message}); }
};
