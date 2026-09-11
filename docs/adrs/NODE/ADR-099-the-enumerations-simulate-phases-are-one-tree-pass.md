# ADR-099: The Enumeration's Simulate Phases Are One Tree Pass

**Status:** Accepted
**Date:** 2026-09-10
**Revises:**
- [ADR-089: `drives` relates two coordinates](./ADR-089-drives-relates-two-coordinates.md) (the per-instance solve boundary: a relation now solves at the end of the OWNING instance's phase, defers to the whole tree's fixpoint what that instance's own attempt cannot reach, and refuses only once every phase has run)
**Cites:**
- [ADR-093: The joints of one class compose in declaration order](./ADR-093-joints-of-one-class-compose-in-declaration-order.md) (the position rule a replaced relation obeys)
- [ADR-096: A relation broadcasts over a repeated child](./ADR-096-a-relation-broadcasts-over-a-repeated-child.md) (a broadcast's n records sit in the pass at the position of their declaration, in copy order)
**OpenSpec change:** `whole-tree-fixpoint`

## Context and Problem Statement

`evidence/survey.md` (27 simulation packages, 676 `drives` sentences)
found fourteen distinct workarounds in twelve projects, every one of
them a constant or a sentence stated in the wrong class, because a
relation may only be solved from a coordinate bound **by the end of the
stating instance's own simulate phase** — the phase runs once per node,
parents before children, and refuses whatever it cannot reach there and
then:

- OpenTorque's 8:1 reducer ratio is stated twice because the sentence
  that states it once, `reducer.planet_1.orbit.drives(output_stack.planet_carrier_b.turn)`,
  is refused: the carrier plates are the body the planets orbit WITH,
  and that coordinate is not reachable from the reducer's own phase.
- openflexure's root sentence does not exist: four laws are sourced from
  the root's `z_motor` driver instead of from
  `z_axis.actuator.column.travel`, recomposing the gear ratio and screw
  pitch the `Axis` class already states.
- Wall clock 01's going train cannot be stated inside `Train`:
  `centre.drives(third)` there, with `power.drives(train.centre)` in
  `Movement`, is refused at `Movement`'s end because `Train`'s own
  relations have not run yet.
- Every one of 32 clocks writes a second relation whose only job is
  making a coordinate readable elsewhere.

Three riders travel with the same root cause, each measured directly on
this tree by a probe in `openspec/changes/whole-tree-fixpoint/evidence/`:

- **`probe_own_read.py`**: a class's own derived coordinate, or a joint
  coordinate its own relation binds, reads as an empty slot inside its
  own `simulate()` — `rotate(None, ...)` silently turns nothing, caught
  only by a pose comparison (Thor's two motor pulleys).
- **`probe_stale.py`**: an author-bound joint's VALUE survives between
  enumerations while its MOTION is swept, because `clear_solved` never
  touched what the author bound — a guard that binds a rest default only
  when `value is None` stands correctly once, then at rest forever
  (Prusa i3: 37.5 mm, 70.4 mm, 0.05 mm of second-render pose deviation).
- **`probe_subclass.py`**: a subclass reassigning a relation to a name
  its base used adds a SECOND relation of that name rather than
  replacing the base's, and the solve raises `DoublyBound`.

## Decision

**One tree pass, opened by the outermost `render()`.** A `render()`
call that finds no enumeration already open OWNS one: it drives every
assembly's phase in the subtree it renders — sweep, rest, LINK the
children (so a refusal names them by path, not by class-name fallback),
clear what this assembly bound last phase, the author's `simulate()`,
then this instance's own relations/wirings ATTEMPTED — parents before
children, declaration order among siblings, before the call returns.
What one instance's own attempt cannot resolve is DEFERRED to the
enumeration rather than refused; a DOUBLY BOUND coordinate is never
deferred, because it is a contradiction and not a question of timing.
Once every phase has run, the enumeration propagates over every
deferred item to a fixpoint, in tree order, and only then refuses
`UnreachedCoordinate`/`NotInvertible` for what is left.

**A read of a coordinate a relation binds is refused, judged at the end
of the pass.** A read of an unbound slot during a simulate phase is
recorded — the coordinate, the reading class, the source location.
Whether it is later refused is decided at the end of the enumeration by
what actually bound the slot: bound by a relation, a derived coordinate
or a wiring afterward — refused, naming both classes and the order.
Bound by the AUTHOR afterward — not refused: that is the rest-default
guard eight sites in the catalogue write, and a refusal at the moment of
the read cannot tell that case from Thor's silent pulley, because at the
read they are the identical event.

**A coordinate is cleared with the motion it caused, by whoever bound
it, judged per enumeration.** At the start of an assembly's phase, the
framework drops the value and binder of every coordinate THIS assembly
bound during its PREVIOUS phase — the author's own binding included —
in the same moment as the sweep that drops the operations. A slot some
OTHER assembly has ALREADY (re)bound during the CURRENT enumeration —
measured on Prusa i3's own tree, where the root's `x.drives(xaxis.carriage.travel)`
binds it before `XAxis`'s own rest-default guard's delayed clear would
otherwise fire — is left alone: the clear is scoped to `_enum_marker`,
the enumeration the slot was last bound in, not merely to "was this
assembly the one who bound it last time." Without this, the later
assembly's stale record of its own past binding wipes out a value the
current pass already produced correctly, before that assembly's own
phase — later in the same cascade — runs.

**A subclass replaces a named relation by name, keeping the base's
position.** `declared_relations` walks the MRO base-first; a relation
ASSIGNED to a name a base already used replaces it at the base's
position in the enumeration (the rule a redeclared joint already obeys,
ADR-093); a BARE statement, or a name no base used, stays additive.

## Consequences

- **The mark that lets a node's phase run once per enumeration is scoped
  to an enumeration that is still open**, not to "the last one ever
  opened, whether still open or since closed." Several call sites bind a
  coordinate directly and call `render()` again with no enumeration in
  between — a test setting a joint by hand twice, `qualified.drive_tree`
  (the serializer's symbolic mode, the loader's default binding) writing
  a node's snapshot directly — and a mark compared against a merely
  remembered last enumeration reads a STALE pose instead of a wrong
  error for those. The accepted cost: a walker that revisits a node
  AFTER its owning enumeration has closed (`assemble()`'s own `as_scad`
  recursion, the serializer, a keyframe re-render) re-attempts that
  node's phase — an idempotent solve, never a source of a stale result,
  measured in the change's cost report.
- **`qualified.drive_tree`** (`solid_node/node/qualified.py`) now
  delivers every node's snapshot over a REST-ONLY walk before rendering
  the tree once, mirroring `set_state`: a nested driver's own render()
  now runs as part of the SAME cascade that reaches it, so its entry has
  to be bound before ANY render() in the tree, not merely before the
  walk's OWN later visit to that node. Not named in the proposal's
  Impact section (which named `set_state` alone); found necessary by
  `tests/test_build_defaults.py` breaking on a nested driver.
- **A bare `render()` call now links its own children**, where before
  only a walker that recursed (the serializer, state propagation) did.
  Two pre-existing tests encoded the opposite as their premise
  (`test_declarative_render.py::test_a_grouping_node_needs_no_methods`,
  `test_a_legacy_render_is_untouched`) and are corrected; a walker that
  ALSO links afterward (the serializer, `as_scad`) now does so twice,
  costed and accepted in `tests/test_traversal_naming.py`.
- **The three refusals keep their names, kinds and message bodies.** A
  node path in a message now resolves by path rather than falling back
  to the class name, because every node is linked before its own phase
  attempts anything.
- **`set_state`/`clear_state`'s propagation is split from enumeration.**
  They deliver the whole snapshot over the tree at rest, then run ONE
  enumeration — otherwise a descendant would simulate against the
  binding a `set_state` call before it, not the one it names
  (`probe_state_order.py`).
- **The catalogue's pose comparison, project by project, before and
  after, is 0.000e+00 for all 23 projects this campaign migrated**
  (`docs/motion-general-refactor.md`), captured from a `git archive
  HEAD` snapshot of each so a concurrently-migrating project's working
  tree is never read live. Prusa i3 and hangprinter's second-render
  deviations, and abacus's own rebind-to-agree workaround, are proven to
  be 0 on the exact mechanism described above (the `_enum_marker`
  clearing fix), not merely unaffected.
- **3DPrintedClocks is refused by the read rule as its code stands.**
  `simulation/shared/motion.py:1060-1072` reads two arbor coordinates
  `Movement`'s own relations bind and assigns the resulting `None` into
  two ports nothing drives — dead code today, a refusal under this ADR.
  The project's own resumption removes it; not exercised in this cycle's
  implementation because the project's working tree was under the
  pilot's own session throughout.
