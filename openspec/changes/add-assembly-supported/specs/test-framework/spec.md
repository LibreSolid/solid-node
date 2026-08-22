# Delta: test-framework — add `assertAssemblySupported`

## ADDED Requirements

### Requirement: Whole-assembly gravity support assertion

The system SHALL provide
`TestCase.assertAssemblySupported(node, gravity=(0, 0, -1), max_drop=1.0, ground=None, supports=None)`
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

When `ground` is `None`, the grounded seeds SHALL be the selected solids whose
conservative world extent along gravity comes within `max_drop` of the
assembly's furthest extent along gravity. When `ground` is a node or sequence
of nodes, each SHALL be resolved to its selected topmost rigid solid, those
solids SHALL be the only seeds, and a `ground` entry that resolves to no
selected solid SHALL raise an error rather than pass silently.

`supports`, when given, SHALL be an iterable of `(supported, supporter)` node
pairs, each resolved to selected topmost rigid solids, adding an explicit
support edge; an unresolvable pair SHALL raise an error. A declared edge SHALL
NOT ground a solid whose supporter is not itself transitively grounded.

A pair of exact solids SHALL be evaluated by the boundary-representation
kernel; any other pair SHALL be evaluated by the cached Manifolds placed by
composed world transforms with the drop displacement applied as a world-frame
translation. Only pairs whose conservative displaced-versus-placed world
bounds overlap SHALL be evaluated by Boolean intersection. A zero `gravity`
vector or a non-positive `max_drop` SHALL raise an error.

On failure the assertion SHALL raise `AssertionError` naming every selected
solid that is not transitively grounded, together with the drop distance and
gravity direction used. The framework SHALL run the assertion only when
ordinary project test code calls it; builders and non-test commands SHALL NOT
invoke it. The assertion's documentation SHALL state its physical exclusions:
no force or torque balance, no toppling analysis, no friction or adhesion, and
no lateral-restraint analysis.

#### Scenario: A single-solid project passes trivially

- **WHEN** `assertAssemblySupported(self.node)` is called on a leaf root or a
  fusion root containing only one topmost rigid solid
- **THEN** the assertion passes without performing any drop intersection

#### Scenario: A floating solid fails diagnostically

- **WHEN** a selected solid, displaced by `max_drop` along gravity, intersects
  no other selected solid and is not a grounded seed
- **THEN** the assertion fails naming that solid, the drop distance, and the
  gravity direction

#### Scenario: A resting stack on the lowest solid passes

- **WHEN** solid `A` rests on solid `B` and `B` holds the assembly's furthest
  extent along gravity with `ground=None`
- **THEN** `B` is a grounded seed, `A` is supported through its drop edge onto
  `B`, and the assertion passes

#### Scenario: Support through a floating supporter does not ground

- **WHEN** solid `A` rests on solid `B`, and `B` neither rests on anything nor
  is a grounded seed
- **THEN** the assertion fails naming every solid that is not transitively
  grounded

#### Scenario: A hanging solid held by engagement passes

- **WHEN** a solid hangs below a grounded solid such that displacing it by
  `max_drop` along gravity makes the two intersect with positive volume
- **THEN** the hanging solid is supported and the assertion passes

#### Scenario: Clearance play below the drop distance is not floating

- **WHEN** a solid sits above its seat by a clearance smaller than `max_drop`
- **THEN** its drop intersects the seat with positive volume and the solid
  counts as supported

#### Scenario: An explicit ground replaces the default seeds

- **WHEN** `ground` names a node whose topmost rigid solid is not at the
  assembly's furthest extent along gravity
- **THEN** only that solid seeds the grounded set, and the default
  lowest-extent seeding is not applied

#### Scenario: A declared support edge holds a friction-fit solid

- **WHEN** a solid held only by a press or friction fit is declared in
  `supports` with a transitively grounded supporter
- **THEN** the assertion passes without requiring a drop intersection for that
  solid

#### Scenario: Invalid knobs raise loud errors

- **WHEN** `gravity` is the zero vector, `max_drop` is not positive, or a
  `ground` or `supports` entry resolves to no selected solid
- **THEN** the assertion raises an error instead of passing or silently
  ignoring the argument

#### Scenario: An exact assembly is verified exactly

- **WHEN** every selected solid in the assembly is exact
- **THEN** each evaluated drop pair is intersected by the
  boundary-representation kernel

#### Scenario: Sparse assembly avoids exhaustive pair booleans

- **WHEN** most selected solids' displaced world bounds are disjoint from the
  others' placed bounds
- **THEN** only bounds-overlapping pairs are evaluated by Boolean intersection

#### Scenario: Current keyframe controls assembled placement

- **WHEN** the assertion is run under two testing instants that place a solid
  first resting on its support and then apart from it beyond `max_drop`
- **THEN** the first instant passes and the second fails without the assertion
  accepting or setting a keyframe argument itself
