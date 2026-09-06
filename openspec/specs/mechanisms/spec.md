# Mechanisms Specification

## Purpose

The mechanism laws the framework carries once so a project's own
`kinematics.py` stops rewriting them: the external spur-gear mesh, the
lead screw, the planar slider-crank, linear delta kinematics, and the
circle geometry a linkage asks for. Records their frames, zeros and sign
conventions, the two faces they inherit from `solid_node.math` and the
declared face they refuse, and the identities each law is held to.
Encodes ADR-076 (mechanism laws as compositions over expression math),
over ADR-022 (cross-runtime degree-trig parity) and ADR-062 (typed
parameters and the exponent algebra).

Code: `solid_node/mechanisms/`.

## Requirements

### Requirement: Mechanism laws as compositions over expression math

The system SHALL provide the package `solid_node.mechanisms`, whose every
function is a composition of `solid_node.math` functions and ordinary
arithmetic, so that one formula computes on plain numbers and builds the
viewer's deferred expression when any argument is symbolic animation time or
a driver. No function in the package SHALL emit an OpenSCAD builtin that
`solid_node.math` does not already emit, so the cross-runtime parity corpus
of the `kinematics` capability covers the package without extension.

The package SHALL re-export every public function under a flat name unique
across its families, so `from solid_node.mechanisms import meshed_angle`
works, and SHALL keep each family in its own module with the family's
conventions stated once in that module.

Every angle SHALL be in degrees, positive by the right-hand rule about the
stated axis, matching `solid_node.math` and the node transform API. Every
function's docstring SHALL state its frame, its zero and its sign, and SHALL
map that convention onto the originating project it was lifted from.

The package SHALL NOT provide a declared (class-body) face: its laws carry
degree literals such as `180` and `360` that the dimension algebra cannot
type as angles, so a declared token reaching a law raises the algebra's own
dimension error at class definition rather than yielding a formula. A class
body that needs a mechanism law over declared parameters evaluates it on
`.value` operands, which is the algebra's stated escape hatch.

#### Scenario: A law rides through a symbolic driver

- **WHEN** `piston_height` is called with a symbolic driver expression as
  the crank angle and numbers for the crank radius and rod length
- **THEN** it returns a symbolic expression composed only of `cos`, `sin`,
  `sqrt` calls and arithmetic, and nothing raises

#### Scenario: Numeric and symbolic faces agree

- **WHEN** each exported law is evaluated once on numbers and once on a
  symbolic expression that is then evaluated at the same numbers
- **THEN** the two results are equal within floating-point tolerance for
  every law and every sampled input

#### Scenario: The declared face is refused

- **WHEN** a class body computes `meshed_angle(theta, 12, 24)` over a
  declared `Angle` parameter `theta`
- **THEN** class definition raises a dimension error, and the same
  computation over `theta.value` succeeds

### Requirement: The external spur-gear mesh law

`meshed_angle(driver_angle, driver_teeth, driven_teeth, line_of_centres=0.0,
driver_gap=0.0, driven_tooth=0.0)` SHALL return the angle of the driven gear
of an external spur pair, and `driving_angle(driven_angle, driver_teeth,
driven_teeth, line_of_centres=0.0, driver_gap=0.0, driven_tooth=0.0)` SHALL
return the driver angle for a driven gear already placed, both in the common
frame in which both gears' angles and the line of centres are measured.

`line_of_centres` SHALL be the direction from the driver's centre to the
driven's. `driver_gap` SHALL be the direction, in the driver's own frame at
angle zero, of the centre of one of its gaps; `driven_tooth` SHALL be the
direction, in the driven's own frame at angle zero, of the tip of one of its
teeth. Both references default to zero and are values a caller reads from
its gear library's convention; the law SHALL NOT read any gear object.

The law SHALL be `driven = line + 180 - driven_tooth - (driver_teeth /
driven_teeth) * (driver_gap + driver_angle - line)`, and `driving_angle`
SHALL be its exact inverse.

#### Scenario: The pair is meshed at the reference pose

- **WHEN** the driver stands so that its referenced gap centre points along
  the line of centres, that is `driver_angle = line - driver_gap`
- **THEN** `meshed_angle` returns `line + 180 - driven_tooth`, the pose in
  which the driven's referenced tooth tip points back along the line of
  centres into that gap

#### Scenario: The driven counter-rotates by the tooth ratio

- **WHEN** the driver angle advances by one degree
- **THEN** `meshed_angle` decreases by `driver_teeth / driven_teeth` degrees;
  for 60 teeth driving 8, by 7.5 degrees

#### Scenario: The cq_gears convention is two values

- **WHEN** `meshed_angle(0, 12, 24, 0, 180 / 12, 0)` is evaluated, the
  driver's tooth centred on its +X at zero so its gap centre sits at
  `180 / 12`, and the driven likewise so its tooth tip sits at zero
- **THEN** the result is `172.5`, the value gearbox's `conjugate_angle(0,
  12, 24)` returns, and `meshed_angle(30, 12, 24, 45, 15, 0)` is `225`,
  matching `conjugate_angle(30, 12, 24, alpha=45)`

#### Scenario: The inverse round-trips

- **WHEN** `driving_angle(meshed_angle(10, 60, 8, 30, 3, 22.5), 60, 8, 30,
  3, 22.5)` is evaluated
- **THEN** the result is `10` within floating-point tolerance, and
  `meshed_angle(10, 60, 8, 30, 3, 22.5)` itself is `315`

### Requirement: The lead screw

`screw_travel(angle, lead)` SHALL return `lead * angle / 360` and
`screw_angle(travel, lead)` SHALL return `360 * travel / lead`, where `lead`
is the axial advance per turn (pitch times starts, never bare pitch).

The convention SHALL be a right-hand thread turned positively by the
right-hand rule about its axis, which advances the screw along that axis
relative to its nut by the returned travel. A left-hand thread, or the nut's
own motion relative to a screw held axially, is the caller's negation; the
functions SHALL take no handedness argument.

#### Scenario: One turn is one lead

- **WHEN** `screw_travel(360, 2.0)` and `screw_angle(1.0, 2.0)` are evaluated
- **THEN** the results are `2.0` and `180`, and the two functions are exact
  inverses for a nonzero lead

#### Scenario: A left-hand screw is the caller's sign

- **WHEN** the openflexure column, whose screw lowers the column as its
  motor turns positively, is expressed
- **THEN** its travel is `-screw_travel(angle, lead)`, and the framework
  function itself carries no sign choice

### Requirement: The planar slider-crank

The crank functions SHALL work in the crank's own plane: the crank axis is
normal to the plane, the cylinder axis is the plane's second coordinate,
called *along*, and the first coordinate is *across*. The crank angle SHALL
be measured from the along axis, positive by the right-hand rule about the
crank axis, with zero at top dead centre.

- `crank_pin(angle, crank_radius)` SHALL return the pin's `(across, along)`
  position: `(-crank_radius * sin(angle), crank_radius * cos(angle))`.
- `crank_rod_angle(angle, crank_radius, rod_length)` SHALL return the
  connecting rod's tilt from the cylinder axis, in the same rotational sense,
  such that a rod authored along the cylinder axis and turned by it carries
  its small end onto the axis: `-asin((crank_radius / rod_length) *
  sin(angle))`.
- `piston_height(angle, crank_radius, rod_length)` SHALL return the small
  end's along coordinate: `crank_radius * cos(angle) + sqrt(rod_length^2 -
  (crank_radius * sin(angle))^2)`.

A caller whose crank axis is not the plane normal maps these with its own
frame rotation; v8-engine's crank about +X with the pin at +Z at zero is
this plane with `across = y` and `along = z`.

#### Scenario: Top, quarter and bottom dead centre

- **WHEN** the three functions are evaluated for a crank radius of 15 and a
  rod length of 60 at angles 0, 90 and 180
- **THEN** `crank_pin` returns `(0, 15)`, `(-15, 0)` and `(0, -15)`,
  `crank_rod_angle` returns `0`, `-asin(0.25)` (about `-14.4775`) and `0`,
  and `piston_height` returns `75`, `sqrt(3375)` (about `58.0948`) and `45`,
  all within floating-point tolerance

#### Scenario: The small end stays on the cylinder axis

- **WHEN** for any sampled crank angle the rod, authored along the cylinder
  axis from the pin, is turned by `crank_rod_angle` and added to `crank_pin`
- **THEN** the small end's across coordinate is zero within tolerance and
  its along coordinate equals `piston_height`

### Requirement: Linear delta kinematics

For a linear delta whose towers stand on a circle about Z and whose
carriages ride vertically:

- `delta_carriage(x, y, rod, radius, tower, plane=0.0)` SHALL return the
  height of the carriage joint on the tower at azimuth `tower` for an
  effector at `(x, y)` whose joint plane is at height `plane`: `plane +
  sqrt(rod^2 - dx^2 - dy^2)` where `(dx, dy) = (x - radius * cos(tower),
  y - radius * sin(tower))` is the horizontal vector from the carriage joint
  to the effector joint, and `radius` is the length of that vector when the
  effector is at the origin.
- `delta_rod(x, y, rod, radius, tower)` SHALL return `(tilt, azimuth)`: the
  rod's lean from vertical, `asin(sqrt(dx^2 + dy^2) / rod)`, and the
  direction of that lean about Z, `atan2(dy, dx)`.

The two rotations SHALL pose a rod authored along Z with either of its
joints at the origin: rotate by `-tilt` about Y, then by `azimuth` about Z,
then translate to that joint. The docstring SHALL record why two rotations
about constant axes are returned rather than one about a computed axis: a
rotation axis in this framework cannot carry a driver symbol.

#### Scenario: A rod at the origin, at the tower's foot

- **WHEN** `delta_carriage(0, 0, 215, 100, 0)` and `delta_rod(0, 0, 215,
  100, 0)` are evaluated
- **THEN** the carriage is at `sqrt(215^2 - 100^2)` (about `190.3287`), the
  tilt is `asin(100 / 215)` (about `27.7177`) and the azimuth is `180`

#### Scenario: Moving toward and beside the tower

- **WHEN** the effector moves to `(10, 0)` and then to `(0, 10)`
- **THEN** the carriage rises to about `195.2562` with tilt about `24.7465`
  and azimuth `180`, then sits at about `190.0658` with tilt about `27.8680`
  and azimuth about `174.2894`

#### Scenario: The posed rod meets both joints

- **WHEN** a unit vector along -Z is rotated by `-tilt` about Y, then by
  `azimuth` about Z, and scaled by `rod`
- **THEN** it equals `(dx, dy, -(carriage - plane))`, the vector from the
  carriage joint to the effector joint, within tolerance

### Requirement: Linkage geometry

- `circle_intersection(centre_a, radius_a, centre_b, radius_b, side=1)`
  SHALL return the 2-tuple at distance `radius_a` from `centre_a` and
  `radius_b` from `centre_b` on the side named: `side = 1` the intersection
  to the left of the direction from `centre_a` to `centre_b` (counter-
  clockwise), `side = -1` to the right.
- `triangle_angle(opposite, adjacent_a, adjacent_b)` SHALL return, in
  degrees, the angle of a triangle opposite the side `opposite` between the
  two adjacent sides: `acos((a^2 + b^2 - opposite^2) / (2 a b))`.
- `link_rise(link, offset)` SHALL return `sqrt(link^2 - offset^2)`, the
  height of a rigid link of length `link` whose ends are `offset` apart
  horizontally.

None SHALL guard against an unreachable configuration numerically: a sqrt
or acos of an out-of-range value raises as `solid_node.math` raises, and
symbolically evaluates to NaN as OpenSCAD and the viewer do. That is the
originating projects' behaviour and the honest one.

#### Scenario: Two circles cross on the side asked for

- **WHEN** `circle_intersection((0, 0), 5, (8, 0), 5, side)` is evaluated
  for both sides
- **THEN** it returns `(4, 3)` for `side = 1` and `(4, -3)` for `side = -1`,
  and `circle_intersection((1, 1), 5, (1, 9), 5, 1)` returns `(-2, 5)`

#### Scenario: The grasshopper's nib is a circle intersection

- **WHEN** `circle_intersection((0, 0), 45, (30, 40), 20, 1)` is evaluated
- **THEN** it equals wall_clock_53's `nib_position((30, 40), 20, 1, 45)`,
  about `(10.3625, 43.7906)`

#### Scenario: A right triangle

- **WHEN** `triangle_angle(5, 3, 4)`, `triangle_angle(3, 4, 5)` and
  `link_rise(5, 3)` are evaluated
- **THEN** the results are `90`, about `36.8699`, and `4`
