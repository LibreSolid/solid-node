## Why

`whole-tree-fixpoint` (ADR-099) promises exactly one shape: "an ancestor
sources from a coordinate a descendant's own relations solve" — the root
sentence openflexure's stage B restored,
`z_axis.actuator.column.travel.drives(body.lower_strut.swing, law=…)`.
The archived change's own scenario says the result holds "at every
pose", but that was never measured past the FIRST `render()`.

It does not hold. openflexure's own `repro_stale.py` (this change's
evidence) shows the driven end tracking the source's PREVIOUS
enumeration's value on every `set_state()` after the first:

    after assemble (z=0): z col travel = -0.0            swing = -0.0
    enum 2 (z=100)      : z col travel = -0.006103515625 swing = -0.0
    enum 3 (z=0)        : z col travel = -0.0            swing = -0.01793...
    enum 4 (z=200)      : z col travel = -0.01220703125  swing = -0.0

**Cause, measured.** Tree order runs an ancestor's own relation attempt
BEFORE the descendant that owns the source has cleared and rebound it
this enumeration (`clear_solved` runs at the START of THAT descendant's
own phase, later in the same pass). `ResolvedEnd.bound()` asked only
`self.slot._value is not None` — true of a value still sitting there
from the PREVIOUS enumeration — so the ancestor's own attempt read it as
already bound and solved the relation immediately, from stale data,
instead of deferring to the pass's own fixpoint. Once solved, the
relation's `direction` is set and the descendant's later, fresh rebind
never reaches it again this enumeration: the driven end is always one
`set_state()` behind. `tests/test_couplings.py::TreeFixpointTest::
test_an_ancestor_sources_from_a_descendant_solved_coordinate` never
caught it because it renders once and never re-poses.

The naive fix — treat any value not bound in the CURRENT enumeration as
unbound — is wrong: it defers forever a value bound by an assembly
OUTSIDE the current enumeration's own subtree (a hand assignment before
the first `render()`, or a node the serializer re-renders alone after
its owning enumeration has already closed, per ADR-099's own accepted
"idempotent re-attempt" case) — nothing will ever rebind it, and
`UnreachedCoordinate` fires where nothing is actually wrong. The correct
question is narrower: is the assembly that bound this value going to
attempt AGAIN before this pass concludes? That is true exactly when it
is the assembly currently attempting its own relations, or one of that
assembly's own descendants — tree order guarantees a descendant's phase
still runs before the pass closes.

## What Changes

- `ResolvedEnd.bound()` (`solid_node/motion/couplings.py`) additionally
  asks, for a non-None value not bound in the CURRENT enumeration,
  whether the assembly that bound it (`slot._bound_by`, new) is the
  assembly whose own attempt is currently running or a descendant of
  it. If so the end reads UNBOUND — this attempt defers, and the pass's
  own fixpoint (`run_deferred`, which runs after every phase, with no
  phase current) picks it up once that descendant has actually rebound
  it. Otherwise the value is trusted, exactly as before.
- `phase.note_bound` (`solid_node/node/phase.py`) stamps `slot._bound_by
  = phase.assembly` alongside the existing `phase.bound` bookkeeping —
  the SAME guard, the SAME call site, no new call site.
- `BoundPort` (`solid_node/motion/ports.py`) gains one new attribute,
  `_bound_by = None`, documented beside `_enum_marker`.

Nothing about deferral, refusal, `_enum_marker`'s own meaning, or the
clear-with-the-motion rule changes. A value already fresh for the
current enumeration (`_enum_marker is current_enumeration()`) is still
trusted immediately, unconditionally — the common case, and the fast
path this change does not touch.

## Impact

- **Specs:** `couplings` — one scenario ADDED under the MODIFIED
  requirement "Relations are solved from the bound side, at the end of
  the owning simulate phase" (ADR-099's own archive modified this
  requirement; every existing scenario heading is unchanged).
- **ADRs:** none. The cause is an implementation gap in what ADR-099
  already decided — "an ancestor sources from a coordinate a
  descendant's own relations solve" is the shape the ADR names as
  working; nothing here revises a decision it states.
- **Code:** `solid_node/motion/couplings.py` (`ResolvedEnd.bound`, one
  new helper `_is_descendant_or_self`), `solid_node/node/phase.py`
  (`note_bound`), `solid_node/motion/ports.py` (`BoundPort._bound_by`).
- **Tests:** `tests/test_couplings.py` — one new regression in
  `TreeFixpointTest`, re-posing the ancestor-sources-from-descendant
  shape three times and asserting the driven end tracks the source's
  CURRENT value on every call.
- **Projects:** none edited. openflexure-microscope's own
  `repro_stale.py` (read-only) and a pose comparison against its
  `restore-the-root-sentence` change's own before-fix capture are the
  evidence; both are this project's own OpenSpec records, not this
  change's.
