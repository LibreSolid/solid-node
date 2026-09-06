## MODIFIED Requirements

### Requirement: Perturbation-based fit assertions

The system SHALL provide `assertBlockedBeyond(node, magnitude, against, ...)`
and `assertFreeWithin(...)` (same signature), which temporarily inject one
perturbation operation into `node.operations` before every pre-existing
operation of the node — at index 0, whatever the node's first operation is —
measure fouling against `against` through the shared intersection helper in
world coordinates, and ALWAYS remove the injected operation in a `finally` —
`node.operations` is left exactly as found. Because the perturbation is the
first operation applied, `axis` and `along` are read in the node's own
untransformed frame and every one of the node's own operations — rotations,
translations, simulated motion — carries them, as do its ancestors'. Two
mutually exclusive modes: rotational via `axis` (default `(0,0,1)` when
neither is given) and translational via `along` (a direction in the node's
own frame, normalized to unit, magnitude in mm). Passing both `axis` and
`along`, a zero `along` vector, or a `directions` value other than
`'both'`/`'forward'` SHALL raise `ValueError`. `directions='both'` (default)
checks both signs; `'forward'` only the positive.

`assertFreeWithin` accepts a list of magnitudes to sweep. `volume_epsilon`
(mm³, default 0.0 = exact emptiness) counts an intersection as fouling only
when `abs(volume) > volume_epsilon`, filtering flush-contact boolean noise.

`volume_epsilon` applies only where flush-contact noise can arise, which is
the faceted path. When a comparison routes exact, the assertion SHALL ignore
`volume_epsilon` and apply the strict verdict. When `volume_epsilon` was
supplied and EVERY comparison the call performed routed exact, the assertion
SHALL emit a warning naming the assertion, so a test does not silently keep
recording a tolerance it no longer applies. When any comparison routed
faceted, the epsilon remains live for those comparisons and no warning is
emitted. Under the faceted comparison kernel no comparison routes exact, so
`volume_epsilon` is live for every comparison and the warning never fires;
the run's own volume epsilon has already been applied to each verdict the
assertion reads, so the two compose as a floor and a filter.

Fit SHALL be certified by the paired contract — Blocked beyond the play
limit AND Free within it; `assertBlockedBeyond` alone is insufficient
(anti-gaming, ADR-025).

#### Scenario: Keyed shaft fit

- **WHEN** a test asserts `assertFreeWithin(gear, 1.5, shaft,
  volume_epsilon=1e-6)` and `assertBlockedBeyond(gear, 3, shaft,
  volume_epsilon=1e-6)`
- **THEN** the pair passes only if the gear rotates freely within 1.5° of
  play and fouls the key beyond 3° in both directions

#### Scenario: Operations restored on failure

- **WHEN** a perturbation assertion raises
- **THEN** the injected operation has already been removed and
  `node.operations` is unchanged

#### Scenario: Translational mode

- **WHEN** `assertBlockedBeyond(pin, 2.0, housing, along=[0, 0, 1])` runs on
  a pin whose placement rotates it onto a bank
- **THEN** the perturbation translates the pin 2 mm along its local axis as
  carried by the placement rotations, not the world Z axis

#### Scenario: A node whose first operation is a rotation

- **WHEN** a perturbation assertion runs on a node whose operations are a
  Rotation of 90° about Z followed by a Translation, with `along=(1, 0, 0)`
- **THEN** the perturbation is inserted before the Rotation, the node is
  displaced along the world direction that Rotation carries local X to, and
  the verdict is the one that displacement reaches

#### Scenario: An epsilon with nothing to absorb is reported

- **WHEN** a perturbation assertion is given `volume_epsilon=1e-6` and both
  compared nodes are exact
- **THEN** the verdict is the strict one and a warning names the assertion
  whose epsilon was ignored

#### Scenario: An epsilon still applies to a faceted comparison

- **WHEN** a perturbation assertion is given `volume_epsilon` and the
  comparison routes faceted
- **THEN** the epsilon filters the verdict as before and no warning is emitted

#### Scenario: A faceted run keeps every epsilon live

- **WHEN** a perturbation assertion is given `volume_epsilon=1e-6` on two
  exact nodes and the run's kernel is faceted
- **THEN** the epsilon filters the faceted verdict and no warning is emitted
