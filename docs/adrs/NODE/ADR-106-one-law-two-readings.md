# ADR-106: One Law, Two Readings — A Relation Is Inspected as an Expression

**Status:** Accepted
**Date:** 2026-09-13
**Depends on:**
- [ADR-105: The run owns the coordinates and binds them](./ADR-105-the-run-owns-the-coordinates-and-binds-them.md)
**Extends:**
- [ADR-089: `drives` relates two coordinates](./ADR-089-drives-relates-two-coordinates.md)
**Cites:**
- [ADR-022: Cross-runtime degree trig parity for `$t` expressions](../MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md)
- [ADR-076: Mechanism laws as compositions over expression math](../MATH/ADR-076-mechanism-laws-as-compositions-over-expression-math.md)
**OpenSpec change:** `run-owns-the-coordinates`

## Context and Problem Statement

A relation states a mechanical fact: this coordinate is a function of
that one. Untimed and looping, the framework reads that fact one way —
it SETS the driven coordinate to `f(driver)`. A machine that keeps its
history needs the other reading of the same fact: over one tick the
driven coordinate MOVES BY the change of `f` along its sources'
movement, from where it stood.

The obvious way to get the second reading is to make the author declare
it — a second face on the law, a `running(r)` protocol. The pilot
ratified exactly that on 2026-09-12 and superseded it on 2026-09-13,
because it makes every project law two laws that can disagree, and
because the information is already in the one law the author wrote.

`Affine.forward` is ordinary arithmetic over whatever it is handed. A
`symbol()` builds an `ExpressionNode` graph; `solid_node.math`'s
primitives emit `call` nodes whose names are the closed list
`SYMBOLIC_BUILTINS` (ADR-022, ADR-076); `GraphValue.evaluate(inputs)`
already evaluates such a graph numerically over named inputs. A law is
therefore already an expression builder, and an expression is something
the framework can evaluate twice.

## Decision Drivers

- One law, not two: a project's `tooth_window` must mean the same thing
  under every base, and a second declared face would be a second thing
  to keep in step.
- Exactness across kinks. The Curta's window is
  `4 + 72 * clamp01((angle − 113.5) / 11.25)`; `clamp01` is `min`/`max`,
  and a numerical derivative across that kink would be wrong at exactly
  the instant the mechanism engages.
- What a law CANNOT say must be refused by name, not integrated wrongly.

## Considered Options

1. **A declared running face (`running(r)`)** — superseded by the
   pilot's decision of 2026-09-13, for the reasons above.
2. **Differentiate the law numerically per tick** — rejected: a slope
   sampled at the tick's start is wrong across every kink, which is
   where a mechanism engages and disengages.
3. **Decide propagation per tick by a worklist from the inputs that
   moved** — rejected: the direction of every relation is already
   decided, by the rest render, from the same facts, and a FIXED
   program is what a later cycle exports and the browser worker
   executes.
4. **Integrate jumps too, by locating crossings inside the tick** — the
   right answer, and the next cycle's; this one refuses a jump by name
   rather than shipping a wrong integration of it.

## Decision

Under a running root, over one tick a CONTINUOUS law contributes exactly
`f(end) − f(start)` to its driven coordinate, from where that coordinate
stood — `f` being the law's `forward` face, or its `inverse` face where
the rest render solved the relation backward. Because it is the
difference of two exact evaluations, it is exact across the kinks of
`abs`, `min` and `max` and of the compositions built on them (`clamp`,
`clamp01`, `ramp`, `piecewise`). A law whose increment is zero although
its source moved contributes nothing, which is what disengagement is.

To evaluate `f` at values of its own choosing the run COMPILES the law,
once, at `Sim` construction: each relation's law is applied to a
symbolic token per source coordinate, in the direction the rest render
solved it, and the expression graph that application builds — over the
qualified ids of the sources — is what the run evaluates on every tick.
A wiring into a bank coordinate is an identity edge, a derived
coordinate a linear one, and edges are ordered by Kahn over the ends
they determine. A relation reaching no bank coordinate is not compiled;
the ordinary solver keeps computing it every tick from the run-bound
sources. The program has an IDENTITY — a digest over the root class, the
bank's ids, the inputs' declarations and every edge's ends, direction
and expression — which is what a snapshot is checked against.

Increments propagate over that program in the direction each relation
was solved; a coordinate no edge determines HOLDS; two increments that
disagree beyond `1e-9·max(1, |a|, |b|)` are a CONFLICT. A tick that
fails commits nothing.

**That same application is the inspection.** What the expression cannot
say is refused at construction, by relation identity, naming the
relation as written and the class that stated it:

- an expression containing a DISCONTINUOUS primitive — a call to
  `floor`, `ceil` or `sign`, the `%` operator, or a comparison — is a
  jump, and jumps are not yet supported;
- a law that raises when applied to a symbol, returns something that is
  neither a number nor an expression, or whose graph holds text the
  framework cannot evaluate or a call outside `SYMBOLIC_BUILTINS`, is
  not an expression over its sources;
- an edge into a bank coordinate whose source the run does not own and
  no compiled edge computes — a plain port an author's `simulate()`
  binds — is a value stated imperatively;
- a driven group mixing bank coordinates and other ends.

## Consequences

- A project law written with `solid_node.math` works under both
  readings with no edit, which is what "one law" means. A law written
  over Python's own `math` is refused by name rather than silently
  losing its symbolic face — a finding worth having at construction.
- The Curta bench's window is refused until jumps land, because its
  periodic form contains `floor`. Its non-periodic form compiles, and
  the same file poses exactly as it always did untimed.
- A law whose expression has no free coordinate — a constant — compiles
  and contributes a zero increment. Refusing a law whose slope is zero
  everywhere, which the pilot's decision asks for, needs jump detection
  to tell a gate from a constant, and is the next cycle's.
- The evaluator is `GraphValue.evaluate` per edge per tick, which builds
  a dict and walks the graph twice. That is the recorded cost —
  1.16 ms/tick on the test machine, 3.2× the untimed loop — and a
  compiled evaluator is a later cycle's business; the spike's
  500-coordinate budget is the target it will be measured against.
- Because the direction is fixed by the rest render rather than decided
  per tick, the program is a static artifact: the same object a later
  cycle publishes in the document and a browser worker executes over the
  expression evaluator the widget already has.
