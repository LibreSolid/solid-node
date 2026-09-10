## Why

A joint says where a body may move, next to the body, once. Today it says
it in **somebody else's frame**: `axis` and `at` are read in the parent's
frame and carried into the body by inverting its rest placement
(ADR-088). So a class that spins on its own bearing cannot say so. It
must know where its parent put it, and write that down a second time.

The consequence, measured across the whole catalogue in
`evidence/survey.md` — 23 projects, **249 class-body joint declarations**:

- **69 anchors exist only to restate the parent's `translate`.** Poseidon
  writes `at=(LEADSCREW_START_X, *DRIVE_AXIS_YZ)` on a bought-hardware
  envelope so the pump's layout constants have to live inside the
  hardware module. OpenMANIPULATOR-X writes every URDF origin twice, once
  in `render().translate()` and once as the joint's `at`. The hexapod
  writes `(COXA_LENGTH, 0, FORK_MID)` at `leg.py:213` and again at
  `leg.py:337`, 123 lines apart in one file.
- **Four of them are multi-line lambdas whose whole job is that
  restatement**, and one of those runs a five-argument geometric solver a
  second and third time to get back a number the parent had already
  computed (`pascaline/pawl.py:29-39` re-evaluating
  `profiles.hinge(...)` that `Sautoir.render()` evaluated at
  `sautoir.py:39-42`). AlbertPro's two knee callables are the reason
  eight subclasses carry a `LEG` attribute. OpenVMP's `CameraArm` carries
  two callables, an `_end`, a `_hand` and an `__init__` override for it.
- **About thirty bodies cannot carry a joint at all**, because one class
  is placed at several points and a class attribute holds one anchor.
  Thor's thirteen catalogue parts — pinions, pulleys, the optodisk, the
  ball cage, the bevels — keep one hand-written `rotate` each with the
  sign read off `placing.axis_sign`; that is the originating sighting,
  filed on the day the layer landed. The V8's four timing gears are the
  eighth sighting; the Prusa i3's two Z screws the sharpest; then
  Metamaquina's Z bars and couplings, openflexure's four flexure legs,
  three quarters of InMoov's wrist group, and the pendulum bob's rating
  button and nyloc in every clock.
- **The documentation already describes the rule we do not have.**
  `docs/driving.rst:208-211`: "`at` defaults to that frame's origin,
  which is the case of a wheel turning on its own bearing." That is only
  true if the parent placed the wheel at its own origin. Today a wheel
  the parent translates, with `at` left out, swings about the parent's
  origin instead of spinning on its bearing — silently.
- **One project already disagrees with itself about which rule is in
  force.** In `3DPrintedClocks`, clocks 22, 41, 49 and 51 write
  `at=arbor_bearing(node)` on a leaf already translated by that bearing;
  clock 48 writes no `at` and says why in a comment: *"Using the
  plate-frame bearing here applies that offset twice."* Under today's
  rule exactly one family is wrong wherever the bearing is not the
  origin.

The rule these all want is one sentence: **a joint is stated in the frame
of whoever declares it.** A joint written in a CLASS BODY is the body's
own statement about itself, so it is read in the body's OWN frame, with
`at` defaulting to the body's own origin — which is MuJoCo's rule, where
a `<joint pos>` is a point of the body frame. A joint passed at a
DECLARATION SITE is the parent's statement about a child it is placing,
so it is read in the declaring parent's frame — URDF's rule. This cycle
does the first; cycle 3 (`declaration-site-joint`) does the second.

ADR-088 considered the own-frame reading and rejected it, before any
project had migrated, on the ground that it "would make the declaration
depend on where the part's own origin happens to be, which is the
accident joints exist to remove". The survey is the answer: where the
origin is an accident, the anchor is written as a genuine point and stays
one (69 rows, 62 of them numerically unchanged); where it is the bearing
it is not an accident, and 133 of 249 declarations (69 restating a
placement, 64 already anchorless) plus about thirty
hand-written rotations say so.

**What it costs, stated up front.** The rule is not free and not
pose-neutral.

*Ten anchors move from the class to cycle 3.* Twelve declarations written
with no `at` on a body their parent translates off the joint's line
change meaning; ten of them cannot honestly be repaired by writing an
anchor, because the line each names belongs to the ASSEMBLY and not to
the body. The strict count of anchors that need the parent's frame is
zero across 249 declarations; **the count in substance is ten** — the
Internal Cycloidal Actuator's two disk `Orbit`s (whose line is the
actuator axis, and whose disks would otherwise orbit at twice the true
eccentricity), InMoov's seven finger `Revolute`s (whose line is the
fork's pivot), openflexure's `GearLockScrew.orbit` (whose line is the
motor shaft). Each is statable from the class only by inverting the
body's own placement by hand and typing the number, and for the Internal
Cycloidal Actuator that number is a literal its ratified spec forbids
anywhere in the project. Their real migration is **cycle 3's site
keyword**, where the parent states the joint in the frame it already
holds; meanwhile all three keep exactly what they have today, and this
cycle proves their poses with an anchor the overlay DERIVES from the
placement rather than transcribes. The other two of the twelve are wall
clock 48's, which the change fixes.

*Five axes lose their literal.* One class placed at opposed rotations
cannot state one own-frame axis: both Prusa belt-guide pairs,
hangprinter's mirrored motor gear and its roller pair, and OpenVMP's two
legs. Two of those three projects wrote the parent-frame axis down as a
deliberate design decision. There are two bridges on day one, both
existing vocabulary, and which is right depends on where the knowledge
lives: **a callable of the realized node** (ADR-088) reading the body's
own parameter or the copy's `index` from cycle 1, where the two sites are
genuinely two different parts; or **the parent supplying the sign in the
relation** — `travel.drives(guides.spin, law=sign_by_index)` under cycle
1's broadcast, or `ratio=-1` on a named copy — where the two sites are
two mountings of one part. The second is what Thor already does, and it
is why Thor's thirteen catalogue parts can share one declaration at both
signs. Nothing is built for either; the literal returns in cycle 3.

## What Changes

- **`Revolute`, `Prismatic`, `Orbit` and `Free` declared in a class body
  are read in that body's REST frame** — the frame its own `render()`
  states its geometry in, one rest placement away from the parent's, and
  the frame every joint operation is read in because a joint's run sits
  innermost. `at` defaults to `(0, 0, 0)`, the body's own origin.
  `Orbit`'s `carries` defaults to `(0, 0, 0)` for the same reason.
  `Free`'s three rotational directions are that rest frame's x̂, ŷ, ẑ,
  and — the translation being the outermost operation of its own run —
  its three translational coordinates displace along those same
  rest-frame directions rather than along the axes the rotations have
  just turned.
- **The framework transforms nothing.** `Joint._carry`, the inversion of
  the rest placement, is deleted. With it go `_OWN_PLACED_ORIGIN` and
  `_OwnPlacedOrigin` (ADR-094's sentinel becomes redundant: in the body's
  own frame that point IS the origin), the joints module's only use of
  `numpy`, and the refusal *"a rest placement the framework cannot invert
  is refused by name"* — nothing inverts, so nothing can fail to invert,
  and a body whose rest placement carries a symbolic value may now carry
  a joint.
- **A joint's arguments no longer depend on the body's placement at all.**
  Two instances of one class placed differently resolve identical joint
  arguments, and a joint's line survives a change to the rest placement.
- **The axis is snapped after normalization**, in `resolve` rather than in
  the deleted carry, so `(0, 0, 3)` still publishes `(0, 0, 1)` exactly.
  Anchors are no longer snapped: an anchor is what the author wrote.
  `Revolute`'s centring pair is still omitted for an anchor within `1e-9`
  of zero.
- **Nothing else in the motion layer moves.** Composition order and the
  contiguous run (ADR-093), what a joint owns (ADR-088), an orbit's
  derived radius and phase (ADR-094), a `Free`'s six coordinates
  (ADR-095), the couplings solver, the wiring path, the document, the
  serializer, the viewer, the parity corpus and the CLI are untouched.
  The joint block is still innermost and hand-written motion still
  composes outside it, for the same reason as before: a joint's
  operations were always expressed in the body's own frame.
- **The framework's own fixtures move to the new form.**
  `tests/joint_project/arm.py`'s `Forearm.elbow` becomes
  `axis=(0, 1, 0), at=(0, 0, 81.5)` — which is `ELBOW_PIVOT_AXIS` and
  `ELBOW_PIVOT` in Thor's own `art2.py`, the same two pinned numbers, now
  written where the project writes them. `Arbor.turn`'s
  `at=lambda node: node.built.bearings[node.index]` is deleted outright.
- **The documentation stops being wrong.** `docs/driving.rst`'s joints
  section is rewritten around the new rule, and `docs/changelog.rst`'s
  Unreleased section gains the entry.

Named sightings and the exact sentence each wants:

| sighting | wants |
|---|---|
| Thor's thirteen catalogue parts | `turn = Revolute(axis=(0, 0, 1), unit='deg')` — verbatim from `workflow/warts.md` |
| the V8's four timing gears (two classes, four placements, two of them `.repeat(2)` copies) | one `turn = Revolute(axis=(1, 0, 0), unit='deg')` per class |
| the hexapod's `Femur.lift`, `Tibia.knee` | `lift = Revolute(axis=(0, -1, 0), unit='deg')` |
| Poseidon's `ThreadedRod`, `ShaftCoupling` | `turn = Revolute(axis=(1, 0, 0), unit='deg')`, with the pump's constants out of the hardware module |
| OpenMANIPULATOR-X's four links | `Revolute(axis=JOINTS["jointN"].axis, range=…)`, the origin written once |
| the Pascaline's `Pawl.swing` | `swing = Revolute(axis=(0, -1, 0), unit='deg')`, the solver run once |
| the Prusa i3's two Z screws | `turn = Revolute(axis=(0, 0, 1), unit='deg')` on `ZScrew`, both sides |

## Decisions for the pilot

Three things this cycle cannot settle on its own. The facts, not a
recommendation.

**(a) 3DPrintedClocks wall clock 48 is expected to move.** Clocks 22, 41,
49 and 51 write `at=arbor_bearing(node)` on a leaf already translated by
that bearing; clock 48 writes no `at` and carries this comment
(`wall_clock_48/clock.py:135-140`): *"Using the plate-frame bearing here
applies that offset twice (invisible on arbor zero, whose bearing happens
to be the origin) and separates the anchor wheel from its independently
modelled pallet pins."* Its anchor arbor is at index 5, so today one of
the two families is wrong. Under the new rule clock 48 becomes correct by
construction, its `TurningArbor` at index 5 and its `TurningPalletPin`
move, and the other four clocks delete their `at` with no movement at
all. The deviation is towards what that project's own source says it
wants. The pose comparison cannot say whether the new pose is right;
that clock's own suite can (tasks §7.3), and the answer is yours.

**(b) Three projects' clean form is cycle 3, and this cycle does not give
it to them.** The Internal Cycloidal Actuator (2 disk `Orbit`s), InMoov
(7 finger `Revolute`s) and openflexure (`GearLockScrew.orbit`) hold ten
anchors that name a line of the ASSEMBLY. After this cycle they are
statable only as a hand-inverted literal, and for the Internal Cycloidal
Actuator that literal is forbidden by its own ratified spec. **What they
carry meanwhile: exactly what they carry today** — the joint keeps its
defaulted anchor and the project keeps whatever hand-written motion it
already has; no project is edited by this cycle. Said plainly: once this
cycle is on main and until cycle 3 lands and those three projects are
resumed on it, their defaulted anchors READ WRONG under the new rule —
the actuator's disks orbit at twice the true eccentricity, the fingers
turn about the wrong line — and the tests that guard those poses
(`test_machine.py:700-730`, `test_hand.py:229-237`) go red. The campaign
runs cycle 3 immediately after this one for that reason; the window is
the campaign's own, not a release's. What they get in cycle 3
is `disk_one = CycloidalDisk(orbit=Orbit(axis=(0, 1, 0)))`, stated where
the actuator axis is known. The only place the derived anchor appears in
this cycle is the throwaway pose overlay, which computes it from the
placement rather than typing it (tasks §7.2).

**(c) Five axes lose their literal, and there are two bridges.** Prusa
`XGuide` and `YGuide`, hangprinter `MotorGear` and `RollerBearing`,
OpenVMP `Leg.turn` — one class at opposed rotations, where one
parent-frame literal serves both sites today and hangprinter states the
choice in prose (`simulation/winch.py:57-64`). Bridge A: a callable of
the realized node reading the body's own parameter (`mirrored`, `side`)
or the copy's `index` from cycle 1. Bridge B: the parent supplies the
sign in the relation — `law=sign_by_index` under cycle 1's broadcast, or
`ratio=-1` on a named copy — which is what Thor already does and which
leaves the body's own axis honest. Neither is built here; both exist.
Which a project takes is its own stage-B decision, and whether cycle 3
should additionally let a declaration-site joint ride a `.repeat()` —
which is what three of the five really want — is an open question this
survey raised (design, Open Questions).

## Impact

- **Specs:** `joints` — one ADDED requirement ("A joint is stated in the
  frame of whoever declares it", the requirement cycle 3 extends) and
  five MODIFIED ("Binding a joint places the body", "Joint arguments
  resolve against the instance at realization", "An orbit's radius and
  phase are derived, never declared", "Joint declarations", "A free joint
  owns six coordinates and floats a body", "A free joint places a
  floating body by a fixed composition"). One scenario is dropped, "An
  unresolvable rest placement is refused", and replaced by "A rest
  placement the framework cannot evaluate no longer prevents a joint".
  `couplings`, `ports`, `node-model` and `simulation` are untouched: the
  relation layer never sees a frame.
- **ADRs:** one new ADR, superseding ADR-088's frame decision in part,
  revising ADR-094's `carries` sentinel, and closing ADR-095's stated
  open question about whether `at` is read in the parent's frame or the
  body's own.
- **Code:** `solid_node/motion/joints.py` only. `Joint.place` uses the
  resolved arguments directly; `_carry`, `_OwnPlacedOrigin`,
  `_OWN_PLACED_ORIGIN` and the `numpy` import go; `resolve` snaps the
  normalized axis; `Orbit.carries` defaults to `(0, 0, 0)`; `Free.axes`
  returns the three literal unit directions. No other framework module
  changes.
- **Tests:** `tests/test_joints.py` — `FrameCarryTest`,
  `NumericHygieneTest` and the `tests/joint_project/` fixtures state the
  new rule; new cases for the one-class-many-placements win, the line
  turning with the body, and the relaxed refusal.
- **Projects:** none is edited by this cycle. The evidence is a read-only
  overlay of each project's simulation package with its joints rewritten,
  captured with `PYTHONPATH` pointing at the copy, compared pose for pose
  against the base. All 23 must compare at maximum deviation 0 — 20 by a
  mechanical rewrite, and 3 (InMoov, the Internal Cycloidal Actuator,
  openflexure) with the old rule's anchor DERIVED in the overlay from the
  placement the framework no longer inverts, never typed as a literal,
  because those ten anchors are cycle 3's and one of them is a literal
  the project's spec forbids (tasks §7.2). One exception:
  **3DPrintedClocks wall clock 48 is expected to move**, and that
  deviation is the fix its own source comment asks for — it is carried to
  the pilot as a question, not accepted as a difference.
- **Users:** none. Joints are unreleased — `docs/releases/release-0.6.md`
  mentions neither `Revolute` nor a joint, and the whole motion layer
  lives in `docs/changelog.rst`'s **Unreleased** section. So there is no
  0.6.0 user whose joints are in the parent frame, no deprecation window
  to run and nothing published that breaks. The changelog entry speaks to
  the catalogue, which is every reader there is.
- **Dependency:** cycle 1 (`repeat-fan-out`) must land first. Four of the
  five axes that lose their literal, and one per-copy anchor, are
  `.repeat()` copies whose migration reads the copy's `index`.
