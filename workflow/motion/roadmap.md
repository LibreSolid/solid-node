# Motion layer: roadmap and progress

The declarative mechanics layer of solid-node: joints that place a body,
ports that carry a value, and `a.drives(b)` between coordinates. This
folder is the durable record of that work, independent of any conversation.

- `joints-and-couplings.md` is the design: the decision, the three concepts,
  the module layout, what it does to wall clock 01 and to Thor, the
  framework surface it touches, and what is deliberately out.
- `mechanics-ontology.md` is the coverage survey that preceded it: which
  kinds of motion the local project catalogue contains. Its class catalogue
  was set aside on 2026-09-09; it stays as evidence and as a checklist the
  primitive must eventually satisfy.
- `../docs/mujoco-viability.md` is the 2026-09-06 research on exporting a
  solid-node tree to MuJoCo. It is cited by the design as a fit check and is
  kept for the future discussion, not for a cycle here.

Design authority is the pilot. Nothing in this folder is ratified until the
OpenSpec change for its cycle is, and nothing is public API until a release
says so.

## Cycles

Three stacked framework cycles, each under the shop's `framework-change`
procedure in its own worktree at `solid-node/WTs/<name>/`, each branching
from the previous one's integrated head. Originating projects are named in
each so the requirement keeps its empirical context.

| # | Cycle | Depends on | Originating projects | Validated on |
|---|---|---|---|---|
| 1 | `motion-package` | none | every project importing ports or `Time` | the framework suite; one migrated project |
| 2 | `joints` | 1 | Thor (`placing.py`), AlbertPro, clock 01 bearings | Thor |
| 3 | `couplings` | 2 | clock 01 (`arbor_angles`), Thor rings and belts | wall clock 01 |

### 1. `motion-package`

Ports and `Time` move out of `solid_node.node` into a new package
`solid_node.motion`, laid out by kind:

- `solid_node.motion.ports`: `Port`, `RotationalPort`, `TranslationalPort`,
  `SignalPort`, `Time`, `bind`, `connect`.
- `solid_node.motion.joints` and `solid_node.motion.couplings`: created
  empty here, filled by cycles 2 and 3.

`solid_node.node` stops exporting the moved names. This is a breaking
change on purpose: no re-export and no deprecation shim. A project fixes
its imports when it upgrades to the release carrying this, and a project
still importing ports from `node` is one that has not migrated to the new
API, which is the hint to refactor it. No behaviour changes; the ports and
declared-time-base specs move with their modules unchanged.

Records: one ADR stating the module rule (each top-level module answers one
question: `parameters` what sizes a design, `node` what has shape, `motion`
what moves and what drives what, `simulation` what the machine is told,
`mechanisms` the arithmetic of laws, `math` the algebra) and recording the
deliberate break. Baseline specs: paths updated, requirements unchanged.

Acceptance: the framework suite passes with the old import paths absent;
one project migrated as proof of the path fix; the changelog names the
break.

### 2. `joints`

`Revolute` and `Prismatic` in `solid_node.motion.joints`. A joint is
declared on the node it moves, with `axis`, `at` and `range` stated in the
parent's frame and a `unit`. A joint is not a port: it owns one coordinate,
and that coordinate is a port, so binding the joint binds its coordinate,
the coordinate can be passed to children as a token, and a root `Driver` is
what an independent joint reads. Binding places the body about the axis and
anchor on top of the rest placement the project's `render()` already
applies. Joint arguments resolve at realization against the instance, the
way child arguments do, so a bearing position computed from a built
movement is allowed. Axes are tuples; there are no axis constants.

Records: new baseline spec `joints`; ADR for the joint as owner of one
coordinate and for axis and anchor in the parent frame; the ports spec
gains the coordinate-of-a-joint case.

Acceptance: Thor's `placing.py` frame math leaves the project and every
Thor pose and pixel is unchanged; a joint bound outside its range fails by
name; a joint whose arguments cannot resolve fails by name at realization.

### 3. `couplings`

`drives(other, ratio=, offset=, law=)` on every child declaration and every
port, and `Affine` in `solid_node.motion.couplings`. With no keywords the
relation is ratio one, offset zero. `law=` takes a callable that the
framework calls at realization with the two realized ends and that returns
an `Affine` or a non-affine law; the law itself is project code, and the
framework looks up no hook on any class and never learns what a gear is.
Direction is mechanical; at realization the framework inventories which
coordinates are bound, orients each relation from the known side, lowers
affine relations to the expression math the viewer already evaluates, and
refuses by name a coordinate nothing reaches, a coordinate bound twice, and
a non-invertible law needed backwards. A relation may name a declaration by
path so a root driver reaches a deep joint without port forwarding. This
cycle carries the narrow relaxation of the declarative-nodes rule "a
sideways read is refused": reading a port off a declaration yields a path
reference; reading a parameter stays refused.

Records: new baseline spec `couplings`; delta to `declarative-nodes` for the
port read; ADR for the verb, the callable law, and the resolution errors.

Acceptance: clock 01's `arbor_angles`, `motion_works_angles`, `gear_pair`,
`line_of_centres`, the depthing wrappers and the assembly `simulate()`
fan-out leave the project and every clock test and pixel is unchanged;
changing a tooth count propagates to the hands with no other edit and the
six-hour test fails when the twelve-to-one is broken; the three named
failures each fail by name.

## Progress

One row per cycle. A cell holds the date and the commit or change name
that proves it, or stays empty.

| Cycle | Proposed | Ratified | Applied | Integrated into main | Released |
|---|---|---|---|---|---|
| 1 `motion-package` | 2026-09-09 · `motion-package` | | | | |
| 2 `joints` | | | | | |
| 3 `couplings` | | | | | |

Projects migrated to the `solid_node.motion` paths, and to joints and
couplings where they apply. A project is listed when its imports come from
`solid_node.motion` and its suite passes on the release or main commit
named.

| Project | Paths | Joints | Couplings | Evidence |
|---|---|---|---|---|
| 3DPrintedClocks (wall clock 01) | | | | |
| Thor | | | | |
| (others as they migrate) | | | | |

## Future, not scheduled

- **MuJoCo and Modelica emission.** Mechanically simple once cycles 2 and
  3 exist (see the design's fit table and `../docs/mujoco-viability.md`),
  but meaningless without mass and inertia, and a prescribed law such as
  the escapement has no constraint form. The pilot wants this discussed
  before anything is built.
- **Spherical and free joints**, native because a quaternion is not three
  hinges and a floating body has no composition.
- **Named compositions** (screw, cylindrical, universal, planar), when a
  project asks for one.
- **Closed loops** and their solver (the Thor gripper), **stateful
  mechanisms** (ratchets, engagement), mass and density, non-holonomic
  contact, flow variables on ports.

## History

- 2026-09-06: MuJoCo viability research, in the shop.
- 2026-09-08: mechanics ontology proposed (17 submodules, class catalogue).
- 2026-09-09: catalogue set aside; Reuleaux pairs plus `drives` chosen;
  design note written; module layout settled as `motion.ports`,
  `motion.joints`, `motion.couplings`; three cycles planned; this folder
  created and the research moved here.
