# Evidence: deferred-read-is-current

Worktree `/home/asa/devel/libresolid-studio/solid-node/WTs/deferred-read-current`,
branch `deferred-read-current`, from main `9a2ff68`. Python
`/home/asa/devel/libresolid-studio/.venv/bin/python`, `PYTHONPATH="$PWD"`
from the worktree unless stated otherwise.

## 0.1 — worktree confirmed

```
$ python -c "import solid_node; print(solid_node.__file__)"
/home/asa/devel/libresolid-studio/solid-node/WTs/deferred-read-current/solid_node/__init__.py
```

`git log --oneline -5` at the start: `9a2ff68` (whole-tree-fixpoint,
ADR-099) at HEAD, working tree clean.

## 1.1 — measuring the cause

Reproduced the openflexure sighting directly with a minimal fixture
(`FixAxis`/`FixRoot`'s exact shape from `tests/test_couplings.py`, with
`FixAxis`'s constant `self.steps = 100.0` replaced by a `Driver` read, so
a re-pose actually changes the source):

```python
class RFAxis(AssemblyNode):
    z = Driver(default=0.0, unit='deg')
    steps = RotationalPort(unit='deg')
    column = FixLeaf()
    steps.drives(column.turn, ratio=0.5)
    def simulate(self):
        self.steps = self.z

class RFRoot(AssemblyNode):
    z_axis = RFAxis()
    strut = FixStrut()
    z_axis.column.turn.drives(strut.swing, ratio=-0.25)

root = RFRoot()
for z in (10.0, 40.0):
    root.set_state(**{'z_axis.z': z})
    print(root.z_axis.column.turn.value, root.strut.swing.value)
```

Output at the base:

```
z=10.0: column.turn=5.0  strut.swing=-1.25  expected_swing=-1.25
z=40.0: column.turn=20.0  strut.swing=-1.25  expected_swing=-5.0   <- STALE
```

Instrumented `_step_relation` (monkeypatched, no source edit) to print,
for the root's own relation, the driver slot's value and whether its
`_enum_marker is current_enumeration()` on every call:

```
--- set_state z=40.0 ---
  [_step_relation #6] record=z_axis.column.turn drives strut.swing
      driver.slot_value=5.0 driver._enum_marker_is_current=False
  [_step_relation #7] record=z_axis.column.turn drives strut.swing
      driver.slot_value=5.0 driver._enum_marker_is_current=False
  [_step_relation #8] record=steps drives column.turn
      driver.slot_value=40.0 driver._enum_marker_is_current=True
  [_step_relation #9] record=steps drives column.turn
      driver.slot_value=40.0 driver._enum_marker_is_current=True
RESULT z=40.0: column.turn=20.0  strut.swing=-1.25
```

**Cause, confirmed by measurement:** calls #6/#7 are `RFRoot`'s OWN
`solve_relations` attempt, which runs BEFORE `RFAxis`'s phase in tree
order. At that moment `column.turn` still holds enumeration 1's value
(`5.0`), because `RFAxis`'s `clear_solved` — which will drop it — has
not run yet this enumeration. `ResolvedEnd.bound()` asked only
`self.slot._value is not None`, found `5.0`, and `_step_relation` solved
the relation immediately (`record.direction = 'forward'`), binding
`strut.swing` from the STALE value. `RFAxis`'s own phase then rebinds
`column.turn` to `20.0` (calls #8/#9, fresh, `_enum_marker` matches) —
but the root's relation already resolved and is never revisited, because
it was never deferred to `enumeration.deferred` in the first place.

## 1.2 — RED

Added `RFAxis`/`RFRoot` and
`TreeFixpointTest::test_a_deferred_relation_reads_the_source_s_current_value`
to `tests/test_couplings.py`, re-posing four times and asserting the
driven end after EACH call:

```
$ python -m pytest -x -q tests/test_couplings.py -k test_a_deferred_relation_reads_the_source_s_current_value
F
...
>           self.assertAlmostEqual(
                root.strut.swing.value, expected_swing,
                msg=f'z={z}: swing reads the source one enumeration stale')
E           AssertionError: -1.25 != -5.0 within 7 places (3.75 difference) : z=40.0: swing reads the source one enumeration stale
1 failed, 135 deselected in 1.45s
```

## 2.1 — the naive fix is wrong (measured)

First attempt: `ResolvedEnd.bound()` returns
`self.slot._enum_marker is current_enumeration()` for a non-None value
(with `marker is None` — bound outside any enumeration — also counted
as bound). The RED test above went green, and the whole-tree scenario
test still passed. But `python -m pytest -x -q tests/test_couplings.py`
then failed at the FIRST subsequent case:

```
FAILED tests/test_couplings.py::FanOutTest::test_symbolic_values_pass_through_a_broadcast
E   solid_node.motion.couplings.UnreachedCoordinate: 'fan' (earth drives
    beads.travel), copy beads-0: nothing bound either end. Column
    (Column).earth and beads-0.travel are both unbound...
```

Cause: `column.earth = 5.0` is set BEFORE `column.render()` is ever
called — no enumeration is open yet, so `earth`'s `_enum_marker` is
`None`. The refined "marker is `None` also counts as bound" rule fixed
that, but the SAME suite run then failed one test later:

```
FAILED tests/test_couplings.py::SymbolicFaceTest::test_a_derived_chain_publishes_the_driver_it_came_from
E   solid_node.motion.couplings.UnreachedCoordinate: relative drives
    pulley.turn: nothing bound either end. upper.relative and
    upper.pulley.turn are both unbound...
```

Traced with `_step_derived` instrumentation (monkeypatched): `arm.render()`
(one enumeration, call it E1) binds `upper.relative` correctly. Then
`symbolic_parts(arm)` calls `serialize_node`, which calls `.render()`
again at EVERY level of ITS OWN recursion — `arm.render()` first (a
whole-tree enumeration E2, since E1 already closed), and then, once
`arm.render()` has FULLY RETURNED and closed E2, `serialize_node`
recurses into `upper.render()` INDEPENDENTLY. Since no enumeration is
open at that point, `upper.render()` OWNS a THIRD enumeration, E3 —
covering only `Upper`'s own subtree, per `_lifecycle_render`'s own
documented "a walker that revisits a node after its owning enumeration
has closed... re-attempts that node's phase" (design.md, whole-tree-
fixpoint). `Arm`'s own phase — which is what binds `upper.art3.elbow`
and `upper.shoulder`, `relative`'s two terms — never runs inside E3 at
all, because `Arm` is an ANCESTOR of `Upper`, outside the subtree E3
walks. So `elbow`/`shoulder` keep E2's value forever inside E3, marker
mismatched — and the naive "marker must match current enumeration"
rule treated a value NOTHING IN THIS PASS WILL EVER TOUCH AGAIN as
unbound, deferring it forever and refusing `UnreachedCoordinate` where
nothing was actually wrong.

**Conclusion:** the deferral question is not "was this bound in the
current enumeration" but "is the assembly that bound it going to run
again before THIS pass concludes" — true exactly when that assembly is
the one currently attempting, or a descendant of it (tree order
guarantees a descendant still has a phase to run); false for an
assembly outside the current pass's own subtree, or one that has
already run without touching it, or none at all (`run_deferred`'s own
fixpoint, which runs with no phase current).

## 2.2-2.3 — the real fix

- `solid_node/node/phase.py`: `note_bound` additionally stamps
  `slot._bound_by = phase.assembly`, inside the SAME guard
  (`phase is not None and phase.kind == SIMULATE`) it already uses for
  `phase.bound`.
- `solid_node/motion/ports.py`: `BoundPort._bound_by = None` added
  beside `_enum_marker`.
- `solid_node/motion/couplings.py`: `_is_descendant_or_self(node,
  ancestor)` (a `_parent`-chain walk, the same climb
  `qualified.instance_path` makes). `ResolvedEnd.bound()` rewritten: a
  value fresh for the current enumeration is bound, unconditionally; a
  non-fresh non-None value is bound UNLESS some assembly's own attempt
  is currently running (`_current_phase()`) and that value's last
  binder (`slot._bound_by`) is that SAME assembly or one of its own
  descendants — in which case it reads unbound and this attempt defers.

## 2.4 — green

```
$ python -m pytest -x -q tests/test_couplings.py
136 passed, 105 subtests passed in 10.45s
```

Includes the new RED test (now green), both regression cases from 2.1,
and every existing scenario, including
`test_an_ancestor_sources_from_a_descendant_solved_coordinate`.

Re-ran the minimal fixture from 1.1 against the fix:

```
z=10.0: column.turn=5.0  strut.swing=-1.25  expected_swing=-1.25
z=40.0: column.turn=20.0  strut.swing=-5.0  expected_swing=-5.0
z=0.0:  column.turn=0.0  strut.swing=-0.0  expected_swing=-0.0
z=25.0: column.turn=12.5 strut.swing=-3.125 expected_swing=-3.125
```

## 3.1 — full suite

```
$ python -m pytest -x -q
2200 passed, 16 skipped, 50 warnings, 804 subtests passed in 291.71s (0:04:51)
```

Base was 2199 passed, 16 skipped (per briefing); +1 is the new
regression test in `tests/test_couplings.py`. No other change in count.

## 3.2 — a second, independently-shaped regression (OpenTorque's shape)

The coordinator separately measured a second sighting: OpenTorque's
`reducer.planet_1.orbit.drives(output_stack.planet_carrier_b.turn)`
lands 4.320e+02 mm off on a second `set_state()`, matching this same
cause. Built the shape directly (source two levels down inside ONE
child subtree, driven end inside a SEPARATE sibling subtree with no
relation of its own — unlike the RED test's single chain into a bare
leaf):

```python
class Reducer(AssemblyNode):
    drive = RotationalPort(unit='deg')
    planet_1 = Leaf()
    drive.drives(planet_1.orbit, ratio=3.0)
    def simulate(self): self.drive = self.speed

class OutputStack(AssemblyNode):
    planet_carrier_b = Leaf()

class TorqueRoot(AssemblyNode):
    speed = Driver(default=0.0, unit='deg')
    reducer = Reducer()
    output_stack = OutputStack()
    def simulate(self): self.reducer.speed = self.speed
    reducer.planet_1.orbit.drives(output_stack.planet_carrier_b.turn, ratio=-2.0)
```

Re-posed four times against the fix:

```
speed=10.0: orbit=30.0 (exp 30.0)  carrier_b.turn=-60.0 (exp -60.0)  OK
speed=40.0: orbit=120.0 (exp 120.0)  carrier_b.turn=-240.0 (exp -240.0)  OK
speed=0.0: orbit=0.0 (exp 0.0)  carrier_b.turn=-0.0 (exp -0.0)  OK
speed=25.0: orbit=75.0 (exp 75.0)  carrier_b.turn=-150.0 (exp -150.0)  OK
```

Confirms the fix generalizes past the single-chain-into-a-leaf shape
the RED test exercises: two independent descendant subtrees, source two
levels down, driven end in a sibling subtree.

## 3.3 — openflexure-microscope's own reproduction

Run read-only from the project root against this worktree:

```
$ cd projects/Lab-Equipment/openflexure-microscope
$ PYTHONPATH=.:<worktree> <venv>/bin/python \
    simulation/openspec/changes/restore-the-root-sentence/evidence/repro_stale.py
after assemble (z=0): z col travel = -0.0    swing = -0.0
enum 2 (z=100)      : z col travel = -0.006103515625    swing = -0.017933625190499233
enum 3 (z=0)        : z col travel = -0.0    swing = -0.0
enum 4 (z=200)      : z col travel = -0.01220703125    swing = -0.03586725213794715
```

`swing` now tracks the SAME line's `z col travel` on every call, rather
than the previous line's, as the project's own script's docstring
describes as the expected (not observed) behaviour.

## 3.4 — pose comparison

```
$ PYTHONPATH=.:<worktree> <venv>/bin/python capture_poses.py capture \
    simulation.microscope.microscope:Microscope <scratch>/openflexure-after-fix.json
captured 11 poses, 113 leaves -> ...

$ <venv>/bin/python capture_poses.py compare \
    <scratch>/before2/openflexure-microscope-openflexure-microscope-before.json \
    <scratch>/openflexure-after-fix.json
max deviation 0.000e+00 over 11 poses
```

Matches the expected `0.000e+00` (main measures `1.793e-04` at
`all@0.63` and `z_motor@1.0` against the same `before2` reference).
