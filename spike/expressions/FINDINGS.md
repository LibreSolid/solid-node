# Spike findings: named-driver expressions, render to pixels

Design evidence for
[ADR-056](../../docs/adrs/NODE/ADR-056-signals-drivers-ports-and-stepped-simulation.md),
per [SCOPE.md](SCOPE.md). Executed 2026-08-26 in the `signal-drivers`
worktree at framework base `ca6ee02`, with **zero framework edits**
(nothing under `solid_node/` changed; the widget's `evaluator.ts` was
read, never touched).

Environment, exactly as run:

- worktree `/home/asa/devel/libresolid-studio/solid-node/WTs/signal-drivers`
- Python `/home/asa/devel/libresolid-studio/.venv/bin/python` (workspace venv)
- OpenSCAD `/usr/bin/openscad`, version 2021.01, driven through
  `xvfb-run -a` (headless box, no GL context otherwise)
- Node `v24.11.1`; jokenizer from
  `solid_node/viewers/widget/node_modules/jokenizer`
- Linux 6.8.0

Reproduce everything with one command from the worktree root:

    PYTHONPATH="$PWD" /home/asa/devel/libresolid-studio/.venv/bin/python \
        spike/expressions/run_spike.py

Two consecutive runs from a clean `_build/` produced identical
transcripts (exit 0); the one figure not guaranteed run-stable is the
rendered PNG's byte count, which OpenSCAD's rasteriser can vary.

Artifacts build under `spike/expressions/_build/` (gitignored):
`snapshot_a.scad`, `snapshot_b.scad`, `snapshot_a.png`,
`anim0000*.png`, `parity_input.json`, `parity_output.json`.

Model: `spike/expressions/machine_model.py` — one `Axis` class
declaring `motor = Driver(...)` and a `TranslationalPort`, instantiated
**twice** as `x_axis` and `y_axis` under a driverless `Machine` parent,
so the class-local name collides for real. Its `render()` deliberately
builds five expression shapes: linear in the driver, driver through a
port scale, non-linear degree trig (`asin(0.25*sin(θ))`), a **mixed**
formula containing both `$t` and a driver term, and a **power** term
(`sqrt(400 − (0.01θ)^2)`, which serializes OpenSCAD's `^`).

## Verdicts

| Sub-question | Verdict |
|---|---|
| 1. Symbolic driver reads | **Validated** behind a spike shim; one seam named |
| 2. Qualification: local names → global ids | **Validated** — eager qualification is viable |
| 3. Client parity | **Validated** — max deviation 2.5e-14 |
| 4. Scad snapshot substitution | **Validated** — rendered, mixed formula survived |
| 5. State-bank qualification | **Invalidated for the shipped API**; validated behind the shim |

**Primary question: validated.** An operation expression referencing
named drivers travelled end to end — built in `render()`, serialized
into `Rotation/Translation.serialized`, evaluated client-side with
degree-trig and `^` parity — while the same model emitted `.scad` with
every driver term numerically substituted and `$t` still symbolic, and
OpenSCAD rendered it.

## Recommended representation

**An eagerly-qualified token that subclasses solid2's
`OpenSCADConstant`** (`spike/expressions/symbolic.py`, `DriverToken`),
whose string *is* the qualified driver id. Not a solid-node expression
tree.

Fourteen lines of shim, and it decided itself on three pieces of
evidence:

1. **The path is knowable at render time** (sub-question 2), which is
   the condition SCOPE named for this option. String-eagerness then
   works *for* the design instead of against it: the id is final at the
   moment the token is created, so flattening loses nothing.
2. **solid2 arithmetic already produces the wire string.** No operator
   overloads were written. `usteps * 0.1125` yields
   `(x_axis.motor * 0.1125)`; `Rotation.serialized`'s `str(angle)`
   publishes it verbatim.
3. **`solid_node/math.py` interoperates for free.** It dispatches on
   `isinstance(x, OpenSCADConstant)`, so a subclass gets the whole
   degree-trig symbolic mode with no change:
   `asin((0.25 * sin((x_axis.motor * 0.1125))))` and
   `(sqrt((400.0 - ((0.01 * (x_axis.motor * 0.1125)) ^ 2))) * 0.1)`
   came out of the shipped module untouched.

The alternative — a tree-preserving solid-node expression type — costs
strictly more and buys nothing here. It would have to reimplement every
solid2 operator, and either subclass `OpenSCADConstant` (whose
`__operator_base__` flattens to the base class, so the tree is lost
anyway unless every operator is overridden) or *not* subclass it, which
silently breaks `solid_node.math`'s symbolic mode for every project
already using it. Keep it in reserve only if a future requirement makes
the path genuinely unknowable at render time — see the ordering caveat
under seam 3.

**Id syntax.** `x_axis.motor` (Modelica flattening, path joined with
`.`) is the recommendation for the wire form. jokenizer parses it as a
`Member` access, so the client holds a **nested** driver map
(`{x_axis: {motor: 8000}}`) and evaluation needs no evaluator change at
all. The flat `x_axis__motor` variant also works and is additionally
legal as an OpenSCAD identifier; that only matters if a future scad
path ever emits driver *variables* rather than substituting them, which
this design does not.

## Evidence per sub-question

### 1. Symbolic driver reads — validated behind a shim

Both halves of the contract were confirmed to hold as shipped:

```
  unbound read raises, as designed: KeyError("no driver state 'motor' bound; bind it with set_state(motor=...)")
  set_state rejects a symbolic value: TypeError(state 'motor' must be a plain number, not motor)
```

Binding tokens *past* `set_state` (writing `_states` directly) then
produced well-formed wire strings for every expression shape:

```
    Machine/x_axis/carriage#0.t0 = (x_axis.motor * 0.0125)
    Machine/x_axis/cover#0.angle = asin((0.25 * sin((x_axis.motor * 0.1125))))
    Machine/x_axis/cover#1.t0    = ((5.0 * cos((360.0 * $t))) + ((x_axis.motor * 0.0125) * 0.1))
    Machine/x_axis/pulley#0.angle = (x_axis.motor * 0.1125)
    Machine/x_axis/pulley#1.t2   = (sqrt((400.0 - ((0.01 * (x_axis.motor * 0.1125)) ^ 2))) * 0.1)
    Machine/y_axis#0.angle       = 90
```

The last line is the static placement applied outside any `render()`:
it stays a numeral, so static and driven operations remain
distinguishable on the wire.

The loud-unbound contract and a symbolic serialization pass **cannot
coexist behind today's single door**: `AssemblyNode._validate_state`
judges every value by `as_number()`, and a symbolic value is
deliberately not a number. That is seam 1 below. Nothing else about the
contract had to bend — in particular `_BoundState`'s "nobody bound that
driver" message stays exactly as valuable, because a symbolic pass
binds *every* declared driver rather than leaving holes.

### 2. Qualification — validated; eager qualification is viable

The decisive question was *when* a node can know its instance path.
Answer: **at the moment its own `render()` runs**, in every pass that
links before it recurses.

A child's name is not its own property — it is derived by the parent
from the attribute holding it (`base.py` `_link_child` /
`_attr_name_for`). Before linking, both instances answer to the class
name:

```
  before any linking: x_axis.name='Axis' y_axis.name='Axis'
  after machine.render() alone: x_axis.name='Axis' (render does NOT link)
```

But `InternalNode.as_scad` and `core/serializer.serialize_node` both
call `_link_child(child)` **before** `child.assemble()` / before
recursing, so a child assembly is always linked by the time its own
`render()` builds expressions. An instrumented `Axis` recorded exactly
that:

```
  render-time identity, in binding/serialization order:
    Axis('x'): name='x_axis' path=('x_axis',) linked=True
    Axis('y'): name='y_axis' path=('y_axis',) linked=True
```

Two instances of one class therefore serialize distinct ids and bind
distinct values:

```
  x pulley angle: (x_axis.motor * 0.1125)
  y pulley angle: (y_axis.motor * 0.1125)
  same two instances bound numerically: x carriage=100.0 mm, y carriage=25.0 mm
```

Two hazards found, both real and both cheap to close:

- **Ordering.** `AssemblyNode.set_state` propagates through
  `_rendered_children`, which renders children **without** linking
  them. On a never-assembled tree that leaves both axes named `Axis`,
  and an unlinked instance qualifies to the bare `'motor'` — a silent
  collision, not an error. Qualification must therefore happen in a
  linked pass (seam 3).
- **Identifier legality.** A child held in a *list* is named
  `<attr>-<index>`, so its driver serializes as
  `(axes-0.motor * 0.1125)` — a **subtraction**, not a name. Any
  qualification scheme needs an identifier rule (seam 4).

### 3. Client parity — validated

182 evaluations (7 sampled snapshots × 26 serialized expressions),
Python bound-render numerics vs the harness evaluating the unbound wire
strings against a nested driver map:

```
  composer self-check vs _compose_world_matrix: max |delta| = 0.000e+00
  evaluated 182 expressions (7 snapshots x 26 expressions)
  max |python - client| over scalars: 2.487e-14 (worst case 1|Machine/y_axis/cover#0.angle)
  `^` rewrite is load-bearing: 14 expressions contain `^`; without powify they diverge by up to 0.186
  max |python - client| over composed 4x4 world matrices: 4.302e-16
```

- **Max absolute deviation: 2.487e-14** on scalars (the worst case is
  the `asin(0.25·sin θ)` degree-trig chain, i.e. accumulated
  double-precision rounding across four transcendental calls, not a
  semantic difference), and **4.302e-16** on the composed 4×4 world
  matrices. Both are far inside ADR-022's discipline, which is exact
  agreement of *semantics* — same function, one evaluated now and one
  deferred — with only float rounding between runtimes.
- The matrix composition used by the comparison was first checked
  against the framework's own `_compose_world_matrix` at
  **exactly 0.0**, so the parity number measures the evaluators and not
  the harness.
- The `^` line is the guard against a false pass: without the
  `powify` rewrite the same expressions differ by up to 0.186, so the
  parity result is evidence about real semantics.

**The harness mirrors, it does not import.** `parity_harness.js`
hand-copies the context map, degree-trig overrides, `powify` pass and
token cache out of `solid_node/viewers/widget/src/evaluator.ts` (a
TypeScript module inside a Vite build; the spike is forbidden to edit
it and cannot import it from plain Node). Stage 3a must reconcile the
two — either by testing the real module or by extracting the semantics
into something both can consume.

Two incidental observations for ADR-022, which stage 3a should not
inherit stale:

- The widget evaluator **now has** the degree-trig overrides and the
  `powify` pass. ADR-022's "KNOWN DEFECT (shipped)" section describes a
  state that no longer exists.
- There is now exactly **one** TS evaluator.
  `viewers/web/app/src/evaluator.ts` (ADR-022's runtime #3) is gone, so
  ADR-022's two-evaluator premise is stale too. Cross-runtime parity is
  still unenforced by any test, which is the part that remains true.

**What replaces `isAnimated`.** Today
`isAnimated(expr) = expr.includes('$t')`, consumed by
`tree.ts:operationIsAnimated` → `TreeNode.animated`, which is what
decides whether a subtree needs per-frame matrix recomputation. A
substring test cannot survive author-chosen driver names (a driver
called `total` would need `includes('total')`, which then fires on the
word `total` anywhere, including inside a function name). The
replacement demonstrated here is a **free-variable set read off the
parsed tree** — the harness already computes it from the same
`tokenize()` output the evaluator caches, so it costs one extra walk
per distinct expression, once, next to the existing token cache:

```
  free variables from the parsed tree (isAnimated candidate):
    Machine/y_axis#0.angle             -> [] (static)
    Machine/x_axis/cover#0.angle       -> ['x_axis.motor']
    Machine/x_axis/cover#1.t0          -> ['$t', 'x_axis.motor']
```

`Member` chains collapse to their dotted name and a `Call`'s callee is
skipped, so function names are never mistaken for variables. An
operation is dynamic iff its free-variable set is non-empty; a
finer-grained client can go further and recompute a subtree only when
one of *its* free variables actually changed — which is what makes
per-driver interactivity cheap.

### 4. Scad snapshot substitution — validated

Two snapshots of the same model, drivers bound numerically and `time`
left unbound so it stays solid2's `$t`:

```
  _build/snapshot_a.scad: 1777 bytes
    mixed: translate(v = [((5.0 * cos((360.0 * $t))) + 10.0), 0, 0]) {
    mixed: translate(v = [((5.0 * cos((360.0 * $t))) + 2.5), 0, 0]) {
  _build/snapshot_b.scad: 1780 bytes
    mixed: translate(v = [((5.0 * cos((360.0 * $t))) + 2.0), 0, 0]) {
    mixed: translate(v = [((5.0 * cos((360.0 * $t))) + 8.0), 0, 0]) {
  openscad rendered _build/snapshot_a.png: 22206 bytes, 256 distinct byte values
  --animate 4 over the same file: 4 frames, 3 distinct -- $t is still live
```

The **mixed formula survived partial substitution**: the `$t` half is
still an OpenSCAD expression while the driver half has already
collapsed to a numeral (`10.0` for `x_axis` at 8000 µsteps, `2.5` for
`y_axis` at 2000). The two files differ per axis and per snapshot, no
driver name appears anywhere in either file, and OpenSCAD rendered
`snapshot_a.scad` to a real image — two axes at 90°, carriages at 100
mm and 25 mm, pulleys lifted by different amounts through the `^` term.
`--animate 4` over the same file produced 4 frames of which 3 are
distinct (frames at `$t`=0.25 and 0.75 coincide because
`cos(360·$t)` is 0 at both) — direct proof `$t` remained live rather
than being frozen along with the drivers. The PNG byte count is the
only figure in this document that is not run-stable: OpenSCAD's
rasteriser varies it by a few hundred bytes between runs.

**Verdict on the ADR's condition:** yes, this is as cheap as the
existing `as_number` machinery suggests — in fact cheaper. It required
**no substitution machinery at all**. Binding a driver numerically and
leaving `time` unbound is already exactly what `set_state`/`self.time`
do; the expression collapses at build time because Python evaluates it
eagerly. ADR-056 can keep OpenSCAD snapshot support on the stated
condition.

One incidental note, not a spike concern: on a *cold* tree the root
`.scad` inlines each leaf's geometry (its STL artifact is not current
yet, so `import_optimized` falls back to the model), while a warm tree
imports STLs. Content about drivers and `$t` is identical either way;
the runner warms the build first so the transcript is stable.

### 5. State-bank qualification — invalidated for the shipped API

Structurally impossible today, on two independent counts, both
observed:

```
  driver_states(Machine) = {} -- Sim enumerates the ROOT class only, and the root declares no driver
  Sim(machine, dt) fails at its first render: KeyError("no driver state 'motor' bound; ...")
  set_state(motor=1234) -> x_axis.motor=1234, y_axis.motor=1234 -- one flat dict reaches every descendant
```

1. `Sim.__init__` builds its bank from `driver_states(type(node))` —
   the **root class only**. A machine whose drivers all live on
   children gets an empty bank and then fails on its own first render.
2. `AssemblyNode.set_state` merges **one flat dict** and propagates
   **the same dict** to every descendant, so two instances of one class
   can never hold different values for their same-named driver.

Behind the shim — a bank keyed by the same qualified id sub-question 2
lands on, with the shipped `DriverState`/`RampProgram` doing the
stepping unchanged — the two axes moved independently:

```
  qualified bank: ['x_axis.motor', 'y_axis.motor']
    tick  1: x carriage =  90.000 mm, y carriage =   8.000 mm
    tick  2: x carriage =  80.000 mm, y carriage =  16.000 mm
    tick 10: x carriage =   0.000 mm, y carriage =  80.000 mm
```

Note what did *not* need changing: `Driver`, `DriverState`,
`RampProgram` and the integer-exact landing all worked untouched. The
whole gap is **addressing**, which is why it lands on the same
qualification scheme as the wire format rather than a second one.

## Seams stage 3a must open

1. **Symbolic binding mode.** `AssemblyNode._validate_state` judges
   every state value by `as_number()`, so there is no way to bind a
   symbolic value through the public door. The serialization pass needs
   an explicit symbolic mode (bind every declared driver to its token,
   render, serialize) that is *distinct* from a numeric snapshot —
   never a relaxation of `_validate_state`, which is what keeps a bound
   pose a pure function of numbers.

2. **Per-instance, qualified state binding.** `set_state`'s flat merge
   plus identical propagation must gain a qualified form:
   `set_state(**{'x_axis.motor': 8000})`, or nested scoping, or an
   explicit per-instance walk. `time` stays global — it is the one
   entry that *should* propagate flat — so the seam is about
   distinguishing global from instance-scoped entries, not about
   replacing propagation.

3. **A guaranteed-linked pass.** Qualification is only correct where
   `_link_child` has run. `_rendered_children` (used by
   `set_state`/`clear_state`) renders children **without** linking
   them, so today the same tree can render under two different name
   assignments depending on how it was reached. Stage 3a must either
   link in `_rendered_children` too, or state that qualification
   happens only in the assemble/serialize passes and make an
   unqualifiable read fail loudly rather than collide silently.

4. **An identifier rule for derived names.** `_attr_name_for` yields
   `<attr>-<index>` for list-held children, which is not a legal
   identifier in jokenizer (it parses as subtraction) or OpenSCAD. The
   driver-id scheme needs a sanitization/validation rule, applied where
   the id is computed, with a loud failure for an unrepresentable name.

5. **Root-relative driver enumeration for `Sim` and the driver table.**
   `driver_states(node_class)` reads one class; a machine's drivers
   live across its whole tree. Stage 3a needs the tree walk
   (`qualified_drivers` here) as the one authority feeding both the
   simulation bank and the serialized driver table, so the id in the
   document and the key in the bank are the same string by
   construction.

6. **Per-instance instructions.** `Sim._instruction` reads
   `self.node.instructions` on the root, but `Axis` declares
   `Instruction({'motor': 0.0}, ...)` with a class-local target name.
   Triggering "home the X axis" needs the same qualification applied to
   instruction lookup and to instruction targets. Not spiked; named
   because it falls out of the same decision.

7. **Evaluator reconciliation.** The parity harness copies
   `viewers/widget/src/evaluator.ts` rather than importing it. Stage 3a
   must make the parity check run against the *real* module, and extend
   `evalExpr(expression, time)` to take a driver map rather than a
   single scalar. `isAnimated` should be replaced by the parsed-tree
   free-variable set described above; `tree.ts:operationIsAnimated` and
   `TreeNode.animated` are its only consumers.

8. **Build-path defaults, restated by this spike.** ADR-056 already
   lists this open question; the spike sharpens it. `Sim` failing on a
   driverless root is the same problem seen from the simulation side:
   *something* must bind declared defaults across the tree before the
   first render, and it cannot be `node/` (which may not import
   `simulation/`). The qualified enumeration in seam 5 is the natural
   place for it.

## Design-invalidating outcomes: none occurred

SCOPE named two. Neither happened:

- A viable moment to qualify a string-eager token **does** exist (the
  linked render), so no tree-preserving expression type is forced and
  no per-driver document re-render is needed — client-side
  interactivity survives.
- Client evaluation **does** match Python numerics (2.5e-14), so
  representation, not evaluator parity, was the real question — as
  ADR-056 assumed.

## Spike code

`spike/expressions/` — `machine_model.py` (the two-instance model),
`symbolic.py` (the shims: `DriverToken`, the binding walk, readback),
`parity_harness.js` (the mirrored evaluator), `run_spike.py` (the
runner and its transcript), plus `pyproject.toml` and `.gitignore`.
About 1050 lines including docstrings and evidence printing; roughly
200 of those are the shim under test. Nothing here ships, and nothing
under `spike/axis/` or `solid_node/` was modified.

## Addendum (2026-08-26, after stage 3a landed)

The `instance-qualified-drivers` change absorbed every shim this spike
prototyped, and this directory became caller validation — the same
transition `spike/axis/` made when stage 2 shipped `steplab.py` into
`solid_node/simulation/`.

**Dissolved, not adapted.** `symbolic.py` lost `DriverToken`,
`driver_id`, `instance_path`, `bind`/`bind_symbolic`/`bind_numeric` and
`qualified_drivers` — all four SEAM markers with them. What shipped:

| shim | shipped as |
|---|---|
| `DriverToken`, `driver_id`, `instance_path` | `solid_node.node.qualified` |
| `bind` (link-aware per-instance walk) | `solid_node.node.qualified.drive_tree`, reached publicly as `AssemblyNode.set_state(**{'x_axis.motor': …})` |
| `bind_symbolic` | `solid_node.core.serializer.symbolic_drivers` |
| `qualified_drivers` | `solid_node.simulation.enumeration.qualified_drivers` |

`collect_ops` stayed: it is measurement, not a shim — a flat map of
operation scalars for comparing two passes key by key, which the
shipped nested-document `serialize_node` does not produce.

**All five verdicts revalidate through the shipped API** (`run_spike.py`,
exit 0, 2026-08-26), with the parity numbers unchanged to the last
digit: 182 evaluations, max scalar deviation **2.487e-14**, max
world-matrix deviation **4.302e-16**, and `^` still worth up to 0.186.
Three verdict lines are re-worded because the answer changed:

- **1** and **2** are now *validated on the shipped API* rather than
  behind a shim.
- **5** was *invalidated for the shipped API*; it is now validated on
  it. `Sim(machine, dt)` constructs over the driverless root, its bank
  is keyed `['x_axis.motor', 'y_axis.motor']`, the two axes step to
  0 mm and 80 mm independently, `self.time` reads 1.0 s after ten
  0.1 s ticks, and `trigger('x_axis.Home')` leaves `y_axis.motor` at
  8000.

**The two hazards are now loud failures**, and the runner asserts the
noise rather than the silence:

```
  after set_state() on a never-assembled tree: names=['x_axis', 'y_axis'] -- the propagation walk links before it recurses
    an unlinked instance refuses to qualify: DriverIdError(cannot qualify Axis 'Axis': it is not linked under Machine 'Machine'...)
  identifier rule: a driver behind a list-held child refuses to qualify: DriverIdError(cannot qualify driver 'motor' through node segment 'axes-0'...)
```

**The revalidation run earned its keep**: it caught a real defect in the
shipped code. An ambiguous *bare* bind rolls the failed binding back and
re-renders, and on a tree nobody had bound yet that re-render raised the
unbound-read `KeyError` *over* the `ValueError` that caused it. Fixed by
skipping the cleanup re-render when the restored snapshot has holes, and
pinned by
`tests/test_state_binding.py::…::test_an_ambiguous_bare_name_on_an_unbound_tree_still_says_so`.

**Seam status.** 1, 2, 3, 4, 5, 6 and 8 are closed by this change. Seam
7 (evaluator reconciliation) is **not**: `parity_harness.js` still
hand-copies `viewers/widget/src/evaluator.ts` rather than importing it,
and `evalExpr` still takes a single scalar time rather than a driver
map. That is stage 3b's work, together with the free-variable
replacement for `isAnimated` this document demonstrated; stage 3a only
gates the shipped viewer on the driver table, so a document it cannot
evaluate is refused instead of rendered at a wrong pose.

`spike/axis/` needed no changes and revalidates unmodified (exit 0,
2026-08-26): all five of its verdicts, including the exact 2700 mm³
teeth overlap.
