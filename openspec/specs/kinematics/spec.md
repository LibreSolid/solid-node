# Kinematics and Animation Specification

## Purpose

How nodes move: the operation objects (rotations/translations), world-pose
composition, multi-driver state binding and the normalized animation
timeline over it, animator-tagged idempotent renders, and the
cross-runtime `$t` expression math contract. Encodes ADR-008 (time-based
animation), ADR-023 (kinematic operations and animator-tagged idempotent
renders; tag renamed by the 2026-08-25 multi-driver-state-seam change),
ADR-022 (cross-runtime degree-trig parity), ADR-028 (cached base meshes
and single-matrix world composition), and ADR-056 stage 1 (multi-driver
state binding).

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
and a plain float once `set_keyframe(time)` is set. `set_keyframe(time)`
SHALL be equivalent to `set_state(time=time)` — the time-only surface over
the multi-driver state snapshot — and SHALL recurse into rendered children so
nested assemblies also render numerically. All assemblies share the single
`$t` timeline; users scale in code.

Keyframed time SHALL be reversible. `clear_keyframe()` SHALL be equivalent to
`clear_state('time')`: it SHALL drop the fixed time, re-render, and recurse
into rendered children exactly as `set_keyframe` does, returning the subtree
to symbolic `$t` while leaving any other bound snapshot entries in place.
Because an assembly's re-render sweeps only the operations it drove, the
operations a cleared subtree carries SHALL be the same symbolic expressions a
never-keyframed render produces — including expressions built through
`solid_node.math` — while static placement applied outside any assembly
render SHALL survive unchanged and operations SHALL NOT accumulate across
repeated `set_keyframe`/`clear_keyframe` cycles. `clear_keyframe()` SHALL be
a no-op on non-animated nodes, mirroring `set_keyframe`.

Both `set_keyframe` and `clear_keyframe` SHALL tolerate an assembly whose
`render()` returns a value that is not a list or tuple, recursing into no
children rather than raising, matching the partial-node tolerance the document
serializer already has.

#### Scenario: Keyframe freezes a frame

- **WHEN** `set_keyframe(0.25)` is called on a root assembly containing a
  nested assembly
- **THEN** both assemblies render with `time == 0.25` as a float and
  `node.mesh` resolves numerically

#### Scenario: Clearing a keyframe restores symbolic time

- **WHEN** `set_keyframe(0.5)` is called on a root assembly containing a nested
  assembly and `clear_keyframe()` is then called on the root
- **THEN** both assemblies report symbolic `$t` for `time`, and the nested
  child's operations serialize to the same `$t` expression strings a
  never-keyframed render produces

#### Scenario: Clearing restores a non-linear symbolic expression

- **WHEN** an assembly whose rotation is built with `solid_node.math` (for
  example `asin((r/l) * sin(360 * $t))`) is keyframed and then cleared
- **THEN** its operation serializes to the deferred OpenSCAD expression string,
  identical to the one a fresh render produces, not to the numeric value the
  keyframe computed

#### Scenario: Keyframe cycles do not accumulate operations

- **WHEN** `set_keyframe` and `clear_keyframe` are alternated several times on
  the same assembly
- **THEN** each driven child holds exactly the operations one render applies,
  and static placement applied outside any assembly render is still present

#### Scenario: A non-list render result is tolerated

- **WHEN** `set_keyframe` or `clear_keyframe` is called on an assembly whose
  `render()` returns a single node rather than a list or tuple
- **THEN** the call completes without raising and recurses into no children

#### Scenario: Keyframe equivalence with state binding

- **WHEN** `set_keyframe(0.3)` is called on an assembly that already holds
  another bound snapshot entry
- **THEN** the effect is exactly `set_state(time=0.3)`: `time` reads `0.3`
  and the other entry is preserved

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

### Requirement: Animator-tagged idempotent renders

The system SHALL make assembly re-renders absolute, never cumulative. Every
`AssemblyNode` subclass `render()` is auto-wrapped: operations applied while
an assembly's render is on the render stack are tagged with that assembly as
its animator, and before each re-render the assembly removes only operations
it applied (`op._animator is self`). Untagged operations (static placement
applied outside any assembly render) SHALL never be swept, and two
independent assemblies animating the same node SHALL not disturb each
other's operations. (The tag was previously named `_driver`; it is renamed
so "driver" can unambiguously mean a simulation input per ADR-056. Behavior
is unchanged.)

#### Scenario: Re-render expresses absolute pose

- **WHEN** an assembly rotating a wheel by `self.time * 360` renders twice at
  the same keyframe
- **THEN** the wheel holds one rotation operation with the same angle, not
  two accumulated rotations

#### Scenario: Static placement survives re-render

- **WHEN** a node was translated during construction, outside any assembly
  render, and its driving assembly re-renders
- **THEN** the static translation remains in `node.operations`

### Requirement: Multi-driver state binding

The system SHALL let an `AssemblyNode` bind a snapshot of named numeric
driver values with `set_state(**states)`. Binding SHALL merge the given
entries into the assembly's current snapshot (an entry is replaced when
re-given, preserved otherwise), re-render the assembly, and recurse into
rendered children exactly as `set_keyframe` does — including tolerating
a `render()` result that is not a list or tuple by recursing into no
children. Snapshot values SHALL be plain numbers.

`render()` SHALL read the bound snapshot through a `state` mapping on
the assembly. Reading a name that is not bound SHALL raise an error
that names the missing entry and `set_state`, so a state-consuming
assembly rendered without a snapshot fails loudly rather than
guessing. The `time` name is the exception: it participates in the
snapshot but falls back to symbolic `$t` through the `time` property
when unbound, preserving the ADR-008 animation path.

`clear_state(*names)` SHALL remove the named entries from the snapshot
— all entries when called with no names — re-render, and recurse the
same way, restoring symbolic `$t` behavior for `time`. Because
re-renders sweep only the operations the assembly drove, repeated
`set_state`/`clear_state` cycles SHALL NOT accumulate operations, and
static placement applied outside any assembly render SHALL survive,
exactly as the idempotent-render requirement already guarantees.

On nodes that do not animate (leaves, fusions), `set_state` and
`clear_state` SHALL be no-ops, mirroring `set_keyframe`.

#### Scenario: Two named drivers bind numerically

- **WHEN** `set_state(motor=4000, lift=2.5)` is called on an assembly
  whose `render()` derives operations from `self.state['motor']` and
  `self.state['lift']`
- **THEN** the assembly re-renders with both values as plain numbers
  and `node.mesh` reflects the resulting pose absolutely

#### Scenario: Merging preserves unrelated entries

- **WHEN** `set_state(motor=4000)` is followed by `set_state(lift=1.0)`
- **THEN** the snapshot holds both `motor=4000` and `lift=1.0`

#### Scenario: Unbound state access fails loudly

- **WHEN** an assembly whose `render()` reads `self.state['motor']` is
  rendered with no snapshot bound
- **THEN** an error is raised naming `motor` and `set_state`

#### Scenario: State cycles do not accumulate operations

- **WHEN** `set_state` is called many times in sequence on the same
  assembly (as a stepping loop does every tick)
- **THEN** each driven child holds exactly the operations one render
  applies, and static placement applied outside any assembly render is
  still present

#### Scenario: Clearing state restores symbolic time

- **WHEN** `set_state(time=0.5, motor=100)` is followed by
  `clear_state()`
- **THEN** the assembly's `time` reports symbolic `$t` again and the
  snapshot is empty

#### Scenario: Leaf tolerance

- **WHEN** `set_state(motor=10)` propagation reaches a leaf node
- **THEN** the call is a no-op on that leaf

