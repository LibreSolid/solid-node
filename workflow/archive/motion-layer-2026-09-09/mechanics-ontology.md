# Provisional mechanics ontology for the declarative API

Status: research proposal, **not ratified, implemented, or a public API promise**.
Date: 2026-09-08. Scope: solid-node's next declarative API, informed by the
local mechanical-project catalogue. No project or framework implementation is
changed by this document.

## Aim and ownership boundary

Make a machine read like its mechanical construction: which bodies are joined,
which interfaces engage, what drives what, and which quantities are independent.
The author supplies design facts; solid-node derives the consequences. A clock
should not need a central function computing every arbor angle, nor should each
gear need to know about elapsed time.

**Gaits, gestures, firing schedules, and demonstration sequences remain in
project code.** They choose inputs to a machine; they are not mechanisms.
This includes robot foot trajectories and gait blends, hand poses, engine firing
order and ignition events, Pascaline arithmetic demonstrations, abacus digit
entry, and gearbox shift demonstrations. Existing generic driver/instruction
facilities may execute those programs without acquiring domain-specific presets.

Geometry and mechanical facts also remain owned by the design: teeth, pivots,
link lengths, cam profiles, crank-throw and cam installation phases, tooth
registration, limits, and the selection of a linkage branch. A reusable mechanism
consumes those facts. Installation phase is a mechanical datum; a firing schedule
is a project program. The framework must not infer one from the other.

The ontology is principally kinematic. It does not promise force balance,
friction, backlash dynamics, combustion, tendon elasticity, motor control,
stability, or finite-element flexure prediction. A prescribed animation must not
be relabelled a physical solution merely because it becomes declarative.

## Proposed import boundary

Keep one convenient public mechanisms namespace, with canonical family
submodules described below. These names are **proposed**, not current imports:

```python
from solid_node.mechanisms import (
    RevoluteJoint, GearMesh, ShaftCoupling, PlanetaryGearSet,
    FourBarLinkage, SliderCrank, CamFollower,
)
```

Nodes, frame facilities and signal ports belong to `solid_node.node`;
mechanical feature descriptors to `solid_node.mechanisms.interfaces`;
dimensional design parameters to `solid_node.parameters`; generic controls and
sequence execution to `solid_node.simulation`. Their existing facilities should be extended and
reused, not copied into a new mechanism-specific driver system. Port/frame
extensions described here are proposals too.

Project-defined specializations import the public extension protocol and live
in the project's package, for example:

```python
from solid_node.mechanisms import Mechanism
from .mechanisms import AnchorEscapement, SautoirCarry
from .programs import walk, grasp, fire, demonstrate  # project-owned
```

These are illustrative names, not claims that the projects already have these
modules. A general mechanism can graduate into the library when its independent
contract is demonstrated; a whole robot, clock, or demonstration is not a
framework class merely because it uses several mechanisms.

## Ontology organized by submodule

Keep the existing package name `solid_node.mechanisms`; do not introduce a
competing `solid_node.mechanics` package. Offer a flat, convenient re-export
surface and explicit family imports for discovery. A class has one canonical
family home; re-exporting it does not create another implementation.

All classes in this section are proposed. Existing function-level modules
(`gears`, `screws`, `cranks`, `linkages`, `deltas`) remain compatible.
New declarative classes compose their laws rather than remove the functional
API. Module names below are import boundaries; this proposal does not require
one enormous source file per family.

| Submodule | Proposed public classes | Calculations it owns |
| --- | --- | --- |
| `interfaces` | `RotaryInterface`, `LinearInterface`, `GearInterface`, `PulleyInterface`, `SprocketInterface`, `DrumInterface`, `CamInterface`, `FollowerInterface`, `RouteAnchor` | Typed mechanical metadata and body-local feature frames; normalize declared interface conventions. These are descriptors, not solvers or CAD generators. |
| `joints` | `FixedJoint`, `RevoluteJoint`, `PrismaticJoint`, `CylindricalJoint`, `SphericalJoint`, `ShaftCoupling`, `SlidingShaftCoupling`, `JointCoupling` | Allowed relative motion, joint-coordinate coupling, local/world transforms and resulting body poses. |
| `gears` | `GearMesh`, `BevelGearMesh`, `CrownGearMesh`, `WormGearMesh`, `RackAndPinion`, `PlanetaryGearSet`, `BevelDifferential` | Mesh ratio, handedness/frame signs, phase/registration, pitch placement or its validation, carrier-relative motions and rack travel. |
| `transmissions` | `BeltDrive`, `ChainDrive`, `DrumDrive`, `CableDrive`, `TendonDrive`, `ProportionalClosure` | Pulley/sprocket rotation, material travel, winding/payout, reeving length balance and explicitly chosen underactuated closure. |
| `screws` | `LeadScrew` | Relative screw/nut angle and translation from lead, handedness and which member is held. |
| `cranks` | `SliderCrank`, `EccentricDrive` | Crank-pin orbit, connecting-rod orientation, slider displacement and eccentric orbit separately from body spin. |
| `cycloidal` | `CycloidalReducer` | Ring-pin/disc-lobe relation, eccentric orbit, disc spin, phased multi-disc poses and output extraction. |
| `linkages` | `FourBarLinkage`, `SerialChain`, `ParallelLinkage`, `PointConstraint`, `DistanceConstraint` | Link closure, supported FK/IK, branch/reachability checks, carried-body poses and target-frame conversion. |
| `deltas` | `LinearDelta` | A supported named parallel-linkage compound: carriage heights and complete rod/effector poses from tower and attachment geometry. |
| `contact` | `CamFollower`, `RollingContact`, `RollingBearing` | Supported profile/follower contact, constrained lift, no-slip travel and rolling-element/cage poses. |
| `indexing` | `RatchetDrive`, `IndexingDrive`, `GenevaDrive` | Tooth/slot advancement, dwell, geometric contact windows, locking and declared retained index. |
| `engagement` | `Engagement` | Activate/deactivate relations, check overlap/phase compatibility, expose free coordinates and enforce exclusive engagements. |
| `routing` | `FlexibleRoute`, `CableCarrier` | Supported tangent/span/wrap geometry, material stationing, route length and linked-carrier poses/bend limits. |
| `oscillators` | `PendulumOscillator` | Declared small-angle or calibrated-reference length/period law and supported swing/phase evaluation; no inferred escapement dynamics. |
| `compliance` | `SpringMount`, `FlexureJoint` | Spring seat-to-shape adaptation and explicitly declared flexure kinematic approximations, with validity limits. |
| `core` | `Mechanism`, `MotionLaw` | Public extension/composition protocol, typed relation declarations and explicit prescribed-law metadata. Compilation and evaluation machinery stay private. |

Examples of equally valid future import styles:

```python
from solid_node.mechanisms import GearMesh, LeadScrew, LinearDelta
# Or use the canonical family homes:
from solid_node.mechanisms.gears import GearMesh
from solid_node.mechanisms.screws import LeadScrew
from solid_node.mechanisms.deltas import LinearDelta
```

### 1. Interfaces describe features, joints define freedoms

Mechanical interfaces live in `mechanisms.interfaces`, not in a parallel
port implementation. They refer to existing node-owned ports/coordinates and
frame facilities. Nodes own identity, source geometry and frames; the mechanics
layer owns the meaning of a shaft, gear or cable anchor.

A `GearInterface` describes the declared tooth/pitch/registration data and its
rotary frame; a `DrumInterface` describes a rotary frame and winding geometry.
Several interfaces on one rigid body share that body's motion. Declaring the
wheel and pinion of one arbor must not invent two independent angular inputs.

`FixedJoint` holds a relative frame while preserving part identities.
`RevoluteJoint` and `PrismaticJoint` each leave one coordinate free.
`CylindricalJoint` leaves independent slide and spin about one axis; it does
not impose a screw law. `SphericalJoint` joins ball centres and leaves relative
rotation free.

`ShaftCoupling` locks angular motion and phase; it is not a complete spatial
attachment. `SlidingShaftCoupling` composes that angular lock with permitted
axial travel, as in the keyed gear-shift cluster. `JointCoupling` expresses an
affine coordinate relationship, including URDF mimic fingers. It must retain
units and provenance rather than pretend the source establishes a physical
gear train.

### 2. Transmission families own the whole relationship

`GearMesh` covers parallel-axis external/internal gears and finite sectors.
Bevel, crown/lantern and worm relations retain their distinct geometry.
`RackAndPinion` couples rotation to rack translation. Tooth conventions are
normalized by explicit interface annotations/adapters, never by branching on
arbitrary third-party gear-object types inside the analytic law.

`PlanetaryGearSet` exposes sun, ring, carrier and individual planets.
`BevelDifferential` exposes both side gears and the carrier. Fixed members and
independent inputs are stated by the assembly. Neither may silently choose a
missing degree of freedom; both derive intermediate poses as well as ratios.

`BeltDrive` and `ChainDrive` consume routes, drive interfaces, idlers and
attachments. Pulley and sprocket rotation, a clamped carriage's translation,
and visible belt/chain travel come from one solution. Chain link pitch is not
a belt's surface radius, even if the implementations share length-balance
machinery. `DrumDrive` connects angular motion to stored/paid-out length with
winding sense and a declared constant radius or supported radius law.
`CableDrive` sums anchored/moving spans, deriving reeving advantage instead of
requiring a project multiplier.

`TendonDrive` specializes routed length balance across joint motion.
An underactuated finger also needs a constitutive or closure assumption.
Offer `ProportionalClosure` as a named **prescribed approximation**, with
project-selected joint weights, rest values and an explicit limit policy.
The framework evaluates the weighted length/angle relationship and reports
unreachable requests; it must not silently redistribute motion after a joint
hits its limit. This removes Inmoov's repeated closure arithmetic without
claiming to predict an actual grasp. Gesture targets still remain project code.

`LeadScrew` uses lead, not pitch mistakenly substituted for a multi-start
thread. `CycloidalReducer` does not reduce to a signed gear ratio: it owns
disc orbits, disc orientation and output extraction. Its `EccentricDrive`
building block must expose orbit and body spin separately.

### 3. Linkage families return poses, not homework

`FourBarLinkage` consumes body-local pivots and link geometry, solves a named
assembly branch and poses all links. Its parallelogram specialization carries
a body without rotating it, as required by YouCanBuildDog and Thor's gripper.

`SliderCrank` consumes a crank pivot/pin, connecting-rod endpoints and slider
guide (including guide offset where supported); it returns all corresponding
body motion. A project must not receive only piston height and then reconstruct
the rod angle and transforms itself.

`SerialChain` consumes declared joints and a tool/foot frame. Forward
kinematics is available from joint inputs; inverse targets require an explicitly
supported solve mode and branch/seed/limit policy. `PointConstraint` names a
point target in a frame. `DistanceConstraint` preserves an endpoint distance;
it does not determine a rod's axial roll without another orientation datum.

`ParallelLinkage` provides the shared closed-loop composition contract and
supported solving infrastructure, not an assertion that arbitrary nonlinear
mechanisms are solved. Promote `LinearDelta` to a named compound now: Kossel
should declare its towers, rods and effector once, not call a carriage law and
manually orient each of six rods. This fits the existing `deltas` module and
reuses its analytic laws. Hangprinter composes cable routes and platform
constraints; support pose-to-payout first, with the supplied platform orientation.
Do not imply that arbitrary cable lengths uniquely determine a feasible pose.

### 4. Contact, engagement and routes are reusable mechanics

`CamFollower` owns the supported contact solution from actual profile and
follower geometry, not just a project-supplied lift curve hidden behind a class
name. A prescribed lift law is a distinct, labelled mode. `RollingContact`
initially handles supported tangential no-slip geometries such as feed rollers,
not arbitrary frictional contact. `RollingBearing` uses declared ring and
rolling-element geometry; its cage speed is not universally half shaft speed.

`RatchetDrive` and `GenevaDrive` specialize physical intermittent relations.
`IndexingDrive` also supports explicitly prescribed advance/dwell laws, which
must not be confused with geometry-derived contact. `Engagement` is shared
with selectable gear meshes: it changes active constraints, never the part tree.
State/phase is mechanical; the schedule of operator actions is project-owned.

`FlexibleRoute` describes anchored/guided spans, their shape policy and
material coordinate. A route that only draws a Bowden tube need not impose an
inextensible length constraint. `CableCarrier` poses discrete links on a
supported route with link count, length and bend limits; it is distinct from
the power-transmitting `ChainDrive`.

`SpringMount` derives installed orientation and extent from seats.
`FlexureJoint` exposes an explicitly selected effective-joint approximation.
Ordinary lever/rod geometry and frame transforms remain library calculations;
only measured/fitted material behavior or genuinely project-specific
approximations need project-defined laws. Neither class promises stiffness
prediction or finite-element deformation.

Clock 48 adds one narrowly scoped analytic dynamics approximation:
`PendulumOscillator` takes effective pendulum length, amplitude/phase and a
declared small-angle or calibrated-reference period model. Adjustment screws
are `LeadScrew` relations; the oscillator derives the resulting period instead
of the project repeating square-root scaling. The project still chooses how its
escapement uses that phase. Time is an explicit external input, never a hidden
second clock. Initially this covers fixed-length configurations; varying length
during a run requires an explicit phase-continuity/state model, not the
assumption that instantaneous phase is simply time divided by changing period.
This does not promise self-sustaining escapement, damping or energy simulation.

### 5. Core machinery stays below the author's API

The framework internally resolves references, inventories free coordinates,
compiles supported relation groups and applies solved poses. Authors should
not have to instantiate graph vertices, register evaluation callbacks, choose
traversal order, perform unit conversion or assemble a general solver's matrix.

`Mechanism` is the common extension protocol: declared interfaces, constraints,
derived outputs, assumptions and supported state. `MotionLaw` is the explicit
escape hatch for a genuinely prescribed mechanical relationship. It is not the
default implementation of every family or a home for machine programs.

Module dependencies should follow this direction:

```text
node ports/frames + quantities + expression math
                     |
            core + interfaces
                     |
      joints / routes / family laws
                     |
     named compound mechanisms
                     |
       project machine assembly
                     |
 project controls, gaits, gestures and demos
```

The diagram shows what builds on what, not runtime evaluation order. Family
modules never import projects or each other's demo code. Geometry adapters
attach declared interface data without making the analytic kernel depend on
CadQuery, OpenSCAD or a particular gear library. Flexible-shape adaptation uses
the existing molejo seam. A compound expands to the same inspectable relations
as a hand-composed mechanism, rather than implementing a second motion engine.

## Calculation ownership: the practical acceptance criterion

Design dimensions and chosen behavior belong in projects; **derived mechanical
consequences do not**. Mathematical design formulas for the shape of a bespoke
part are legitimate project code. Repeating a standard mechanism's kinematics
for each machine is the duplication this API should remove.

| Project supplies | Framework derives and validates | Must disappear from project motion code |
| --- | --- | --- |
| Gear interfaces and which member is driven/fixed | Tooth ratios, mesh phase, signs in frames, dependent rotations | Central arbor-angle dictionaries, repeated `-a * n1 / n2`, per-part rotation loops |
| Pulleys/sprockets, route, idlers and carriage clamp | Route length, travel, winding directions, all rotary/linear outputs | Separate belt phase, idler spin and motor-angle formulas |
| Lead and held screw/nut member | Screw/nut relative travel and rotation | Hand-coded turns-to-millimetres conversion |
| Pivots, link lengths, branch and independent input/target | Supported closure, reachability, frame conversions and complete poses | Repeated `acos`/`atan2`, hand-built inverse transforms and rod-placement code |
| Cycloid ring/disc/eccentric geometry and member attachments | Orbit, spin, disc phase and output motion | Per-disc sine/cosine offsets and copied reduction constants |
| Cable anchors/reeving, drum geometry; finger closure assumption if needed | Path-length balance, payout and prescribed joint distribution | Hand-counted mechanical advantage and duplicated tendon angle-budget functions |
| Cam profile, follower shape/path and installed phase | Contact and lift for supported geometry | Per-valve profile support calculations and independent time-driven cam/valve formulas |
| Selector path, gear-face spans and admissible engagements | Active mesh, neutral/free outputs and phase compatibility | Smooth ratio interpolation presented as transmission physics |
| Effective pendulum length, amplitude/phase and selected period approximation | Period scaling and supported oscillator phase/swing | Repeated square-root clock-rate compensation |
| Joint inputs generated by gait, gesture, firing or demo code | Machine response to those inputs | Nothing: generating those input programs intentionally remains local |

Designing a project-specific escapement or Sautoir remains legitimate. But
standard circle intersections, cam contact, lever arcs, tooth indexing and
frame handling inside it should compose family operations. An opaque project
function producing every part's pose is evidence that the declarative layer
still lacks a useful compound, not proof that `MotionLaw` makes it sufficient.

## What changed after the wider survey

The original sample (clocks, OpenTorque, Thor, Inmoov, the hexapod, Pascaline and
V8) established the core joints, gear/belt/screw/tendon drives, linkage/contact
families and extension seam. The wider survey established these additions:

- Kossel and Hangprinter: parallel constraints, spherical joints, explicit
  route-length balance and a first-class `LinearDelta` compound.
- Both cycloidal actuators: eccentric orbit and `CycloidalReducer`.
- Snappy: `RackAndPinion` and `CableCarrier`.
- OpenVMP: `ChainDrive`.
- Printer extruders/Fender Bender: rolling feed and flexible routes.
- OpenManipulator/OpenArm: imported mimic `JointCoupling`.
- OpenFlexure: explicit `FlexureJoint` approximations.
- Gear-shift: cylindrical/sliding angular coupling, `Engagement`, neutral
  freedoms and re-engagement compatibility.
- Additional clock models: Geneva indexing distinct from prescribed rise,
  reeved cord payout and pendulum adjustment/period scaling.
- The organization pass: typed physical interface descriptors and named
  `ProportionalClosure` keep standard metadata/closure arithmetic out of
  project control code.

The initial vocabulary was therefore insufficient without these additions and
semantics. No framework `Gait`, `Gesture`, `FiringSchedule`, `DemoSequence`,
`Robot`, `Clock` or `Gearbox` class is added. No hydraulic, combustion,
detent-force, synchronizer or locomotion solver is inferred from a directory
name. Physical stops and exclusive-engagement checks are joint/engagement
contracts; operator sequences remain project programs.

## Semantics needed to make these classes useful

### Mechanical interfaces, not just scalar ports

A scalar rotational port can carry an angle, but cannot by itself identify a
shaft axis, tooth count or mesh registration. The proposed API needs typed,
named mechanical interfaces attached to body-local frames. Interfaces refer to
the part's own declared dimensions; they do not duplicate them in a second
parameter bag. Imported geometry may require explicit interface annotations;
the framework must not guess mating features from arbitrary STL surfaces.

Examples of interface information include rotation/translation coordinate,
axis, pivot, tooth count, pitch/module, handedness, engagement span and rest
registration. A body can expose several interfaces: the clock's wheel and
pinion share one arbor coordinate while engaging different neighbours.

Frame ownership resolves the repeated inverse transforms in Thor, the hexapod
and OpenVMP. Gear centre distance can be derived when placement is a declared
unknown; when imported placements are fixed, the same relation validates them
and reports inconsistency instead of silently moving source geometry.

### One declared relationship, two discoverable directions

The author should declare a mesh once. From that relation the framework can
report both "driven by" and "drives". Requiring authors to maintain both lists
creates two competing truths. A `driven_by=` convenience spelling is desirable,
but should lower to the same named `GearMesh` object as an assembly-level
connection. Use explicit connection objects for multi-member mechanisms such
as differentials and planetary sets.

The part tree describes containment/identity. The mechanical network describes
relations. They are different structures. A ring, sun and carrier do not become
parent and child merely because they constrain one another.

### Solve what is constrained; expose what is free

Resolve interfaces and build the mechanical network before deriving motion.
Evaluation must not depend on whether one sibling's `simulate()` happened to
run first. Acyclic relations can lower to expressions; supported closed loops
need an explicit solver/analytic compound and diagnostics. Generic
`ParallelLinkage` syntax alone is not an implementation of that solver.

The author declares independent coordinates and fixed members. The framework
derives dependent values, checks residuals and reports insufficient or
contradictory constraints. A free differential side gear, neutral gearbox
output, or underactuated finger must not silently receive zero or a convenient
ratio. Where a known joint/output pose is supplied, supported kinematic
relations may solve upstream motor positions too; this does not assert physical
backdrivability of a worm or screw.

Errors must name the involved body/interface paths, units, branch and failed
relation. Reachability, singularities, finite gear sectors, joint limits and
incompatible tooth registration are part of the mechanical contract.

### Distinguish expressions, state and approximation

Smooth ideal gear trains are usually functions of current independent
coordinates. Ratchets and re-engagement may depend on previous state, while
some intermittent mechanisms can be expressed with unwrapped input phase.
Declare which kind a mechanism implements. Stateful mechanisms need initial
conditions and deterministic reset/replay semantics for seeking time; arbitrary
viewer evaluation order must not alter the result.

Every law must distinguish geometry-derived, prescribed and approximated
behavior. Inmoov's chosen distribution of tendon travel, OpenFlexure's
small-displacement assumptions, and a prescribed escapement release law are
visible model assumptions. An opaque callback returning a dictionary of all
part angles is not an acceptable built-in mechanism contract.

Use the same equations for numeric evaluation and symbolic/interactive
evaluation. Preserve dimensional quantities through mechanism expressions,
including angle constants. Unsupported equations or state behavior must fail
explicitly, not work in Python while breaking in the viewer. If new runtime
support is needed, changes to the independent viewer are a separate concern;
this document does not authorize either implementation.

### Flexible geometry shares the mechanical solution

A routed belt's phase/travel and its pulleys must come from the same relation.
A spring's seats determine its installed shape. A cable carrier's links follow
its route. Use solid-node's existing flexible-leaf/molejo integration rather
than inventing another flexible-mesh system inside `mechanisms`.

Keep three concepts separate: a route used only to draw a tube; an inextensible
length constraint; and a force-bearing flexible material model. A rendered
taut Hangprinter line is not evidence that all cable tensions are feasible.

### Small authoring surface, inspectable expansion

The combined class catalogue is a library vocabulary, not boilerplate that
every project must import. Most models need a handful. Compound classes expand
to the same joints, interfaces and relations that an advanced author can
inspect, override or compose. Do not replace a long project script with an
equally long generic constraint script when a named, tested compound exists.

Illustrative future clock fragment, **not executable with today's API**; the
project part classes expose the named interfaces and mechanical installation
data, and grounding/joints are omitted here to focus on the gear train:

```python
class MotionWorks(AssemblyNode):
    cannon = CannonPinion()
    intermediate = MotionWorksArbor()
    hour_holder = HourHolder()

    first_mesh = GearMesh(cannon.pinion, intermediate.wheel)
    second_mesh = GearMesh(intermediate.pinion, hour_holder.wheel)

    minute_hand = MinuteHand()
    hour_hand = HourHand()
    minute_mount = ShaftCoupling(cannon.shaft, minute_hand.hub)
    hour_mount = ShaftCoupling(hour_holder.shaft, hour_hand.hub)
```

The project supplies the cannon input through its public interface. Tooth
counts and registration live with the interfaces; there is no independently
programmed `hour = minute / 12`. Replacing a gear changes the physical result
and lets a clock-specific check detect whether the desired twelve-hour ratio
is still achieved. The mechanical network does not hard-code that goal.

## Gear-shift: the decisive additional fixture

Evidence: [gearbox model](../../projects/Vibecoded-demos/gear-shift/root/gearbox.py)
and [design](../../projects/Vibecoded-demos/gear-shift/docs/design.md).
The model has a fixed 20:20 primary mesh, an axially sliding keyed layshaft
cluster, and four selectable output meshes:

| Selector travel (mm) | Layshaft : output teeth | Engaged output/input angular increment ratio |
| --- | --- | --- |
| 0 | 18 : 34 | 9/17 |
| 12 | 22 : 30 | 11/15 |
| 24 | 26 : 26 | 1 |
| 36 | 30 : 22 | 15/11 |

The two external meshes produce the same net rotational sense under the
project's shaft convention. These are ratios **within an engagement**, not
global absolute-angle formulas across gear changes.

`GearboxDemo._ratio_at_time()` currently interpolates the ratios between
detents, and `render()` multiplies that changing ratio by the accumulated input
angle. That gives a display path, not a mesh-derived transmission: it imposes
output motion even between engagements and, during interpolation, the rate of
the product is not just the chosen ratio times input speed.

The declarative model should instead state:

1. Which bodies are keyed to each shaft, and which cluster may slide.
2. The selector/fork's translational relation to that cluster while permitting
   cluster spin. A rigid attachment must not make the fork spin with it.
3. Four `GearMesh` relations activated by actual axial overlap; the source's
   5 mm faces and 12 mm station pitch produce neutral travel between pairs.
4. At most one selectable mesh may be engaged at a time.
5. In neutral the output is mechanically free. Any held-angle, coast or driven
   behavior is separately declared; no output ratio is interpolated.
6. Re-engagement requires compatible phase/state or an explicitly supplied
   transition model. Instantaneously snapping to `ratio * input_angle` is not
   phase preservation. The initial ideal model may reject incompatible shifts
   without simulating impacts or synchronization.

The project's demonstration still decides when to move the selector and turn
the crank. An explicit project display-only interpolation remains possible, but
must be labelled as such rather than passed off as engaged mechanical motion.

## Coverage audit

Method: static inspection of local project manifests, model roots and motion
implementations, cross-checked by a catalogue-wide scan for `solid_node` imports.
Generated artifacts, environments, vendored/upstream copies and Git internals
were excluded from discovery. This is a survey of the simulations in this
workspace, **not of every upstream repository on the internet**. No CAD rebuild,
collision sweep, hardware validation or new test run was performed for this
document. Links below name the implementation evidence; they refer to the local
catalogue, whose repositories are independently owned and may evolve.

The scan found **25 non-sandbox upstream-project integrations** containing
solid-node code, including the static Ada assembly; **24 have motion code**.
It also found **four Vibecoded demos**, all included below. There are eleven
registered 3DPrintedClocks models, counted as one project. Mere existence of a
`pyproject.toml` was not treated as a completed simulation.

### Upstream projects

| Project and inspected evidence | Mechanical coverage and limitation |
| --- | --- |
| [3DPrintedClocks](../../projects/3DPrintedClocks/simulation/shared/assemblies.py), [movement](../../projects/3DPrintedClocks/simulation/shared/movement.py), [Geneva](../../projects/3DPrintedClocks/simulation/shared/geneva.py), [grasshopper](../../projects/3DPrintedClocks/simulation/shared/grasshopper.py) | `GearMesh`, shaft/joint connections, bevel transfer, `IndexingDrive`/`GenevaDrive`, project escapement specializations. Clock 48 adds adjustment `LeadScrew` relations and `PendulumOscillator`; clock 50 adds reeved cord payout (`DrumDrive`/`CableDrive`). Reviewed shared motion and registered variants: wall clocks 01, 02, 03, 48–52, 53 grasshopper, 54, and mantel 34 steampunk. The Geneva cross currently uses a smooth prescribed rise, not an exact pin-slot law. Winding-knob fitting is a project demonstration; spring/ratchet geometry is not proof of simulated stored energy. |
| [Metamaquina2](../../projects/3D-Printers/Metamaquina2/metamaquina2/metamaquina2.py) | Cartesian prismatic stages, `BeltDrive`, `LeadScrew`, shaft couplings and flexible filament routing. X/Y belt motion and Z screw turns should be consequences of the stage constraints. |
| [Prusa3-vanilla](../../projects/3D-Printers/Prusa3-vanilla/simulation/prusa_i3.py), [belts](../../projects/3D-Printers/Prusa3-vanilla/simulation/belts.py) | Same Cartesian families plus geared extruder `RollingContact` and `FlexibleRoute`. Feed travel, hob rotation and visible filament need one mechanical source. |
| [snappy-reprap](../../projects/3D-Printers/snappy-reprap/simulation/motor_segment.py), [cable carrier](../../projects/3D-Printers/snappy-reprap/simulation/cable_chain.py) | Adds `RackAndPinion` and `CableCarrier` to joints and `LeadScrew`. Current cable-chain routing is a supported U-bend model, not general chain dynamics. |
| [kossel](../../projects/3D-Printers/kossel/simulation/kossel.py) | `ParallelLinkage` with spherical joints, rod lengths, prismatic carriages and belts; `LinearDelta` reuses existing delta laws and owns rod poses. Target paths stay local. Bowden visualization does not establish constant material length. |
| [hangprinter](../../projects/3D-Printers/hangprinter/simulation/hangprinter.py), [winch](../../projects/3D-Printers/hangprinter/simulation/winch.py) | `CableDrive`, `DrumDrive`, `BeltDrive`, `FlexibleRoute`, parallel length constraints. Reeving advantage matters; do not replace it with one direct distance per motor. No cable-tension equilibrium claim. |
| [fender-bender](../../projects/3D-Printers/fender-bender/simulation/kinematics.py), [assembly](../../projects/3D-Printers/fender-bender/simulation/fender_bender.py) | `RollingContact`, routed filament/slack loop and ordinary slide/hinge coordinates. Loop has two contributing spans; release/pin-pull demonstration remains project code. |
| [OpenTorque-Actuator](../../projects/Actuators/OpenTorque-Actuator/simulation/reducer.py), [kinematics](../../projects/Actuators/OpenTorque-Actuator/simulation/kinematics.py) | `PlanetaryGearSet`: sun 18, planets 54, ring 126 fixed; carrier input/8 and carrier-relative planet spin. A ratio solution alone does not establish clearance of the imported source solids. |
| [OpenCycloid](../../projects/Actuators/OpenCycloid/simulation/actuator.py) | Adds `CycloidalReducer`/`EccentricDrive`: two phased orbiting discs and 20:1 output reduction. Distinguish each disc's orbit, spin and extracted output. |
| [Internal-Cycloidal-Actuator](../../projects/Actuators/Internal-Cycloidal-Actuator/simulation/actuator/assembly.py) | Same family: 9 ring rollers, 8 disc lobes and eccentric output extraction. Preserve imported rest frames and mesh phase. |
| [open_robot_actuator_hardware](../../projects/Actuators/open_robot_actuator_hardware/simulation/actuator.py) | Two 3:1 timing-belt stages, shafts, pulleys and idlers: `BeltDrive` composes to 9:1. No new actuator-specific mechanism class needed. |
| [openflexure-microscope](../../projects/Lab-Equipment/openflexure-microscope/simulation/microscope/kinematics.py) | Gears/screws drive flexural lever and parallel-stage approximations. Adds `FlexureJoint`; uses `FourBarLinkage`/`ParallelLinkage` and explicit project approximation laws. This is not a stiffness or deformation-field solution. |
| [poseidon](../../projects/Lab-Equipment/poseidon/simulation/pump.py) | `LeadScrew`, prismatic carriage/nut/plunger and fixed microscopy components. Pump, microscope and combined roots do not require a fluid-flow solver to express their present mechanics. |
| [science-jubilee](../../projects/Lab-Equipment/science-jubilee/simulation/jubilee.py) | Cartesian tool positioning relative to a fixed deck. Current source raises the tool to represent bed-relative Z; it does not model the actual chassis transmission. No evidence here for a required `CoreXY` class. |
| [Thor](../../projects/Robotic-Arms/Thor/simulation/art4.py), [wrist](../../projects/Robotic-Arms/Thor/simulation/art56.py), [gripper](../../projects/Robotic-Arms/Thor/simulation/gripper.py) | Revolute serial arm, internal/spur gears, timing belts, bevel differential/crown gearing, rolling-bearing model and gripper four-bars. Relative elbow/shoulder and wrist-carrier frames must be explicit; source pivot approximations must not disappear behind a solver. |
| [BCN3D-Moveo](../../projects/Robotic-Arms/BCN3D-Moveo/simulation/moveo.py) | Five revolute coordinates and a symmetric gripper: `SerialChain`, joints and coordinate coupling. The current simulation is a collision-envelope proxy, not a detailed drive-train model. |
| [open_manipulator](../../projects/Robotic-Arms/open_manipulator/simulation/open_manipulator_x.py) | Four revolute joints and opposing prismatic fingers: `SerialChain`, `PrismaticJoint`, `JointCoupling` for source mimic semantics. |
| [openarm](../../projects/Robotic-Arms/openarm/simulation/arm.py), [gripper](../../projects/Robotic-Arms/openarm/simulation/gripper.py) | Seven-joint arms, including a joint frame without its own visual leaf, and equal-angle mirrored fingers: `SerialChain` and `JointCoupling`. Gestures remain local. |
| [Inmoov-sim](../../projects/Robotic-Hands/Inmoov-sim/Inmoov_sim/kinematics.py) | `DrumDrive`, `TendonDrive`, serial finger joints and wrist gearing. Current proportional finger closure is an explicit underactuation assumption, not determined by tendon length alone. Additional elbow/upper-arm code introduces screw/linkage and worm relations beyond the default forearm root. |
| [HACKberry](../../projects/Robotic-Hands/HACKberry/simulation/imported/assembly.py) | Current inspection model moves rigid digit groups around declared pivots, including the thumb's two axes. Joints/serial chains cover what is modeled; do not claim distal tendon/linkage motion or independent hardware actuation from its six inspection controls. |
| [Ada_3D_model_files](../../projects/Robotic-Hands/Ada_3D_model_files/simulation/ada_hand.py) | Static left/right assemblies only: fixed placement suffices today. The single flexible palm stays in its released open shape; future finger deformation is **not** coverage evidence from this model. |
| [hexapod_spiderbot_model](../../projects/Robots/hexapod_spiderbot_model/simulation/spiderbot.py) | Six three-revolute leg chains with foot targets transformed into chassis/leg frames: `SerialChain` and `PointConstraint` with supported IK. Gait phase offsets remain local. |
| [AlbertPro](../../projects/Robots/AlbertPro/simulation/leg.py), [root](../../projects/Robots/AlbertPro/simulation/albert.py) | Four two-revolute legs, source MJCF frames/limits and coordinated hardware parts. `SerialChain`/joints suffice; gait tables, blends and upstream motion data remain project programs. |
| [YouCanBuildDog](../../projects/Robots/YouCanBuildDog/simulation/leg.py), [root](../../projects/Robots/YouCanBuildDog/simulation/dog.py) | Four parallelogram legs plus chassis articulation: `FourBarLinkage` and joints. The carried lower leg translates without rotating; ordinary serial nesting alone misses this. |
| [openvmp / Don1](../../projects/Robots/openvmp/simulation/don1/robot.py), [frame helpers](../../projects/Robots/openvmp/simulation/don1/link.py) | Articulated legs, wheel spin, camera pan/tilt, worm reductions and sprocket ratios. Adds `ChainDrive`; named frames remove repeated inverse transforms. Wheel rotation is not presently a solved wheel-ground locomotion constraint. |

### Vibecoded demos

| Project and evidence | Mechanical coverage and limitation |
| --- | --- |
| [pascaline](../../projects/Vibecoded-demos/pascaline/pascaline/kinematics.py), [digit](../../projects/Vibecoded-demos/pascaline/pascaline/digit.py) | Crown/lantern transfer, cam/contact-driven lift, pawl/ratchet and indexing compose a project `SautoirCarry`. Current fall and contact approximations must be labelled. Physical carry relationships belong in the machine; operand entry, arithmetic examples and demonstration sequencing do not. |
| [v8-engine](../../projects/Vibecoded-demos/v8-engine/v8_engine/kinematics.py), [timing](../../projects/Vibecoded-demos/v8-engine/v8_engine/final_drive/timing_drive.py), [valves](../../projects/Vibecoded-demos/v8-engine/v8_engine/valvetrain/valve_motion.py) | Eight `SliderCrank` units, timing gear train, `CamFollower`, shaft couplings and `SpringMount`. Cam geometry determines valve lift; project firing schedules do not. Spring rendering follows installed extent, not predicted valve-train dynamics. |
| [gear-shift](../../projects/Vibecoded-demos/gear-shift/root/gearbox.py) | Adds sliding angular coupling and conditional engagement/neutral semantics; detailed above. Four meshes and a selector are reusable mechanics, while the shift sequence remains local. |
| [abacus](../../projects/Vibecoded-demos/abacus/abacus/column.py), [laws](../../projects/Vibecoded-demos/abacus/abacus/kinematics.py) | Bead slide joints and travel limits. Digit-to-bead selection and counting demonstrations remain local; the ontology needs no `Abacus`, `DigitProgram` or generic arithmetic controller. |

### Discovery exclusions and supplemental sandbox check

[Berkeley Humanoid](../../projects/Robots-Bipedal/berkeley-humanoid-sim/README.md)
explicitly says nothing is simulated yet and has no model entry. Its anticipated
cycloidal joints cannot count as a validated ontology fixture. OpenAstroMount and
the other catalogue checkouts without solid-node model source were likewise
outside the simulation coverage claim.

The import scan also found 22 sandbox directories. They are not treated as
additional upstream integrations, but their motion-bearing source was screened
for overlooked families:

| Sandbox group | Result |
| --- | --- |
| `american-windmill`, `american-windmill-2`, `windmill`, `dutch-windmill`, `dutch-windmill-2`, `dutch-windmill-3`, `dutch-windmill-4`, `dutch-windmill-5` | Shaft groups, spur/bevel/crown gearing and belt stages fit the proposed vocabulary. Several are partial builds or use independent time-derived ratios. A rotating water-lifting screw is not a `LeadScrew` merely because both are helical; no fluid prediction is represented. Evidence includes [Dutch motion laws](../../projects/sandbox/dutch-windmill/root/kinematics.py) and [moving shaft group](../../projects/sandbox/dutch-windmill-5/dutch_windmill_5/moving_group.py). |
| `gearbox`, `delme-claude` | Simple gear pairs; [gearbox](../../projects/sandbox/gearbox/root/gear_pair.py) already uses the framework mesh law. No additional family. |
| `inmoov-hand` | [Reconstructed hand](../../projects/sandbox/inmoov-hand/inmoov_hand/inmoov_hand.py) has independently time-driven joint and drum poses. `SerialChain` covers the poses; its animation does not prove a tendon-length solution. |
| `classroom-polder-mill`, `gear-shift-2`, `demo_gearbox`, `dragon_r1`, `newcomen-engine`, `guitar`, `snowman`, `snowman-2`, `snowman-3`, `delme-opencode`, `test-agents` | Static, partial or placeholder models in the screened source; no additional motion family established. In particular [newcomen-engine](../../projects/sandbox/newcomen-engine/newcomen_engine/newcomen_engine.py) is currently a primitive solid, not evidence for a beam-engine mechanism. Do not infer machinery from directory names. |

## Relationship to the current framework

This is an extension proposal, not a description of the current release. The
local [mechanism exports](../../solid-node/solid_node/mechanisms/__init__.py)
are functions such as `meshed_angle`, `screw_travel`, `piston_height`,
`delta_carriage` and `circle_intersection`, not the classes proposed here.
Those laws already eliminate some duplicated mathematics and should be reused
as the analytic foundation, with their assumptions retained.

The [ports implementation](../../solid-node/solid_node/node/ports.py) provides
typed value binding, not the full physical interface/constraint/state network
described above. [ADR-056](../../solid-node/docs/adrs/NODE/ADR-056-signals-drivers-ports-and-stepped-simulation.md)
separates present signal/port semantics from deferred equation solving.

Two current boundaries need an explicit design decision before implementation:

- The [declarative-node spec](../../solid-node/openspec/specs/declarative-nodes/spec.md)
  currently refuses reading attributes from child declarations in a class body.
  The clock fragment requires a narrowly defined symbolic **interface reference**,
  resolved per assembly instance, not arbitrary eager sibling-instance access.
- [ADR-076](../../solid-node/docs/adrs/MATH/ADR-076-mechanism-laws-as-compositions-over-expression-math.md)
  and the mechanism package document that the present degree-literal laws do not
  support the declared-quantity face. Dimensioned mechanism expressions need a
  supported constant/quantity path; stripping `.value` everywhere is not the
  intended declarative API.

No baseline spec or accepted ADR is changed by this provisional document.

## Sufficiency verdict and useful implementation order

**The amended ontology provides a vocabulary for the categories of motion actually represented in
all 29 non-sandbox integrations/demos surveyed**, including one static upstream
integration. This is conceptual coverage, not an implementation or solver
conformance result. Project-specific escapements, Sautoir details and documented
approximations remain honest extension points. Missing physics and not-yet-built
projects do not become covered by writing `Mechanism` in a table.

The essential additions are parallel/closed-loop constraints, cycloidal motion,
rack and chain transmission, routed flexible motion, imported joint mimic
relations, and selectable engagement with state. Their implementations should
be earned against the named originating models:

1. Prove the interface-reference and dimensional-expression model with clock 01:
   joints, meshes, couplings, derived hand motion, no central angle dictionary.
2. Exercise compound/reversible relationships with OpenTorque and Thor; belts,
   screws, rack and roller feed with the Cartesian printers and Poseidon.
3. Exercise explicit branches and multi-input constraints with Kossel, the
   hexapod, YouCanBuildDog and Hangprinter; include underconstraint tests for
   Inmoov rather than silently solving an arbitrary grasp.
4. Exercise orbit versus body spin with both cycloidal actuators; flexure and
   route approximations with OpenFlexure and Snappy.
5. Use gear-shift, Pascaline and the clock day complication to prove neutral,
   engagement, dwell, initialization and replay semantics before claiming
   general stateful mechanisms.

Each fixture should prove that changing a tooth count, link length, lead or
installation phase propagates through the machine without another hand-written
ratio/pose function. It should also fail clearly for incompatible geometry,
unreachable branches, conflicting drivers and missing independent inputs.
Numeric results, interactive evaluation and visible mechanical alignment must
agree. Measure the reduction in project motion code as well as the size of the
replacement declarations.

Ratify the API shape and supported solver/state scope separately before
implementation. This document records the proposed vocabulary and the empirical
reasons for it; it does not open or authorize that implementation cycle.
