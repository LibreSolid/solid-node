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

## ADDED Requirements

### Requirement: Instance checks

The system SHALL call `check()` on a declarative node instance once its
parameters are resolved and before any of its children is realized. An
exception raised by `check()` SHALL refuse the instance and propagate
unchanged, and the refused instance SHALL have realized no child. The base
implementation SHALL do nothing, so a subclass MAY chain `super().check()`.
The framework SHALL NOT call `check()` on a non-declarative instance.

#### Scenario: A cross-parameter guard refuses an instance

- **WHEN** a leaf declares `stem = Length(4.0)` and `stop = Length(6.0)` and
  a `check()` raising `ValueError` when `stop <= stem`, and is constructed
  with `stop=3.0`
- **THEN** construction raises that `ValueError`, and constructing with the
  defaults succeeds

#### Scenario: A refused parent realizes nothing

- **WHEN** an assembly declaring a child and a `check()` that raises is
  constructed
- **THEN** the child's class is never instantiated

#### Scenario: Checks chain

- **WHEN** a subclass defines `check()` calling `super().check()` and its
  base's `check()` raises for the supplied values
- **THEN** construction raises the base's error
