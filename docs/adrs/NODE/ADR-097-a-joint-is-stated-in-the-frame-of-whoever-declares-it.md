# ADR-097: A Joint Is Stated In The Frame Of Whoever Declares It

**Status:** Accepted
**Date:** 2026-09-10
**Supersedes (in part):**
- [ADR-088: A joint owns one coordinate](./ADR-088-a-joint-owns-one-coordinate.md) (the frame decision only; everything else in ADR-088 stands)
**Revises:**
- [ADR-094: An orbit carries a point and derives its radius](./ADR-094-an-orbit-carries-a-point-and-derives-its-radius.md) (the `carries` sentinel; the open consequence about a `Revolute`'s own-placed-origin `at`)
- [ADR-095: A free joint owns six coordinates](./ADR-095-a-free-joint-owns-six-coordinates.md) (closes the stated open question about which frame `at` and the translation read)
**Depends on:**
- [ADR-093: The joints of one class compose in declaration order](./ADR-093-joints-of-one-class-compose-in-declaration-order.md)
**OpenSpec change:** `joint-frame-follows-declarer`

## Context and Problem Statement

ADR-088 built the joint and chose, from five options, that a joint's
`axis` and `at` are stated in the **parent's** frame — the frame the
parent's `render()` places the declaring body in — and carried into the
body's own frame by inverting its rest placement. Option 4 of that
decision, "axis and anchor stated in the moving node's OWN frame, so no
carry is needed", was rejected in one sentence:

> it would make the declaration depend on where the part's own origin
> happens to be, which is the accident joints exist to remove, and it is
> not what an exporter would read.

That was written before a single project had been migrated. Twenty-three
projects declaring 249 class-body joints have been written since, and a
read-only survey of every one of them
(`openspec/changes/joint-frame-follows-declarer/evidence/survey.md`)
answers that sentence in both directions.

Where a joint's line runs through the body it moves — a wheel on its own
bearing, a gear on its own axle, a pinion, a pulley, a screw — the
body's own origin is **not** an accident: it is the bearing. 133 of 249
declarations are this shape (69 sites whose `at` only restates the
parent's placement a second time, 64 already anchorless) and roughly 30
more are hand-written `rotate()` calls that exist ONLY because a shared
class placed at several sites, or at several attitudes, has no way to
state a parent-frame anchor that is right everywhere — Thor's thirteen
catalogue parts, the V8's four timing gears, the Prusa i3's two Z
screws, openflexure's four flexure legs. `docs/driving.rst` already told
readers that a defaulted `at` was "the case of a wheel turning on its
own bearing"; under the parent-frame rule that sentence was only true
when the parent happened to place the wheel at its own origin, and
`3DPrintedClocks` contains two clock families written for the two
different readings of the same declaration — one of them silently
wrong wherever the bearing is not the origin.

Where a joint's line runs somewhere else — a body carried round a
remote axis, several copies of one class sharing one machine line — the
parent's frame is right. The survey found this shape too, and it is
real: ten anchors and five axes, concentrated in six projects, that this
ADR's Consequences section states exactly rather than rounding away.

The two shapes map onto the two places a joint can be written: a class
body is the body's own statement about itself, and a declaration
site (passed as a keyword when the parent places a child) is the
parent's statement about a child it is placing. Neither is invented
here — they are MuJoCo's `<joint pos>` (a point of the body frame) and
URDF's `<joint><origin>` (a point of the parent link's frame),
respectively — and the frame follows the declarer in both. This ADR
does the first. The second is `declaration-site-joint`, the next cycle
of the same campaign, and is deliberately not pre-built here.

## Decision Drivers

- The catalogue, not a synthetic case: 249 shipped declarations, traced
  to the placement each parent applies, is more evidence than ADR-088
  had for either reading.
- A joint declared where a shared or catalogue class is placed at
  several sites, or by a parent that rotates it, should be statable at
  all — today it is not, and roughly 30 hand-written rotations exist
  only because of that gap.
- State plainly where the rule costs something, rather than reporting
  only the win: an axis under an opposed rotation and an anchor that
  names a line of the assembly are both real, and are not solved by
  this cycle.
- Nothing else in the motion layer moves: composition order (ADR-093),
  what a joint owns (ADR-088 otherwise), an orbit's derivation
  (ADR-094 otherwise), a `Free`'s six coordinates (ADR-095 otherwise),
  the couplings solver, the document, the serializer, the viewer and the
  CLI are untouched.

## Considered Options

1. Keep ADR-088's parent-frame reading for every class-body joint, and
   build the declaration-site keyword as a NEW, second class-body
   spelling (e.g. `at=PARENT_FRAME(...)`) for the sites that need it.
2. Own-frame reading for a class-body joint (ADR-088's option 4,
   revisited on the survey); a declaration-site keyword, reading the
   parent's frame, as a separate feature for a separate cycle.
3. Own-frame reading, with the framework also accepting a per-instance
   "parent-frame" override on the SAME class-body declaration, resolved
   by inspecting the call site.

## Decision Outcome

Chosen option 2.

**A joint is stated in the frame of whoever declares it.** A joint
written in a CLASS BODY is the body's own statement about itself, so it
is read in the body's own REST FRAME — the frame its own `render()`
states its geometry in, one rest placement away from the parent's, and
the frame every joint operation is placed in because a joint's run sits
innermost, before every rest operation, whatever the body's other
freedoms or hand-written motion are doing. `at` defaults to
`(0, 0, 0)`, the body's own origin, so a joint whose line runs through
the body's origin is written with no anchor at all. `Orbit`'s `carries`
defaults to `(0, 0, 0)` for the same reason. A joint PASSED AT A
DECLARATION SITE (option 1's second spelling, option 3's per-instance
override — both rejected as this cycle's business) is the parent's
statement about a child it is placing, read in the parent's frame; it is
`declaration-site-joint`'s feature, not a branch grafted onto this one.

Option 1 was rejected because it keeps the accident ADR-088 objected to
in the cases the survey shows dominate (the 133-plus own-origin shape)
while adding a second class-body spelling for a minority the campaign's
next cycle already has a home for. Option 3 was rejected because
"resolved by inspecting the call site" is exactly the kind of implicit,
position-dependent reading a declaration should not have: which frame a
number means should be legible from the declaration alone.

**The framework transforms nothing.** `Joint._carry` — the inversion of
the composed rest placement that mapped a parent-frame axis and every
declared point into the node's own frame — is deleted outright, because
the operations a joint places have always gone in innermost, in the
body's own frame, before every rest operation (ADR-088,
`apply_joint_motion`). What changes is only where the numbers come
from: before, through an inversion; now, already there. With `_carry`
goes its only use of `numpy`, so `solid_node/motion/joints.py`'s import
cost returns to `solid_node.motion.ports` and `math` alone, exactly
ADR-087's ceiling for the module before ADR-094 opened it for the
carry's linear algebra.

**A body its parent ROTATES carries its joint line WITH it.** This is
the half of the decision that is not a deletion. Today an axis is
carried through the inverse of the rest placement, so a body the parent
turns keeps its joint line pointing where the PARENT's frame said.
Under this rule the axis is the body's own, so the joint line turns
WITH the body — MuJoCo's own rule — which is what lets Thor's thirteen
catalogue parts, the V8's four timing gears, and openflexure's four
flexure legs each state one declaration and have it be right at every
site a parent places or rotates them to, instead of the parent-frame
literal that is right at exactly one.

**The axis is snapped after normalization, in `resolve`; an anchor is
not snapped at all.** Residue used to come from the carry's inversion;
with the carry gone, the one remaining arithmetic step is the
normalization of a declared axis, which turns `(0, 0, 3)` into
`(0.0, 0.0, 0.9999999999999999)` and would otherwise leak into the
document. So the normalized axis is snapped to an exact `0`, `1` or
`-1` within `1e-9`, exactly as before. An anchor is different: it is no
longer carried through anything, so there is no inversion residue to
clean up, and rounding an author's own number would be the framework
silently editing the project's arithmetic. `Revolute`'s and `Free`'s
centring test — whether every anchor component is zero, which decides
whether the centring pair is emitted at all — keeps its own `1e-9`
tolerance so an anchor a project computes as `3e-17` still omits the
pair; the PUBLISHED anchor, when the pair is not omitted, is exactly
what the author wrote, including `81.49999999999999`.

**The deleted refusal.** `_carry` used to raise when a node's rest
placement carried a value it could not resolve to a number — "an
unresolvable rest placement is refused by name" was a scenario of the
`joints` spec. Nothing inverts now, so nothing can fail to invert: a
body whose rest placement carries a symbolic value may carry a joint.
This is a REMOVED scenario, replaced by "a rest placement the framework
cannot evaluate no longer prevents a joint". It is a genuine relaxation,
not a tightening — the Internal Cycloidal Actuator met exactly this
wall at its own stage B ("a joint's callable cannot read the rest
placement at realization"), and while that finding is not re-opened
here, the wall it hit is gone.

**What does not move.** `Joint.axes(node)` and
`Joint.carried_points(node, anchor)` — the seam ADR-094 built so a
subclass states which directions and points its `placement` takes, and
in what order — survive intact. They stop meaning "the parent-frame
things this joint needs carried" and start meaning "the own-frame
things this joint's placement takes", and every subclass that used them
keeps using them unchanged. Composition (ADR-093), what a joint owns
(ADR-088's other decisions), an orbit's derived radius and phase
(ADR-094's own arithmetic), a `Free`'s six coordinates as coordinates
(ADR-095's naming rule and composition contract), the couplings solver,
the document, the serializer, the viewer, the parity corpus and the CLI
are all untouched: the relation layer never sees a frame, and a joint's
operations were always expressed in the body's own frame, which is
precisely why ADR-088 gave joints their own seam instead of
`_place_operation` in the first place.

**`Orbit`'s sentinel becomes redundant, and is deleted rather than kept
as a second spelling of zero.** ADR-094 introduced
`_OWN_PLACED_ORIGIN`/`_OwnPlacedOrigin` because "the body's own placed
origin" was not a number resolvable before the body was placed. In the
body's own frame that point **is** `(0, 0, 0)` — no different from any
other defaulted vector, resolved at realization like every other
argument. `Orbit.carries` now defaults to the plain tuple `(0, 0, 0)`
and `resolve` resolves it through the same `_vector` path as `at`, with
no sentinel branch. ADR-094's consequence "whether a `Revolute`'s
own-placed-origin `at` stays open" is CLOSED by this ADR: it is not
open, it is the default, for every one-coordinate joint and now for
`Orbit`'s `carries` as well.

**`Free`'s three directions are the declaring body's own rest frame's,
literally.** ADR-095 built `Free` with its stated open question:
"whether `at` is read in the parent's frame or the body's own." This
ADR closes it, for `at` and for the three translational coordinates
together. `axes(node)` returns the literal constants
`(1, 0, 0)`, `(0, 1, 0)`, `(0, 0, 1)` — what an identity carry would
have returned anyway, now stated directly with nothing to compute. The
three rotations turn about these FIXED rest-frame directions rather
than about axes that turn with each other (the extrinsic x-y-z sequence
ADR-095 already specified). The one new fact ADR-095 left unstated is
the translation: because it is the OUTERMOST operation of a `Free`'s own
run, it displaces along these SAME rest-frame directions, not along
whichever direction the roll, pitch and yaw have just turned the body
to. Binding `x` moves the body along the rest frame's x̂ whatever `yaw`
holds. For the hexapod, the campaign's one `Free`, the two readings are
indistinguishable — its chassis has an identity rest placement, so its
rest frame IS its parent's frame at every pose — which is why this is
recorded here as a closed question and a risk together: no project in
the catalogue has yet measured the difference.

## Consequences

- **The strict count of anchors that need the parent's frame, across
  249 shipped declarations, is 0.** There is no anchor a class cannot
  write down at all. **The count in substance is 10.** The Internal
  Cycloidal Actuator's two disk `Orbit`s, InMoov's seven finger
  `Revolute`s and openflexure's `GearLockScrew.orbit` each name a line
  that belongs to the ASSEMBLY — the actuator axis, the finger fork's
  pivot, the motor shaft — and the class can reach it only by inverting
  its own rest placement by hand and typing the number that falls out.
  That is the parent's knowledge frozen into the child, the exact shape
  `declaration-site-joint` exists to remove, and for the Internal
  Cycloidal Actuator the required literal is one its own ratified spec
  forbids in as many words. The distinction matters because reporting
  those ten as "write this anchor" would have made this change look
  cheaper than it is, and because it is the reason none of the three
  projects is migrated by this cycle: they keep exactly what they carry
  today — a defaulted anchor that now reads wrong under the new rule,
  and the hand-written motion or callable they already have — until
  `declaration-site-joint` gives the assembly a place to state the line
  it already knows.
- **Five axes lose their literal.** Where one class is placed at
  several sites with OPPOSED rotations — both Prusa belt-guide pairs,
  hangprinter's mirrored motor gear and roller pair, OpenVMP's two legs
  — today's one parent-frame literal serves every site; the own-frame
  axis is different per site and cannot be written as one literal at
  all. Two bridges exist, neither of them new machinery: a callable of
  the realized node reading the body's own parameter or the copy's
  `index` (from `repeat-fan-out`, ADR-096), where the two sites are
  genuinely two different parts; or the PARENT supplying the sign in
  the relation (`ratio=-1` on a named copy, or `law=` under a broadcast)
  where the two sites are two mountings of one part — which is what
  Thor already does. Neither is built here; the literal returns in
  `declaration-site-joint`.
- **Twelve `ZERO-BUT-PLACED` sites change a pose** if a project migrates
  mechanically with no further thought: a joint written today with no
  `at` on a body its parent translates off the joint's line meant "about
  the parent's origin" and now means "about my own origin". Ten of the
  twelve are the `PARENT-KNOWLEDGE-IN-SUBSTANCE` anchors above; the
  other two are 3DPrintedClocks wall clock 48's, which are this ADR's
  one intentional exception, next.
- **3DPrintedClocks wall clock 48 is expected to move, and the move is
  the fix.** Clocks 22, 41, 49 and 51 write `at=arbor_bearing(node)` on
  a leaf already translated by that bearing — the parent-frame reading.
  Clock 48 writes no `at` at all, with a source comment saying plainly
  that using the plate-frame bearing there "applies that offset twice".
  Under the parent-frame rule exactly one of the two families was wrong
  wherever the bearing is not the origin; under this rule clock 48
  becomes correct by construction and the other four delete their `at`
  with no pose change. Whether the corrected pose is right is a
  question for that project's own tests, carried to the pilot rather
  than assumed.
- **The precise frame is the body's REST frame, not its moved frame.** A
  joint's operations sit innermost, so they are read in the frame one
  rest placement away from the parent's, and that reading does not
  chase the body's OTHER freedoms or any hand-written motion applied to
  it — a joint's line is invariant to everything composed outside it,
  which is a promise the `joints` spec already made and this ADR makes
  stronger: the line is now also invariant to the rest placement itself,
  since nothing carries it through that placement any more.
- `solid_node/motion/joints.py` is the only module touched:
  `Joint._carry`, `_OwnPlacedOrigin` and `_OWN_PLACED_ORIGIN` are
  deleted; `Joint.place` uses `axes(node)`/`carried_points(node, anchor)`
  directly; `Joint.resolve` snaps the normalized axis;
  `Orbit.__init__`'s `carries` defaults to `(0, 0, 0)` and `Orbit.resolve`
  drops the sentinel branch; `Free.axes` returns the literal three
  directions; the `Revolute`/`Free` centring test gains an explicit
  `1e-9` tolerance now that nothing upstream snaps the anchor for it.
- **No project is edited by this cycle.** The evidence is a read-only
  overlay of each project's simulation package with its joints
  mechanically rewritten per the survey, captured and compared against
  the unmodified project. All 23 surveyed projects (and a 24th,
  OpenCycloid, whose own stage B landed mid-cycle and is recorded as an
  addendum to the survey) compare at maximum deviation 0, with wall
  clock 48 the one stated exception; the three (four, with OpenCycloid)
  `PARENT-KNOWLEDGE-IN-SUBSTANCE` projects prove their poses with an
  anchor the overlay DERIVES from the placement the framework no longer
  inverts, never typed as a literal, because typing it is exactly what
  `declaration-site-joint` exists to make unnecessary. Each project's
  real migration is its own stage-B cycle in its own repository.
- **Churn between this cycle and the next is accepted deliberately.**
  The inversion this ADR deletes is forty lines, and
  `declaration-site-joint` re-adds an inversion of its own shape against
  the joint that needs it — a site-declared joint whose arguments are in
  the parent's frame and whose operations still go innermost on the
  child. A branch nothing takes today is worse than re-deriving those
  forty lines there against a pinned fixture (Thor's elbow, kept as this
  cycle's own fixture for exactly that reason).
- Users: none. Joints are unreleased — `docs/releases/release-0.6.md`
  mentions neither `Revolute` nor a joint, and the whole motion layer
  lives in `docs/changelog.rst`'s Unreleased section — so there is no
  deprecation window to run and nothing published breaks.
- Open, deliberately: whether `declaration-site-joint` should let a
  site-declared joint ride a `.repeat()`, which is what three of the
  five opposed-axis projects actually want; whether the hand-written
  `rotate()` form is ever deprecated now that the catalogue has a clean
  own-frame form for the shape that dominates it; what a joint exports
  as, which this ADR makes easier for MuJoCo and no harder for URDF but
  does not decide.
