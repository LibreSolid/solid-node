## Context

A node's parameters today live in three places a human keeps in sync by
hand, and its children are built in `__init__` before `super().__init__()`
runs, so a node knows nothing about itself while it constructs them. The
framework already has two working precedents for class-level declaration
read off the instance: `Port` (`node/ports.py`: typed subclasses,
`__set_name__`, a lazily materialized per-instance slot, `declared_ports`)
and `DriverDeclaration` (`node/qualified.py`: a data descriptor whose
`__set__` raises, a shadow guard in `__set_name__`, a per-class scan cache).
This change adds the two missing members of that family — parameters and
children — and the algebra that lets one class-body formula stand in for a
hand-derived constant.

The design reference is `docs/new-declarative-api.md` in the shop
repository, settled in pilot discussion on 2026-08-31 and 2026-09-01. Its
open questions, and the places where it conflicts with the existing
framework, were resolved one by one with the pilot on 2026-09-01; the
decisions below record the outcome and the reasoning.

Constraints that shape everything below:

- Migration must be additive. `render()`-based projects keep working
  byte-for-byte; solid-node is approaching a broadly usable release.
- Floats at the render boundary. `uniq_id`, the backends and the serializer
  never see a token; the typed boundary is the declaration layer.
- Structure varies with parameters, never with time. Artifact identity
  depends on the children set, and a fusion whose membership depended on
  `$t` would have no single artifact.
- Empirical fact forcing the model: a node constructed in a class body is
  one object mutated by every parent instance. Class-body construction must
  therefore yield a declaration, never an instance.
- Every node file stays loadable on its own. `solid develop piston.py`
  works today because a node constructs with no arguments; a node whose
  parameter has no default is loadable with the value stated.

## Goals / Non-Goals

**Goals:**

- Remove the `__init__` boilerplate for the common case and make artifact
  identity complete by construction.
- Catch dimensional mistakes (`bore + pressure_angle`) on `import`.
- Let one root value move the whole machine, from Python and from the
  command line.
- Express identical repeated units as one part with many placements.
- Keep every existing project working without edits.

**Non-Goals:**

- Unit conversion. `Length` means "a length in the project's unit", as the
  framework already fixes millimetres and degrees everywhere.
- Geometric or mechanical validation (interference, clearance direction).
  Cross-parameter assertions are a natural second tier on the same formula
  layer and are out of this change.
- Sideways reads of a sibling declaration's parameter. Depending on a
  child's parameter is the anti-pattern; declaring on the parent is the
  pattern, and a sideways read raises with that advice.
- An enumerated `Choice` kind. It appeared in the reference without having
  been presented to the pilot; `Flag` is the only selector until a project
  shows a case.
- Publishing declared parameters in the serialized document. The
  enumeration this change creates is what a future viewer would draw knobs
  from; publishing it is a schema decision better made with that consumer
  in front of us.
- Renaming `render()`, `assemble()` and `shape()` into the reference's
  workshop verbs. Both `assemble()` (the build lifecycle entry, called by
  the builder, the simulation, the snapshot tool and ten project test
  files) and `shape()` (the exact-geometry accessor, called by the test
  runner and by project tests) are public today, so the rename is a
  breaking refactor the pilot has deferred.
- Detecting a class-body list comprehension. Python raises `NameError` for
  the class-level name before the framework sees anything; the
  documentation says why and shows the literal-list and `repeat` forms.

## Decisions

### D1. `render()` stays, and on an internal node it may return nothing

The reference split `render()` into two verbs. That split is deferred (see
Non-Goals). What remains of it is the simplification that carries the
declarative model: an internal node's `render()` positions and selects,
and when it returns `None` the framework takes the children from the
declarations — the realized declared children in declaration order, minus
those `omit()` marked during this render. A `render()` that returns a list
keeps today's contract to the letter; a class with nothing to position
defines no `render()` at all.

The substitution lives in one place, the wrapper the framework already
puts around a subclass `render()` for the animator sweep
(`AssemblyNode.__init_subclass__` and `_idempotent_render`). Every tree
walker — `as_scad`, the serializer, the driver walk, `set_state`
propagation — calls `render()` and treats a non-list result as "no
children", so the wrapper is what turns `None` into the list before any of
them see it. `FusionNode` subclasses get the same wrapper for the same
reason; the sweep part of it is a no-op for a fusion, which applies no
kinematic operations. The base `InternalNode.render()` returns `None`, so a
methodless class goes through the same path.

`omit()` marks a node absent for the render in progress. The wrapper
clears the marks on this instance's declared children before calling the
author's `render()`, so presence is decided afresh each render, and it
records the omitted set: a later render of the same instance whose set
differs raises naming the node and both sets. Under symbolic time a
condition on a time-derived value already raises, because solid2 refuses
to evaluate a symbolic value as a boolean; the recorded-set check is what
enforces the rule under a bound keyframe or a simulation snapshot, where
time is a plain number. An instance's parameters cannot change, so a
difference can only come from time or from a bug. An omitted child is not
linked, built, exported, fused or serialized; it is not in the machine.

### D2. Class-body detection through the node metaclass

A call in a class body must yield a declaration while the same call in
`__init__`, a test or a realization must yield a node. The only
deterministic hook around the execution of a class body is the metaclass:
`__prepare__` runs before the body and hands the class statement the
namespace the body executes in. `NodeMeta.__prepare__` returns a namespace
of a private type, and `AbstractBaseNode.__new__` recognizes an executing
body by finding that namespace as the locals of a frame on its stack: while
a node class body is executing it returns a `ChildDeclaration` capturing the
class, args and kwargs, and Python skips `__init__` because the returned
object is not an instance of the class. Outside a class body construction is
untouched.

*Implementation note (2026-09-01).* The ratified text had `__prepare__`
increment a depth counter that the metaclass `__new__` decrements. The
implementation found that a body that raises — which the algebra does on
purpose, on `import` — never reaches `__new__`, so the counter would stay
stuck and every later construction would yield declarations. The namespace's
identity on the stack carries the same decision without that failure: an
aborted body is no longer on the stack. The same namespace names each
declaration as it is assigned, which is what lets a dimension error in the
next line say `bore` and `pressure_angle`. The per-class scans for parameters,
formulas and children read the class dictionaries base-first and are cached,
like the port and driver scans.

Consequences accepted by the pilot:

- `CadQueryNode`'s existing `CheckCQEditor` metaclass derives from
  `NodeMeta`; Python requires a derived class's metaclass to subclass every
  base's metaclass. A project defining its own node metaclass must do the
  same, which the docs say beside `CheckCQEditor`.
- Any node constructed while a node class body executes becomes a
  declaration, even through a helper function. That is the intended
  meaning of the position.
- A legacy class that constructed a node at class level relied on a shared
  instance; it now holds a declaration the framework realizes per instance.
  That pattern was the bug the reference's probe found.

Alternatives: frame inspection (`sys._getframe`) to recognize a class-body
frame is fragile under helpers and interpreters; intercepting the
namespace's `__setitem__` is too late because the node has already been
constructed with side effects (build directories, source closure); an
explicit `Child(Piston, ...)` wrapper was the rejected earlier draft's
syntax and is exactly what the settled reference removes.

### D3. One algebra, two runs: formulas carry dimensions and evaluate later

Every declared parameter is a `Formula` leaf (a token); operators on tokens
build a formula tree whose dimension is computed at construction, so a
mismatch raises `DimensionError` in the class body, on `import`. At
instantiation the same tree is evaluated against the instance's bound
values, producing a plain `float`, `int` or `bool`. One implementation, run
once symbolically and once concretely.

A dimension is a mapping from axis name to integer exponent: `Length` is
`{'L': 1}`, `Angle` is `{'A': 1}`, `Count`, `Ratio` and plain numbers are
`{}`. Multiplication adds exponents, division subtracts, integer powers
scale, and addition, subtraction and comparison require equality. `Angle`
gets its own axis because the reference makes it a quasi-dimension: the
degree-trig discipline of `kinematics.py` becomes a type fact. A project
extends the ontology by subclassing `Quantity` with its own `dimension`
(`class Torque(Quantity): dimension = {'M': 1, 'L': 2, 'T': -2}`); the engine
never enumerates kinds.

`Count` and `Ratio` share the dimensionless exponent, so `teeth + fraction`
passes the algebra. Giving `Count` its own axis would refuse `teeth *
module` producing a plain length and `count / 2` producing a plain
fraction, the cases the reference wants without special rules. The algebra
catches dimensional mistakes; `Count` versus `Ratio` is a naming
distinction for humans. Integrality is a constraint on a declared `Count`,
checked at instantiation, not a property carried through formulas.

Functions take part through `solid_node.math`, whose `sin`, `cos`, `tan`,
`asin`, `acos`, `atan`, `atan2` and `sqrt` already dispatch between a
numeric and a symbolic-time mode; they gain a third, formula mode, so one
name works on tokens, numbers and symbolic time. The dimension rules:
`sqrt` requires even exponents and halves them; the trig functions require
an `Angle` and return dimensionless; the inverse trig functions require a
dimensionless argument and return an `Angle`. The evidence for this is
windmill's parameter layer, whose `input_pitch_angle`, `outer_cone_distance`
and `drive_axis_y` use `atan`, `sqrt` and `cos` and feed the bevel gear
children; arithmetic alone would have left those parents with a hand-written
`__init__`.

`Scalar` is the escape hatch: its dimension is unchecked, and any operation
involving a Scalar yields an unchecked Scalar. `.value` on any token or
formula yields the unchecked form of the same expression, so nothing is
inexpressible, only inconvenient. `Flag` is outside the algebra: arithmetic
on it raises. Operators supported: `+`, `-`, `*`, `/`, unary `-`, `**` with
an integer exponent, with plain numbers on either side. Comparison
operators raise in the declaration layer; a comparison belongs in
`render()`, on concrete values.

### D4. Parameters are data descriptors; a default is optional

A parameter declaration (`bore = Length(30.0, min=0)`) is a data
descriptor. On the class it returns itself (the token, usable in
formulas); on an instance it returns the resolved concrete value from a
private per-instance slot (`instance.__dict__['_parameters']`, a private
key so `_attr_name_for`'s name derivation sees exactly what it sees
today). `__set__` raises, exactly as `DriverDeclaration` does, so
`self.bore = 5` cannot shadow a declaration. `__set_name__` refuses a name
that would shadow a non-declaration attribute of any base (`name`, `time`,
`mesh`, `children`, `color`, `rigid`, ...); redeclaring an inherited
parameter stays legal, subclass wins.

A declaration may omit its default: a value that depends on the parent has
no sensible default, and inventing one would be the quiet mistake the
change removes. The error is at instantiation, never at class definition:
when neither the parent's declaration nor the caller (Python or the command
line) supplies the value, construction raises naming the class and the
parameter. This is what happens when the command line loads such a node
directly without `--set`, and it is the honest outcome.

A bare formula assigned in the class body (`piston_diameter = bore - 2 *
wall_clearance`) is found by `NodeMeta.__new__` in the namespace and
wrapped into the same descriptor kind with no default and no constraints:
read on an instance it is the evaluated value, assignment raises, and it is
not settable from a parent or the command line. `declared_parameters(cls)`
enumerates declared and derived parameters base-first with a per-class
cache, mirroring `declared_ports` and `declared_drivers_of`.

Resolution coerces: `Length`, `Angle`, `Ratio` and `Scalar` to `float`,
`Count` to `int` (refusing a non-integral value), `Flag` to `bool`
(refusing anything but a boolean). Constraints (`min=`, `max=`) are checked
on the resolved value. Coercion is what keeps `Piston(diameter=30)` and
`Piston(diameter=30.0)` one artifact; a legacy call that passed an integer
length re-keys once after migration, and the changelog says so.

### D5. Child declarations realize per instance, in declaration order, top-down

`NodeMeta.__new__` records, in namespace order, every attribute holding a
`ChildDeclaration`, a literal `list` of them, or a `RepeatDeclaration`
(`Piston(...).repeat(count)`); `declared_children(cls)` enumerates them
base-first with a per-class cache.

Construction order for an instance of a class that declares parameters or
children, all inside `AbstractBaseNode.__init__`:

1. Reject positional arguments (declaration order is a reading order, not
   a call order) and unknown keywords (today a silently hashed no-op), with
   a `TypeError` listing the declared names. Resolve declared parameters
   from kwargs, defaults filling the rest; raise for a missing one with no
   default. Evaluate derived formulas. Coerce and check constraints.
2. Compute `uniq_id` from the class and the resolved declared values (D6).
3. Base construction as today: name, source, build directories, artifact
   paths, source closure.
4. Realize declared children in declaration order: evaluate each
   declaration's kwargs (tokens and formulas against this instance's values;
   plain values pass through; `name=` passes through), construct the child
   outside any class body so it is a real node, and store it in
   `self.__dict__[attr]` — a plain attribute, a list, or the `repeat` list —
   so `_link_child`/`_attr_name_for` derive names exactly as today, with
   zero change to naming, qualification or the serialized document.

A child's class may itself be legacy (an `__init__` that takes kwargs):
realization just calls it with the resolved kwargs. Declarative and legacy
classes mix freely in one tree. A subclass with its own `__init__` sees its
realized children after `super().__init__()` returns.

Reading an attribute off a `ChildDeclaration` in a class body raises,
naming the two attributes and advising that the shared parameter be
declared on this class and passed to both children.

### D6. Identity is the class plus the resolved declared values

For a declarative class `uniq_id` is `_build_uniq_id(cls, (), resolved)`,
where `resolved` maps each *declared* (not derived) parameter to its
resolved value. The existing canonical serialization (class qualname, then
kwargs sorted by key, `str()` of each value) is reused unchanged, so a class
migrated with the same parameter set it used to forward keeps its key, and
a class that used to forget a kwarg gets a new, correct one. `name` stays
out of identity. Derived values are excluded because they are functions of
the declared ones and would only lengthen the readable prefix.

`repeat(count)` realizes count-many instances with identical resolved
values; by the existing "identical instances share artifacts" rule they
share one `uniq_id` and one artifact, which is the BOM and build win the
reference wants. The list names `<attr>-0 .. <attr>-(count-1)` are declared
identity: an omitted member leaves the others' indices untouched, because
names derive from the position in the realized list, not from the rendered
subset.

Rebuild semantics need no new mechanism. Artifacts are keyed by resolved
values, so `Engine()` and `Engine(bore=32.0)` coexist on disk and switching
back is a cache hit; a child whose parameters do not depend on the changed
value keeps its key and is not rebuilt; the published build describes one
parameter set at a time. The build's existing sweep of unreferenced
artifacts bounds the disk cost, as it does for differing kwargs today.

### D7. Root parameters from the command line

Every command that loads a node accepts `--set name=value`, repeatable,
registered once beside the shared `reference` positional in
`cli.add_command_parser` so no command re-declares it. The loader
constructs `klass(**overrides)` instead of `klass()`. The declared kind
gives parsing: `Length`, `Angle`, `Ratio` and `Scalar` parse a float,
`Count` an int, `Flag` one of `true`/`false`; constraints apply as they
would from Python. An unknown name fails listing the root's declared
parameters; a root that declares nothing refuses the flag; a derived
parameter is not settable. The develop loop constructs a `Builder` per
reload from the same path, so the overrides travel beside the path into
every `Builder` it starts and survive reloads.

The enumeration the flag reads is the same one a serializer table would
publish and a viewer would draw knobs from later. The command line is the
first consumer; nothing here forecloses the second.

### D8. Port assignment binds

`Port.__set__(instance, value)` performs the same binding `connect(value,
port)` performs, scale applied, so `unit.crank = angle + THROW_PHASES[pin]`
is legal in `render()`. Making `Port` a data descriptor also means an
assignment can no longer silently shadow a port declaration with a raw
value, which today would break `FlexibleNode.bound_values()` later.
`connect()` remains for the port-to-port form and for readers who prefer
the explicit verb.

Drivers on repeated units stay where they are: `driver_id` already refuses
a `<attr>-<index>` path segment because the id must be a legal identifier
in the runtimes that evaluate expressions, so a driver declared on a
`repeat` member or a literal-list member cannot be qualified. Ports fed per
unit from the parent's `render()` are the drive path for identical units,
and the docs say so beside `repeat`.

### D9. Loader and realization order

`load_node` constructs the root with the command line's overrides, or with
none, and still calls `bind_declared_defaults`. Realization is top-down
because each child is constructed by its parent's `__init__` with values
already resolved, so by the time any `render()` runs every parameter is a
plain value.

## Risks / Trade-offs

- [Metaclass on every node class] → It counts body depth and scans the
  namespace once per class; the one framework metaclass is rebased, and a
  project metaclass must derive from it, documented beside `CheckCQEditor`.
- [Artifact re-keying on migration] → Only classes that previously omitted a
  parameter from `super().__init__()` or passed an integer where a float
  kind now resolves change key; a one-time rebuild, noted in the changelog.
- [`Port` becomes a data descriptor] → A project that today assigns a raw
  value to a port attribute would have shadowed the declaration and broken
  later reads; now the assignment binds. No project in the corpus does
  either.
- [Structure stability check needs a first render to record] → The first
  render of an instance defines its structure; the check catches a
  time-conditioned omission on the second instant at the latest, and the
  symbolic pass catches it on the first.
- [`None` from a leaf `render()`] → Stays the error it is today; the
  substitution applies to internal nodes only.
- [Class-body construction changes meaning for a legacy class that did it]
  → The old meaning was a shared mutable instance, an error the reference's
  empirical probe documents; the new meaning realizes one child per parent.
- [A node without defaults is not loadable bare] → By design: the value
  depends on the parent, and the command line states it with `--set` when
  loading such a node directly.

## Migration Plan

Additive: no existing class changes behaviour unless it declares. Deploy is
a release like any other; rollback is reverting the change. The originating
projects (v8-engine, windmill) migrate afterwards on a shop floor and are the
validation step of the chain the shop contract describes; that is also where
a case for sideways reads or an enumerated kind would surface, if one
exists.

## Open Questions

None. Every open point of the reference and every conflict with the
existing framework was resolved with the pilot on 2026-09-01 and is
recorded in the decisions above.
