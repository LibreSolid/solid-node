## Why

Cycle 2 states the rule: **a joint is stated in the frame of whoever
declares it.** It builds the class-body half — the body's own frame,
`at` defaulting to the body's own origin — and names this cycle as the
other half, the joint the PARENT states about a child it is placing, in
the parent's own frame. It deliberately builds no part of it.

What is left over, measured in `evidence/sightings.md` against the source
after cycle 2, is fourteen live sightings in eight projects of one thing:
**a body whose freedom its own class cannot state, for a reason that has
nothing to do with arithmetic.** One of them is not an elegance at all —
it is a shipped machine that cycle 2 leaves unstateable.

- **OpenCycloid's twelve orbiting bodies are REFUSED by cycle 2, not
  merely misread.** Four declarations, all `Orbit(axis=AXIS, unit="deg")`
  with both `at` and `carries` defaulted: the two cycloidal disks
  (`printed.py:162, 177`), four repeated eccentric bearings and six
  repeated output pins on two catalogue classes (`hardware.py:25, 54`;
  `actuator.py:59-61, 108`). Today `at` defaults to the drive's origin —
  the drive axis — and `carries` to each body's own origin, the point
  that rides the circle, and that project's comment says what that buys:
  the 2.5 mm radius and the −90° phase are *"derived … Neither number is
  typed anywhere"* (`printed.py:157-161`). Under cycle 2's own-frame rule
  the two defaults collapse onto ONE point, the carried point lies on the
  line, and all twelve are refused at the first binding for a radius of
  zero. Ten of the twelve are `.repeat()` copies, so nothing short of a
  site joint on a repeat restores them.

- **Four classes exist only to hold a joint.** openvmp's `Wheel` and
  `CameraArm` add no geometry and no behaviour to `Link`
  (`robot.py:74-77, 148-164`); OMX's `LeftFinger` and `RightFinger` are
  three lines of `Prismatic` each over `VisualPack`
  (`open_manipulator_x.py:22-37`), and that module's own docstring calls
  them "two one-line `VisualPack` subclasses". `CameraArm` carries two
  callables, an `__init__` override and two instance attributes whose
  only readers are those callables — all of it to smuggle the parent's
  handedness into the child so the child can restate it. Its docstring
  says so: *"the sign of both the axis and the anchor is the end's
  handedness times the side's, **which only the declaring parent
  knows**"*.
- **Shared catalogue hardware cannot carry a joint at all.** InMoov's
  wrist axle is the catalogue `Bolt` (`forearm.py:147-150`); a joint on
  it would give every bolt in the hand a wrist freedom. openflexure
  subclasses `No2SelfTapScrew` purely to hold one (`small_gear.py:77-89`).
- **Ten anchors name a line of the ASSEMBLY**, which cycle 2's survey
  counted and could not close: the Internal Cycloidal Actuator's two disk
  `Orbit`s (whose line is the actuator axis), InMoov's seven finger
  `Revolute`s (whose line is the fork's pivot), openflexure's gear-lock
  screw (whose line is the motor shaft). Cycle 2 leaves all ten reading
  WRONG under its own rule and names this cycle as their migration.
- **Five axes are unstateable as a literal**, because one class stands at
  two opposed placements: both Prusa belt-guide pairs, hangprinter's
  mirrored motor gear and its roller pair, openvmp's two legs. Two of
  those three projects wrote the parent-frame axis down as a deliberate
  decision, and hangprinter's comment describes the framework's carry
  from the outside: *"the framework carries this direction into each
  body's own frame and finds the local axis mirrored gears turn about
  there too"* (`winch.py:57-64`).
- **82 children a loop builds from a data file have no class to declare
  anything on**, and openvmp moves them through eight hand-written
  `spin()` calls whose helper (`link.py:116-129`) is `Joint._carry`
  open-coded, docstring included.
- **One project states the requirement in its own source.** InMoov's
  forearm, `:254-265`: *"What this wants is a joint stated where the
  child is placed, by the parent that knows its own frame; the framework
  does not offer one yet."*

The sentence all of them want is the one URDF has had all along, and the
one cycle 2 promised:

    stage_one = CycloidalDiskStageOne(orbit=Orbit(axis=AXIS, unit='deg'))
    output_pins = Pin(orbit=Orbit(axis=AXIS, unit='deg')).repeat(OUTPUT_PIN_COUNT)
    disk_one = CycloidalDisk1(orbit=Orbit(axis=ACTUATOR_AXIS, carries=DISK_1_BORE_CENTRE))
    gear_screws = GearLockScrew(orbit=Revolute(axis=(0, 0, 1), unit='deg')).repeat(2)
    middle = MiddlePhalanx(mcp=Revolute(axis=_HINGE, unit='deg'))
    camera = Link('link-camera', dir=side,
                  tilt=Revolute(axis=lambda parent: (0.0, -parent.side, 0.0), …))
    guides = XGuide(spin=Revolute(axis=(0, 1, 0), at=(X_IDLER[0], 0.0, X_IDLER[1]))).repeat(2)

**More than half of the site declarations this cycle's migration writes
carry no anchor at all** — every one of InMoov's seven finger `mcp`s,
openflexure's screw pair, and all four of OpenCycloid's orbits — because
at a declaration site `at` defaults to the DECLARING parent's origin,
which is the fork pivot, the motor shaft, the actuator axis and the drive
axis. Not one sighting needs a number the project does not already have,
and OpenCycloid keeps ten derived radii and ten derived phases it would
otherwise have to type.

**What the evidence says against the plan note, up front.** Two of the
three example sentences in `workflow/docs/motion-catalogue-2.md` §3.3 are
answered by cycle 2, better, and should not be repeated: Poseidon's
`ThreadedRod` anchor is a `RESTATES` row cycle 2 DELETES, and Prusa's
`ZScrew` declares no joint today and gets a clean own-frame one from
cycle 2 with no flag and no `±17`. A third, the Internal Cycloidal
Actuator's `disk_one = CycloidalDisk(orbit=Orbit(axis=(0, 1, 0)))`, is
short by its `carries=` and as written would carry each disk round a
circle of twice the true eccentricity at a wrong phase, silently.
`evidence/sightings.md` §5 has the numbers. The finding stands on its
other fourteen sightings; the examples and two of the four named
validation projects do not, and neither names the sharpest sighting of
all, OpenCycloid.

## What Changes

- **A joint passed as a keyword where a parent declares a child declares
  a freedom on that child**, stated in the DECLARING parent's frame,
  `axis` and `at` alike, with `at` defaulting to `(0, 0, 0)` — the
  parent's own origin, URDF's rule. It is not a wiring (it declares a
  coordinate rather than binding one), not a parameter (it never reaches
  the child's constructor) and not identity (two children differing only
  in a site joint share one artifact). Told apart from a wiring by the
  VALUE: a joint declared on no class is a site declaration; a coordinate
  declared on the declaring class is a wiring, as today.
- **An `Orbit`'s `carries` keeps ADR-094's asymmetry.** Written, it is a
  point of the declaring parent's frame; DEFAULTED, it is the CHILD's own
  origin — ADR-094's `_OWN_PLACED_ORIGIN` sentinel, which cycle 2 deleted
  as redundant in the body's own frame and which is needed again at a
  site. A `Free` declared at a site floats against the declaring parent's
  frame, which gives ADR-095's open reading its own spelling.
- **A site joint's operations go in INNERMOST, in the child's rest
  frame**, by carrying the declared parent-frame arguments through the
  inverse of the child's rest placement at binding. `Joint._carry` is
  restored — the arithmetic cycle 2 deleted, re-derived against the Thor
  elbow fixture cycle 2 pinned for the purpose — and applies to
  site-declared joints only. The alternative, outermost and outside the
  rest placement, produces the identical pose and is rejected in design
  decision 3: it would put a node's joints in two composition zones, make
  the clash rule reorder a body's other freedoms silently, and depend on
  a position in the operations list that `render()` and the checkpoint
  index both disturb.
- **One composition order.** A site joint of a name the class declares
  REPLACES that declaration and keeps its slot; a site joint of a new
  name comes after every class-declared joint, in keyword order.
  ADR-093's rule read one writer further out than a subclass.
- **Callables are handed the DECLARER.** `at=lambda parent: …` is called
  once per realized child with the realized declaring parent, at the
  child's realization — after the parent's parameters and `check()`,
  before its `render()` — and may read the parent's parameters and flags
  and nothing that a placement or a render produces. A `.repeat()` copy's
  `index` is NOT handed to it: measured at the site, all four sightings
  cycle 2 predicted would need it need nothing, because the sign is what
  each copy's own carry produces.
- **A site joint may ride a `.repeat()`** — one declaration, n copies,
  one set of resolved arguments, n carries, each copy's own number
  falling out of its own rest placement. Cycle 2 raised this as an open
  question; OpenCycloid makes it a REQUIREMENT, since ten of its twelve
  refused bodies are repeat copies. It is also what four of the five
  unstateable axes want. A relation may broadcast onto such a coordinate
  (`eccentric_shaft.spin.drives(eccentric_bearings.orbit)`), so a
  repeated declaration's path reading finds a site joint too.
- **The declaration SPECIALIZES the class it declares**, so the site's
  joint is ordinary class metadata on the class the child is realized as:
  one specialization per declaration site, shared by every child it
  realizes, with the written class's name, qualified name, module and
  source file copied DELIBERATELY — a joint is not identity, so two
  children differing only in the joints their sites passed must key one
  artifact. `isinstance` against the written class holds; the class is
  bound in no module namespace, so model discovery cannot reach it.
  Every other rule then follows from machinery that exists:
  `declared_joints`'s MRO walk delivers the slot and the clash rules, the
  descriptor protocol delivers `self.turn` and `self.turn = value`,
  `declared_ports` delivers the enumeration and therefore `get_coordinate`,
  `set_coordinate` and `capture_poses.py`, and `read_through` delivers
  `screw.turn` and `pins.orbit` as paths checked at class definition. The
  `couplings` and `ports` capabilities need no delta, and no hook is added
  to any path a node already takes.
- **Nothing is added for a child a loop builds from data**, because
  cycle 2 already answers it: a class-body joint is now stated in the
  body's OWN frame, and a data-built part knows its own STEP frame, so
  openvmp writes a project-side `TurningPart(StepPart)` with two declared
  parameters and ADR-088's callable and its existing loop builds them —
  giving all 82 parts real coordinates and deleting `spin()`'s hand
  inversion, with vocabulary that shipped two cycles ago. What no cycle
  in this campaign gives it is the OTHER half of its sentence: a relation
  naming such a child by its realized name, which is class metadata
  checked at class definition. Said plainly: openvmp does not get the
  sentence it wrote down, and that stays a separate finding.
- **Refusals by name**: a keyword naming a port, a parameter (including a
  named parameter of a non-declarative child's `__init__`) or any other
  attribute the child answers to; a joint declared on a third class; two
  site joints of one name; a site joint and a wiring of one coordinate;
  and — restored for site joints only — a rest placement the framework
  cannot evaluate at binding.
- **Documentation.** `docs/driving.rst`'s joints section gains the second
  half of the frame rule; `docs/changelog.rst`'s Unreleased entry says
  which frame each site means and what a defaulted `at` and a defaulted
  `carries` mean.

Named sightings and the exact sentence each wants:

| sighting | wants |
|---|---|
| OpenCycloid's two disks, four eccentric bearings and six output pins | `stage_one = CycloidalDiskStageOne(orbit=Orbit(axis=AXIS, unit="deg"))`, `eccentric_bearings = RadialBearing(inner_diameter=17.1, outer_diameter=26.0, width=5.0, orbit=Orbit(axis=AXIS, unit="deg")).repeat(4)`, `output_pins = Pin(orbit=Orbit(axis=AXIS, unit="deg")).repeat(OUTPUT_PIN_COUNT)` — today's text, one level out, ten radii and ten phases still derived |
| openvmp `Wheel` | `wheel = Link('link-wheel', spin=Revolute(axis=(0, -1, 0), at=WHEEL_OFFSET, range=WHEEL_RANGE, unit='deg'))` — the subclass deleted |
| openvmp `CameraArm` | the same, with the two callables reading `parent.dir` / `parent.side`; the subclass, its `__init__` and `_end`/`_hand` deleted |
| OMX `LeftFinger` / `RightFinger` | `left_finger = VisualPack("gripper_left_palm.stl", travel=Prismatic(axis=…, at=…, range=…, unit="mm"))` — both subclasses deleted |
| InMoov's seven finger joints | `middle = MiddlePhalanx(mcp=Revolute(axis=_HINGE, unit='deg'), pip=Revolute(axis=_HINGE, at=PROXIMAL_JOINT, unit='deg'))` — no anchor on any `mcp` |
| InMoov's wrist axle | a site joint on the shared catalogue `Bolt`, replacing three hand-written operations |
| the Internal Cycloidal Actuator's two disk `Orbit`s | `disk_one = CycloidalDisk1(orbit=Orbit(axis=ACTUATOR_AXIS, carries=DISK_1_BORE_CENTRE, unit='deg'))`, `at` omitted |
| openflexure's `GearLockScrew` | `gear_screws = GearLockScrew(orbit=Revolute(axis=(0, 0, 1), unit='deg')).repeat(2)` — one declaration, two copies, no sign |
| Prusa's `XGuide` / `YGuide` | the parent-frame axis and anchor at the site, on the `.repeat(2)` |
| hangprinter's `MotorGear` / `RollerBearing` | the same, `MotorGear` written at both winch classes |
| openvmp `Leg` | `left_leg = Leg(side=1, turn=Revolute(axis=(0, -1, 0), at=SIDE_OFFSET, range=THIGH_RANGE, unit='deg'))`, and the same on `right_leg` |
| openvmp's 82 data-built parts | nothing from THIS cycle: a project-side `class TurningPart(StepPart)` with `spin = Revolute(axis=lambda node: node.spin_axis, at=lambda node: node.spin_point)` and two declared parameters, built by the existing loop — cycle 2 and ADR-088 alone. Not the relation the project asked for |

## Decisions for the pilot

**(a) Two of the four validation projects named in the plan note are
cycle 2's, and one example sentence is silently wrong.**
`evidence/sightings.md` §5, with the source and the numbers. Poseidon
needs nothing from this cycle; Prusa i3 needs it for its belt guides and
not for its Z screws; three quarters of InMoov's wrist group is cycle 2's
and the axle is left for a different reason than the note gives; and the
actuator's example sentence omits a `carries=` whose absence is a 2 mm
error and a wrong phase with no refusal. This cycle proposes the
corrected list and does not quietly rewrite the note.

**Poseidon's `ThreadedRod` and Prusa's Z screws are cycle 2's**, and
neither belongs to this cycle. The validation projects this cycle
actually serves are:

| project | what this cycle gives it |
|---|---|
| OpenCycloid | its four `Orbit`s' `at`, at the site — twelve bodies cycle 2 refuses, ten of them `.repeat()` copies |
| Internal Cycloidal Actuator | its two disk `Orbit`s' `at`, with `carries` written |
| Inmoov-sim | the seven finger joints, anchorless, and the wrist axle on the shared catalogue `Bolt` |
| open_manipulator (OMX) | the two gripper fingers, both three-line subclasses deleted |
| openvmp | `Leg` and `CameraArm` (and `Wheel`), three subclasses and an `__init__` override deleted |
| Prusa3-vanilla | the belt guides, `XGuide` and `YGuide`, on their `.repeat(2)` |
| hangprinter | `MotorGear` and `RollerBearing` |
| openflexure-microscope | `GearLockScrew`, one declaration for both copies |

**(b) The specialization is visible in exactly two places, and both are
named.** `type(x) is ZScrew` is false for a child whose site gave it a
joint — `isinstance` holds, and the one identity check in the framework
is `internal.py:166`'s guard against a render returning its own type,
which such a child of its parent's own class would slip past. And a
reader printing `type(child)` sees the written class's name for a class
that is not the written class, because the copy of name, module and file
is total and deliberate: it is what makes a joint not be identity. The
rejected alternative — site joints in the instance dict, with
`__getattr__`/`__setattr__` hooks on the node base, two node-level
enumerators and a public `attach_joint` — avoids both at the price of
reproducing, for one kind of declaration, everything the class machinery
already does for the other, on a path every node attribute assignment
takes (design decision 6).

**(d) A new finding this cycle exposes and does not fix.** A parent's
hand-written `self.child.rotate(...)` is read in the CHILD's frame, while
a site joint the same parent declares is read in the PARENT's. After this
cycle a project can write both on one child and get two frames from one
author. Filed, not fixed (tasks 8.6).

## Impact

- **Specs:** `joints` — one ADDED requirement ("A joint declared where a
  child is placed") and five MODIFIED ("A joint is stated in the frame of
  whoever declares it", "Binding a joint places the body", "Joint
  arguments resolve against the instance at realization", "An orbit's
  radius and phase are derived, never declared", "Joint declarations"). `declarative-nodes` — one MODIFIED ("Class-body child
  declarations"): the keyword, its refusals, and the path a class body
  may read through it. `couplings`, `ports`, `node-model`, `simulation` and
  `kinematics` are UNTOUCHED: the site's joint is class metadata on the
  class the child is realized as, so a path resolves, a coordinate
  enumerates and a name reads back by the rules those capabilities
  already state.
- **ADRs:** one new NODE ADR, "A joint may be declared where a child is
  placed". It extends the cycle-2 ADR (the second half of its own rule),
  revives ADR-094's `_OWN_PLACED_ORIGIN` for the site default, extends
  ADR-093 to the slot a site joint takes, and gives ADR-095's open
  reading a spelling without overturning cycle 2's choice.
- **Code:** `solid_node/motion/joints.py` (the site mark, the restored
  `_carry` and ADR-094 sentinel for site declarations, and skipping a
  site joint in the eager resolution) and
  `solid_node/node/declarative.py` (the keyword's classification and
  validation, the specialization, and resolving the site's joints against
  the parent in `realize`). `solid_node/node/base.py` changes in one
  respect only: `ChildDeclaration.realize` receives the realized parent,
  where it receives the declaring class's NAME today.
  `solid_node/motion/ports.py` and `solid_node/motion/couplings.py` are
  untouched.
- **Tests:** `tests/test_joints.py`, `tests/test_declarative.py`, a
  path/broadcast case in `tests/test_couplings.py` and an enumeration
  case in `tests/test_ports.py` — both asserting the existing rules
  answer for a site joint without having changed — and the
  `tests/joint_project/` fixtures. The cycle-2 fixture pinning Thor's
  elbow is what the restored carry is re-derived against.
- **Projects:** none is edited. The evidence is a read-only overlay per
  project, as cycle 2 does, at maximum deviation 0 — including the three
  projects whose poses cycle 2 knowingly leaves wrong, whose reference
  captures therefore come from cycle 2's BASE and not from its head.
- **Users:** none. Joints are unreleased; the whole motion layer lives in
  `docs/changelog.rst`'s Unreleased section, and the changelog entry
  speaks to the catalogue, which is every reader there is.
- **Window:** between cycle 2 landing and this cycle landing, OpenCycloid
  is not merely wrong but REFUSED — twelve bodies raise at the first
  binding, and its own suite goes red with them, beside the three
  projects cycle 2 already names. The campaign runs this cycle
  immediately after cycle 2 for that reason; the window is the campaign's
  own, not a release's.
- **Dependency:** cycle 2 (`joint-frame-follows-declarer`) must be
  implemented, integrated and ARCHIVED first. Every delta here is written
  against the baseline cycle 2 leaves behind, and three of this cycle's
  four `joints` MODIFIED requirements do not exist in the baseline until
  cycle 2 archives. Cycle 1 (`repeat-fan-out`) is already on this branch
  and is what makes a site joint on a `.repeat()` meaningful.
