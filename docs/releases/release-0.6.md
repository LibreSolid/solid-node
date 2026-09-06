# solid-node 0.6.0 — release announcement

Released 1 September 2026. Full changelogs: [`HISTORY.rst`](../../HISTORY.rst)
and [`docs/changelog.rst`](../changelog.rst).

---

**The release that makes a model a machine.**

Since 0.5.0, 22 ratified change cycles landed. Until now a solid-node model
moved as a function of one looping `$t`; it can now declare named inputs, be
stepped deterministically in Python, and be driven by hand in the viewer.
Alongside that, three new kinds of part — laser-cut sheets, imported STL
meshes, and flexible parts whose shape follows machine state — and an
assembly assertion that knows about gravity.

## Drivers — the big one

A machine has more inputs than a clock: a carriage position, a crank angle,
a valve lift. An assembly now declares them —

```python
class Axis(AssemblyNode):
    motor = Driver(default=8000, range=(0, 100), unit='ustep', dtype=int,
                   scale=MM_PER_USTEP)
```

— and reads them back as ordinary attributes, in the same expressions
`self.time` always lived in. `time` is now one driver among several.

Driver state is honest by construction. A value belongs to a bound snapshot:
assigning to a driver raises and names `set_state`, reading an unbound one
raises and names the driver, and a declaration that would shadow a node
member fails at class-definition time. `range` is what a slider travels and
never clamps.

Two instances of one class stop being a corner case. A printer's X and Y
axes are the same `Axis` class, and their same-named driver publishes as
`x_axis.motor` and `y_axis.motor` — one dotted id, identical in the
document's driver table, the simulation's state bank, `set_state` and
instruction targets. A tree that cannot be qualified fails loudly instead of
silently sharing one value between siblings.

## A stepped simulation layer

`solid_node.simulation` steps a machine deterministically: `Sim` is a
fixed-`dt` loop whose instants are integer tick counts, with `at(t)`
actions, an `every(period, fn)` cadence, per-tick snapshot binding and
trajectory recording. `Instruction` names driver targets in design units
plus a duration; triggering one ramps each target and **lands exactly on
target** — an integer driver ramps integer-exactly (`start + delta*k//n`),
so no run accumulates float error.

`ScenarioTest` packages the loop for suites, and it is the portability
claim of the layer: one class runs under plain pytest and under
`solid test`, unmodified. A homing scenario holds an interference check at
a 0.1 s cadence all the way in; its adversarial twin drives into the stop
on purpose and asserts the exact tick the overlap is caught.

## A viewer you can drive

The widget evaluates driver expressions, not just `$t`. A machine grows one
slider (numeric readout, design units) per driver and one button per
instruction declared at the focused assembly layer, with a breadcrumb that
walks focus down into subassemblies and back up. The scoping is strict on
purpose: a root that declares nothing shows nothing, which is pressure to
declare machine-level moves on the machine.

Triggers ramp client-side over their declared duration and land exactly on
target. Dragging one driver re-evaluates only the expressions whose free
variables moved — cross-runtime agreement between the Python producer and
the JavaScript evaluator is now pinned by tests rather than measured. Hosts
building their own UI get `drivers()`, `instructions()`, `driver(id)`,
`setDriver(id, value)`, `onDriverChange(fn)` and `trigger(name)` on the
mount handle, and `driverControls: 'none'` to suppress the chrome. A
document with no drivers looks exactly as it did before.

## Three new kinds of part

**Sheets.** `SheetLeafNode` (first backend: `Build123dSheetNode`) authors a
laser-cut part as a 2D `profile()` plus a declared `thickness`. The base
owns `render()` — the extrusion of that profile — so the solid you preview
and the outline a cutter consumes cannot drift apart. Each sheet writes a
nominal, kerf-free `.dxf` beside its STL and BREP, arcs preserved. Kerf
compensation, SVG import, engraving, nesting and a production-export
command are deliberately left out; the persisted exact profile keeps them
all additive.

**Imported meshes.** `StlNode` wraps an `.stl`, so a design published only
as a mesh can be assembled and a new part designed to fit it. A
non-watertight mesh fails at build naming the defect
(`require_watertight = False` admits one knowingly); a multi-body file is
a part pack, selected by `body` with a per-body inventory on
omission; `adjust(self, mesh)` corrects the mesh in code, not constructor
knobs. An `StlNode` in a fusion makes that fusion faceted — the documented
price of designing against a downloaded part.

**Flexible parts.** `FlexibleNode` (first adapter: `MolejoNode`) is the
leaf ADR-003 deferred and the roadmap long carried: a valve spring, timing
belt, cable loom or filament path whose *shape* is a function of its
declared ports' bound values. It never caches a rigid artifact — its
representation in the document is a [molejo](https://molejo.readthedocs.io)
shape spec plus one expression per parameter, evaluated in the browser into
reused buffers only on frames its inputs changed. Exact geometry comes from
molejo's OCCT evaluator.

## Assemblies are checked against gravity

`assertAssemblySupported` proves two things about the same solids
`assertNoSolidInterference` compares. Support reachability: displaced along
gravity, every solid lands on another with positive volume, and reaches a
grounded seed through those "rests on" edges — a part left floating in
space fails. Static equilibrium: push-only contact forces over the detected
contacts must balance every solid's gravity wrench, force *and* torque, for
the whole assembly at once, decided by one deterministic linear program — a
bar supported at one end fails, a tall solid on a small footprint fails.
`ground` anchors bolted solids, `supports` declares press-fits the geometry
cannot prove, `stability_margin` rejects knife-edge balances. Friction,
adhesion and dynamics remain out of scope, and the docstring says so.

## Also in this release

- **build123d is a fifth backend** (`Build123dNode`): exact OCCT geometry,
  a `.brep` beside the STL, no OpenSCAD binary — and exact fusion works
  across backends, CadQuery and build123d children fusing exactly together.
- **Freshness is integer-nanosecond exact.** Float mtime round trips lost a
  sub-quantum remainder, which on millisecond-resolution filesystems killed
  caching outright (50 of 100 whole-millisecond stamps failed the round
  trip). Stamps are now the exact value read; freshness stays exact
  equality, no tolerance window.
- **`manifold3d` is conditional**, resolved at the operation that needs it:
  an all-exact project runs its geometric assertions without the compiled
  wheel — including on WebAssembly, where none exists.
- `clear_keyframe()` joins `set_keyframe(t)` as its explicit inverse, and
  `export_node` leaves nodes in symbolic time.
- The driver readout holds still under a drag: fixed decimals, tabular
  figures, the unit in its own segment.

## Breaking changes at a glance

1. **Reinstall required.** `cadquery` 2.5 → 2.7, `build123d` 0.10 joins,
   and the shared `cadquery-ocp` binding moves 7.7 → 7.8 — two versions of
   that large binary wheel cannot coexist, so recreate the environment. No
   project source changes.
2. **Document schema 1 → 2 (drivers), 3 with a flexible part.** The
   producer emits the lowest version its content needs, and this release's
   viewer renders 1, 2 and 3 — but a 0.5.x viewer has no version gate and
   will *silently* render only the part of a 0.6 document it can evaluate.
   Hosts pinning their own bundle must upgrade it with the framework.
   Declared viewer API version: 5.
3. `export_node` leaves the node symbolic rather than in the caller's last
   pose; a host reusing the node re-applies `set_keyframe`.
4. solid-node now depends on molejo (`brep` extra) and the bundled viewer
   on the molejo npm package, pinned to molejo's minor.

---

## Where this release came from

As with 0.5.0, almost nothing above started as a design idea. The drivers
and the simulation layer grew from machines that needed more than one
clock; the flexible leaf from the V8 engine's valve springs, which a rigid
leaf could only fake — and whose first molejo drawing coiled 14 mm beside
the valve stem, which is why the docs now warn you where a helix winds.
The sheet leaf came from laser-cut structure, the STL leaf from designing
against parts the world publishes only as meshes, and the gravity
assertion from assemblies that passed every interference check while
floating in mid-air.

The Metamaquina 2 — a real, shipped open-hardware printer whose OpenSCAD
sources this framework now reads in place, drives on three axes and
threads with flexible filament — is the kind of machine 0.6.0 exists for.
It is embedded, driveable, in [the documentation's examples
page](https://solid-node.readthedocs.io/en/latest/examples.html).
