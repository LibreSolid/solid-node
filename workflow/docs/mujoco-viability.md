# Is MuJoCo viable inside solid-node?

An assessment, 2026-09-06. Measured against solid-node main at
`solid-node/`, MuJoCo 3.12.0, and real parts from six projects in
`projects/`. Nothing was changed in any repository; the spike ran in a
throwaway venv in the session scratchpad.

## Verdict

**Viable, but not as a physics backend for what solid-node currently
promises, and not yet.** MuJoCo cannot answer any question solid-node's
assertions ask, because its collision geometry is convex and a real CAD
part is not — measured below. It can answer a question solid-node does
not ask at all today: *what does this machine do when nobody poses it*.

The one integration shape that survives the evidence is narrow and
attractive: MuJoCo as a **producer of driver values** for the existing
`Sim` loop, behind an optional extra, over a joint layer the framework
does not have yet. Geometry stays a pure function of the driver snapshot,
which is ADR-056's guardrail, and MuJoCo just becomes another way to
decide what the snapshot contains — beside a `RampProgram` and an
`Instruction`.

Three things must exist before that is worth building, and only one of
them is about MuJoCo.

## What MuJoCo would add

solid-node today simulates *kinematically*. A driver holds a number, the
author writes `simulate()` as arithmetic over that number, and geometry
follows. `mechanisms/` is a library of forward-kinematic laws for exactly
this: `piston_height`, `delta_carriage`, `meshed_angle`. The machine goes
where the author says it goes.

Nothing in the framework knows about mass, force, momentum, or contact
response. `assertAssemblySupported` is the sole physical claim, and it is
deliberately a *statics* claim: an LP feasibility problem over frictionless
unilateral contacts (ADR-049), with friction, adhesion and dynamics named
as exclusions and "friction, adhesion and dynamics" sitting on the public
roadmap.

MuJoCo would bring, in one dependency: forward dynamics with contact and
friction, actuators with real limits, closed kinematic loops through
equality constraints (`connect`, `weld`, `joint`, `tendon` — the last two
are exactly gear ratios and belts), and an integrator fast enough that a
whole machine steps in microseconds. Measured here: 1000 steps of a
one-body model in 2 ms.

That is a genuinely different class of question. "Does the escapement
actually escape at this depthing." "Does the delta effector overshoot."
"Does the carriage back-drive the leadscrew." "Does the hexapod fall over
mid-gait." None of those is expressible today.

## The four obstacles

### 1. Collision geometry is convex, and CAD parts are not

MuJoCo replaces every non-convex mesh with its convex hull (qhull) for
collision. Over 48 randomly sampled built parts from kossel, openvmp,
v8-engine, Prusa3-vanilla, fender-bender and 3DPrintedClocks:

    median hull volume / part volume = 2.25x
    mean = 3.71x
    34 of 48 parts inflate by more than 1.5x

The worst are the parts that matter most: a filament loop at 23.2x, a
Bowden tube at 21.5x, a clock arbor at 11.3x, a valve spring at 7.6x, a
belt at 6.4x.

Concretely, on kossel's effector: **31.6% of its convex hull is void the
hull calls solid**, and a 1 mm probe sphere placed at a point measured
5.95 mm clear of any material is reported by MuJoCo as **2.39 mm
penetrated**.

This is ADR-049's rejection restated with numbers, and it still holds.
Every hole, pocket, tooth flank and printed clearance disappears. No
assertion solid-node makes today could be re-decided by MuJoCo, and any
assembly whose parts nest inside one another — which is most of them —
explodes on the first step.

Convex decomposition (CoACD, VHACD) is the standard escape, but it is
approximate at roughly the scale of a printed clearance, it is slow, and
it turns one authored part into dozens of collision geoms. It does not
recover the sub-millimetre fits that the exact-kernel work of 0.5 and 0.6
was built to answer.

### 2. There is no joint topology to export

This is the deeper obstacle, and it has nothing to do with meshes.

A MuJoCo model is a tree of *bodies connected by joints* with declared
degrees of freedom. A solid-node model is a tree of nodes each carrying
an ordered chain of `Rotation` and `Translation` operations, composed into
one world matrix per node (ADR-028). The chain is written by hand inside
`simulate()` as arithmetic over drivers. A revolute joint is not declared
anywhere — it is an emergent property of the author having written
`self.rotate(self.angle, [0, 0, 1])` after a particular translation.

There is no way to read a DOF, its axis, its anchor, its limits or its
parent body off a solid-node tree, so there is nothing to compile into an
MJCF kinematic tree. `Port` comes closest — a typed connection point —
but its docstring is explicit that it is kinematic-only and carries no
flow variable by design.

An exporter would therefore have to *infer* joints from transform chains,
which is guesswork, or the framework would have to grow a declared joint
(a `Revolute`, a `Prismatic`, with axis, anchor and limits) that the
author writes instead of the transform. That is a first-class API change
of the same size as drivers were in 0.6, and it belongs in the declarative
API work, not bolted onto an exporter.

### 3. There is no mass anywhere

`grep` finds no density, material or mass declaration in the node layer.
`assertAssemblySupported` deliberately works in "unit density under unit
gravity, so weight IS volume", precisely so no density constant ever has
to be named.

Dynamics needs real masses and inertias, so a material or density
declaration is a prerequisite. MuJoCo will compute inertia from the mesh —
and `inertia="exact"` does it correctly on the real parts, which matters:
on the v8 con rod the default convex inertia gives 13.0 g against the true
4.4 g, a 2.95x error that tracks the hull inflation exactly. So the
framework need only supply density; but it must supply density.

### 4. The verdict changes character

Every solid-node assertion is exact, reproducible bit-for-bit, and names
the offending part in the model's own vocabulary. ADR-050 and the
integer-tick design of `Sim` exist so two runs of one scenario compare
with `==`.

A dynamics verdict is a trajectory. It depends on timestep, solver
iterations, contact softness (`solref`/`solimp`) and the hull
approximation, and it answers "did it fall over within 3 seconds by more
than 5 mm", which needs thresholds nobody can derive from the design.
ADR-048 rejected a physics engine partly on this: "a nondeterministic
verdict that depends on solver settings and timestep, and diagnostics that
cannot name the offending part".

That argument does *not* forbid MuJoCo. It forbids MuJoCo deciding
assertions. Dynamics as **evidence a maker looks at** — a trajectory to
watch in the viewer, a driver trace to inspect — sidesteps it entirely.

## What already works, measured

The mechanical parts of an integration are cheap, which is worth saying
plainly:

- MuJoCo 3.12.0 is **Apache-2.0**, the same licence as solid-node. No
  repeat of the AGPL viewer split.
- The Linux wheel is 19.8 MB and installs against Python 3.12 with only
  numpy, glfw, PyOpenGL, absl-py and etils. It is an optional-extra-sized
  dependency, exactly like `viewer` and `web-snapshot` (ADR-046 is the
  precedent).
- **Project STLs load unmodified.** kossel's effector (9 444 faces) and
  the v8 con rod (23 832 faces) compile in 16 ms and 112 ms respectively,
  with correct exact-mesh inertia.
- `mujoco.MjSpec` builds and edits a model programmatically from Python
  and recompiles it, so no XML file needs to be written or parsed. That is
  the right seam for a builder that already holds a node tree in memory.
- Units are a non-issue with care: MuJoCo is unit-agnostic, so a
  millimetre model works with `gravity="0 0 -9810"` and density in
  t/mm³ (1.24e-6 for PLA). The spike used exactly that.

## Where it would pay off

Ranked by how much the current projects want it:

1. **3DPrintedClocks** — an escapement is a dynamics problem wearing a
   kinematics costume. The measured escapement phase in
   `mantel_clock_34_steampunk` and `wall_clock_02` is authored, not
   derived. Whether the pallet actually receives impulse is not a question
   the framework can ask. This is the strongest case — and also the one
   most damaged by hull collision, since the tooth flank *is* the contact.
2. **hexapod_spiderbot_model, openvmp** — gait and pose stability. Legged
   robots are what MuJoCo was built for, and here the poses are already
   the recorded design finding ("the foot fouls the thigh's knee motor
   past 45°").
3. **kossel, hangprinter, Metamaquina2** — back-drivability, belt tension,
   overshoot. MuJoCo tendons model belts and cables natively, which is
   also where molejo's flexible parts already have a story.
4. **fender-bender** — the snap-fit release path. MuJoCo is the *wrong*
   tool here: a snap fit is elastic deformation of a non-convex feature,
   and both halves of that are outside rigid convex dynamics.

## Recommendation

Not now, and not as a framework dependency. In this order:

1. **Declared joints first.** A `Revolute`/`Prismatic` declaration with
   axis, anchor and limits, replacing hand-written transform chains where
   an author means a joint. This pays for itself with no physics engine at
   all — it is what would let the viewer show a DOF, what would let
   `assertBlockedBeyond` find its own axis, and what makes `mechanisms/`
   a library of laws over declared joints rather than over bare numbers.
   Its natural home is the declarative API cycle, and ADR-056's
   bond-graph note is the design context.
2. **Density on a part.** Small, independently useful (a BOM wants mass
   anyway), and it lets `assertAssemblySupported` stop assuming unit
   density.
3. **Then, and only then, an optional `mujoco` extra with one job:** an
   exporter from a declared-joint tree to `MjSpec`, and a `Program`
   implementation that steps MuJoCo and hands the resulting `qpos` to the
   existing driver states as their values. Dynamics produces the snapshot;
   geometry stays a pure function of it; every existing assertion keeps
   working, unchanged, on the poses dynamics produced.
4. **Never** let MuJoCo decide a geometric assertion. Hull collision makes
   that unsound, and the measurements above are the reason.

The honest short answer for a pilot deciding today: MuJoCo is the right
engine and the wrong moment. The blocker is not MuJoCo, it is that
solid-node has no joints.
