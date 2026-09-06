## Why

Thirteen mechanical projects in this workspace carry a `kinematics.py`, and
beneath the arithmetic each one rebuilds (the subject of the parallel
`expression-math` change) sit a handful of textbook mechanism laws written
again and again, each in that project's own frame and sign convention, some
of them numeric-only and therefore broken the moment a symbolic driver
reaches them:

- **The spur-gear mesh law**, four times: `conjugate_angle` in
  `projects/sandbox/gearbox/root/kinematics.py` over cq_gears' conventions,
  and `pinion_angle_for_wheel` / `wheel_angle_for_pinion` in
  `projects/3DPrintedClocks/design/wall_clock_01`, `wall_clock_02` and
  `mantel_clock_34_steampunk/kinematics.py` over the MrBunsy `Gear` object's.
  They are one law, `driven = line + 180 - ref_driven - (z1 / z2) *
  (ref_driver + driver - line)`, differing only in where each library says a
  tooth or a gap sits at zero.
- **The lead screw**, three times: `elbow_reach` in
  `projects/Inmoov-sim/Inmoov_sim/kinematics.py`, `column_travel` and
  `screw_angle` in
  `projects/openflexure-microscope/simulation/microscope/kinematics.py`, and
  `angle` in `projects/snappy-reprap/simulation/z_screw.py`, each
  `lead * angle / 360` with its own sign.
- **Circle geometry**, three shapes: `nib_position` in
  `projects/3DPrintedClocks/design/wall_clock_53_grasshopper/kinematics.py`
  (a circle-circle intersection with a side), the elbow's law of cosines in
  Inmoov, and the `sqrt(L^2 - d^2)` rise of a rigid link in the openflexure
  stage, the kossel and Inmoov's flexed elbow reach.
- **The slider-crank**, in `projects/v8-engine/v8_engine/kinematics.py`
  (`pin_center_at`, `rod_angle_at`, `piston_height_at`), textbook and tied
  to that engine's bank frame.
- **Delta kinematics**, in `projects/kossel/simulation/kinematics.py`
  (`carriage_height`, `rod_tilt`, `rod_azimuth`), including a finding about
  this framework specifically: a rod is posed by two constant-axis rotations
  because a rotation axis cannot carry a driver symbol.

Every one of these is a law, not a design decision, and every project that
writes one has to rediscover its sign convention against a rendered mesh.
The museum of printers the shop is about to simulate (deltas, corexy,
i3-style) will write the delta and the screw again unless the framework
carries them.

## What Changes

- A new package `solid_node.mechanisms`, one module per mechanism family,
  re-exporting a flat set of names unique across families:
  - gears: `meshed_angle`, `driving_angle` — the external spur-gear mesh law
    and its inverse, with the tooth-reference angles as arguments so any
    gear library's convention is a pair of values, not a fork of the law.
  - screws: `screw_travel`, `screw_angle` — lead-screw travel from angle and
    angle from travel, right-hand thread, sign-neutral.
  - cranks: `crank_pin`, `crank_rod_angle`, `piston_height` — the planar
    slider-crank in the crank's own plane.
  - deltas: `delta_carriage`, `delta_rod` — carriage height, and the two
    posing rotations of a diagonal rod, for a linear delta.
  - linkages: `circle_intersection`, `triangle_angle`, `link_rise` — the
    circle-circle intersection with a side, the law of cosines, and the
    rise of a rigid link over a horizontal offset.
- Every function is a composition over `solid_node.math`'s existing
  functions and ordinary arithmetic, so it computes on numbers and builds
  the viewer's expression on symbolic time and drivers. No new OpenSCAD
  builtin is emitted, so the ADR-022 parity corpus needs no extension.
- Each function's docstring states its frame, zero and sign convention and
  maps it onto the originating project it was lifted from.
- Documentation: a "Mechanisms" section in the API reference, a mention in
  the animation guide, a changelog entry, an architecture-map row.

Deliberately **not** included, each recorded in `design.md`: a declared
(class-body) face for these laws, internal and bevel gear meshes, the
four-bar decomposition of the openflexure legs, the kossel rod's own spin,
belt wraps (molejo's territory), escapements (repeated only inside one
project), and the demo-timeline slicing (one line once `expression-math`
lands).

No existing behaviour changes: nothing is removed or renamed, and the
package depends only on `solid_node.math` names that exist at this change's
base, so it is independent of the parallel `expression-math` cycle.

## Capabilities

### New Capabilities

- `mechanisms`: the mechanism laws the framework carries, their
  conventions, their faces, and how they are validated against the
  projects that originated them.

### Modified Capabilities

None. The `kinematics` capability's expression-math contract is unchanged:
this package emits nothing that contract does not already cover.

## Impact

- `solid_node/mechanisms/__init__.py`, `gears.py`, `screws.py`,
  `cranks.py`, `deltas.py`, `linkages.py` — new.
- `tests/test_mechanisms.py` — red-first coverage: pinned numbers per law,
  the mesh identities, the inverse round trips, symbolic-face string tests,
  numeric/symbolic agreement, and the declared-face refusal.
- `docs/api-reference.rst`, `docs/animation.rst`, `docs/changelog.rst`,
  `docs/architecture.md`.
- An ADR recording that mechanism laws live in the framework as compositions
  over expression math with reference-angle seams, extracted after
  implementation confirms the design.
- Callers, as evidence only and in their own repositories: gearbox and
  wall_clock_01 for the mesh, openflexure and Inmoov for the screw and the
  circle geometry, v8-engine for the crank, kossel for the delta,
  wall_clock_53_grasshopper for the intersection. No project commit belongs
  to this change.
- `solid-node-viewer` is not touched.
