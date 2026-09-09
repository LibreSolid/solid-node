## Why

A revolute joint exists in every project in the catalogue and in no line
of the framework. It is, in the words of the 2026-09-06 viability
research, "an emergent property of the author having written
`self.rotate(self.angle, [0, 0, 1])`" — and when the axis does not run
through the moving part's own origin, of the author having written the
frame arithmetic that carries a pivot into that part's frame as well.

Thor is the evidence. `simulation/placing.py` is 150 lines of framework
work living in a project: `rotate_about` (bring the line to the origin,
turn, carry it back), `into_local` (undo a rest placement to state a
parent-frame pivot in the part's own coordinates), `turn_about` (the two
composed), `axis_sign` (which way a mirrored part's own +Z runs). The
elbow axis is 81.5 mm from the forearm's origin and the wrist axis
111.5 mm up the forearm, so none of it is avoidable by choosing better
origins. Every arm in the catalogue has written some subset of it:
AlbertPro, YouCanBuildDog, BCN3D-Moveo, open_manipulator, openarm,
hexapod_spiderbot, openvmp. 3DPrintedClocks writes the degenerate case
instead — `TrainArbor.simulate()` loops over the parts on one arbor and
rotates each about Z, because the framework has no way to say "these
parts are one body turning at this bearing".

The value that moves such a body is already a framework concept: a port
carries it, a `Driver` supplies it, an expression keeps it symbolic
through to the viewer. What is missing is the statement of WHERE the
body may move, next to the body, once — the pair, in Reuleaux's sense,
that MuJoCo writes as a `hinge` with an `axis` and a `pos` and Modelica
as a `Joints.Revolute` between two frames.

Cycle 1 built the home (`solid_node.motion`, with `joints.py` empty).
This is cycle 2 of the three in `workflow/motion/roadmap.md`: the two
one-coordinate lower pairs, `Revolute` and `Prismatic`. Cycle 3 adds the
relations between coordinates (`drives`, `Affine`, derived coordinates,
references by path); it needs a joint to relate, which is why the joint
comes first.

## What Changes

- **`Revolute` and `Prismatic` in `solid_node.motion.joints`**, declared
  as class attributes on the node they move:
  `elbow = Revolute(axis=(0, 0, 1), at=(0, 160, 68), range=(-135, 135),
  unit='deg')` and
  `carriage = Prismatic(axis=(1, 0, 0), range=(0, 200), unit='mm')`.
  `axis` and `at` are stated in the PARENT's frame — the frame the
  parent's `render()` places this node in — which is where both target
  formats put them. Axes are tuples of three numbers or parameter
  tokens; there are no axis constants.
- **A joint owns one coordinate, and that coordinate is a port.** Read
  on an instance, a joint is its bound coordinate: a rotational slot for
  a `Revolute`, a translational one for a `Prismatic`, carrying the
  joint's `unit`. Assigning to a joint binds that coordinate exactly as
  assigning to a port does, from a number, an expression, another port
  or a `Driver` read.
- **Binding the joint moves the body.** The framework composes the
  motion onto the node's rest placement: it carries the parent-frame
  axis and anchor into the node's own frame by inverting the rest
  placement, then applies `translate(-anchor)`, `rotate(angle, axis)`,
  `translate(anchor)` for a `Revolute` and `translate(distance * axis)`
  for a `Prismatic` — the arithmetic Thor's `placing.turn_about` does by
  hand. The operations are ordinary `Rotation`/`Translation` objects
  with a symbolic angle, so the published document and the viewer need
  nothing new (ADR-076).
- **A coordinate may be passed down to a child declaration as a token**:
  `wheel = Arbor(index=index, turn=turn)`, where `turn` is a joint or a
  port declared on the parent and `Arbor` declares a port or joint of
  that name. The framework records the wiring and rebinds the child's
  end from the parent's on every `simulate()`. Such a kwarg is a wiring,
  not a parameter: it does not enter identity, and a kwarg that is
  neither a declared parameter nor a valid wiring stays the `TypeError`
  it is today.
- **A `range` refuses, by name, a numeric binding outside it**
  (`JointRangeError`, naming the node path, the joint, the value and the
  range). A symbolic binding is not checked at bind time; a `Driver`
  bound to a joint keeps its own range, and both apply.
- **Joint arguments resolve at realization against the instance**, the
  way child-declaration arguments do: numbers, parameter tokens, derived
  formulas, or a callable of the realized node for a value that comes
  out of a built library object (clock 01's bearing positions). An
  argument that cannot resolve, an axis that is not three numbers or has
  zero length, or a malformed range fails by name at realization.
- **Hand-written motion still works.** A project may go on turning
  children in `simulate()`; a node may carry both, and both apply. No
  existing model changes behaviour, and nothing is deprecated here.
- One ADR (`docs/adrs/NODE/ADR-088`) records the joint as the owner of
  one coordinate, the parent-frame statement of axis and anchor, the
  composition onto rest placement by inversion, and the downward wiring
  by token. `docs/architecture.md` and the changelog follow.

## Capabilities

### New Capabilities

- `joints`: the one-coordinate lower pairs. What a joint declaration
  carries and where its axis and anchor are stated; that it owns one
  coordinate which is a port; that binding the coordinate places the
  body about that axis on top of its rest placement, as motion in the
  simulate phase; how its arguments resolve; and how a range refuses a
  binding outside it.

### Modified Capabilities

- `ports`: a joint's coordinate is a port for every purpose the ports
  capability names — enumeration off the class, per-instance value,
  causal binding, scale — and a port or a joint coordinate may be wired
  down to a child declaration, rebound from the parent's end on every
  `simulate()`.
- `declarative-nodes`: a child declaration accepts a kwarg naming a port
  or joint the child declares, whose value is a port or joint declared
  on the declaring class. It is a wiring, not a parameter: it is absent
  from the resolved parameters and from identity, and a wiring the child
  cannot receive fails at class definition naming both classes.
- `kinematics`: "Render at rest, simulate per instant" states that a
  joint bound during `simulate()` applies its motion as operations of
  the node the joint is declared on, tagged with the binding assembly
  like any other motion.
- `cli-startup-cost`: the motion package's import ceiling covers
  `solid_node.motion.joints` now that it has contents — it costs what
  `solid_node.motion.ports` costs and no more.

## Impact

**Framework code.** `solid_node/motion/joints.py` gains `Joint`,
`Revolute`, `Prismatic`, `JointRangeError` and `declared_joints`;
`solid_node/motion/ports.py` gains the hook that lets `declared_ports`
report a joint's coordinate; `solid_node/node/declarative.py` gains the
wiring rule on `ChildDeclaration` (`__set_name__` validation,
`realize`/`resolve_parameters` exclusion) ;
`solid_node/node/assembly.py` applies recorded wirings at the end of the
simulating phase. No new operation type, no serializer change, no viewer
change.

**Tests.** New `tests/test_joints.py` and a new fixture project
`tests/joint_project/` (a two-link arm with an elbow off the child's
origin, and a wheel on a bearing) exercised through `set_state`,
`set_keyframe`, the serializer and a snapshot. `tests/test_motion_package.py`
from cycle 1 has its import-cost expectation widened, because
`motion.joints` now imports `motion.ports`.

**Docs.** `docs/architecture.md` (Node model, Kinematics), a joints page
or section in the user documentation, `docs/api-reference.rst`,
`docs/changelog.rst` "Unreleased", `docs/adrs/NODE/ADR-088`,
`docs/adrs/README.md`.

**Projects.** Nothing breaks: joints are additive, and no existing
declaration changes meaning. Thor and clock 01 are the originating
projects and are refactored in their own repositories after cycle 3,
when derived coordinates and relations by path complete what their
motion code needs. This cycle commits nothing outside the framework
repository.

**Downstream.** Cycle 3 (`couplings`) depends on this cycle for the
joint, its coordinate and the enumeration; it adds `drives`, `Affine`,
derived coordinates over ports, relations by path, and the relaxation
that lets a class body read a port off a declaration. None of that is
introduced here.
