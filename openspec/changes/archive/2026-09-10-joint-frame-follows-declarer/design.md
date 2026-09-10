## Context

ADR-088 built the joint and chose, from five options, that a joint's
`axis` and `at` are stated in the **parent's** frame. Option 4 — "axis
and anchor stated in the moving node's OWN frame, so no carry is needed"
— was rejected in one sentence:

> it would make the declaration depend on where the part's own origin
> happens to be, which is the accident joints exist to remove, and it is
> not what an exporter would read.

That was written before a single project had been migrated. Twenty-three
projects declaring 249 class-body joints have been written since, and the
catalogue answers that sentence in both directions.
`evidence/survey.md` is every one of them, with the placement its parent
applies and what its anchor means; this design is what that table says,
including where the table says the rule costs something.

The finding has been in `workflow/warts.md` since the day the layer
landed, under the name **"a joint cannot be anchored at a design-placed
part's own origin"**, and it has been re-sighted in nine projects since:

- **Thor** (`workflow/warts.md`, "3DPrintedClocks wall clock 01 and Thor"):
  thirteen catalogue parts that spin on their own bearings — pinions,
  pulleys, the optodisk, the ball cage, the bevels — get **no joint at
  all**, and keep one hand-written `rotate` each with the sign taken from
  `simulation/placing.py`'s `axis_sign`. The sentence the project wants is
  in the wart verbatim:

      base_yaw = Revolute(axis=(0, 0, 1), unit='deg')   # anchored at my own placed origin, no `at`

- **the v8-engine**, "the eighth own-placed-origin sighting (one class,
  four anchors)": four timing gears of one class, four different
  placements, so one class metadata cannot serve them.
- **the hexapod**: "`Femur.lift` and `Tibia.knee` restate the parent's
  `translate` as `at`."
- **Poseidon**: `ThreadedRod` and `ShaftCoupling` are bought-hardware
  envelopes that must carry the pump's layout constants — "even though
  both anchors are exactly the rods' own placed origins".
- **OpenMANIPULATOR-X**: "every arm link writes its URDF origin twice —
  in the parent's `render().translate()` and again as the joint's `at`."
- **the Pascaline**: `Pawl.swing`'s anchor "must re-evaluate the
  `profiles.hinge(...)` formula `Sautoir.render()` already computed".
- **fender-bender**, **the Prusa i3's Z screws**, **OpenVMP's
  `CameraArm`** and **InMoov's wrist group** are the same finding read
  from the other side: the anchor is the *parent's* knowledge, and the
  class cannot state it.

Two of those groups are asking for opposite things, which is why the plan
note (`workflow/docs/motion-catalogue-2.md` §3.2–3.3) cuts them into two
cycles. This one answers the first group. Cycle 3
(`declaration-site-joint`) answers the second.

The rule, in one line: **a joint is stated in the frame of whoever
declares it.** A joint written in a class body is the body's own
statement about itself, so it is read in the body's OWN frame — MuJoCo's
rule, where a `<joint pos>` is a point of the body frame and defaults to
the body's origin. A joint passed at a declaration site (cycle 3) is the
parent's statement about a child it is placing, so it is read in the
declaring parent's frame — URDF's rule, where a `<joint><origin>` is in
the parent link's frame. Neither rule is invented here: the two
declaration sites map onto the two formats' two conventions, and the
frame follows the declarer in both.

## Goals / Non-Goals

**Goals**

- A class-body joint's `axis`, `at` and (for an `Orbit`) `carries` are
  read in the declaring body's own frame, with `at` defaulting to that
  body's own origin.
- Every `at` that only restates where the parent put the body is deleted.
- A shared or catalogue class placed at several sites, or placed by a
  parent that rotates it, can carry a joint — which today it cannot.
- No project's pose moves once its joints are rewritten: maximum
  deviation 0 over all twenty-three projects that declare joints, with
  one named, explained exception (decision 9).

**Non-Goals**

- The declaration-site joint. A project whose anchor genuinely belongs to
  the parent's frame is cycle 3's, and this cycle builds **no second
  escape hatch** for it.
- Any change to composition order (ADR-093), to what a joint owns
  (ADR-088), to an orbit's derivation (ADR-094), to the six coordinates
  of a `Free` (ADR-095), or to the couplings solver. The relation layer
  never sees a frame.
- Any change to the document, the serializer, the viewer, the parity
  corpus or the CLI.
- Deprecating the hand-written form. Both still sit on one node.

## Decisions

### 1. The rule, stated where a reader meets it

**Which frame, exactly.** "The body's own frame" in this document always
means the body's **REST frame**: the frame the body's own `render()`
states its geometry in, which differs from the parent's frame by exactly
the rest placement the parent applied and by nothing else. It is not the
MOVED body's frame: a joint's operations sit innermost, so every one of
them is read in the rest frame however much other motion is composed
outside it, and a joint's line therefore does not chase the body's other
freedoms. That is the same promise the joints spec already makes ("a
joint's line is the line the parent's frame stated whatever the body's
other freedoms are doing"), now stated in the frame that survives.

A joint declared in a class body is read in the rest frame of the body it
is declared on:

- `axis` is a direction of that body's rest frame;
- `at` is a point of that rest frame, defaulting to `(0, 0, 0)` — the
  body's own origin, wherever its parent puts it;
- an `Orbit`'s `carries` is a point of that rest frame, defaulting to
  `(0, 0, 0)` for the same reason;
- a `Free`'s three rotational directions are that rest frame's x̂, ŷ, ẑ,
  and — because a `Free`'s translation is the OUTERMOST operation of its
  own run (ADR-095) — its three translational coordinates displace along
  those same rest-frame directions, **not** along the axes the roll,
  pitch and yaw have just turned. Binding `x` moves the body along the
  rest frame's x̂ whatever `yaw` holds.

Nothing is carried, because there is nothing to carry: the operations a
joint places have always gone in **innermost**, in the body's rest frame,
before every rest operation (ADR-088, `apply_joint_motion`). What changes
is only where the numbers come from. Before, they came from the parent's
frame through an inversion; now they are already there.

### 2. What this deletes: `_carry`, and the ADR-094 sentinel

`Joint._carry` inverts the composed rest placement and maps the axis
(rotation block) and every declared point (full transform) through it. It
has no caller left after this cycle and is removed, with it:

- **`_OWN_PLACED_ORIGIN` and `_OwnPlacedOrigin`** (ADR-094). The sentinel
  existed because "the body's own placed origin" was not a number that
  could be resolved before the body was placed. In the body's own frame
  that point **is** `(0, 0, 0)`, so `Orbit.carries` gets a plain default
  of `(0, 0, 0)` and `resolve` resolves it like any other vector. This is
  the redundancy the briefing asks about, and it is answered by deletion,
  not by keeping a second spelling of zero.
- **The refusal "an unresolvable rest placement is refused"** — the
  `ValueError` naming the node, the joint and the operation whose
  `matrix()` carried a non-numeric value. Nothing inverts, so nothing can
  fail to invert. This is a REMOVED scenario of the joints spec and a
  behaviour the change **relaxes**: a body whose rest placement carries a
  symbolic value may now carry a joint. The Internal Cycloidal Actuator
  met exactly this wall at stage B ("a joint's callable cannot read the
  rest placement at realization"); it is not re-opened here, but the
  refusal that stood in its way goes.

`_snapped` stays, and moves. Residue used to come from the inversion; it
now comes from the one arithmetic step left, `resolve`'s normalization of
the declared axis, which turns `(0, 0, 3)` into `(0.0, 0.0, 1.0)` and can
leave `0.9999999999999999`. So the axis is snapped **after
normalization**, in `resolve`, and reaches the document exact. Anchors
are no longer snapped at all: an anchor is now literally what the author
wrote, and rounding an author's number would be the framework editing the
project's arithmetic. The zero test that omits a `Revolute`'s centring
pair keeps its `1e-9` tolerance, so an anchor the project computes as
`3e-17` still produces one rotation and nothing else.

**Cycle 3 will want the inversion back**, for a site-declared joint whose
arguments are in the parent's frame and whose operations still go
innermost on the child. It is re-added there, against the joint that
needs it, rather than left here as a branch nothing takes. The arithmetic
is forty lines and its acceptance — Thor's elbow, `(0, 1, 0)` about
`(0, 0, 81.5)` — is preserved as a fixture in this cycle's own tests
(decision 6), so cycle 3 restores it against a pinned number rather than
from memory.

What does **not** go is ADR-094's real seam: `Joint.axes(node)` and
`Joint.carried_points(node, anchor)` still say which directions and which
points a subclass's `placement` takes and in what order. They stop
meaning "the parent-frame things this joint needs carried" and start
meaning "the own-frame things this joint's placement takes". `Orbit`
still returns its anchor and its carried point; `Free` still returns the
frame's three directions — now its own, as the literal constants
`(1,0,0)`, `(0,1,0)`, `(0,0,1)`, which is what an identity inversion
returned anyway.

### 3. A joint on a body its parent ROTATES: the axis turns with the body

This is the half of the change that is not a deletion, and the half worth
reading twice.

Today an axis is stated against the parent and carried in, so a body the
parent turns keeps its joint line pointing where the parent's frame said.
Under the new rule the axis is the body's own, so **the joint line turns
with the body**. That is MuJoCo's rule (`<joint axis>` is in the body
frame) and it is what makes a shared class work at several sites:

- **Thor**, `simulation/placing.py`: `axis_sign` exists because thirteen
  catalogue parts are placed with different rotations and each hand-written
  `rotate` needs the sign of its own placement. Under the new rule each
  part writes `turn = Revolute(axis=(0, 0, 1), unit='deg')` once, on the
  part, and every site gets the right line because the line is the part's.
- **the v8-engine**'s four timing gears: one class, four placements, one
  declaration.
- **OpenVMP's `CameraArm`**: "its anchor's sign is the PARENT's handedness
  times its own". The *own* half stops needing to be written; the
  *parent's* half is cycle 3's, and the survey row says which.

The cost is stated as plainly, and the survey found it to be the change's
only real one. Thirty-four declarations sit on a body its parent rotates.
Eleven are untouched, because the rotation is ABOUT the joint's own
line and the axis is invariant (OpenTorque's three 120°-clocked planets,
the Internal Cycloidal Actuator's five, snappy's pinion). Eighteen need a
one-time literal rewrite, and the survey gives every new value. **Five
cannot be written as a literal at all**, and they are §2.2 of the survey:

| declaration | the two placements | today | tomorrow |
|---|---|---|---|
| Prusa `XGuide.spin`, `YGuide.spin` | `.repeat(2)`, `along_y` vs `along_minus_y` | one literal serves both | `(0,0,1)` and `(0,0,-1)` |
| hangprinter `MotorGear.turn` | mirrored on two winches of four | one literal | `(0,0,±1)` |
| hangprinter `RollerBearing.spin` | two rollers, Rx(+90) and Rx(−90) | one literal | `(0,0,∓1)` |
| OpenVMP `Leg.turn` | left Rz(180°), right Rz(0°) | one literal | `(0,±1,0)` |

Two of the three projects wrote the reason down as a design decision —
`hangprinter/simulation/winch.py:57-64` says stating the axis in the
winch's frame "is what lets one declaration serve both the unmirrored and
the mirrored leaf". So the change does not only add: it moves the
"one class, several placements" problem from the ANCHOR (69 sites, all
fixed) to the AXIS (5 sites, all made worse). Ten to one is the trade,
and decision 4 says what the five do meanwhile.

**A mirror is not one of these cases, and cannot be.** The framework has
exactly two operations, `Rotation` and `Translation`
(`solid_node/node/operations.py`); there is no mirror operation and no
`Node.mirror`. A project that builds a mirrored part mirrors the geometry
INSIDE `render()` — or, as hangprinter does, multiplies the mirror into
the leaf and passes it `mirrored=True` — where the placement seam never
sees it. So neither the old rule nor the new one derives a mirrored axis,
and the placement the framework inverts is always a proper rigid motion.
Wherever "mirror" appears in this cycle's evidence it means mirrored
geometry, and the honest answer is that this cycle does not fix it.

### 4. What a body the class cannot describe does, and the one path left open

Two kinds of joint cannot be stated as a class-body literal after this
change: the five axes of decision 3, and any anchor whose value differs
between two placements of one class. **For both, the long answer is cycle
3's declaration-site keyword** — a joint stated by the parent, in the
parent's frame, at the site the parent places the child. It is named as
the migration in the proposal and NOT pre-built here: this cycle adds no
second escape hatch.

**Between the two cycles there are two bridges, and neither is new
machinery.** They are equals, and which one is right depends on where the
knowledge lives.

*Bridge A — a callable of the realized node* (ADR-088), where the body
can tell its own site apart from its OWN declared parameters:

- hangprinter's `MotorGear` holds `mirrored`, so
  `axis=lambda node: (0, 0, -1 if node.mirrored else 1)`;
- OpenVMP's `Leg` holds `side`, so `axis=lambda node: (0, node.side, 0)`;
- the `.repeat()` cases — both Prusa guides, hangprinter's roller pair,
  openflexure's `GearLockScrew` anchor — read the copy's `index`, which
  **cycle 1 of this campaign puts on every repeated copy** and which
  lands before this cycle. That is a real dependency and the tasks state
  it.

*Bridge B — the PARENT supplies the sign in the relation*, where the
handedness belongs to the site rather than to the body. The body keeps
its honest own-frame literal `axis=(0, 0, 1)`, and the parent writes

    carriage.travel.drives(guides.spin, law=sign_by_index)   # cycle 1's broadcast
    motor.turn.drives(left_gear.turn, ratio=-1)              # copies named one by one

This is not a workaround invented here: **it is what Thor already does**,
and it is why Thor's thirteen catalogue parts can share one declaration
at both signs — `PulleyGT2` and `Art56SmallGear` each appear mirrored,
and the sign lives in the parent's `ratio=`, where the mirroring is
known. Nothing is built for it; the verb exists.

Prefer B when the two sites are two mountings of one part and the sign is
the assembly's fact; prefer A when the body genuinely differs (a
left-handed leaf that is a different part). A project that would rather
wait keeps what it has today — the hand-written `rotate` — because none
of the affected projects loses a joint it cannot re-state.

**What the survey found about anchors, stated exactly.** Strictly,
`PARENT-KNOWLEDGE` is **zero** across 249 shipped declarations: there is
no anchor a class cannot write down at all. But **ten anchors are the
parent's knowledge in substance** — the Internal Cycloidal Actuator's two
disk `Orbit`s, InMoov's seven finger `Revolute`s, openflexure's
`GearLockScrew.orbit` — because the line each names is the assembly's
(the actuator axis, the fork pivot, the motor shaft) and the class can
reach it only by inverting its own rest placement by hand and typing the
result. For the Internal Cycloidal Actuator that literal is one its
ratified spec forbids in as many words. Those ten are `PARENT-KNOWLEDGE-
IN-SUBSTANCE` in the survey, and **their real migration is cycle 3**:

    disk_one = CycloidalDisk(orbit=Orbit(axis=(0, 1, 0)))

stated by the assembly that already holds the actuator axis. They carry a
port and a hand-written motion meanwhile, exactly as they do today —
except in this cycle's own pose overlay, where the anchor is DERIVED from
the placement rather than typed (tasks §7.2).

Every other anchor that looks like the parent's — OpenVMP's `dir * side`,
AlbertPro's `KNEE_POS[LEG]`, the Pascaline's `hinge(...)`, HACKberry's
`other_closure_anchor` — needs the parent only to restate a placement,
and all of them delete.

### 5. Composition, ADR-093, and hand-written motion

Nothing here touches composition, and the reason is worth stating because
it is easy to think otherwise. `apply_joint_motion` inserts a joint's run
at its declaration slot, before every hand-written motion and before
every rest operation, and marks it `_motion`. The joint's operations were
already expressed in the body's own frame — that is precisely why
ADR-088 gave joints their own seam instead of `_place_operation`. So:

- the joint block is still innermost, in declaration order (ADR-093);
- hand-written motion still composes outside the whole block, in call
  order among itself;
- a parent's hand-written motion on the same child is `_motion` and was
  already excluded from the rest placement `_carry` inverted, so it never
  interacted with a joint's frame and still does not.

One promise gets **stronger**. The spec says a joint's line is carried
through the rest placement only, "so that a joint's line is the line the
parent's frame stated whatever the body's other freedoms are doing".
Under the new rule the line is not carried through anything, so it is
independent of the rest placement as well: a body whose rest placement
changes keeps its joint line, and two instances of one class placed
differently have the same line in their own frames.

### 6. What the tests keep, and what they must lose

Three existing tests pin the inversion itself and are the change's own
red-first cases:

- `FrameCarryTest.test_the_elbow_lands_on_thors_hand_written_constants`
  and `test_the_anchor_follows_the_parameter_per_instance`. Thor's elbow
  is the framework's one pinned real number. It does not disappear: the
  fixture `tests/joint_project/arm.py` rewrites `Forearm.elbow` from
  `axis=(0, 0, 1), at=(0, reach, 68)` to the forearm's own
  `axis=(0, 1, 0), at=(0, 0, 81.5)` — which is `ELBOW_PIVOT_AXIS` and
  `ELBOW_PIVOT` in Thor's own `art2.py`, the same two constants, now
  written where the project writes them. The assertion is unchanged; what
  changes is that the project no longer needs `into_local` to get there.
- `NumericHygieneTest.test_a_slide_translates_along_its_carried_axis`.
  The gantry rotates its carriage a quarter turn about z, and the test
  asserts the parent-frame `(1, 0, 0)` arrives as `-y`. Under the new rule
  it arrives as `+x`: the slide runs along the carriage's own x. The test
  is rewritten to assert that, and a NEW test asserts the thing the old
  one was really protecting — that the two idle components are the plain
  number `0` and not an expression multiplied by zero.
- `NumericHygieneTest.test_residue_never_reaches_the_document`. Three
  quarter turns of rest placement produced residue through the inversion.
  With no inversion there is no residue from that source; the test moves
  onto the source that remains, an axis that needs normalizing.

And `ArborStack`/`Arbor` in `tests/joint_project/arm.py` is the fixture
that shows the point: its
`at=lambda node: node.built.bearings[node.index]` exists ONLY to restate
`ArborStack.render()`'s `translate([0, PITCH * index, 0])`. Under the new
rule the callable is deleted and the joint reads
`turn = Revolute(axis=(0, 0, 1), unit='deg')`. The callable form itself
stays — an own-frame anchor may still come off a built object — but its
originating case evaporates, and the fixture says so.

### 7. The documentation already describes the new rule

`docs/driving.rst:208-211` reads:

> `axis` and `at` are stated in the **parent's frame** … `at` defaults to
> that frame's origin, **which is the case of a wheel turning on its own
> bearing**.

The second clause is only true when the parent places the wheel at its
own origin. Today, a wheel the parent translates and whose `at` is left
out turns about the PARENT's origin — it swings on an arm instead of
spinning on its bearing, silently. That sentence is not a slip to be
corrected; it is what a reader of the documentation already believes, and
it is what the new rule makes true.

### 8. The silent case: `at` omitted on a body the parent moves

This is the change's one silent behaviour change and its principal risk.
A `Revolute`, `Orbit` or `Free` written today with no `at` on a body its
parent translates means "about the parent's origin"; tomorrow it means
"about my own origin". Nothing can refuse it — the omitted anchor is the
form the whole change exists to make idiomatic — so it is caught by
measurement, not by a message.

The survey counts **47** such rows and measured every one. **35 are
inert**: 23 `Prismatic`s, whose anchor never enters the placement at all,
and 12 `Revolute`s whose placement translation runs ALONG their own axis,
where sliding the anchor down its own line changes nothing. **12 change a
pose**, and — this is the part the first draft of this design understated
— **ten of the twelve cannot honestly be fixed by writing an anchor**:

- **Inmoov's seven** finger joints (`fingertip.py:58,73`,
  `finger.py:56,62,73,80`, `middle_phalanx.py:36`). The line is the
  FORK's pivot. The only class-side spelling is the negated placement,
  `(0, -34.99, 1.01)` or `(0, -59.97, 2.03)`, typed.
- **the Internal Cycloidal Actuator's two disk `Orbit`s**, the severest
  in the catalogue: the disks' own origins are 3.9974 and 3.9488 mm off
  the ACTUATOR's axis, so a defaulted anchor would carry them round a
  circle at twice the true 2.000 mm eccentricity at a wrong phase. The
  rest-frame anchors are computable — and are literals that project's
  ratified spec forbids anywhere in the project.
- **openflexure's `GearLockScrew.orbit`**, which orbits the MOTOR's shaft
  3.9 mm away, with the sign differing per `.repeat(2)` copy.

All ten are `PARENT-KNOWLEDGE-IN-SUBSTANCE` (decision 4): the line
belongs to the assembly, the class can only reach it by inverting its own
placement by hand, and their clean form is cycle 3's site keyword. This
cycle does not ask those three projects to commit the literal. It proves
the poses with an overlay that DERIVES the anchor from the placement it
inverts (tasks §7.2), and leaves the projects as they are.

The remaining two are **3DPrintedClocks wall clock 48's**, which are
decision 9: nothing to write, because the change is what that clock
already asks for.

The general safety condition, which three projects' source comments
derive independently, is worth stating once because it is what makes 35
of 47 free: **a defaulted anchor is safe exactly when the placement
translation is parallel to the joint's axis, or the joint is a
`Prismatic`.**

### 9. One project is already written for the new rule, and disagrees with itself

`3DPrintedClocks` contains two families written for two readings.
Clocks 22, 41, 49 and 51 write `at=lambda node: arbor_bearing(node)` on a
leaf `place_train_arbor` has already translated by that bearing — the
inverting reading. Clock 48 writes no `at` at all, with this comment
(`wall_clock_48/clock.py:135-140`):

> This leaf is placed at its bearing by the containing fixed-rod arbor,
> so its own freedom is about its local origin. Using the plate-frame
> bearing here applies that offset twice (invisible on arbor zero, whose
> bearing happens to be the origin) and separates the anchor wheel from
> its independently modelled pallet pins.

Under today's rule exactly one of the two families is wrong wherever the
bearing is not the origin, and clock 48's anchor arbor is at index 5.
Under the new rule clock 48 becomes correct by construction and the other
four delete their `at`.

The consequence for this cycle's evidence is stated plainly rather than
worked around: **wall clock 48 is the one place where the pose comparison
is expected NOT to be zero**, and its deviation is the fix. Whether the
new pose is right is a question for that project's own tests
(`simulation/shared/testing.py:235-251` is the only test in the catalogue
written against this failure mode, and it guards the pendulum rod only),
not for a deviation count. The tasks carry it as a named exception and as
a question for the pilot, not as an accepted difference.

## Risks / Trade-offs

- **ADR-088 chose the other rule**, from five options, and rejected this
  one in one sentence: it "would make the declaration depend on where the
  part's own origin happens to be, which is the accident joints exist to
  remove". The catalogue answers both halves. Where a part's own origin
  is an accident — a design-placed body whose origin means nothing — the
  survey found the anchor is written as a genuine point and stays one
  (69 `PARENT-FRAME-OFFSET` rows, 62 of them numerically unchanged).
  Where the part's own origin IS the joint — a wheel, a gear, a pinion,
  a screw, an arbor — it is not an accident, it is the bearing, and 133
  of 249 declarations (69 restating a placement, 64 already anchorless)
  plus ~30 hand-written rotations say so. This cycle
  supersedes that part of ADR-088 on evidence ADR-088 did not have.
- **The five axes of decision 3 are a real regression** for the four
  months between this cycle and cycle 3, in three projects that
  documented the parent-frame axis as a deliberate choice. Mitigated by
  the callable, not removed.
- **The exporter argument in ADR-088 was half right.** URDF reads the
  parent's frame; MuJoCo reads the body's. The framework now has both
  conventions, one per declaration site, which is a better position for
  an exporter than one convention was — but nothing exports a joint yet,
  so this is an argument, not a measurement.
- **`Free` floats against its REST frame now.** ADR-095 left "whether
  `at` is read in the parent's frame or the body's own" explicitly OPEN.
  This cycle closes it for `at` *and* for the three translational
  directions: both become the body's rest frame — the frame its own
  geometry is stated in, one rest placement away from the parent's, and
  fixed under the joint's own rotations because the translation is
  outermost. **For the hexapod, the one project with a `Free`, the two
  readings are indistinguishable**: its chassis has an identity rest
  placement, so its rest frame IS its parent's frame at every pose. No
  project in the catalogue measures the difference, which is why this is
  recorded as a rule and a risk rather than as something the catalogue
  proved.
- **The silent case of decision 8**, twelve sites, and the one expected
  non-zero pose of decision 9.
- **Churn between cycles 2 and 3.** The inversion is deleted here and
  re-added there. Accepted: a branch nothing takes is worse than forty
  lines re-derived against a pinned fixture.
- **The evidence is a read-only overlay, not the projects.** No project
  repository is edited by this cycle, so no project is PROVED migrated
  here; what is proved is that a mechanical rewrite of its joints
  reproduces its poses. Each project's real stage B is its own cycle.

## Migration Plan

Per declaration, from `evidence/survey.md`:

1. `RESTATES` (69) → delete the `at`, and with it four multi-line
   lambdas, eight `LEG` class attributes and one twice-run solver.
2. `OWN-ORIGIN-ALREADY` (64) → nothing.
3. `PARENT-FRAME-OFFSET` with an identity placement (62) → nothing: the
   written value already IS the own-frame value.
4. `PARENT-FRAME-OFFSET` with a real placement (7) → the new `at` is
   `M_rest⁻¹ · at`; the survey gives all seven values.
5. `ZERO-BUT-PLACED`, inert (35) → nothing.
6. `ZERO-BUT-PLACED`, pose-changing (12) → **not migrated in this
   cycle.** Ten are `PARENT-KNOWLEDGE-IN-SUBSTANCE` and belong to cycle
   3; they keep what they have today, and this cycle proves their poses
   with a derived anchor in the overlay (tasks §7.2). The other two are
   wall clock 48's, which are decision 9.
7. Axis under a rotation: invariant (11) → nothing; literal rewrite (18)
   → the survey's value; unstateable (5) → **either bridge of decision
   4**, chosen by where the knowledge lives: a callable of the body's own
   parameter or of cycle 1's `index` when the two sites are two different
   parts, or the PARENT supplying the sign in the relation
   (`law=sign_by_index` under cycle 1's broadcast, `ratio=-1` on a named
   copy) when the two sites are two mountings of one part — which is what
   Thor already does and what keeps the body's own axis honest.
8. Anything cycle 3 would state better keeps its hand-written `rotate`
   until cycle 3: the ten anchors of step 6, and the five axes of step 7
   for any project that prefers to wait rather than take a bridge.

The framework's own migration is the fixture rewrite of decision 6. No
project repository is touched by this cycle: the pose comparison runs
against a read-only overlay (tasks §7).

## Open Questions

- **Wall clock 48** (decision 9): is the corrected pose the right one?
  The pose comparison cannot say. For the pilot, with that project's own
  tests.
- Whether `Free`'s three translational coordinates should float against
  the body's own frame (chosen here, by the one rule) or against the
  parent's (the more usual reading of a floating base). No project
  distinguishes them; the first one that does settles it.
- Whether cycle 3 should let a declaration-site joint be passed to a
  `.repeat()`, which is what the five axes of decision 3 really want and
  what three of them will still want after cycle 3 as currently planned.
  Recorded here because the survey is where it became visible.
- Whether the hand-written `rotate` form should be deprecated once the
  catalogue has migrated. ADR-088 deferred it "for at least this cycle
  and the next"; both have passed, and it is still not this cycle's.
- What a joint exports as. ADR-088 and ADR-094 both left it open; this
  cycle makes the answer easier for MuJoCo and no harder for URDF.
