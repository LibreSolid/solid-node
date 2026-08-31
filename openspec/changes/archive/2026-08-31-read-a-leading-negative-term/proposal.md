## Why

The viewer returns a different number than the producer for an expression
whose leading term is negative, and the parity corpus that exists to make that
impossible does not contain one.

`viewer-package` already requires that "the viewer's expression evaluation …
SHALL match the producer's numeric resolution of the same expressions to
within floating-point rounding", enforced by a producer-generated corpus
covering linear driver terms, degree-trig chains, `^` terms, mixed `$t`-and-
driver formulas, and native conversions. Five shapes, and a sum whose head is
a negative literal is not one of them — so nothing caught this:

| expression | producer | shipped evaluator |
| --- | ---: | ---: |
| `(-100.0 + x)` at `x = 100` | `0` | `-200` |
| `(-2 * 3 + 4)` | `-2` | `-10` |
| `(-a - b)` at `a = 5, b = 3` | `-8` | `-2` |

`jokenizer@0.4.5` — the parser `solid_node/viewers/widget/src/evaluator.ts`
builds on — parses a unary operator's operand as a whole expression rather
than as the term beside it, so `-100.0 + x` becomes `-(100.0 + x)`. That is
not a rounding difference: the sign of the driver's coefficient changes. The
model tracks its driver **backwards**, about the one setting where the two
readings happen to agree, which is why a spot check at rest does not find it.

The evidence came from Metamaquina2, where the machine publishes where the
filament enters the extruder as `(-((((-100.0 + x) - -100.0) + 0) - 400))`.
The leading `-100.0` is the carriage's own rest position, which on that
machine is at the near end of the travel rather than at its middle. Of the 265
distinct expressions that model publishes, that one is the only one the viewer
read differently — and it was enough to make the drawn filament run away from
the print head instead of following it, while the model's own geometry was
correct at every position. No contract the project could write would find it:
a project test evaluates the expression in Python, and Python reads it
correctly.

Two things are wrong, then, and the second is the one that matters: the parser
is wrong, and the corpus that is supposed to be the reason we would know is
missing the shape.

## What Changes

- **`jokenizer` moves from `^0.4.5` to `^1.0.1`**, where a unary operator
  takes the term beside it rather than the rest of the expression. The parse
  tree's node kinds are unchanged (`Group`, `Binary`, `Unary`, `Variable`,
  `Member`, `Call`, `Literal`), so `powify` and the free-variable walk are
  untouched by the upgrade.
- **The parity corpus gains the shape.** `spike/expressions/machine_model.py`
  places the front rail from a rest position on the far side of the origin,
  which is how a negative literal comes to head a sum, and the regenerated
  fixture carries fourteen cases of it. Held to the same standard as the rest
  of the corpus: the expected values are the producer's own render, not a
  reimplementation.
- **`^` under a leading minus is settled where `^` is already settled.**
  Converting the operator is the only place the two languages' disagreement
  can be resolved, and they do disagree: JavaScript has no answer at all —
  `-2 ** 2` is a syntax error there for exactly this reason — while OpenSCAD
  binds `^` tighter than the unary minus, as Python does, so `-2 ^ 2` is
  `-(2^2)`. `powify` now lifts a negation out of the base it is applied to.
  Nothing solid-node emits reaches this, because the producer parenthesises
  fully; an expression written by hand does.
- The producer's side of the seam is pinned too: `test_driver_ids.py` asserts
  that `-25.0 + token * 0.0125` is written `(-25.0 + (x_axis.motor * 0.0125))`,
  beside the five shapes it already pins.

## The manifest had to be installable first

Nothing could be installed at all, so the parser could not be either.
`package.json` declared `molejo: ^0.0.1`, a version that has never existed on
npm — `npm ci` and `npm install` both failed with `ETARGET` before they ever
reached `jokenizer`, and the committed `package-lock.json` had no molejo entry
at all, having been generated before the dependency was added. What was
actually resolving was a hand-made symlink in the shared `node_modules`
pointing at this workspace's own molejo working copy.

So the declaration now says what was already true: `molejo` is
`file:../../../../molejo/js`, the working copy beside the framework, at spec
version 2. That is what the widget needs rather than a preference — the
published molejo is `0.1.0` and implements spec version 1, while a machine
with a belt bent backwards over a pulley publishes a document declaring
version 2 and no `0.1.0` runtime will read it. `npm ci` from a clean layout
now resolves `jokenizer@1.0.1` from the registry and `molejo@0.2.0` from that
path.

Two consequences, both stated rather than hidden. The path is relative to the
manifest, so it is correct from the primary checkout and not from a worktree
six levels down; a worktree keeps sharing the primary's `node_modules`, which
is the convention anyway. And a clone of solid-node without this workspace
beside it cannot install the widget. Publishing molejo `0.2.0` is what removes
that, and it is not this change's to do.

The one convention this change could not keep is the other half of that rule:
a worktree never installs or builds inside itself. The whole change is which
version of a dependency is installed, so the worktree was given its own copy —
copied, not installed over the shared one, so the primary checkout's install
was left exactly as it was until the pilot integrates.

## Capabilities

### Modified Capabilities

- `viewer-package`: the parity requirement names operator precedence and the
  corpus covers a leading negative term.

## Impact

- `solid_node/viewers/widget/package.json`,
  `solid_node/viewers/widget/package-lock.json` — the parser version, and the
  molejo declaration that made the manifest installable at all.
- `solid_node/viewers/widget/src/evaluator.ts` — `^` under a leading minus.
- `solid_node/viewers/widget/src/evaluator.test.ts` — the precedence cases,
  including the Metamaquina2 expression verbatim.
- `spike/expressions/machine_model.py` — a sixth expression shape.
- `solid_node/viewers/widget/src/parity-fixture.json` — regenerated.
- `solid_node/viewers/widget/src/parity-fixture.test.ts` — the corpus asks for
  the new shape by name.
- `tests/test_driver_ids.py` — the producer writes the sum as the sum it is.
