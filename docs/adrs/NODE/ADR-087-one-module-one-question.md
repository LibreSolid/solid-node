# ADR-087: One Module, One Question

**Status:** Accepted
**Date:** 2026-09-09
**Amends:**
- [ADR-056: Signals, drivers, ports, and stepped simulation](./ADR-056-signals-drivers-ports-and-stepped-simulation.md) (export location only)
- [ADR-072: A declared time base](./ADR-072-a-declared-time-base.md) (export location only)
**OpenSpec change:** `motion-package`

## Context and Problem Statement

`solid_node/node/ports.py` (ADR-056) and `solid_node/node/timebase.py`
(ADR-072) declared `Port`, `RotationalPort`, `TranslationalPort`,
`SignalPort`, `bind`, `declared_ports`, `Time` and `declared_time` inside
`solid_node.node` because that was the only package a declaration could
go in at the time each was written. Neither describes a shape:
`solid_node.node` answers "what has shape" — `AssemblyNode`, the CAD
backends, the declarative structure helpers — and a port carries a value
between nodes while the declared time base states what a second means.
Neither is geometry.

The working note `workflow/motion/joints-and-couplings.md` (2026-09-09)
settles the rule this record adopts: **each top-level module answers one
question, and a name is imported from the module that answers its
question.** `solid_node.parameters` sizes a design. `solid_node.node`
has shape. `solid_node.simulation` tells the machine what to do.
`solid_node.mechanisms` is the arithmetic of laws. `solid_node.math` is
the algebra. Nothing answered "what moves, and what drives what" — and
the roadmap in `workflow/motion/roadmap.md` plans two further cycles,
`joints` and `couplings`, that need exactly that home. Putting a joint in
`solid_node.node` would be the same category error a third time, and
putting it anywhere else while ports stayed in `node` would split one
subject across two packages.

The evidence that this was worth doing as its own cycle, before either
later cycle needed the home: seventy-nine files across thirty-eight
packages under `projects/` import a port kind or `Time` from
`solid_node.node`. Every one of them is refactored to joints and
couplings eventually; the import line is where that refactor starts.

## Decision Drivers

- One module answers one question; a name is reachable from the module
  that answers its question, and from nowhere else.
- `joints` and `couplings` need a home that does not require a second
  relocation once they exist, and that home must not be `solid_node.node`.
- Zero behaviour change: the same classes, descriptors, errors, warnings
  and expressions, only reachable from a different import line.
- `cli-startup-cost`'s ceiling is unchanged: nothing already lazy may
  become eager, and the new package must cost nothing beyond what a port
  or a node declaration already costs.
- The break, once made, must be visible at the failing import line rather
  than silently tolerated by a shim — seventy-nine files migrate on one
  release, not gradually behind a compatibility path nobody is forced to
  leave.

## Considered Options

1. A new package `solid_node.motion` with `ports`, `joints` and
   `couplings` submodules; `node/ports.py` and `node/timebase.py` move
   into `motion/ports.py` verbatim, merged under one docstring; the two
   removed submodules and the six names fail loudly from `solid_node.node`
   with a message naming the new module; no re-export, no alias, no
   deprecation warning.
2. Leave ports and the time base in `solid_node.node`, and put only
   `joints` and `couplings` in the new package.
3. Move ports and the time base, but keep a compatibility shim in
   `solid_node.node` that re-exports them with a `DeprecationWarning`.
4. A separate `solid_node.motion.timebase` module beside
   `solid_node.motion.ports`, mirroring the two original files.

## Decision Outcome

Chosen option 1.

**One package, three submodules, no package-level export.**
`solid_node/motion/__init__.py` carries a docstring naming the three
submodules and the question each answers, and exports no name and no
`__getattr__` deferring to one — `from solid_node.motion import
RotationalPort` is not a working import, only `from
solid_node.motion.ports import RotationalPort` is. A convenience
re-export would restore exactly the ambiguity the `node`/`parameters`
split (ADR-062's amendment) removed: two working paths for one name.

**`motion.ports` holds both original files' subjects.** `Time` reads as
a port-kind thing — a declaration descriptor with a per-instance value,
the same shape `Port` has — so it merges into `ports.py` rather than
keeping a separate `timebase.py` beside it (option 4, rejected: it would
preserve a split with no question behind it, and the roadmap names
`motion.ports` as `Time`'s home explicitly). The merge is verbatim: no
logic in either original file changed, only the two imports that named
their old location — `note_read` now comes from `solid_node.node.phase`,
and `Time`'s two function-local imports (`AssemblyNode`, `read_time`) now
come from `solid_node.node.assembly`, both unchanged in every other
respect. `solid_node/node/ports.py` and `solid_node/node/timebase.py` are
deleted, not left behind as shims (option 3, rejected: the roadmap and
the working note are explicit that the break is deliberate, and a
shim leaves an unmigrated project running, the outcome the break exists
to prevent).

**`joints` and `couplings` are created empty in this cycle.**
`solid_node/motion/joints.py` and `solid_node/motion/couplings.py` each
carry a docstring stating what will fill them — `Revolute` and
`Prismatic` for the former, `Affine` for the latter — and export no name.
Naming a class in either now would let the cycles that fill them (2 and
3 of `workflow/motion/roadmap.md`) be written against a guess instead of
their own design.

**Dependency direction: `node` imports `motion`; `motion` reaches back
into `node` only through the render-phase leaf and, lazily, through the
assembly module.** `solid_node/motion/ports.py` imports exactly one
framework name at module scope, `note_read` from `solid_node.node.phase`
— a module whose own docstring says it imports nothing, so this edge
closes no cycle. `Time.__set_name__` and `Time.__get__` keep their
function-local imports of `solid_node.node.assembly`, exactly as before,
which happen at class-definition and attribute-read time rather than at
module load. `solid_node/node/internal.py`, `solid_node/node/assembly.py`
and `solid_node/node/flexible.py` import `bind`, `declared_time` and
`declared_ports` from `solid_node.motion.ports` at module scope, the
normal direction for a consumer importing its vocabulary. Both import
orders — `solid_node.motion.ports` first, and any `solid_node.node`
submodule first — complete without seeing a half-built module, verified
in a fresh interpreter rather than argued from the source alone
(`tests/test_motion_package.py`).

**The old path fails as an `ImportError`, not the `AttributeError`
`docs/architecture.md`'s parameter-module precedent suggested.**
`solid_node/node/__init__.py` gains a `_MOVED` table (the six names plus
the two removed submodule names, `ports` and `timebase`, all mapping to
`'solid_node.motion.ports'`) consulted by `__getattr__` before the
existing deferred-export and submodule lookup. Reading one of those
names off `solid_node.node`, by any path, raises an error whose message
names the new module and the replacement import line. The exception
raised is `ImportError`, not `AttributeError`, and that departs from
this record's own design note and from the `cli-startup-cost` spec
delta's literal wording — see Consequences.

## Pros and Cons of the Options

### Option 1: `solid_node.motion` package, empty joints/couplings, unshimmed break

- Good: gives `joints` and `couplings` their home before either is
  filled, so filling them is not a second relocation.
- Good: the message at the failing import line is the exact information
  a project needs to migrate, at the moment it needs it.
- Good: no behaviour changes for anything that does migrate; every
  descriptor, error and warning is the class it already was.
- Bad: seventy-nine project files break at once, on the release that
  carries this. Accepted: the break lands in an unreleased version, so no
  published release changes meaning under a user, and the changelog and
  the failure message both give the exact replacement line.
- Bad: merging two files loses `git log --follow` on one of them. Its
  history stays reachable through the delete; this record names both
  origins.

### Option 2: leave ports in `node`, only relocate the future joints/couplings

- Bad: splits one subject — what moves, and what drives what — across
  two packages, which is the exact defect this record exists to remove.
  A joint owning a coordinate that is also a port would then straddle
  `solid_node.node` and `solid_node.motion` for no reason a reader could
  see.

### Option 3: compatibility shim with a deprecation warning

- Good: no project breaks immediately.
- Bad: the roadmap and the working note are explicit that the break is
  deliberate; a warning shim is exactly the outcome — an unmigrated
  project that keeps running — the break exists to prevent, and it is a
  second export table to keep in sync with the real one for as long as
  it lives.

### Option 4: separate `motion/timebase.py`

- Bad: preserves a split — two files for one kind of declaration — that
  the working note's rule does not ask for; `Time` and `Port` answer the
  same question.

## Consequences

- New `solid_node/motion/__init__.py`, `solid_node/motion/ports.py`
  (merging `node/ports.py` and `node/timebase.py` verbatim), empty
  `solid_node/motion/joints.py` and `solid_node/motion/couplings.py`.
  `solid_node/node/ports.py` and `solid_node/node/timebase.py` deleted.
- `solid_node/node/__init__.py`: `_EXPORTS` loses the six names; a new
  `_MOVED` table and the `__getattr__` branch that consults it before
  falling through to `_submodule`.
- Internal consumers repointed at module scope: `node/internal.py`
  (`bind`), `node/assembly.py` (`declared_time`), `node/flexible.py`
  (`declared_ports`), `core/serializer.py` and `manager/snapshot.py`
  (`declared_time`), and the `solid_node/parameters.py` docstring
  sentence naming the old path.
- **The exception raised for a moved name is `ImportError`, not
  `AttributeError`, and this is a deliberate departure from what this
  cycle's own design assumed going in.** The design reasoned that raising
  `AttributeError` from `solid_node.node.__getattr__` would let CPython's
  import machinery "convert" it into an `ImportError` carrying the same
  message when a project writes `from solid_node.node import
  RotationalPort`. That is not what CPython does: `from module import
  name` catches the `AttributeError`, **discards its message
  unconditionally**, and raises its own generic `ImportError` — `cannot
  import name 'RotationalPort' from 'solid_node.node' (path)` — naming
  neither the reason nor the replacement. This was verified directly
  against the interpreter this framework runs on (3.11 and 3.12), not
  assumed from the language reference, once the red-first suite exercised
  it. Raising `ImportError` itself from `__getattr__` is the one exception
  type that survives the import machinery's internal `hasattr()` probe
  (which only ever suppresses `AttributeError`) and therefore the only way
  the message reaches a project's failing import line at all — which is
  the entire point of a message that names where a name went. The same
  choice already governs a broken CAD backend (`solid_node/node/_load`):
  a name that used to resolve and now cannot must not be reported as a
  plain missing attribute. One consequence: the `cli-startup-cost` spec
  delta's "A port kind is not a node export" scenario, written against
  the same incorrect assumption, says literally "`AttributeError` is
  raised naming `solid_node.motion.ports`" — the code here raises
  `ImportError` instead, satisfying the `ports` and `kinematics` deltas'
  explicit requirement that the message survive `from ... import ...`
  verbatim, at the cost of that one sentence's literal exception type.
  The planning record was corrected before archival: the
  `cli-startup-cost` requirement and its scenario now say `ImportError`,
  and the reason is stated there.
  yields.
- Two facts the working note `workflow/motion/joints-and-couplings.md`
  got wrong, corrected here: there is no module-level `connect` to move —
  `connect(source, sink)` is a method of `InternalNode`
  (`solid_node/node/internal.py`), sugar over `bind`, and stays exactly
  where it is; and `BoundPort` and `declared_time` move to
  `solid_node.motion.ports` too, alongside the six names the note does
  list, because the serializer and the snapshot manager read
  `declared_time` and `Port.__get__` returns a `BoundPort`.
- `docs/animation.rst`, `docs/driving.rst`, `docs/leaf-nodes.rst`,
  `docs/api-reference.rst`, `docs/declaring.rst`, `docs/changelog.rst` and
  `docs/architecture.md` updated to the new import path; no doc keeps a
  working example against the removed one.
- 3DPrintedClocks (`simulation/shared/assemblies.py`, wall clocks 48, 50,
  52, 54) is migrated as evidence that the new path works end to end, in
  its own repository, uncommitted from this cycle. Every other project
  named in this change's proposal fixes one import line per file on its
  own migration schedule.
