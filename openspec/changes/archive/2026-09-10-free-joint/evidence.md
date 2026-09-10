# `free-joint`: implementation evidence

Worktree `solid-node/WTs/composed-joints`, branch `composed-joints`,
planning commit `b3982ef` on base `8fa5ef2` (cycle 2, ADR-094, which is
also `solid-node` main). Everything below was run from the worktree with
`PYTHONPATH="$PWD"` and `/home/asa/devel/libresolid-studio/.venv/bin/python`,
which reports the worktree's own `solid_node/__init__.py`.

## 1. The full suite, before and after

    before (planning commit, clean tree)
      2031 passed, 16 skipped, 49 warnings, 592 subtests passed in 302.00s
    after (this implementation)
      2066 passed, 16 skipped, 49 warnings, 683 subtests passed in 284.86s

35 new tests and 91 new subtests, no failure, no skip added, no
pre-existing failure to explain. Four source files and three test files
changed; `tests/test_animator_tag.py`, `tests/test_simulate_split.py`,
`tests/test_docs_exports.py` and every other module are green **with no
edit**, and so are the whole of the cycle-1 and cycle-2 sections of
`tests/test_joints.py` (task 3.5: nothing there needed an edit, so the
composition contract is unchanged).

## 2. Red first

### 2.1 The weak red: the name does not exist

    $ pytest tests/test_joints.py -q
    tests/test_joints.py:32: in <module>
        from solid_node.motion.joints import (Free, Joint, JointRangeError, Orbit,
    E   ImportError: cannot import name 'Free' from 'solid_node.motion.joints'
    1 error in 0.33s

The whole file failing to collect, which says nothing about what any one
case asserts. So, as cycle 2 did:

### 2.2 The strong red: a stub whose name exists and whose behaviour does not

`Free` was written in full — the declaration, the six ports, the naming
rule, the bound-coordinates view, the `__set__` refusal, `resolve`,
`axes` — with **`placement()` returning `[]`** and with **none of the
three seams changed** (`ports.py`, `couplings.py` and `declarative.py`
exactly as the planning commit left them). Every case then fails on its
own assertion or on the measured seam:

    24 failed, 192 passed, 209 subtests passed in 6.90s
    (over tests/test_joints.py, tests/test_ports.py, tests/test_couplings.py)

| Case | Task | RED under the stub (verbatim) |
|---|---|---|
| `FreeJointTest::test_the_six_coordinates_enumerate_under_dotted_names` | 1.2 | `AssertionError: Lists differ: [] != ['pose.roll', 'pose.pitch', 'pose.yaw', 'pose.x', 'pose.y', 'pose.z']` — `declared_ports` reports NOTHING for a six-coordinate joint, the measured hole |
| `FreeJointTest::test_two_instances_read_their_own_six_slots` | 1.2 | green under the stub — red only on the name (2.1). What it distinguishes: six coordinates sharing one slot, or a view that reads the declaration rather than the instance |
| `FreeJointTest::test_an_unknown_coordinate_is_refused_by_name` | 1.2 | green under the stub — red only on the name |
| `FreeJointTest::test_the_composition_is_the_one_the_hexapod_hand_inverts` | 1.3 | `Not equal to tolerance rtol=0, atol=1e-12 … ACTUAL array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]) DESIRED array([[ 8.974877e-01, -4.290650e-01, …, 1.650000e+02], …])`; and `AssertionError: 165.0 not less than 1e-12` |
| `FreeJointTest::test_the_anchored_composition_is_the_same_product_conjugated` | 1.3 | `AssertionError: 161.32538211084898 not less than 1e-12`, six of the seven poses failing individually |
| `FreeJointTest::test_the_hexapods_own_inverse_round_trips` | 1.4 | `AssertionError: 210.89827253155028 not less than 1e-09` |
| `FreeJointTest::test_unbound_coordinates_place_nothing_and_still_read_unbound` | 1.5 | `AssertionError: 'pose.x' not found in {}` |
| `FreeJointTest::test_all_six_unbound_places_nothing_at_all` | 1.6 | green under the stub — the weak case the task expected. What it distinguishes: a placement that runs at realization, or one that publishes six identity operations for a body nobody posed |
| `FreeJointTest::test_the_binding_order_of_the_six_does_not_matter` | 1.7 | `AssertionError:` on the composed matrix (identity against the pose). Its first half — two benches binding FOUR coordinates in opposite orders — is green under the stub, two bodies with no operations being trivially equal; the case was therefore extended with three benches binding ALL SIX in scrambled orders and asserting the resulting matrix against the NumPy product, which is red. Re-run against the stub to confirm: `1 failed, 2 subtests passed` |
| `FreeJointTest::test_re_binding_one_coordinate_re_places_the_whole_joint` | 1.8 | `AssertionError: Lists differ: ['t','t'] != ['t','r','t','t','t','t']` |
| `FreeJointTest::test_an_anchored_free_joint_turns_about_its_anchor` | 1.9 | `AssertionError: Lists differ: ['r', 't'] != ['t', 'r', 't', 'r', 't']` |
| `FreeJointTest::test_assigning_the_joint_as_a_whole_is_refused` | 1.10 | green under the stub — red only on the name |
| `FreeJointTest::test_an_axis_and_a_range_are_refused_at_the_declaration` | 1.11 | green under the stub — red only on the name |
| `FreeJointTest::test_the_anchor_resolves_against_the_instance`, `…_a_callable_anchor…`, `…_a_malformed_anchor…` | 1.12 | green under the stub — characterisation of the inherited argument path, red only on the name, and the methods say so |
| `FreeJointTest::test_a_symbolic_binding_publishes_ordinary_operations` | 1.13 | `AssertionError: Lists differ: [] != ['r', 'r', 'r', 't']` |
| `JointDeclarationTest::test_the_kinds_are_exported_from_the_joints_module` | 1.14 | red on the name only, as the task states (`Free` added to the existing case rather than a second test) |
| `CompositionOrderTest::test_a_free_joint_is_one_unbroken_run_at_its_own_slot` | 3.1 | `AssertionError: Lists differ: ['t','t','r','t','t'] != ['t','t','r','r','t','t','t','r','t','t']` |
| `CompositionOrderTest::test_a_hand_written_rotation_sits_outside_the_free_joints_run` | 3.2 | `AssertionError: Lists differ: ['t','t','r','t','r','t'] != ['t','t','r','r','t','t','t','r','t','r','t']` |
| `CompositionOrderTest::test_re_binding_one_coordinate_returns_the_whole_run_to_its_slot` | 3.3 | `AssertionError: Lists differ: ['t','t','r','t','t'] != ['t','t','r','r','t','t','t','r','t','t']` |
| `CompositionOrderTest::test_a_free_joint_composes_with_an_orbit_of_the_same_body` | 3.4 | `AssertionError: Lists differ: ['t','t'] != ['t','r','t','t','t','t']` |
| `MultiCoordinateWiringTest::test_the_six_coordinates_enumerate_and_the_joint_does_not` | 2.6 | `AssertionError: Lists differ: [] != ['pose.roll', …]` |
| `MultiCoordinateWiringTest::test_a_plain_port_beside_the_six_keeps_its_own_name` | 2.6 | `AssertionError: Lists differ: ['roll'] != ['pose.pitch', 'pose.roll', 'pose.x', 'pose.y', 'pose.yaw', 'pose.z', 'roll']` |
| `MultiCoordinateWiringTest::test_the_joint_cannot_be_wired_whole` | 2.6 | `AssertionError: TypeError not raised` — the joint passed whole is SILENTLY taken for a parameter and reaches the child's constructor, exactly as measured |
| `MultiCoordinateWiringTest::test_a_dotted_coordinate_is_not_a_wiring_keyword` | 2.6 | `AssertionError: 'assignment' not found in "Rig.chassis: Chassis cannot receive a coordinate as 'pose.roll', because it declares no port or joint of that name; it declares: none."` — the misleading refusal that would have become an ACCEPTANCE the moment `declared_ports` reported the six |
| `MultiCoordinateWiringTest::test_a_one_coordinate_joint_is_wired_exactly_as_before` | 2.7 | GREEN before and after — a characterisation guard, and the method says so |
| `MultiCoordinateWiringTest::test_a_name_declared_as_a_free_joint_and_a_port_is_refused` | 2.8 | `AssertionError: TypeError not raised` — `_refuse_coordinate_clash` returns early and the last assignment silently wins |
| `MultiCoordinateEndTest::test_a_relation_reaches_one_coordinate_by_path` | 2.1 | `SidewaysReadError: cannot read 'pose' off the Chassis declaration (chassis.pose): a sibling's parameter is not a value in a class body; declare the shared parameter on this class and pass it to both children. Chassis declares: no port, joint or child.` |
| `MultiCoordinateEndTest::test_a_relation_into_a_free_coordinate_inverts` | 2.1 | the same `SidewaysReadError` |
| `MultiCoordinateEndTest::test_a_relation_is_stated_in_the_joints_own_class_body` | 2.2 | `TypeError: Floater: the coordinate 'pose.roll' named by the relation pose.roll drives pulley.turn is not declared on Floater -- Floater declares it.` — the joint's coordinate is not in `declared_ports(owner)`, so `OwnRef.check_declared_on` refuses the class's own coordinate |
| `MultiCoordinateEndTest::test_the_path_grammar_pops_two_segments` | 2.3 | `SidewaysReadError: cannot read 'pose' off the Chassis declaration (shoulder.chassis.pose): …` |
| `MultiCoordinateEndTest::test_the_joint_itself_is_not_an_end` | 2.4 | the same `SidewaysReadError` (the wrong refusal, as measured) |
| `MultiCoordinateEndTest::test_a_part_the_joint_does_not_own_is_refused_by_name` | 2.4 | the same, raised one segment earlier than the `twist` it should name |
| `MultiCoordinateEndTest::test_a_node_whose_one_joint_is_free_is_not_an_end` | 2.5 | `AssertionError: TypeError not raised` — `_the_one_joint` passes `len(joints) == 1` and returns a declaration with no coordinate: a wrong pose, not an error |
| `MultiCoordinateEndTest::test_a_relation_binds_through_the_joint_and_not_by_attribute` | 2.9 | the same `SidewaysReadError`, before the `setattr` hole it guards can even be reached |

The stub was then removed (`placement` restored, one line) and the three
seams changed. All 24 went green, with no further edit to any test.

## 3. The mechanism as implemented

**`solid_node/motion/joints.py`**

- `Joint` grows an ordered `coordinates` mapping of FULL NAME to `Port`,
  built in `__init__` as `{self.name: self.coordinate}` and rebuilt in
  `__set_name__` where the single coordinate is named. `coordinate`
  keeps its meaning for `Revolute`, `Prismatic` and `Orbit`.
- `Joint.__set_name__`'s shadowing walk moves into `_refuse_shadowing`,
  so `Free` inherits the check without inheriting the coordinate naming.
- `Joint.axes(node)` is the new hook, returning
  `(self.arguments(node)[0],)`. `_carry(node, axes, points)` now takes a
  TUPLE of directions and carries each through the ONE inversion it
  already computed, mirroring what cycle 2 did for points. `place`
  passes the carried axes then the carried points to `placement`, so
  `Revolute.placement`, `Prismatic.placement` and `Orbit.placement` are
  byte-identical to what they were.
- `Free` is the new declaration: `__init__` refuses any keyword but
  `at`, `angle_unit` and `length_unit` by name; six ports in the order
  roll, pitch, yaw, x, y, z; `__set_name__` renames them to
  `<joint>.<short>`; `__get__` returns `_BoundCoordinates`, a per-read
  view holding the joint and the node; `__set__` refuses, listing the
  six; `__getattr__` gives the class-body read (`pose.roll.drives(…)`);
  `resolve` resolves an `at` and returns `(None, anchor, None)`, so
  `_refuse_out_of_range` reads a `None` span and returns; `axes` returns
  the parent frame's three unit directions; `placement` reads the six
  slots and emits the run.
- `_BoundCoordinates.__setattr__` binds through `bind()` and then calls
  `joint.place(node, None)` — **the whole joint is re-placed on every
  binding**, from whatever the six then hold, which is what makes the
  composition independent of binding order. `Joint.clear` already drops
  the previous run by recorded identity.
- `coordinates_of(joint)` is the small public reader the refusals list.

**The run**, in list order (application order, innermost first):
`translate(-anchor)` when the carried anchor is non-zero;
`rotate(roll, x̂)`, `rotate(pitch, ŷ)`, `rotate(yaw, ẑ)`, each omitted
when its coordinate is unbound; `translate(anchor)` with its pair; and
one `translate` outermost when any translational coordinate is bound.

**The insertion rule, in one sentence:** unchanged — `place` hands the
whole run to `apply_joint_motion` at the joint's index in
`declared_joints(type(node))`, which inserts it as ONE contiguous block
after every joint of an earlier-or-equal slot and before every
hand-written motion, so a joint that places six operations occupies
exactly one position in the declaration order.

**`solid_node/motion/ports.py`**

- `declared_ports` prefers a `coordinates` mapping of ports (keys are
  already full names) and falls back to the singular `coordinate` for a
  derived coordinate. Still duck-typed; `ports` still does not import
  `joints`.
- `set_coordinate(node, name, value)` splits on the LAST dot, reads the
  head and assigns the tail, so a plain name is `setattr` exactly as
  before and `pose.roll` reaches the view's setter.

**`solid_node/motion/couplings.py`**

- `_coordinates_of(value)` is the companion of `_coordinate_of`, and
  `_refuse_several_coordinates(joint, written, detail)` is the one
  refusal every site raises.
- `read_through` gains a branch returning a joint that owns several;
  `PathRef.__getattr__` steps into one for a coordinate and refuses an
  unknown part listing the six; `PathRef.declaration` refuses a path
  that STOPS on one; `PathRef._walk` pops
  `coordinate.name.count('.') + 1` segments; `_the_one_joint` refuses a
  node whose one joint owns several.
- `coordinate_ref` refuses the joint named directly in a class body
  (`pose.drives(…)` and `tilt.drives(pose)`), which is the one place
  both spellings pass through.
- `ResolvedEnd.bind` and `Wiring.apply` bind through `set_coordinate`.

**`solid_node/node/declarative.py`**

- `_coordinates_of` and `_is_coordinate` beside the existing
  `_coordinate_of`; `_is_joint` is now "not a port declaration and owns
  coordinates".
- `ChildDeclaration.__init__` treats a joint of ANY arity as a wiring
  value, so a `Free` passed whole is a wiring (and refused) rather than
  a parameter.
- `_check_wiring` raises `_refuse_wiring_several` for a source that owns
  several coordinates and for a keyword whose first segment names a
  child joint that owns several — so both `Chassis(pose=pose)` and
  `Chassis(**{'pose.roll': lean})` are refused at class definition,
  naming the joint, listing what it owns and saying the coordinates are
  bound by assignment or by relation.
- `_refuse_coordinate_clash` sees a `Free`.

## 4. The three measured seams, and what replaced them

| Seam | Measured before (probe, and the red above) | After |
|---|---|---|
| `declared_ports` | `declared_ports : []` | the six, under `pose.roll` … `pose.z`, in declaration order, with no entry `pose` |
| `read_through` / `PathRef` | `SidewaysReadError: cannot read 'pose' off the Chassis declaration … a sibling's parameter is not a value in a class body … Chassis declares: no port, joint or child` | `chassis.pose.roll` resolves; `chassis.pose` and `chassis.pose.twist` raise `'chassis.pose' names the joint 'pose', which owns 6 coordinates and stands for none of them… it owns pose.roll, pose.pitch, pose.yaw, pose.x, pose.y, pose.z, so name one of them -- pose.roll.` |
| `ResolvedEnd.bind` / `Wiring.apply` | `setattr(node, 'pose.roll', 12.0)` → `'pose.roll' in node.__dict__` is `True`, slot unbound | `set_coordinate`; the test asserts `'pose.roll' not in rig.chassis.__dict__` and the slot holds the value |

## 5. The hexapod fixture, measured (task 7.1)

`evidence/probe_free_matrix.py`, over the same seven poses
`evidence/probe_matrix.py` measured the hand-written four calls at,
against the same NumPy product. "identity rest" is `FloatingChassis`,
the hexapod's own case; "turned+moved rest" is `AnchoredFloat`, whose
parent applies `rotate(25, x)` then `translate([0, 12, 4])` and whose
`at` is `(0, 30, 5)` in the parent's frame.

        roll   pitch      yaw        h    identity rest   turned+moved rest   _to_chassis (mm)
         0.0     0.0      0.0      0.0        0.000e+00           0.000e+00          0.000e+00
        12.0     8.0     25.0    165.0        0.000e+00           5.329e-15          0.000e+00
       -15.0   -15.0      0.0     70.0        0.000e+00           1.421e-14          1.421e-14
         5.0    -3.0    180.0    120.0        8.674e-19           1.421e-14          7.105e-15
        90.0     0.0     45.0    100.0        4.979e-17           3.553e-15          3.553e-15
         0.0    90.0     30.0     60.0        4.979e-17           3.553e-15          5.329e-15
       -33.3    21.7   -119.9   143.25        1.110e-16           2.842e-14          1.421e-14

    max |Free - NumPy product|, identity rest      = 1.1102230246251565e-16
    max |Free - NumPy product|, turned+moved rest  = 2.842170943040401e-14
    max |_to_chassis(Free(p)) - p| (mm)            = 1.4210854715202004e-14

The identity-rest maximum is **exactly** the hand-written equivalent's
own `1.11e-16`, and the round trip is **exactly** its `1.42e-14 mm`: the
framework's composition is the project's composition, not merely close
to it. The asserted tolerances are `atol=1e-12` and `1e-9` as the task
states; nothing was loosened.

## 6. Nothing existing moved (task 7.3)

`evidence/probe_placement_parity.py` poses **22 joint-carrying fixtures
of the existing suite** — every `Revolute`, `Prismatic` and `Orbit`
fixture cycles 1 and 2 left behind, plus Thor's arm at four angles — and
prints each composed world matrix to 15 significant figures together
with its serialized operations. Run against the base tree
(`/home/asa/devel/libresolid-studio/solid-node`, read-only, at `8fa5ef2`)
and against this implementation:

    $ diff before.txt after.txt && echo IDENTICAL
    IDENTICAL

Byte-identical, matrices and operation lists alike. This is the
"by matrix comparison, not by the tests pass" the task asked for.

## 7. Serialization (task 7.4)

`evidence/probe_serial_free.py` runs the hand-written rig of
`probe_serial.py` and a `Free` rig side by side at the same pose
(`roll=5`, `pitch=0`, `yaw=0`, `height=120`, the sideways freedoms never
touched) and diffs the whole document:

    --- hand-written
    [["r", "5.0", [1, 0, 0]], ["r", "0.0", [0, 1, 0]], ["r", "0.0", [0, 0, 1]], ["t", ["0", "0", "120.0"]]]
        document keys: ['children', 'color', 'model', 'operations', 'type']
    --- Free
    [["r", "5.0", [1, 0, 0]], ["r", "0.0", [0, 1, 0]], ["r", "0.0", [0, 0, 1]], ["t", ["0", "0", "120.0"]]]
        document keys: ['children', 'color', 'model', 'operations', 'type']

    identical: True

Identical to `design.md` §9 in every particular, including the plain
`"0"` in the two components no bound coordinate reaches. No new document
key, no new operation kind. A symbolic binding of all six publishes
three `$t`-carrying rotations and one `$t`-carrying translation
(`test_a_symbolic_binding_publishes_ordinary_operations`), and
`set_keyframe`/`clear_keyframe` make them numeric and symbolic again.

## 8. Pixels (task 7.2)

`evidence/floating.py` — a slab with a mast up `+z` and an arm out `+x`,
placed by a `Free` over a ground plane, so roll, pitch and yaw are all
legible from one view. Rendered with
`solid snapshot floating.py:Machine --set <coordinate>=… --viewall`:

    free-level.png         nothing bound but the four the machine binds at
                           zero: the slab square to the ground, mast
                           straight up, arm out +x
    free-rolled.png        roll=35: the mast has tilted a third of a right
                           angle in the y-z plane and the arm still runs
                           +x -- a roll about the parent frame's x̂, which
                           is what the first rotation of the run is
    free-lifted.png        height=60, yaw=40: the body floats clear of the
                           ground, mast vertical, the arm swung round by
                           the yaw. The lift is a pure translation applied
                           OUTSIDE the rotations
    free-gimbal-lock.png   roll=30, pitch=90, yaw=45: the degenerate pose.
                           The slab stands on edge and the mast lies
                           horizontal; roll and yaw are now the same
                           freedom, and the picture is on the record as a
                           picture rather than only as a number

Looked at, all four.

## 9. What the design could not state, and what was chosen

**Which frame the three TRANSLATIONAL coordinates are read in.** The
design (§4, item 6) writes the last operation as `Translation([x, y, z])`
and carries only the three DIRECTIONS into the body's frame; `tasks.md`
1.3 asks the anchored fixture to equal "the same product **conjugated by
its rest placement and its anchor**", which requires the translation to
be a PARENT-frame displacement. On an identity rest placement — the
hexapod, every probe, and the whole of the evidence — the two readings
are the same transform, exactly. Where they differ, the implementation
displaces along the three CARRIED unit directions, the way a
`Prismatic`'s value runs along its carried axis:

- it is what the change's own acceptance test states;
- it reduces to `translate([x, y, z])` verbatim on an identity rest
  placement, including the plain numeric `0` per unbound component,
  which is what the spec's wording describes;
- it is what makes a floating body float against the PARENT's frame
  rather than against its own, which is what "six freedoms against the
  ground" means.

Recorded in ADR-095's Consequences and as question 13 of
`workflow/docs/composed-joints.md` §7. It is a rule chosen, not a thing
a project proved — the same shape as the open question about `at`.

**The default anchor on a body its parent MOVES.** `at` defaults to the
PARENT frame's origin, which is only the body's own placed origin when
the parent does not move it. So `Free()` on a body the parent translates
turns about the parent's origin and emits the two centring
translations — exactly what a `Revolute` with a default `at` does, and
invisible to the hexapod, whose chassis has an identity rest placement.
The fixtures record it: `AnchoredFloat` (an `at` off the origin) and
`PlainFloat` (the default, on a body the parent only TURNS) differ in
their operation kinds, `['t','r','t']` against `['r']`.

**The centring pair is emitted whenever the carried anchor is non-zero**,
including when no rotation is bound — the literal reading of both the
spec and the design, which state the omission rule over the anchor
alone. With no rotation between them the pair composes to the identity,
so it is document noise in one narrow case (`at` off the origin, only
translational coordinates bound) and never a wrong pose. Left literal
rather than quietly narrowed.

**What was deliberately NOT done**

- **No spec sync and no archive.** `tasks.md` 5.1 asks for the sync; the
  orchestrating session reviews first and then syncs and archives.
  `openspec validate free-joint` passes.
- **No project file touched.** The hexapod's stage B is its own cycle in
  its own repository (task 6.3); `libresolid-studio/docs/motion-general-refactor.md`
  is untouched.
- **No `Spherical`**, no quaternion, no export mapping. Carried as open
  questions 9, 10 and the ADR's own.
- **No fix to `solid_node/node/flexible.py`**, which iterates
  `declared_ports(type(self))` and calls `getattr(self, name)` for each.
  A `Free` on a FlexibleNode would raise an `AttributeError` there
  rather than a named refusal. No node is both today, nothing in the
  design's Impact list names it, and inventing a behaviour for a
  combination nobody has written would be guessing; recorded here and in
  ADR-095 instead.
- **No performance bench** for the six re-placements per six bindings.
  Task 8.5 offered "measure it here rather than carrying it"; a bench
  that measured anything real would need a tree, a phase and a baseline
  to compare against, none of which exists, so the honest answer is the
  one ADR-093's cycle gave: recorded as a known unmeasured cost.

## 10. Open questions (task 8)

- **8.1 quaternion `Free`** — carried. `design.md`'s open questions and
  ADR-095's Consequences.
- **8.2 the MuJoCo/Modelica export mapping** — carried, undesigned.
- **8.3 whether `at` is the parent's frame or the body's own** — carried,
  and now half VISIBLE rather than merely stated: the default anchor on
  a moved body turns about the parent's origin, which the anchored
  fixtures record.
- **8.4 wiring a `Free` coordinate downward** — CLOSED as refused by
  name, in both roles, at class definition, with the refusal saying what
  to write instead.
- **8.5 the cost of re-placing on every binding** — carried, unmeasured,
  for the reason in §9.
- **New, raised here: which frame the translational coordinates are read
  in.** §9. Recorded as a rule, not as evidence.
