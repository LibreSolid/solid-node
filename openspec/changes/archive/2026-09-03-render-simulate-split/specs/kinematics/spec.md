## ADDED Requirements

### Requirement: Render at rest, simulate per instant

The system SHALL split an assembly's lifecycle into a rest build and a
per-instant motion. `render()` SHALL build the machine at rest — structure,
`omit()`, and the placement of every part that does not move — and SHALL
read no driver, no animation time and no port. `AssemblyNode.simulate()`, a
no-op in the base, SHALL be run by the framework after `render()` on every
call that enumerates the assembly's children, under whatever binding is
current: symbolic `$t` when nothing is bound, plain numbers under
`set_state`, `set_keyframe`, the test runner, the snapshot tool and the
simulator. Drivers, time and ports SHALL be read and bound in `simulate()`.

An operation applied during `simulate()` SHALL compose innermost: it is
inserted before every operation `render()` or construction applied to the
node, so the node moves in its own frame and is then carried by its rest
placement. Operations applied during `simulate()` SHALL be tagged with the
simulating assembly and swept before that assembly's next `simulate()`, so
poses are absolute and never accumulate; two assemblies simulating one node
SHALL keep their operations apart.

An assembly whose first `render()` read nothing SHALL run that `render()`
once per instance: later calls SHALL return the same children and SHALL NOT
re-run the author's `render()`, and the operations it applied SHALL persist
unswept. `omit()` called during `simulate()` SHALL raise `StructureError`.

#### Scenario: Motion composes innermost

- **WHEN** an assembly's `render()` translates a child to `[10, 0, 0]` and
  its `simulate()` rotates the child by `90` degrees about z
- **THEN** the child's operations are the rotation then the translation,
  and its origin lands at `[10, 0, 0]` rather than `[0, 10, 0]`

#### Scenario: Rest render runs once

- **WHEN** an assembly whose `render()` reads nothing is rendered under
  three successive `set_state` bindings
- **THEN** the author's `render()` ran once, the placement operation
  objects are the same objects each time, and the `simulate()` operation
  holds the current binding's value with no accumulation

#### Scenario: Symbolic simulate in the build path

- **WHEN** an assembly is rendered with nothing bound
- **THEN** the operation `simulate()` applied carries the symbolic `$t`
  expression, `set_keyframe(0.25)` makes it numeric, and `clear_keyframe()`
  restores the symbolic form

#### Scenario: Two simulators of one node

- **WHEN** two assemblies each simulate the same node and one re-simulates
- **THEN** only that assembly's operation is replaced and the other's is
  untouched

#### Scenario: Structure cannot move

- **WHEN** `simulate()` calls `omit()` on a declared child
- **THEN** `StructureError` is raised naming the node

### Requirement: Reading a driver in render is deprecated, not refused

The system SHALL keep every current model working. An assembly whose
`render()` reads a declared driver, `self.time` or a port value SHALL keep
the previous behaviour for that instance — the author's `render()` re-runs
on every call, its operations are tagged and swept, and rest placement
applied outside any render survives — and the framework SHALL emit one
`FutureWarning` per class naming the class, the first read, and
`simulate()` as the new home. The decision SHALL be made on the instance's
first `render()`. Placement applied in `__init__` SHALL continue to
survive, composed before rest placement.

#### Scenario: A legacy assembly still animates

- **WHEN** an assembly rotates a child by `self.time * 360` in `render()`
  and is rendered at two keyframes
- **THEN** the child holds one rotation with the second keyframe's angle,
  and a `FutureWarning` was emitted once naming the class and `time`

#### Scenario: A port read in render warns

- **WHEN** an assembly reads a child's port value in `render()`
- **THEN** a `FutureWarning` names the class and the port, and the render
  keeps re-running per binding

## MODIFIED Requirements

### Requirement: Animator-tagged idempotent renders

The system SHALL make assembly re-simulation absolute, never cumulative.
Operations applied while an assembly's `simulate()` — or a legacy
`render()` that reads a driver — is on the phase stack are tagged with that
assembly as its animator, and before each run the assembly removes only
operations it applied (`op._animator is self`). Untagged operations (rest
placement applied in a once-only `render()`, in `__init__`, or outside any
phase) SHALL never be swept, and two independent assemblies animating the
same node SHALL not disturb each other's operations.

#### Scenario: Re-simulation expresses absolute pose

- **WHEN** an assembly rotating a wheel by `self.time * 360` in
  `simulate()` is simulated twice at the same keyframe
- **THEN** the wheel holds one rotation operation with the same angle, not
  two accumulated rotations

#### Scenario: Rest placement survives re-simulation

- **WHEN** a node was translated by its parent's once-only `render()`, or
  during construction, and its simulating assembly re-simulates
- **THEN** the translation remains in `node.operations`, after the motion
