// Read-only integration probe: bundle the installed viewer's own evaluator
// into a temporary file, never copy its implementation into the framework.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const [widget, ...files] = process.argv.slice(2);
const require = createRequire(path.join(widget, 'package.json'));
const esbuild = require('esbuild');
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'expression-viewer-'));
try {
  const output = path.join(temporary, 'evaluator.mjs');
  await esbuild.build({stdin: {contents:
    "export {evalExpr} from './src/evaluator'; export {bindingTable} from './src/bindings';",
    resolveDir: widget, loader: 'ts'}, outfile: output, bundle: true,
    platform: 'node', format: 'esm'});
  const {evalExpr, bindingTable} = await import(pathToFileURL(output));
  const reports = [];
  let pinned;
  for (const file of files) {
    const fixture = JSON.parse(fs.readFileSync(file, 'utf8'));
    const table = bindingTable(fixture, file);
    let maximum = 0;
    for (const row of fixture.cases) {
      const actual = evalExpr(row.expression, {...row.scope, bindings: table.roots()});
      const error = Math.abs(actual - row.expected);
      if (!Number.isFinite(actual) || error > 1e-9)
        throw new Error(`${file}: ${row.key}: ${actual} != ${row.expected}; error ${error}`);
      maximum = Math.max(maximum, error);
    }
    const expected = fixture.cases.map(row => [row.key, row.expected]);
    if (!pinned) pinned = expected;
    else if (fixture.generated_by && JSON.stringify(pinned) !== JSON.stringify(expected))
      throw new Error('The original pinned expectations moved');
    reports.push({file, cases: fixture.cases.length,
      bindings: (fixture.bindings || []).length, maximum_absolute_error: maximum});
  }
  console.log(JSON.stringify(reports, null, 2));
} finally {
  fs.rmSync(temporary, {recursive: true});
}
