# Release roadmap — 0.7, 0.8, 0.9

Provisional, 2026-09-10. Working record, not a promise: nothing here is
ratified, and an OpenSpec spec or an accepted ADR outranks it. Version
numbers are the pilot's stated intent for the shape of each release, not a
schedule.

Where things stand: 0.6.0 is the released version, on PyPI since
1 September 2026. `main` is 28 commits ahead of its remote and unpushed, and
already carries most of what 0.7 is meant to be.

## 0.7 — the declarative and motion API

The release that lets a model say what it *is* instead of computing it.

Already on `main`:

- the declarative node API — children, parameters and drivers declared as
  class statements;
- node-scoped currency (ADR-071), the declared time base (ADR-072), finite
  tick-aligned simulation time (ADR-083);
- the motion layer: `solid_node.motion.ports`, `.joints`, `.couplings` —
  one module one question (ADR-087), a joint owning one coordinate
  (ADR-088), `drives` relating two coordinates with a `law=` (ADR-089);
- composed joints: composition in declaration order (ADR-093), the orbit
  joint (ADR-094), the free joint.

Still open before it is a release: the catalogue's deferred projects
(`docs/motion-general-refactor.md`), the open gaps recorded in
`workflow/warts.md`, and a push.

## 0.8 — production

The release that knows how a part is *made*. Process and material stop being
something a maker holds in their head and become something the model
declares: printed in this material at this layer height, turned from this
bar, cut from this sheet.

Mass arrives from here, and that ordering is deliberate. Density is not a
number to be typed onto a solid — it is a consequence of knowing how the
part is produced. A framework that knows the process knows the material,
knows the density, and can compute mass and inertia from geometry it already
has exactly. It also makes the BOM real, and lets
`assertAssemblySupported` stop assuming unit density (ADR-048/049).

## 0.9 — dynamics

The release that asks what the machine *does*, once 0.8 has made mass real.

The direction assessed on 2026-09-10, alongside the earlier MuJoCo research
in `mujoco-viability.md`:

- **The integration shape is a producer of driver values,** not a physics
  backend. An external engine simulates, and its result becomes the driver
  snapshot; geometry stays a pure function of that snapshot, and every
  existing assertion keeps working unchanged on the poses dynamics produced.
  This is ADR-056's item 3 — "sampled traces from numeric solving slot in
  without touching consumers".
- **`law=` is not the hook.** A law is a memoryless map evaluated at an
  instant, and the values it carries are often symbolic solid2 expressions.
  Dynamics has state, is solved globally rather than one unknown at a time
  per assembly, and produces numbers. Stepping a stateful engine inside
  `forward()` would reintroduce the rewind/replay disease ADR-027 removed.
- **What the motion layer did buy** is the topology, for free: declared
  ports carry a physical domain and are readable off the class, relations
  record what drives what, and `Affine` records the ratio. That is emittable
  to `Modelica.Mechanics.Rotational` (`Inertia`, `IdealGear`, `connect`) or
  to a `MjSpec` almost directly. A non-affine `law=` — an escapement — has
  no constraint form and would still be authored on the engine's side.
- **Two engines, two questions.** Contact-rich rigid body — gait, pose
  stability, tooth on pallet — is MuJoCo, with the caveat measured in
  `mujoco-viability.md` that convex hulls make tooth flanks unsound.
  Lumped multi-domain — motor, gearbox, belt compliance, control, losses,
  torque budgets — is Modelica, which has no collision detection at all.
  The clocks want both, for different halves of themselves.
- **Dependency shape.** MuJoCo is Apache-2.0 and a 20 MB wheel. Modelica's
  standard library is BSD-3 but OpenModelica is a gigabyte-class compiler
  under OSMC-PL, so the clean path is consuming FMUs (FMPy, BSD-2) and
  leaving compilation to the pilot's own toolchain. Either way an optional
  extra, on the `viewer` / `web-snapshot` precedent (ADR-046), never a core
  dependency.
- **Never let an engine decide a geometric assertion.** A trajectory verdict
  depends on solver settings and timestep; reporting it as a pass reports on
  the solver, not on the machine.

Where it pays off first, from the projects that exist: the clocks (does the
weight actually run the train, what amplitude does the pendulum settle at),
the printers (belt compliance, back-drivability, stepper torque margin), and
the legged robots (per-joint servo torque budget).

## Why the order

Each release is the prerequisite of the next. Motion gave the topology but
carries no flow variable, so it cannot state a torque balance. Production
gives the material, and therefore mass and inertia, without which a dynamics
verdict is meaningless — the finding already recorded in
`../archive/motion-layer-2026-09-09/roadmap.md`. Only then is an engine worth
attaching.
