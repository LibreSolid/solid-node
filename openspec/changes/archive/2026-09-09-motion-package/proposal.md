## Why

`solid_node.node` answers one question — what has shape. Ports and the
declared time base have never answered it: a `RotationalPort` carries a
value between nodes and a `Time(loop=…)` states what a second means, and
neither has a geometry. They sit in `solid_node/node/` because that is
where they were written, and the design note
`workflow/motion/joints-and-couplings.md` (2026-09-09) settles the rule
that makes their location wrong: **each top-level module answers one
question, and a name is imported from the module that answers its
question.** `parameters` sizes a design, `node` has shape, `simulation`
tells the machine what to do, `mechanisms` is the arithmetic of laws,
`math` is the algebra — and the thing that moves, and the thing that
drives what, has no module at all.

The two cycles that follow this one (`joints`, then `couplings`) add
`Revolute`, `Prismatic` and `Affine`. Putting a joint in
`solid_node.node` would be the same stretch a third time, and putting it
anywhere else while ports stay in `node` would split one subject across
two packages. The home has to exist before either can be filled, and it
has to be built by moving the names already in the subject, not by
growing beside them. Doing the move now, in its own cycle, keeps the
break one migration for every project rather than three.

The evidence is the project catalogue. Seventy-nine files across
thirty-eight packages in `projects/` import a port kind or `Time` from
`solid_node.node` today — 3DPrintedClocks (`simulation/shared`, wall
clocks 48, 50, 52, 54), Thor, AlbertPro, Metamaquina2, Prusa3-vanilla,
fender-bender, hangprinter, kossel, snappy-reprap, the cycloidal
actuators, openflexure-microscope, poseidon, BCN3D-Moveo,
open_manipulator, openarm, HACKberry, Inmoov-sim, YouCanBuildDog,
hexapod_spiderbot_model, openvmp, abacus, pascaline, v8-engine. Every
one of them will be refactored to joints and couplings; the import line
is where that refactor starts, and an import that still says
`solid_node.node` is the visible mark of a project that has not started.

## What Changes

- **New package `solid_node.motion`**, answering "what moves, and what
  drives what", with three submodules. Its `__init__` exports no names:
  the import line names the submodule, so it says which kind of thing is
  in use.
- **`solid_node.motion.ports`** becomes the home of `Port`, `BoundPort`,
  `RotationalPort`, `TranslationalPort`, `SignalPort`, `bind`,
  `declared_ports`, and — joining them from `node/timebase.py` — `Time`
  and `declared_time`. `solid_node/node/ports.py` and
  `solid_node/node/timebase.py` are **removed**, not left as shims.
- **`solid_node.motion.joints` and `solid_node.motion.couplings`** are
  created empty: a module docstring saying what will fill each
  (`Revolute` and `Prismatic`; `Affine`) and no exported names.
- **BREAKING: `solid_node.node` stops exporting `Port`,
  `RotationalPort`, `TranslationalPort`, `SignalPort`, `declared_ports`
  and `Time`.** `from solid_node.node import RotationalPort` raises
  `ImportError`. No re-export, no deprecation alias, no warning shim.
  The one concession is the message, which names
  `solid_node.motion.ports` so an unmigrated project reads where the
  name went.
- **No behaviour changes.** Every requirement of the `ports` capability
  and of the `kinematics` capability's "Declared time base" holds
  unchanged, at the new import path. Port declaration, per-instance
  slots, scale, causal binding, the render-phase `FutureWarning`, the
  time base's `$t * loop`, its name and `AssemblyNode` guards: all
  identical.
- `InternalNode.connect()` stays a method of the node it is called on —
  it is not, and never was, a module-level function of `ports.py`; it
  keeps working and simply imports `bind` from the new path.
- Documentation follows: the user docs that show the old import line,
  an "Unreleased" changelog entry naming the break and its migration,
  and `docs/architecture.md`, which gains the module rule.
- One ADR (`docs/adrs/NODE/ADR-087`) records the module rule and the
  deliberate break, amending ADR-056 and ADR-072 on export location
  only. It is written during apply, once implementation confirms the
  design.

## Capabilities

### New Capabilities

None. `solid_node.motion.joints` and `solid_node.motion.couplings` are
created empty in this cycle and export nothing, so there is no behaviour
to specify yet; cycles 2 and 3 introduce the `joints` and `couplings`
capabilities with their contents.

### Modified Capabilities

- `ports`: the requirements gain the export path
  `solid_node.motion.ports`, and a new requirement states that the port
  names are not exported from `solid_node.node` and that the old path
  fails with a message naming the new one.
- `kinematics`: the "Declared time base" requirement says `Time` is
  exported from `solid_node.motion.ports` rather than from
  `solid_node.node`.
- `cli-startup-cost`: "Node backend exports resolve on first use" no
  longer lists the ports among `solid_node.node`'s deferred exports, and
  gains the requirement that importing `solid_node.motion` or either of
  its submodules stays as cheap as importing `solid_node.node` — no CAD
  backend, no geometry stack.
- `user-documentation`: the documented import path for the port kinds
  and the time base is the new one.

## Impact

**Framework code.** `solid_node/node/ports.py` and
`solid_node/node/timebase.py` move to `solid_node/motion/ports.py`; new
`solid_node/motion/__init__.py`, `joints.py`, `couplings.py`;
`solid_node/node/__init__.py` loses six entries from `_EXPORTS` and
gains the redirect message; internal consumers update their imports —
`solid_node/node/internal.py` (`bind`), `solid_node/node/assembly.py`
and `solid_node/node/flexible.py`, `solid_node/core/serializer.py`,
`solid_node/manager/snapshot.py`, and the `solid_node/parameters.py`
docstring that names the old module.

**Tests.** `tests/test_ports.py`, `tests/test_time_base.py`,
`tests/test_node_lazy_exports.py`, `tests/test_simulate_split.py`,
`tests/meta_project/machine.py`, plus a new
`tests/test_motion_package.py`. `spike/expressions/machine_model.py` and
`spike/axis/axis_model.py` are spike code and are updated with them.

**Docs.** `docs/leaf-nodes.rst`, `docs/driving.rst`,
`docs/animation.rst`, `docs/api-reference.rst`, `docs/changelog.rst`,
`docs/architecture.md`.

**Projects.** Every project importing a port kind or `Time` breaks on
the release carrying this and fixes one import line per file.
3DPrintedClocks is migrated inside this cycle as proof the new path
works end to end; its files are evidence, never committed from here.

**Downstream cycles.** This is the first of three stacked cycles in this
worktree lineage: `joints` (cycle 2) and `couplings` (cycle 3) each
branch from the previous integrated head. They may depend on nothing
from this cycle beyond **the package existing and `motion.ports` being
where ports live**: no joint base class, no coordinate protocol, no
registry, no hook on `Port`, and no reserved name in `joints.py` or
`couplings.py` beyond the docstring. If cycle 2 needs a change to a port
in order to own a coordinate, that change belongs to cycle 2.

Nothing outside the framework repository is committed by this change.
