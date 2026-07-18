# Kinematics and Animation Specification

## Purpose

How nodes move: the operation objects (rotations/translations), world-pose
composition, the normalized animation timeline, driver-tagged idempotent
renders, and the cross-runtime `$t` expression math contract. Encodes ADR-008
(time-based animation), ADR-023 (kinematic operations and driver-tagged
idempotent renders), ADR-022 (cross-runtime degree-trig parity), and ADR-028
(cached base meshes and single-matrix world composition).

Code: `solid_node/node/operations.py`, `solid_node/node/assembly.py`,
`solid_node/node/base.py`, `solid_node/math.py`.

## Requirements

### Requirement: Tri-consumer operation objects

The system SHALL represent transforms as first-class operation objects
(`Rotation(angle, axis, node)`, `Translation(vector, node)`) that each render
for three consumers: `.scad(obj)` (OpenSCAD wrap), `.mesh(mesh)` (trimesh
transform with animated values resolved to floats; rotation applied in
radians), and `.serialized` (wire form `['r', angle, axis]` / `['t',
vector]`). Each operation SHALL also provide `.reversed`, and `.matrix()` —
its 4×4 homogeneous world matrix, with animated values resolved through
`as_number()` at access time and never cached, so a keyframe change is always
reflected. The registry plus `unserialize()` SHALL round-trip the wire form.
A new operation type MUST implement all of these surfaces and register
itself.

#### Scenario: Wire round-trip

- **WHEN** an operation is serialized and passed through `unserialize()`
- **THEN** an equivalent operation object is reconstructed

### Requirement: Chainable transform API

The system SHALL expose `rotate(angle, axis)` and `translate(translation)` on
every node, each appending an operation to `node.operations` and returning
`self` for chaining. `save_checkpoint()`/`restore_checkpoint()` SHALL
snapshot and roll back the operations list.

#### Scenario: Chained placement

- **WHEN** a render calls `part.rotate(45, [0, 0, 1]).translate([10, 0, 0])`
- **THEN** both operations are queued on the part in that order

### Requirement: World-pose mesh composition

The system SHALL compute a node's world-space mesh (`node.mesh`) by applying
its own operations first, then each ancestor's operations up the `_parent`
chain, folded into a single composed 4×4 world matrix (each operation's
matrix premultiplied in encounter order — later operations outermost). This
composition is the single source of truth consumed by the test assertions and
mirrored by both browser renderers (ADR-027 pins the viewer to the same
semantics). The world matrix SHALL be recomposed from scratch on every
access — never cached — because operation values can be animated expressions
that change with the keyframe and `node.operations` can be mutated in place
(e.g. the perturbation assertions inject and remove an operation).

#### Scenario: Nested placement

- **WHEN** a translated leaf sits inside a rotated assembly
- **THEN** `leaf.mesh` reflects the translation carried by the assembly's
  rotation (own ops first, then ancestors')

#### Scenario: Keyframe change reflected without cache staleness

- **WHEN** `set_keyframe` moves an assembly and `node.mesh` is read again
- **THEN** the returned mesh reflects the new pose (the world matrix was
  recomposed at access time)

### Requirement: Base mesh caching

The system SHALL load a node's base STL geometry (no operations applied) at
most once per `(stl_file, mtime)` in a module-level cache, evicting stale
entries for the same file when the STL is rebuilt under a new mtime.
`node.mesh` SHALL return a fresh mutable copy of the cached base mesh with
the composed world matrix applied in a single transform pass; the cached
base mesh itself is never mutated.

#### Scenario: Repeated access skips disk

- **WHEN** a test suite reads `node.mesh` many times without the STL
  changing
- **THEN** the STL is loaded from disk once and each access returns an
  independent copy

#### Scenario: Rebuild invalidates the cache

- **WHEN** the STL is regenerated with a new mtime
- **THEN** the next `mesh` access loads the new geometry and the entry
  cached under the old mtime is evicted

### Requirement: Normalized animation time

The system SHALL expose animation exclusively on `AssemblyNode` via a `time`
property normalized to 0..1: symbolic OpenSCAD `$t` in the build/viewer path,
and a plain float once `set_keyframe(time)` is set. `set_keyframe` SHALL
recurse into rendered children so nested assemblies also render numerically.
All assemblies share the single `$t` timeline; users scale in code.

#### Scenario: Keyframe freezes a frame

- **WHEN** `set_keyframe(0.25)` is called on a root assembly containing a
  nested assembly
- **THEN** both assemblies render with `time == 0.25` as a float and
  `node.mesh` resolves numerically

### Requirement: Driver-tagged idempotent renders

The system SHALL make assembly re-renders absolute, never cumulative. Every
`AssemblyNode` subclass `render()` is auto-wrapped: operations applied while
an assembly's render is on the render stack are tagged with that assembly as
driver, and before each re-render the assembly removes only operations it
drove (`op._driver is self`). Untagged operations (static placement applied
outside any assembly render) SHALL never be swept, and two independent
assemblies driving the same node SHALL not disturb each other's operations.

#### Scenario: Re-render expresses absolute pose

- **WHEN** an assembly rotating a wheel by `self.time * 360` renders twice at
  the same keyframe
- **THEN** the wheel holds one rotation operation with the same angle, not
  two accumulated rotations

#### Scenario: Static placement survives re-render

- **WHEN** a node was translated during construction, outside any assembly
  render, and its driving assembly re-renders
- **THEN** the static translation remains in `node.operations`

### Requirement: Degree-convention dual-mode math

The system SHALL provide `solid_node/math.py` as the single `$t` math
semantics — OpenSCAD's degree conventions (`sin(90) == 1.0`, `asin(0.5) ==
30.0`). Each function SHALL compute numerically when given a real number and
emit an equivalent deferred OpenSCAD expression when given a symbolic value.
Every runtime that evaluates `$t` expressions (math.py, OpenSCAD, the dev
viewer's evaluator, the export widget's evaluator) is expected to reproduce
these semantics function-for-function, treating `^` as exponentiation.

Note: ADR-022 records a known shipped deviation — the export widget's
evaluator currently uses radian trig and lacks the `^`→`pow()` rewrite, so
non-linear `$t` expressions render wrong in exported widgets. Fixing that is
delta material; parity has no automated cross-runtime enforcement yet.

#### Scenario: Dual-mode trig

- **WHEN** `math.sin` is called with a float under `set_keyframe`
- **THEN** it returns the numeric degree-convention result
- **WHEN** the same call receives a symbolic `$t` expression
- **THEN** it returns an OpenSCAD expression string for deferred evaluation
