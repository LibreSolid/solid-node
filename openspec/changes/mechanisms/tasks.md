## 1. Red first: the failing tests

- [ ] 1.1 Create `tests/test_mechanisms.py` importing every flat name from
  `solid_node.mechanisms`; prove it red on the missing package.
- [ ] 1.2 Gear tests: the reference-pose identity (`driver_angle = line -
  driver_gap` gives `line + 180 - driven_tooth`), the counter-rotation ratio
  (60 driving 8 gives -7.5 per driver degree), the cq_gears values
  (`meshed_angle(0, 12, 24, 0, 15, 0) == 172.5`, `meshed_angle(30, 12, 24,
  45, 15, 0) == 225`), `meshed_angle(10, 60, 8, 30, 3, 22.5) == 315` and
  its `driving_angle` round trip.
- [ ] 1.3 Screw tests: `screw_travel(360, 2.0) == 2.0`, `screw_angle(1.0,
  2.0) == 180`, and the inverse identity over a sweep.
- [ ] 1.4 Crank tests: the dead-centre values for radius 15 and rod 60, and
  the small-end-on-axis identity over a sweep of angles (rotate a rod
  authored along the cylinder axis by `crank_rod_angle`, add `crank_pin`,
  assert across is zero and along equals `piston_height`).
- [ ] 1.5 Delta tests: the three effector positions from the spec for rod
  215, radius 100, tower 0, and the posed-rod identity (a -Z unit vector
  rotated by `-tilt` about Y then `azimuth` about Z, scaled by the rod,
  equals the carriage-to-effector vector) over several effector positions
  and tower angles.
- [ ] 1.6 Linkage tests: `circle_intersection((0, 0), 5, (8, 0), 5, ±1)`,
  `circle_intersection((1, 1), 5, (1, 9), 5, 1) == (-2, 5)`, the grasshopper
  nib value `circle_intersection((0, 0), 45, (30, 40), 20, 1)`,
  `triangle_angle(5, 3, 4) == 90`, `triangle_angle(3, 4, 5)`, and
  `link_rise(5, 3) == 4`.
- [ ] 1.7 Symbolic-face tests: every exported law called with a symbolic
  `$t` or driver token in its driving argument returns an `OpenSCADConstant`
  whose string contains only names `solid_node.math` already emits (check
  against the set of builtins the base module's `_symbolic_call` sites use)
  and arithmetic, and nothing raises.
- [ ] 1.8 Agreement test: for every law, evaluate the symbolic string at
  sampled inputs with the existing `_eval_openscad_expr` helper from
  `tests/test_math.py` (import or lift it) and compare with the numeric
  face.
- [ ] 1.9 Declared-face refusal test: a class body computing
  `meshed_angle(theta, 12, 24)` over a declared `Angle` raises a dimension
  error at class definition, and the same over `theta.value` succeeds.

## 2. The package

- [ ] 2.1 Create `solid_node/mechanisms/__init__.py` with a package
  docstring stating what a mechanism law is here (a composition over
  `solid_node.math`, two faces, conventions in each family module, no
  declared face and why) and eager flat re-exports with `__all__`.
- [ ] 2.2 `gears.py`: `meshed_angle` and `driving_angle`, module docstring
  stating the frame, the reference-angle seam, and the cq_gears and
  MrBunsy recipes (including flipped parts and lantern pinions).
- [ ] 2.3 `screws.py`: `screw_travel` and `screw_angle`, docstring stating
  the right-hand convention, that `lead` is per turn, and that handedness
  and nut-versus-screw are the caller's sign.
- [ ] 2.4 `cranks.py`: `crank_pin`, `crank_rod_angle`, `piston_height`,
  docstring stating the `(across, along)` plane, zero at top dead centre,
  the rod-angle sign's purpose, and the v8-engine mapping.
- [ ] 2.5 `deltas.py`: `delta_carriage` and `delta_rod`, docstring stating
  what `radius` is, the posing recipe, and why two constant-axis rotations
  are returned.
- [ ] 2.6 `linkages.py`: `circle_intersection`, `triangle_angle`,
  `link_rise`, docstring stating the side convention and that unreachable
  configurations are not guarded.
- [ ] 2.7 Confirm the package imports only `sin`, `cos`, `asin`, `acos`,
  `atan2` and `sqrt` from `solid_node.math` and nothing from the
  `expression-math` change; confirm `tests/test_node_lazy_exports.py` and
  `tests/test_cli_lazy_imports.py` still pass (the package must not be
  imported by anything at startup).
- [ ] 2.8 Run `tests/test_mechanisms.py` green, then the full framework
  suite.

## 3. Caller evidence (each in its own repository, uncommitted)

- [ ] 3.1 gearbox: assert `conjugate_angle(theta, z1, z2, alpha)` equals
  `meshed_angle(theta, z1, z2, alpha, 180 / z1, 0)` over a sweep, and run
  the project's tests. The comparison passed over 900 cases at a worst
  difference of 2.27e-13, but the project's own tests could not be run:
  `cq_gears` is absent from the workspace venv, so `solid test` fails at
  import. Left unticked for that half.
- [ ] 3.2 wall_clock_01: assert `pinion_angle_for_wheel` and
  `wheel_angle_for_pinion` equal `meshed_angle` and `driving_angle` with
  `driver_gap = gap_centre_angle(wheel, flipped)` and `driven_tooth =
  tooth_tip_angle(pinion, flipped)` over that clock's actual train, and run
  its tests.
- [ ] 3.3 v8-engine: assert `pin_center_at`, `rod_angle_at` and
  `piston_height_at` equal `crank_pin`, `crank_rod_angle` and
  `piston_height` over a sweep, and run the project's tests.
- [ ] 3.4 kossel: assert `carriage_height`, `rod_tilt` and `rod_azimuth`
  equal `delta_carriage` and `delta_rod` over a sweep of effector
  positions and the three towers, and run the project's tests.
- [ ] 3.5 wall_clock_53_grasshopper: assert `nib_position(pivot, arm,
  branch, radius)` equals `circle_intersection((0, 0), radius, pivot, arm,
  branch)` for that clock's pivots.
- [ ] 3.6 openflexure: assert `column_travel(steps)` equals
  `-screw_travel(motor_angle(steps) / GEAR_RATIO, SCREW_PITCH)` for that
  machine's gearing -- the motor turns `GEAR_RATIO` times as fast as the
  screw, so the ratio belongs in the identity -- and Inmoov's
  `elbow_reach` against `screw_travel` with
  `PISTON_LEAD`.
- [ ] 3.7 Record every comparison's result and the project test outcomes in
  the report; revert nothing that is evidence, commit nothing.

## 4. Documentation

- [ ] 4.1 Add a "Mechanisms" section to `docs/api-reference.rst` listing
  each family, its functions and conventions, and the no-declared-face rule
  with the `.value` recipe.
- [ ] 4.2 Mention the package in `docs/animation.rst` beside the
  `solid_node.math` guidance, with the delta two-rotation finding as the
  worked reason.
- [ ] 4.3 Changelog entry under `Unreleased` in `docs/changelog.rst`, house
  style: bold lead, the originating projects, the OpenSpec change name.

## 5. Records (after implementation confirms the design)

- [ ] 5.1 Extract an ADR under `docs/adrs/MATH/` recording that mechanism
  laws live in the framework as compositions over expression math with
  reference-angle seams and no declared face; add it to the ADR index.
- [ ] 5.2 Add a "Mechanisms" subsection and a map row to
  `docs/architecture.md`.
- [ ] 5.3 Sync the baseline specs from the delta and archive the change.
- [ ] 5.4 Report to the pilot the two open questions in `design.md`.
