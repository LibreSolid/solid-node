## ADDED Requirements

### Requirement: Declared time base

A root assembly MAY declare its time base as a class attribute named `time`
holding a `Time(loop=<seconds>)` declaration, exported from `solid_node.node`.
`loop` SHALL be a positive finite number of seconds: the span of machine time
one turn of the animation timeline covers. The declaration SHALL be frozen
class metadata readable off the class (`Root.time.loop`); assigning
`self.time` SHALL fail naming `set_keyframe`.

A `Time` declaration SHALL be refused at class-definition time when it is
bound to any attribute name other than `time`, or when the declaring class is
not an `AssemblyNode`, each with an error naming the rule.

Under a declared time base `self.time` SHALL read machine time in seconds on
every path:

- unbound, it SHALL be the symbolic expression `$t * loop`, so the normalized
  0..1 `$t` timeline is unchanged and published expressions carry the
  multiplication verbatim (`(360 * ($t * 43200))` rather than a constant);
- bound by `set_keyframe(t)` or `set_state(time=t)`, it SHALL be exactly the
  bound number, which callers state in seconds;
- under a stepped simulation, it SHALL be the simulation clock in seconds
  exactly as the `simulation` capability already states.

The time base is a property of the root: every assembly below it SHALL read
the root's time base, whether or not it declares one itself. Reading `time`
on a linked descendant whose own class declares a `Time` SHALL fail naming
the descendant and the root, so a stray declaration can never silently scale
one subtree differently. An assembly that is itself the root of the tree it
is read in — including a sub-assembly loaded on its own — uses its own
declaration.

A root that declares no time base SHALL keep the normalized 0..1 behaviour
of the "Normalized animation time" requirement unchanged.

#### Scenario: Symbolic time carries the loop

- **WHEN** a root declares `time = Time(loop=43200)` and a nested assembly
  rotates a child by `360 * self.time / 3600`
- **THEN** the nested assembly reads the same `$t * 43200` expression as the
  root, and the serialized operation names `$t` with the loop inside the
  expression rather than a constant

#### Scenario: Keyframes bind seconds

- **WHEN** `set_keyframe(2700)` is called on a root declaring
  `Time(loop=43200)` containing a nested assembly
- **THEN** both assemblies read `time == 2700` as a float and their meshes
  resolve at the pose 2700 seconds into the loop

#### Scenario: Clearing restores the loop expression

- **WHEN** a root declaring a time base is keyframed and then cleared
- **THEN** `time` reads the symbolic `$t * loop` expression again and the
  nested child's operations serialize to the same strings a never-keyframed
  render produces

#### Scenario: A misnamed declaration is refused

- **WHEN** a class body binds `clock = Time(loop=60)`
- **THEN** class definition fails with an error naming `time` as the only
  name a time base may be bound to

#### Scenario: A declaration below the root is refused

- **WHEN** a root without a declaration links a child assembly whose class
  declares `time = Time(loop=60)` and that child's `simulate()` reads
  `self.time`
- **THEN** the read fails naming the child and the root

#### Scenario: A sub-assembly loaded alone uses its own declaration

- **WHEN** an assembly declaring `Time(loop=60)` is loaded as the root
- **THEN** its `time` reads `$t * 60`

#### Scenario: The declaration is readable off the class

- **WHEN** a producer reads `type(root).time` on a root declaring
  `Time(loop=43200)`
- **THEN** it gets the declaration and `loop == 43200.0`, without
  constructing the node

#### Scenario: An undeclared root is unchanged

- **WHEN** a root declares no time base
- **THEN** `self.time` is bare `$t` unbound and the keyframed fraction when
  bound, exactly as before

## MODIFIED Requirements

### Requirement: Normalized animation time

The system SHALL expose animation exclusively on `AssemblyNode` via a `time`
property. For a root that declares no time base it SHALL be normalized to
0..1: symbolic OpenSCAD `$t` in the build/viewer path, and a plain float once
`set_keyframe(time)` is set. For a root declaring a time base it SHALL read
seconds as the "Declared time base" requirement states; everything below
about keyframes, clearing, recursion and tolerance holds in both cases with
the bound number meaning whatever the root's time base says. `set_keyframe(time)`
SHALL be equivalent to `set_state(time=time)` — the time-only surface over
the multi-driver state snapshot — and SHALL recurse into rendered children so
nested assemblies also render numerically. All assemblies share the single
`$t` timeline; a root that declares no time base scales in code.

Keyframed time SHALL be reversible. `clear_keyframe()` SHALL be equivalent to
`clear_state('time')`: it SHALL drop the fixed time, re-render, and recurse
into rendered children exactly as `set_keyframe` does, returning the subtree
to symbolic time while leaving any other bound snapshot entries in place.
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
