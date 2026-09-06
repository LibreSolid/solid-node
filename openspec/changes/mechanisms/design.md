## Context

`solid_node.math` is the framework's one expression semantics (ADR-022):
each function computes on numbers, emits a deferred OpenSCAD call on a
symbolic `$t` or driver token, and builds a dimension-checked `Formula` on a
declared parameter (ADR-062). Everything a project's `kinematics.py` writes
over it is one of two things: arithmetic the module should have carried
(the parallel `expression-math` change), or a mechanism law. This change is
the second kind.

The laws were surveyed across every `kinematics.py` in the workspace. Five
families recur or are certain to: the spur-gear mesh (four copies over two
gear libraries' conventions), the lead screw (three copies, three signs),
circle geometry (three shapes), the slider-crank (one, textbook), and the
linear delta (one, and every delta printer in the shop's museum plan will
need it). Each copy carries a convention that had to be rediscovered
against a rendered mesh, and the numeric-only ones break under a symbolic
driver.

This cycle runs in parallel with `expression-math` from the same base,
`66f6bee`. The two must stay independent so either can integrate first.

## Goals / Non-Goals

**Goals:**

- Carry each law once, in the framework, with its convention stated in the
  code and mapped onto the project it was lifted from.
- Keep every law a composition over `solid_node.math`, so it inherits the
  numeric and symbolic faces and emits nothing the parity corpus does not
  already cover.
- Make a gear library's convention a pair of argument values rather than a
  fork of the mesh law.
- Validate each law against its originating project's own function, as
  evidence, without committing to that project.

**Non-Goals:**

- A declared (class-body) face for the laws. See D3.
- Internal or bevel gear meshes, the four-bar decomposition of the
  openflexure legs (`leg_lean`, `lever_rise`), the kossel rod's own spin
  about its axis (a ball-joint pair's detail), and the timeline slicing
  the abacus, fender-bender and pascaline share, which is `time * count -
  index` once `expression-math` lands.
- Belt wraps (Prusa3, hangprinter, kossel): molejo's territory.
- Escapements: repeated only inside the clocks project, by that project's
  own choice.
- Migrating any originating project. Each is edited in its own repository
  as evidence and left uncommitted.
- Using any name the `expression-math` change adds. The package imports
  only `sin`, `cos`, `asin`, `acos`, `atan2` and `sqrt`, which exist at the
  base; a later maintenance change may simplify once both are integrated.

## Decisions

### D1 — A package named `mechanisms`, one module per family, flat re-exports

`solid_node/mechanisms/` with `gears.py`, `screws.py`, `cranks.py`,
`deltas.py` and `linkages.py`, and an `__init__.py` that re-exports every
public function eagerly. Eager, not deferred as `solid_node.simulation`
does, because each module imports only `solid_node.math`; there is no heavy
import to defer.

Family modules exist so a family's frame and sign conventions are stated
once at the top of the file the functions live in. Flat re-exports exist so
the import line a project writes is `from solid_node.mechanisms import
meshed_angle`. The names are therefore chosen unique across families:
`crank_rod_angle` rather than `rod_angle`, `delta_rod` rather than
`rod_tilt`, so no two families ever fight over a name and the family is
readable in the call.

*Alternative rejected:* the name `solid_node.kinematics`. It would shadow,
in every reader's head, the project-local `kinematics.py` this package is
meant to shrink, and the `kinematics` OpenSpec capability already means
operations, poses and the expression contract.

### D2 — Every law is a composition; nothing new reaches the parity corpus

Each function is written over `solid_node.math` and arithmetic and has
exactly one definition. It therefore has the numeric and symbolic faces for
free, and the symbolic string it builds contains only calls the parity
fixture already pins. The `mechanisms` spec makes that a requirement, so a
future law that wanted a new builtin would have to go through
`solid_node.math` first, where the corpus rule lives.

### D3 — No declared face, and the spec says so

`meshed_angle` contains `+ 180`; `screw_travel` contains `/ 360`. In the
dimension algebra a plain number is dimensionless and `Angle` is its own
axis, so `line + 180` over a declared `Angle` raises, and `lead * angle /
360` over a declared `Length` and `Angle` would type as length-times-angle.
The `expression-math` cycle hit exactly this with its `bump` and chose a
trig-free shape; a mechanism law cannot choose away its degree literals.

So the package promises two faces and states the third is refused: a
declared token reaching a law raises the algebra's own dimension error at
class definition, which is loud and early. A class body that wants a static
mesh phase computes it over `.value` operands, the algebra's documented
escape hatch. One scenario pins both halves.

*Alternative rejected:* an `Angle`-typed literal in the algebra (a way to
spell "180 degrees" as a dimensioned constant). That is a real gap in
ADR-062 and would give every law and `bump` a proper third face, but it is
an algebra change with its own consequences and belongs to its own cycle.
Recorded as an open question.

### D4 — The mesh law takes reference angles, not gear objects

Gearbox's `conjugate_angle` and the clocks' `pinion_angle_for_wheel` are the
same law with two different answers to "where does a tooth sit at zero":
cq_gears centres a tooth on +X, so a gap centre sits at `180 / z`; MrBunsy's
`Gear.get2D` starts at a gap, so a gap centre sits at `gap_angle / 2` and a
tooth tip at `gap_angle + tooth_angle / 2`, negated for a flipped part, and
zero for a lantern pinion. The framework function takes `driver_gap` and
`driven_tooth` as plain angles and reads no object, so each library's
convention is two lines in the caller and the law is one function.

The references are asymmetric on purpose: what defines a mesh is a tooth of
the driven pointing into a gap of the driver along the line of centres, so
the driver is described by a gap and the driven by a tooth. `driving_angle`
is the algebraic inverse, needed for walking a clock train backward from the
escape wheel, which is the end the escapement fixes.

*Alternative rejected:* an internal-gear flag. No project has an internal
mesh; adding the sign flip without a caller would ship an untested branch.

### D5 — The screw is right-hand and sign-neutral

`screw_travel` returns the screw's advance relative to its nut for a
right-hand thread turned positively about its own axis. That is the one
convention that follows from the right-hand rule alone. The three
originating copies each carried a different sign because each machine's
lever or handedness inverts somewhere; that inversion is the machine's
design, and it stays in the caller as a minus sign, where it can be read
beside the reason for it. `lead`, not `pitch`, so a multi-start thread is
stated rather than assumed.

### D6 — The crank is planar, in the crank's own plane

The v8-engine's functions are written for a crank about +X with the pin at
+Z at zero, plus that engine's bank offset and throw phases folded into a
`time`-taking wrapper layer. The framework keeps the plane and drops the
engine: `(across, along)` coordinates with the crank axis as the plane
normal, the crank angle from the cylinder axis, zero at top dead centre.
v8's frame is this plane with `across = y`, `along = z`, and its
`pin_center_at`, `rod_angle_at` and `piston_height_at` are the three
functions verbatim. A caller in any other frame maps with its own rotation.

The rod angle keeps v8's sign, negative of the arcsine, so that a rod
authored along the cylinder axis and turned by the returned angle in the
same rotational sense puts its small end exactly on the axis. The spec pins
that identity rather than the sign, so the test says what the sign is for.

### D7 — The delta returns two posing rotations, and says why

`delta_rod` returns `(tilt, azimuth)`, and its docstring records the
framework finding kossel made: a `Rotation`'s axis is a constant, it cannot
carry a driver symbol, so a rod's lean toward a moving effector is two
rotations about constant axes, minus the tilt about Y then the azimuth
about Z, rather than one rotation about the computed perpendicular. The
posing recipe works for a rod authored along Z with either joint at the
origin, which the spec pins with a vector identity. `delta_carriage` is
separate because the tower's carriage is a different node from the rod and
reads only the height.

`radius` is kossel's `delta_radius`, the horizontal distance from effector
joint to carriage joint at the home position, stated as such because the
three radii a delta has (tower, carriage joint, effector joint) are where
every delta's conventions go wrong.

### D8 — Linkage geometry is three small functions with a side argument

`circle_intersection` generalises the grasshopper's `nib_position`, which
intersected a circle about the origin with a circle about the pivot; the
general form takes both centres and a `side` of +1 for the left of the
direction from the first centre to the second. The grasshopper's call is
`circle_intersection((0, 0), radius, pivot, arm, branch)`, verified to the
digit. `triangle_angle` is the law of cosines Inmoov's elbow writes out;
`link_rise` is the `sqrt(L^2 - d^2)` the kossel, the openflexure stage and
Inmoov's flexed reach all write. All three are numeric-only in their origins
and become symbolic-safe here.

No numeric guard against unreachable configurations: `sqrt` of a negative
raises numerically and evaluates to NaN symbolically, exactly as the origins
behave and as `solid_node.math` behaves. A guard would have to choose a
lie (clamp? zero?) for a pose that does not exist.

### D9 — Validation is by the originating project's own function

Framework tests pin the numbers in the spec and the identities (mesh
reference pose, inverse round trip, small end on axis, posed rod meets both
joints, numeric equals symbolic). Beyond that, each law is checked against
the function it was lifted from, in that project's own worktree, as
evidence recorded in the report and left uncommitted: gearbox's
`conjugate_angle` over a sweep, wall_clock_01's two depthing functions with
the MrBunsy references, v8's three crank functions, kossel's three delta
functions, the grasshopper's `nib_position`, openflexure's `column_travel`
as the negated screw. Projects are not importable from the framework suite,
so this is caller evidence, not a framework test.

### D10 — An ADR after implementation

That the framework carries mechanism laws at all, as compositions over the
expression math with reference-angle seams and no declared face, is a
consequential interface decision. Per the shop's framework-change
discipline the ADR is extracted after implementation confirms the design,
under `docs/adrs/MATH/`, and `docs/architecture.md` gains a subsection and
a map row.

## Risks / Trade-offs

- **A caller misreads a convention** → every docstring states frame, zero
  and sign and maps to a project; the spec pins identities, not just
  numbers, so a sign error fails a test that says what the sign is for.
- **No declared face surprises a class-body author** → refused loudly at
  class definition by the algebra's own error, and documented with the
  `.value` recipe. Fixing it properly is the open question below.
- **Name collisions as families grow** → family-prefixed names from the
  start; the spec requires uniqueness across families.
- **`solid_node.math` evolves under this package** → the package imports
  only names present at the base; when `expression-math` integrates,
  nothing here changes.
- **Two standalone cycles from one base** → whichever integrates second
  will find `main` moved from its recorded base and must stop and report
  per the framework-change skill; the files touched are disjoint, so the
  pilot's resolution is a rebase, not a merge.

## Migration Plan

None required. The package is new; nothing existing changes.

## Open Questions

1. An `Angle`-typed literal in the dimension algebra, so `line + 180` can be
   spelled in a class body. It would give these laws and `expression-math`'s
   `bump` a real third face. Its own cycle, if the pilot wants it.
2. Whether the openflexure legs' four-bar decomposition (`leg_lean` and
   `lever_rise`) is a law worth carrying once a second flexure stage
   appears.
