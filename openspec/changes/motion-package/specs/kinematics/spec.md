## MODIFIED Requirements

### Requirement: Declared time base

A root assembly MAY declare its time base as a class attribute named `time`
holding a `Time(loop=<seconds>)` declaration, exported from
`solid_node.motion.ports` — the module that answers what moves, alongside
the port kinds — and no longer from `solid_node.node`.
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

#### Scenario: The time base is imported from the motion package

- **WHEN** a root's module writes
  `from solid_node.motion.ports import Time` and declares
  `time = Time(loop=43200)`
- **THEN** the declaration behaves exactly as it did when `Time` came from
  `solid_node.node`, and `from solid_node.node import Time` raises
  `ImportError` naming `solid_node.motion.ports`
