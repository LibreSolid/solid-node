# test-framework delta: static equilibrium in the gravity support assertion

## MODIFIED Requirements

### Requirement: Whole-assembly gravity support assertion

The system SHALL provide
`TestCase.assertAssemblySupported(node, gravity=(0, 0, -1), max_drop=1.0, ground=None, supports=None, stability_margin=0.0)`
as an ordinary project assertion. Starting at `node`, it SHALL select topmost
rigid solids exactly as `assertNoSolidInterference` does, and SHALL evaluate
their assembled world-space geometry at the testing instant already set by the
runner. Selection of zero or one solid SHALL pass without geometric work.

The assertion SHALL prove that every selected solid is transitively supported
against gravity. A solid `A` is directly supported by a solid `B` when `A`,
displaced by `max_drop` along the normalized `gravity` vector in the world
frame, intersects `B` with positive volume; non-empty zero-volume boundary
contact after the displacement SHALL NOT count as support. The assertion SHALL
build the directed support graph of those relations, seed a grounded set, and
require every selected solid to reach the grounded set through support edges;
mutual-support cycles SHALL be grounded exactly when some member is
transitively supported by a grounded solid.

When support reachability holds, the assertion SHALL additionally prove
frictionless static equilibrium: there SHALL exist an assignment of
non-negative (push-only) normal contact forces over the detected contact
interfaces that simultaneously balances gravity's force and torque on every
non-anchored selected solid, decided by a deterministic linear feasibility
program. Contact interfaces SHALL be extracted from the displaced-intersection
geometry of detected contacts in both displacement directions: the drop
(`+max_drop` along gravity) and a lift (`−max_drop` against gravity), so
overhead restraints can complete force couples. Each interface's contact
points and outward normals SHALL lie on the undisplaced surface of the
supporting solid. Lift-detected contacts SHALL contribute contact interfaces
only; they SHALL NOT add support-graph edges. Contact extraction and mass
properties SHALL be evaluated on the placed faceted geometry at uniform
density; support-edge existence keeps its exact-kernel routing.

When `ground` is `None`, the grounded seeds SHALL be the selected solids whose
conservative world extent along gravity comes within `max_drop` of the
assembly's furthest extent along gravity, and the equilibrium phase SHALL
anchor only a virtual floor whose top plane lies at that furthest extent and
which spans the assembly laterally: default-seeded solids SHALL balance on
their detected floor contacts rather than being exempt. When `ground` is a
node or sequence of nodes, each SHALL be resolved to its selected topmost
rigid solid, those solids SHALL be the only seeds and the only anchored
bodies, no virtual floor SHALL exist, and a `ground` entry that resolves to no
selected solid SHALL raise an error rather than pass silently.

`supports`, when given, SHALL be an iterable of `(supported, supporter)` node
pairs, each resolved to selected topmost rigid solids, adding an explicit
support edge; an unresolvable pair SHALL raise an error. A declared edge SHALL
NOT ground a solid whose supporter is not itself transitively grounded. In the
equilibrium phase a declared edge SHALL transmit an unrestricted wrench —
force and torque in both signs — between its pair, exempting that hold from
frictionless statics while keeping the exemption visible in the test.

`stability_margin` (millimetres, default `0.0`) SHALL shrink each contact
interface toward its own centroid by the given distance before the
equilibrium decision, so a positive margin rejects balances that depend on
the boundary of a contact patch; at the default the check SHALL be pure
feasibility. A negative `stability_margin` SHALL raise an error.

A pair of exact solids SHALL be evaluated by the boundary-representation
kernel; any other pair SHALL be evaluated by the cached Manifolds placed by
composed world transforms with the displacement applied as a world-frame
translation. Only pairs whose conservative displaced-versus-placed world
bounds overlap SHALL be evaluated by Boolean intersection, in the drop and
lift sweeps alike. A zero `gravity` vector or a non-positive `max_drop` SHALL
raise an error.

On reachability failure the assertion SHALL raise `AssertionError` naming
every selected solid that is not transitively grounded, together with the
drop distance and gravity direction used. On equilibrium failure it SHALL
raise `AssertionError` naming every solid whose balance cannot be satisfied
and whether force or torque balance fails, and SHALL point at `supports` as
the declared-hold escape. A solid whose reachability rests on edges yielding
no extractable contact interface SHALL fail the equilibrium phase rather than
pass silently. The framework SHALL run the assertion only when ordinary
project test code calls it; builders and non-test commands SHALL NOT invoke
it. The assertion's documentation SHALL state its physical claims and
exclusions: support reachability, force balance, torque balance, and toppling
over detected contacts ARE claimed; friction, adhesion, purely lateral
(gravity-parallel) wall reactions, single-solid floor toppling, and all
dynamic effects are NOT.

#### Scenario: A single-solid project passes trivially

- **WHEN** `assertAssemblySupported(self.node)` is called on a leaf root or a
  fusion root containing only one topmost rigid solid
- **THEN** the assertion passes without performing any drop intersection

#### Scenario: A floating solid fails diagnostically

- **WHEN** a selected solid, displaced by `max_drop` along gravity, intersects
  no other selected solid and is not a grounded seed
- **THEN** the assertion fails naming that solid, the drop distance, and the
  gravity direction

#### Scenario: A balanced resting stack on the lowest solid passes

- **WHEN** solid `A` rests centred on solid `B`, `B` holds the assembly's
  furthest extent along gravity with `ground=None`, and each solid's weight
  is balanced by its detected contacts
- **THEN** `B` is a grounded seed, `A` is supported through its drop edge onto
  `B`, the equilibrium program is feasible, and the assertion passes

#### Scenario: Support through a floating supporter does not ground

- **WHEN** solid `A` rests on solid `B`, and `B` neither rests on anything nor
  is a grounded seed
- **THEN** the assertion fails naming every solid that is not transitively
  grounded

#### Scenario: A hanging solid held by balanced engagement passes

- **WHEN** a solid hangs below a grounded solid such that displacing it by
  `max_drop` along gravity makes the two intersect with positive volume, and
  the engagement's contact interfaces balance its hanging weight and torque
- **THEN** the hanging solid is supported, the equilibrium program is
  feasible, and the assertion passes

#### Scenario: Clearance play below the drop distance is not floating

- **WHEN** a solid sits above its seat by a clearance smaller than `max_drop`
- **THEN** its drop intersects the seat with positive volume and the solid
  counts as supported

#### Scenario: An explicit ground replaces the default seeds and anchors

- **WHEN** `ground` names a node whose topmost rigid solid is not at the
  assembly's furthest extent along gravity
- **THEN** only that solid seeds the grounded set and only that solid is
  anchored in the equilibrium phase; the default lowest-extent seeding and the
  virtual floor are not applied

#### Scenario: A declared support edge holds a friction-fit solid

- **WHEN** a solid held only by a press or friction fit is declared in
  `supports` with a transitively grounded supporter
- **THEN** the assertion passes: the declared edge grounds the solid without a
  drop intersection and transmits the unrestricted wrench that balances it

#### Scenario: Invalid knobs raise loud errors

- **WHEN** `gravity` is the zero vector, `max_drop` is not positive,
  `stability_margin` is negative, or a `ground` or `supports` entry resolves
  to no selected solid
- **THEN** the assertion raises an error instead of passing or silently
  ignoring the argument

#### Scenario: An exact assembly is verified exactly

- **WHEN** every selected solid in the assembly is exact
- **THEN** each evaluated drop pair's support-edge existence is decided by the
  boundary-representation kernel, while contact interfaces and mass
  properties come from the placed faceted geometry

#### Scenario: Sparse assembly avoids exhaustive pair booleans

- **WHEN** most selected solids' displaced world bounds are disjoint from the
  others' placed bounds
- **THEN** only bounds-overlapping pairs are evaluated by Boolean
  intersection, in the drop and lift sweeps alike

#### Scenario: Current keyframe controls assembled placement

- **WHEN** the assertion is run under two testing instants that place a solid
  first resting on its support and then apart from it beyond `max_drop`
- **THEN** the first instant passes and the second fails without the assertion
  accepting or setting a keyframe argument itself

#### Scenario: A bar supported at one end fails on torque

- **WHEN** a horizontal bar's only detected contact interface lies under one
  end, so no non-negative normal force distribution cancels the torque of its
  centre of mass about that patch
- **THEN** the assertion fails naming the bar with an unbalanced torque, even
  though the bar transitively reaches ground

#### Scenario: A bar supported at both ends passes

- **WHEN** the same bar gains a second grounded contact interface under its
  other end
- **THEN** the equilibrium program is feasible and the assertion passes

#### Scenario: An offset stack whose cumulative mass leaves the base fails

- **WHEN** each solid in a stack rests stably on the one below, but the
  combined centre of mass of the upper solids passes beyond the lowest
  interface's patch
- **THEN** the assertion fails naming the unbalanced solid(s), although every
  single interface would balance its immediate top solid alone

#### Scenario: A counterweighted assembly passes

- **WHEN** a solid's own centre of mass overhangs its support patch, but a
  counterweight resting on it restores a feasible force distribution over the
  detected contacts
- **THEN** the equilibrium program is feasible and the assertion passes

#### Scenario: A cantilevered pin held by a snug hole passes

- **WHEN** a horizontal pin cantilevers from a grounded block's snug hole, the
  drop detecting the hole's lower-wall contact and the lift detecting its
  upper-wall contact
- **THEN** the two interfaces form the force couple that balances the pin and
  the assertion passes without a `supports` declaration

#### Scenario: A tippy default-seeded solid fails on the virtual floor

- **WHEN** with `ground=None` a default-seeded solid's centre of mass lies
  beyond its own detected contact patch on the virtual floor
- **THEN** the assertion fails naming that solid instead of exempting it as a
  seed

#### Scenario: A stability margin rejects a boundary-exact balance

- **WHEN** an assembly balances only at the boundary of a contact patch and
  the assertion is called with a positive `stability_margin`
- **THEN** the shrunken interfaces make the equilibrium program infeasible and
  the assertion fails, while the same assembly passes at the default margin
