# ADR-066: render() Builds the Machine at Rest, simulate() Moves It

**Status:** Accepted
**Date:** 2026-09-03
**Extends:**
- [ADR-002: Template-Method Pattern for Node Lifecycle](./ADR-002-template-method-pattern-for-node-lifecycle.md)
- [ADR-023: Kinematic Operations and Driver-Tagged Idempotent Renders](./ADR-023-kinematic-operations-and-driver-tagged-idempotent-renders.md)
**Depends on:**
- [ADR-056: Signals, drivers, ports, and stepped simulation](./ADR-056-signals-drivers-ports-and-stepped-simulation.md)
- [ADR-064: An Internal render() That Returns Nothing, and Structural Omission](./ADR-064-an-internal-render-that-returns-nothing.md)

## Context and Problem Statement

Since ADR-023 an assembly's `render()` has done two jobs the framework
could not tell apart: placing the parts that never move and moving the
ones that do. The animator sweep tags every operation applied during a
render and drops it before the next, so a rest placement was restated on
every instant, its operation objects churned, and a class that wanted a
placement to persist put it in `__init__`, outside any render, where the
sweep would not see it — the recommendation the fixes cycle (ADR-065's
neighbour) wrote down.

Migrating three projects showed the recommendation wrong in kind. An
operation applied in `__init__` is innermost on the part's chain, and a
once-only turn that must compose *outside* a driven rotation — the
forearm's presentation turn over the wrist rotation in Inmoov-sim, the
static translations after a time-driven rotation in v8-engine — could not
be hoisted at all. The pilot's assessment: which operations persist and
which are per-instant is a lifecycle fact, and the lifecycle should say it.

The design reference's rename of `render()` into `shape()`/`assemble()`,
deferred by ADR-064, is dropped: *render* also means *to make*, and it
names the building of the initial state on a leaf and an internal node
alike.

## Decision Drivers

- The author states rest and motion by where the code goes, not per
  operation.
- Every current model keeps working; the pilot refused raising on a
  driver read in `render()`.
- Motion must compose inside rest placement, which is what every case in
  the migrated projects needs.
- No walker, the serializer, the published document, the widget, or the
  test runner's checkpoint mechanics change.

## Considered Options

1. **`render()` at rest, run once; `simulate()` per instant, run by the
   framework inside the existing render wrapper; motion inserted at the
   head of the one operations list; a driver read in `render()` detected
   and warned** (chosen)
2. A separate `motion` list composed before `operations`
3. Classify by whether the class defines `simulate()`
4. Raise on a driver read in `render()`
5. Keep `__init__` placement as the rest mechanism

## Decision Outcome

Chosen: option 1.

**Lifecycle.** `AssemblyNode` gains `simulate()`, a no-op in the base.
The wrapper installed by `__init_subclass__` (`_lifecycle_render`,
formerly `_idempotent_render`) sweeps the assembly's tagged operations,
produces the children at rest, then runs `simulate()` with the assembly
on the phase stack (`solid_node/node/phase.py`) in the *simulate* phase,
and returns the children. Every walker still calls `render()` and gets a
tree posed for the current binding; the scad build runs `simulate()` once
under symbolic `$t`, the simulator, tests and snapshots per binding.

**Motion is innermost.** An operation applied during the simulate phase
is flagged `_motion` and inserted at the end of the leading motion region
of the node's single `operations` list; one applied in a render phase or
outside any phase is appended. Composition walks the list in order, so
motion precedes rest placement. The sweep removes tagged operations
wherever they sit, and the invariant that motion leads holds because only
the simulate phase inserts. The serialized `operations` array the widget
composes in order is unchanged (option 2 rejected: it would have touched
every consumer and the document schema).

**A render that read nothing runs once.** `DriverDeclaration.__get__`,
`AssemblyNode.time` and `BoundPort.value` report a read to the innermost
render phase, and `ports.bind` reports a binding the same way, since a
binding in a once-only render would never rebind. When the first run ends with no read, the operations it
applied are untagged and the returned children are kept on the instance;
later calls skip the author's `render()`. With a read, the instance is
marked legacy — re-run, tagged and swept per binding exactly as before —
and one `FutureWarning` per class names the class, the read and
`simulate()`. `FutureWarning` because Python shows it to end users;
`DeprecationWarning` is hidden outside `__main__`. Option 3 was rejected
because a pure grouping node would be legacy for no reason and a class
defining `simulate()` while reading a driver in `render()` would freeze
its first binding silently; option 4 was refused by the pilot.

**Structure stays at rest.** `omit()` raises `StructureError` in the
simulate phase. The recorded-set check of ADR-064 remains for the legacy
path.

**Naming.** `children`, the framework's linked list set by `as_scad`, is
excluded from `_attr_name_for`: with a kept rest render the same
instances are in that list on every later link and would otherwise be
renamed `children-<index>`.

**Leaves.** No `simulate()`. A leaf renders from its parameters and, for
a flexible leaf, its bound ports, when the tree is walked for export,
snapshot or a test instant — after the assembly has bound its state.
`FusionNode` is untouched. Placement in `__init__` still works (option 5
is not removed, only no longer recommended).

## Consequences

- The `__init__` placement recommendation of the fixes cycle is
  withdrawn; the declaring page documents the split and the migration.
- Every assembly in the framework's own suite that reads `self.time` in
  `render()` now warns; the suite runs green with the warnings.
- A `render()` whose driver read is conditional is classified by its
  first run. A read through solid2's `get_animation_time()` directly is
  not detectable; the docs say to read `self.time`.
- The test harness that re-assembles a tree must forget the memoized
  assembly of every node, not only the root, because the children are now
  the same instances.
- A later cycle may remove the legacy path once the projects are
  migrated; nothing here prevents it.

## References

- `solid_node/node/phase.py`, `solid_node/node/assembly.py`
  (`_sweep`, `_rest`, `_lifecycle_render`, `simulate`),
  `solid_node/node/base.py` (`_place_operation`, `omit`,
  `_attr_name_for`), `solid_node/node/qualified.py`,
  `solid_node/node/ports.py`
- `tests/test_simulate_split.py`
- OpenSpec change `render-simulate-split`, capabilities `kinematics`,
  `node-model`, `ports`, `declarative-nodes`, `user-documentation`
- Originating evidence: `projects/Inmoov-sim` and `projects/v8-engine`,
  branch `declarative-api`, round-two migration findings (2026-09-02)
