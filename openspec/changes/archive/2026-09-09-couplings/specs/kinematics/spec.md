## MODIFIED Requirements

### Requirement: Render at rest, simulate per instant

The system SHALL split an assembly's lifecycle into a rest build and a
per-instant motion. `render()` SHALL build the machine at rest — structure,
`omit()`, and the placement of every part that does not move — and SHALL
read no driver, no animation time and no port. `AssemblyNode.simulate()`, a
no-op in the base, SHALL be run by the framework after `render()` on every
call that enumerates the assembly's children, under whatever binding is
current: symbolic `$t` when nothing is bound, plain numbers under
`set_state`, `set_keyframe`, the test runner, the snapshot tool and the
simulator. Drivers, time and ports SHALL be read and bound in `simulate()`,
and a joint's coordinate is a port for this purpose.

An operation applied during `simulate()` SHALL compose innermost: it is
inserted before every operation `render()` or construction applied to the
node, so the node moves in its own frame and is then carried by its rest
placement. Operations applied during `simulate()` SHALL be tagged with the
simulating assembly and swept before that assembly's next `simulate()`, so
poses are absolute and never accumulate; two assemblies simulating one node
SHALL keep their operations apart. A joint bound during `simulate()` SHALL
apply its motion as operations of the node the joint is declared on,
tagged with the assembly whose `simulate()` is running and swept with the
rest of that assembly's motion, whether the joint is that assembly's own or
one of a node below it.

The simulate phase of one assembly SHALL run in a fixed order: FIRST
the framework clears the value and the binder record of every
coordinate this assembly bound through a wiring or a relation in its
previous run, so the run that follows sees only values bound in the
current walk; THEN the author's `simulate()` runs; THEN the wirings and
the relations the class declared are solved together, each wiring
binding once its source is bound and each relation applied from
whichever of its ends is. All of it happens while the phase is still
that assembly's, so every motion it causes carries that assembly's tag
and is swept before its next run. A value the author's own code bound
in an earlier run and not in this one SHALL NOT be cleared: it is the
author's, as it is today. Because each class solves its own relations
in its own instance's phase, a relation stated on an ancestor and
reaching a descendant's coordinate by path SHALL be solved before that
descendant's own relations are.

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

#### Scenario: Joint motion is swept like any motion

- **WHEN** an assembly binds a child's joint in its `simulate()` and the
  tree is enumerated twice at different instants
- **THEN** the child carries one joint motion for the current instant,
  tagged with that assembly, and the rest placement its parent applied is
  untouched

#### Scenario: The phase solves the wirings and the relations together

- **WHEN** an assembly binds one joint in `simulate()`, declares a
  wiring whose source another relation of the same class solves, and
  states that relation
- **THEN** the relation is applied and the wiring binds from its solved
  source in the same solve, all the motion is tagged with that
  assembly, and all of it is swept before its next run

#### Scenario: A phase clears what it bound last run

- **WHEN** an assembly whose relations solve a train from one binding
  in `simulate()` is enumerated at three successive instants
- **THEN** each run cleared the coordinates it had bound in the
  previous one before the author's `simulate()` ran, and each run's
  solve produced that instant's angles rather than refusing or
  repeating the first instant's

#### Scenario: An ancestor's relation binds before the descendant solves

- **WHEN** a root states a relation reaching a joint declared two levels
  down, and that level's own class states relations over the same joint's
  neighbours
- **THEN** the root's relation bound the joint before the descendant's
  relations were solved, and the descendant solved against that value

#### Scenario: Structure cannot move

- **WHEN** `simulate()` calls `omit()` on a declared child
- **THEN** `StructureError` is raised naming the node
