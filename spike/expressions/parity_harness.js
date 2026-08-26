/*
 * Spike parity harness for ADR-056 named-driver expressions.
 * NON-SHIPPING. Run:
 *
 *   node spike/expressions/parity_harness.js <input.json> <output.json>
 *
 * This MIRRORS solid_node/viewers/widget/src/evaluator.ts: the context
 * map, the OpenSCAD degree-trig overrides, the `^`-as-pow rewrite and
 * the token cache below are a hand copy of that file (which the spike
 * is forbidden to edit and does not import -- it is TypeScript inside a
 * Vite build). Stage 3a must reconcile the two; see FINDINGS.md.
 *
 * It adds ONE thing the shipped evaluator does not have: `freeVars`,
 * the set of variable names an expression actually reads, taken from
 * the parsed tree rather than by substring search. That is the
 * candidate replacement for `isAnimated`'s `includes('$t')`.
 */

const fs = require('fs');
const path = require('path');
const { tokenize, evaluate } = require(
  path.join(__dirname, '..', '..', 'solid_node', 'viewers', 'widget',
            'node_modules', 'jokenizer'));

// ---- copied from viewers/widget/src/evaluator.ts ------------------
const context = {};
for (const name of Object.getOwnPropertyNames(Math)) context[name] = Math[name];
context.ln = Math.log;
context.log = (base, value) => Math.log(value) / Math.log(base);
context.mod = (a, b) => a % b;
context.sin = (d) => Math.sin(d * Math.PI / 180);
context.cos = (d) => Math.cos(d * Math.PI / 180);
context.tan = (d) => Math.tan(d * Math.PI / 180);
context.asin = (v) => Math.asin(v) * 180 / Math.PI;
context.acos = (v) => Math.acos(v) * 180 / Math.PI;
context.atan = (v) => Math.atan(v) * 180 / Math.PI;
context.atan2 = (y, x) => Math.atan2(y, x) * 180 / Math.PI;

function powify(node) {
  if (node === null || typeof node !== 'object') return node;
  if (Array.isArray(node)) return node.map(powify);
  const result = {};
  for (const key of Object.keys(node)) result[key] = powify(node[key]);
  if (result.type === 'Binary' && result.operator === '^') {
    return {
      type: 'Call',
      callee: { type: 'Variable', name: 'pow' },
      args: [result.left, result.right],
    };
  }
  return result;
}

const tokenCache = new Map();
function tokensFor(expression) {
  const cached = tokenCache.get(expression);
  if (cached !== undefined) return cached;
  const tokens = powify(tokenize(expression));
  tokenCache.set(expression, tokens);
  return tokens;
}
// ---- end copy -----------------------------------------------------

// The isAnimated replacement candidate: free variables read from the
// parsed tree. A Member chain (`x_axis.motor`) collapses to its dotted
// name; a Call's callee is a function, not a variable, so it is not
// reported -- which is exactly why substring matching cannot do this
// job once driver names are author-chosen.
function dottedName(node) {
  if (node.type === 'Variable') return node.name;
  if (node.type === 'Member') {
    const owner = dottedName(node.owner);
    return owner === null ? null : `${owner}.${node.name}`;
  }
  return null;
}

function freeVars(node, found) {
  if (node === null || typeof node !== 'object') return found;
  if (Array.isArray(node)) {
    for (const item of node) freeVars(item, found);
    return found;
  }
  if (node.type === 'Variable' || node.type === 'Member') {
    const name = dottedName(node);
    if (name !== null) {
      found.add(name);
      return found;
    }
  }
  for (const key of Object.keys(node)) {
    if (node.type === 'Call' && key === 'callee') continue;
    freeVars(node[key], found);
  }
  return found;
}

const input = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const results = {};
for (const [key, entry] of Object.entries(input.cases)) {
  const tokens = tokensFor(entry.expression);
  let value = null;
  let error = null;
  try {
    const raw = evaluate(tokens, { ...context, ...entry.context });
    value = typeof raw === 'number' ? raw : Number(raw);
    if (!Number.isFinite(value)) error = `non-finite result ${raw}`;
  } catch (e) {
    error = e.message;
  }
  // Evidence that the `^`-as-pow rewrite is load-bearing rather than
  // decorative: what the SAME expression evaluates to without it.
  let rawPow = null;
  if (entry.expression.includes('^')) {
    try {
      rawPow = evaluate(tokenize(entry.expression),
                        { ...context, ...entry.context });
    } catch (e) { rawPow = null; }
  }

  results[key] = {
    value,
    error,
    rawPow,
    freeVars: [...freeVars(tokens, new Set())].sort(),
  };
}
fs.writeFileSync(process.argv[3], JSON.stringify(results, null, 1));
console.log(`evaluated ${Object.keys(results).length} expressions`);
