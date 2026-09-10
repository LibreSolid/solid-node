## MODIFIED Requirements

### Requirement: Class-body child declarations

The system SHALL treat a node constructed inside a node class body as a
declaration of a child, never as an instance: the class-body expression
`piston = Piston(diameter=piston_diameter)` records the child class and its
arguments, and each parent instance realizes its own child at construction.
Arguments to a declaration MAY be tokens and formulas, resolved against the
parent instance's values at realization, or plain values passed through;
`name=` passes through. A `Flag` token passed to a declaration SHALL resolve
to the parent instance's boolean at realization, exactly as a numeric token
does. A literal list of declarations SHALL declare enumerated children named
`<attr>-<index>`. A list comprehension in the class body over values the
comprehension can see — module-level names and literals — SHALL declare an
enumerated list exactly as a literal list does; the body is recognized while
the comprehension runs, and class-level names remain invisible to it as
Python defines. `.repeat(count)` on a declaration, where `count` is an
integer or a `Count` token, SHALL declare count-many identical children
named `<attr>-<index>`. Every child a repeat realizes SHALL carry its
own 0-based position in the repeat, readable on the realized node as
`index`. That position SHALL NOT be a declared parameter, SHALL NOT
enter the node's identity, and SHALL NOT make the copies different
parts: a repeat is one geometry, one build identity and one cached
artifact, whatever a copy's index is used for. Per-unit GEOMETRY is
therefore not what a repeat states, and children that differ
geometrically SHALL be declared individually or in a literal list.

A repeat of a class that already answers to the name `index` — as a
declared parameter, a port, a joint, a child declaration, or any other
attribute of the class — SHALL be refused AT CLASS DEFINITION, where the
repeat is written, naming the declaring class, the attribute, the
repeated class and what it found, because a declaration wins over an
instance attribute of the same name and the position would otherwise be
silently invisible. Realization SHALL proceed top-down from the root's
bound values in declaration order, and by the time any `render()` runs
every parameter SHALL be a plain value.

A keyword argument whose VALUE is a port or joint declaration SHALL be a
WIRING rather than a parameter: it SHALL NOT be resolved as a parameter,
SHALL NOT be passed to the child's construction, and SHALL NOT enter the
child's identity, because it states which value reaches the child at each
instant and not what geometry is built. Every keyword whose value is not
such a declaration SHALL keep the meaning it has today, including the
`TypeError` an unknown one raises.

A wiring SHALL be validated at class definition, where both ends are
known: the value SHALL be a port or joint declared on the class whose body
holds the declaration, and the keyword SHALL name a port or a joint the
child class declares. A wiring failing either test SHALL be refused at
class definition, naming the declaring class, the child class, the keyword,
and the ports and joints the child does declare.

Two parent instances SHALL never share a realized child. A declared child
whose class is a non-declarative node SHALL be realized by calling its
constructor with the resolved arguments. Declared children SHALL be
enumerable off the class without instantiating it.

Reading an attribute off a declaration in a class body SHALL depend on
what that attribute IS on the declared class:

- a PORT, a JOINT or another CHILD DECLARATION SHALL yield a PATH
  REFERENCE — `anchor.turn`, `motion_works.cannon.turn`,
  `shoulder.art2.art3.wrist` — which names a place in the tree rather
  than a value, is resolved per parent instance at realization to the
  coordinate of the realized descendant, and may be either end of a
  relation between coordinates. A path reference SHALL be readable to
  any depth, each segment checked against the class the previous
  segment names, and a segment naming an attribute no class along the
  path declares SHALL be refused at class definition naming the path,
  the segment and what that class declares;
- a REPEATED child declaration SHALL yield a path reference that names
  the same coordinate of every copy — the BROADCAST the `couplings`
  capability specifies — usable as the DRIVEN end of a relation and
  refused as its source;
- a LIST-HELD child declaration SHALL be refused, because its children
  carry their own arguments and are named one by one;
- a DECLARED PARAMETER, or anything else, SHALL keep raising as it does
  today, advising that the shared parameter be declared on this class
  and passed to both children. A parameter is a value belonging to a
  realized instance, and a class body has none.

A child declaration SHALL additionally carry the verb that states a
relation between two coordinates, so a class body may write
`power.drives(centre, law=going_train)`, the declaration standing for
its class's one joint.

#### Scenario: Each parent realizes its own child

- **WHEN** two instances of a class declaring `piston = Piston()` are
  constructed and one translates its piston
- **THEN** the other instance's piston carries no operation and the two are
  distinct objects

#### Scenario: Tokens flow to children by reference

- **WHEN** `CylinderUnit` declares `bore = Length(30.0)` and
  `piston = Piston(diameter=bore - 0.6)`, and a parent realizes
  `CylinderUnit(bore=32.0)`
- **THEN** the realized piston's `diameter` reads `31.4`

#### Scenario: A flag flows to a child

- **WHEN** a parent declares `fitted = Flag(False)` and
  `supply = PowerSupply(fitted=fitted)`, and is realized with `fitted=True`
- **THEN** the realized supply's `fitted` reads `True`, and realized with
  the default it reads `False`

#### Scenario: A comprehension declares

- **WHEN** a class body assigns `boxes = [Box() for _ in TABLE]` over a
  module-level `TABLE` of two entries
- **THEN** the class declares two children `boxes-0` and `boxes-1`, two
  instances of the class realize distinct boxes, and a `render()` returning
  `None` yields both

#### Scenario: Identical units repeat

- **WHEN** a class declares `count = Count(8)` and
  `units = CylinderUnit(bore=bore).repeat(count)` and is realized with
  `count=6`
- **THEN** `self.units` holds six distinct instances named `units-0`
  through `units-5`, all with the same resolved parameters

#### Scenario: A copy carries its position

- **WHEN** the same class is realized with `count=6`
- **THEN** the six copies read `index` as `0` through `5` in order, all
  six share one `uniq_id` and one cached artifact, and none of their
  resolved parameters carries an index

#### Scenario: A repeat of a class that declares its own index is refused

- **WHEN** a class body declares `arbors = Arbor().repeat(4)` where
  `Arbor` declares a parameter, port or joint named `index`
- **THEN** class definition raises naming the declaring class, the
  attribute, `Arbor` and the declaration it found, with the advice to
  rename it or declare the children in a list

#### Scenario: A legacy class is a valid child

- **WHEN** a declarative parent declares `guard = Guard(thickness=wall)`
  where `Guard` defines an ordinary `__init__(self, thickness, name=None)`
- **THEN** realization calls that constructor with the resolved thickness
  and the guard is linked and named as any child

#### Scenario: A sideways read is refused

- **WHEN** a class body declares `piston = Piston()` and then
  `con_rod = ConRod(pin_bore=piston.pin_bore)`, where `pin_bore` is a
  declared parameter of `Piston`
- **THEN** class definition raises naming both attributes and advising that
  the shared parameter be declared on this class and passed to both children

#### Scenario: A port read off a declaration is a path reference

- **WHEN** a class body declares `anchor = TrainArbor(index=4)` and
  `pendulum = Pendulum()`, and states
  `anchor.turn.drives(pendulum.swing)`
- **THEN** class definition succeeds, and on each realized parent the
  relation's ends are the realized anchor's and pendulum's own
  coordinates

#### Scenario: A path reaches through several declarations

- **WHEN** a class body reads `shoulder.art2.art3.wrist`, each segment
  naming a child declaration of the previous segment's class and the
  last naming a joint
- **THEN** the read yields a path reference, and on each realized parent
  it resolves to that descendant's coordinate

#### Scenario: A path naming nothing is refused at class definition

- **WHEN** a class body reads `shoulder.art2.wist`, misspelling a joint
- **THEN** class definition raises naming the path, the segment and the
  ports, joints and children that class declares

#### Scenario: A path through a list-held child is refused

- **WHEN** a class reads `frame.plates.turn`, where `plates` is a
  list-held child declaration of `Frame`
- **THEN** class definition raises naming the list-held declaration and
  saying its children carry their own arguments and are named one by one

#### Scenario: A path through a repeated child is refused

- **WHEN** a class declaring `units = Unit().repeat(count)` reads
  `units.turn` and names it as the SOURCE of a relation, or reads on
  through a second repeated declaration
- **THEN** class definition raises naming the repeated declaration and
  the path as written: a relation's source is one value while the copies
  hold one each, and a broadcast fans out over one repeat

#### Scenario: A path through a repeated child names every copy

- **WHEN** a class declaring `units = Unit().repeat(count)` reads
  `units.turn`
- **THEN** the read yields a path reference that names that coordinate
  of every copy, which the `couplings` capability admits as a driven end
  and refuses as a source

#### Scenario: A wired coordinate is not a parameter

- **WHEN** a class declaring `turn = Revolute(axis=(0, 0, 1), unit='deg')`
  and `index = Count(0)` declares `wheel = Arbor(index=index, turn=turn)`,
  where `Arbor` declares a `Count` parameter `index` and a
  `RotationalPort` `turn`
- **THEN** the realized `Arbor` was constructed with `index` only, its
  resolved parameters carry no `turn`, and two such parents differing only
  in what they bind to `turn` realize arbors sharing one `uniq_id`

#### Scenario: A wiring the child cannot receive fails at class definition

- **WHEN** a class body declares `wheel = Arbor(turn=turn)` where `Arbor`
  declares neither a port nor a joint named `turn`
- **THEN** class definition raises naming the declaring class, `Arbor`,
  `turn`, and the ports and joints `Arbor` declares

#### Scenario: A coordinate of another class is refused

- **WHEN** a class body declares `wheel = Arbor(turn=elsewhere)` where
  `elsewhere` is a port declared on an unrelated class
- **THEN** class definition raises naming the declaring class, the
  keyword and the class the coordinate belongs to

#### Scenario: An unknown keyword is still a TypeError

- **WHEN** a class body declares `wheel = Arbor(spin=1.0)` where `Arbor`
  declares no parameter `spin`
- **THEN** realization raises the `TypeError` it raises today, naming the
  class, the unknown keyword and the declared parameters

### Requirement: Realization at the root and framework-owned identity

The system SHALL realize a declarative root with its defaults when
constructed with no arguments, and SHALL rebind the root's declared
parameters from keyword arguments when given, every derived value and child
following. A declarative class SHALL reject positional arguments and unknown
keyword arguments with a `TypeError` that lists the declared names. Its
`uniq_id` SHALL be derived from the class and the resolved values of its
declared parameters, never from a hand-forwarded map, and `name` SHALL stay
out of it. Repeated identical children SHALL share one `uniq_id` and one
artifact, and the position a copy carries SHALL NOT enter that
identity. The loader SHALL construct the root with the caller's overrides,
or with none, and bind declared driver defaults exactly as it does today.

#### Scenario: One number moves the machine

- **WHEN** `Engine(bore=32.0)` is realized where `Engine` passes `bore` to
  `cylinders` and `block`
- **THEN** both subtrees read the same `32.0` and their leaves' `uniq_id`s
  differ from those of `Engine()`

#### Scenario: A copy's position is not part of its identity

- **WHEN** a class declaring `units = Unit().repeat(8)` is realized
- **THEN** the eight copies read eight different `index` values and
  share one `uniq_id`, the same one a single un-repeated `Unit()` of the
  same arguments has

#### Scenario: Unknown and positional arguments are rejected

- **WHEN** a declarative class is constructed as `Piston(31.0)` or
  `Piston(diamter=31.0)`
- **THEN** construction raises `TypeError` naming the class and, for the
  keyword, the unknown name and the declared ones

#### Scenario: Identity is complete by construction

- **WHEN** a declarative leaf with six declared parameters is realized twice
  with one value differing
- **THEN** the two `uniq_id`s differ, and two realizations with equal values
  share one `uniq_id` and one artifact set

#### Scenario: Coercion keeps one artifact per geometry

- **WHEN** a declarative leaf is realized once with `diameter=30` and once
  with `diameter=30.0`
- **THEN** both read `30.0` and share one `uniq_id`

#### Scenario: Repeated units are one part

- **WHEN** eight identical units are realized through `repeat(8)` and built
- **THEN** exactly one artifact set is produced for them and each of the
  eight carries its own placement
