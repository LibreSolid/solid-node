## MODIFIED Requirements

### Requirement: Typed parameter declarations

The system SHALL let a node class declare its parameters as class attributes
of typed kinds: `Length` (a linear dimension), `Angle` (in degrees), `Count`
(an integer), `Ratio` (a dimensionless fraction), `Flag` (a boolean) and
`Scalar` (an unchecked number). Those kinds, the `Quantity` base a project
subclasses to extend the ontology, the enumerator over a class's
declarations, and the errors a bad declaration raises SHALL be imported from
one dedicated module for build parameters, separate from the module that
exports node classes. A build parameter SHALL NOT be reachable from the node
package: reading one there SHALL raise as any unexported name does.

A declaration SHALL carry an optional
default and optional value constraints (`min=` and `max=` on numeric kinds).
A declaration without a default SHALL be supplied by the parent's
declaration or by the caller; instantiating without a value for it SHALL
raise naming the class and the parameter, never at class definition.

Read on an instance, a declared parameter SHALL be a plain Python value —
`float` for `Length`, `Angle`, `Ratio` and `Scalar`, `int` for `Count`,
`bool` for `Flag` — never a token. Read on the class it SHALL be the
symbolic token usable in formulas. Assigning to a declared parameter on an
instance SHALL raise. A declaration whose name would shadow a
non-declaration attribute of a base class SHALL be rejected at class
definition. Declared parameters SHALL be enumerable off the class without
instantiating it, base-first, a subclass redeclaration winning.

#### Scenario: A parameter is imported from the parameter module

- **WHEN** a node module declares `bore = Length(30.0, min=0)`
- **THEN** `Length` was imported from the build-parameter module, and the
  same import line does not carry a node class

#### Scenario: The node package does not answer for a parameter

- **WHEN** a module reads a parameter kind, the `Quantity` base or the
  parameter enumerator off the node package
- **THEN** `AttributeError` is raised naming the requested name, exactly as
  for any name that package does not export

#### Scenario: Defaults realize and read as plain values

- **WHEN** a leaf declares `bore = Length(30.0, min=0)` and is constructed
  with no arguments
- **THEN** `self.bore` inside `render()` is the float `30.0`

#### Scenario: A constraint is checked at instantiation

- **WHEN** a node declaring `count = Count(8, min=2)` is constructed with
  `count=1`, or `Count` receives `2.5`, or a `Flag` receives `1`
- **THEN** construction raises naming the class, the parameter and the
  violated constraint

#### Scenario: A parameter without a default must be supplied

- **WHEN** a node declares `height = Length()` and is constructed without
  `height`, by a parent's declaration or directly
- **THEN** construction raises naming the class and the parameter, and the
  class itself was defined without error

#### Scenario: Assignment is refused

- **WHEN** a `render()` body executes `self.bore = 5`
- **THEN** an error is raised and the declared value is unchanged

#### Scenario: A declaration cannot shadow a base attribute

- **WHEN** a class body declares `name = Length(1.0)` or `time = Angle(0.0)`
- **THEN** class definition raises naming the shadowed attribute

#### Scenario: Declared parameters are enumerable

- **WHEN** a consumer enumerates a class declaring two parameters and one
  derived formula
- **THEN** it receives all three by name with their kinds without
  constructing an instance
