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
named `<attr>-<index>`. Realization SHALL proceed top-down from the root's
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
constructor with the resolved arguments. Reading an attribute off a
declaration in a class body SHALL raise advising that the shared parameter
be declared on this class and passed to both children. Declared children
SHALL be enumerable off the class without instantiating it.

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

#### Scenario: A legacy class is a valid child

- **WHEN** a declarative parent declares `guard = Guard(thickness=wall)`
  where `Guard` defines an ordinary `__init__(self, thickness, name=None)`
- **THEN** realization calls that constructor with the resolved thickness
  and the guard is linked and named as any child

#### Scenario: A sideways read is refused

- **WHEN** a class body declares `piston = Piston()` and then
  `con_rod = ConRod(pin_bore=piston.pin_bore)`
- **THEN** class definition raises naming both attributes and advising that
  the shared parameter be declared on this class and passed to both children

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
