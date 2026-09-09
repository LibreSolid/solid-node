## Context

Cycle 3 of the three in `workflow/motion/roadmap.md`, and the last.
Cycle 1 made `solid_node.motion` and created `couplings.py` empty;
cycle 2 filled `joints.py` with `Revolute` and `Prismatic`, gave a
joint one coordinate that is a port, and let a parent WIRE one of its
own coordinates down into a child declaration. This cycle adds the
relation between two coordinates that are not in that parent-child
relationship, in either direction and at any depth.

Read from the source rather than from the design note
(`workflow/motion/joints-and-couplings.md`), the state this builds on:

- **A class body is a frame whose locals are a `_DeclaringNamespace`**
  (`node/declarative.py`, ADR-061). `in_class_body()` walks the stack
  for one — or, inside a PEP 709 inlined comprehension, for the plain
  `dict` COPY that still carries the `__solid_node_body__` mark. The
  namespace's `__setitem__` names each declaration as it is assigned,
  which is why a class-body error can say `bore` rather than describe
  an anonymous token. `NodeMeta.__new__` pops the mark before the class
  exists.
- **A sideways read is refused by `ChildDeclaration.__getattr__`**,
  which raises `SidewaysReadError` for every non-underscore attribute,
  with the advice to declare the shared parameter on the parent. It
  never consults the child's class.
- **A port is a data descriptor with a per-instance slot.**
  `Port.__get__` materializes a `BoundPort` under `_port_values`;
  `Port.__set__` calls `bind`, which applies the SINK's declared scale
  and refuses an unbound source. Cycle 2 makes a joint hold a `Port` as
  its `coordinate` and `declared_ports` report it under the joint's
  name. `DriverDeclaration` (`node/qualified.py`) is the same shape;
  its `__get__` reads `instance._states[name]` and its `__set__`
  refuses, because a driver's value belongs to the snapshot.
- **Every symbolic value is a solid2 `OpenSCADConstant`** and its
  arithmetic is string-eager (`core/expressions.py` docstring):
  `ratio * x + offset` builds a well-formed wire expression when `x` is
  a `DriverToken` or `$t`, and a plain number when it is one.
  `(y - offset) / ratio` does the same in the other direction. ADR-080
  interns the shared subexpressions when the document is published, so
  a chain solved backwards through four arbors does not publish four
  copies of its tail.
- **The lifecycle is `_sweep` → `_rest` → push SIMULATE →
  `self.simulate()` → [cycle 2: bind wirings] → pop**
  (`node/assembly.py`). An operation applied under a simulate phase is
  placed innermost, tagged with the simulating assembly and dropped by
  that assembly's next sweep (ADR-023, ADR-066).
- **`solid_node.mechanisms` is arithmetic, not vocabulary** (ADR-076).
  `meshed_angle(driver_angle, driver_teeth, driven_teeth,
  line_of_centres, driver_gap, driven_tooth)` is affine in
  `driver_angle`, and `driving_angle` is its algebraic inverse over the
  same six arguments. The package deliberately has no declared
  (class-body) face, because its degree literals cannot be typed by the
  dimension algebra.

The originating evidence:

- **Wall clock 01**, `simulation/shared/`. `Movement.arbor_angles`
  walks backwards from the escape wheel through
  `depthing.wheel_angle_for_pinion`, which is `driving_angle` with
  `gap_centre_angle(wheel)` as the driver's registration and
  `tooth_tip_angle(pinion)` as the driven one. Each step is
  `driven = A - (driver_teeth / driven_teeth) * driver`: an affine
  relation whose ratio is a tooth ratio negated because an external
  pair reverses, and whose offset is the registration and the line of
  centres. `motion_works_angles` is the same law twice with the pinion
  driving the wheel. `simulate_for_seconds` then fans the resulting
  dictionary into `TrainArbor.turn`, `Pendulum.swing`,
  `MotionWorks.minute_arbor` and the escapement's ports. The six-hour
  test asserts `hands.hour.value % 360 == 180` and the minute hand back
  at zero, and is the only place the twelve-to-one is stated.
- **Thor**, `simulation/`. Seven root `Driver`s forwarded by hand down
  five levels, with `Art3`, `Art4` and `Art56` declaring ports only to
  pass them on. Ratios at each stage: `BASE_RATIO = 50/10`,
  `SHOULDER_RATIO = 60/10`, `ELBOW_RATIO = 117/20`,
  `COLUMN_RATIO = -20/10`, the ball cage at `yaw / 2`,
  `CROWN_RATIO = 30/15` giving `wrist ± 2*tool`, `BELT_RATIO = 40/20`.
  Two non-ratio shapes: `Art2` turns its child by `elbow - shoulder`
  because the elbow belt is anchored on the shoulder housing, and
  `Art56.pinion_turns` returns `wrist + spin, wrist - spin`. Both belts
  are `travel = turn * (pi/180) * pitch_radius(teeth)`, written as a
  plain multiply rather than `math.radians` because under `solid build`
  the turn is a symbolic expression — a constraint every law in this
  cycle inherits.

## Goals / Non-Goals

**Goals:**

- One verb, `a.drives(b)`, that relates two coordinates wherever they
  are in the tree, and no second vocabulary.
- The law is project code handed to the framework, which never learns
  what a gear is and looks up no hook on any class.
- The author states the mechanical direction; the framework works out
  which way to solve it, per run, from what is actually bound.
- A root driver reaches a deep joint without a chain of forwarded
  ports.
- Everything stays symbolic, so a build still publishes expressions the
  viewer evaluates with the math it already has.
- Every failure fails by name, with the node paths, the relation as
  written, and the ends.

**Non-Goals:**

- Closed loops and their solver (the Thor gripper's parallelogram).
  Refused by name as an over-constrained coordinate; not solved.
- Stateful mechanisms: ratchets, engagement, neutral, backlash. A
  relation is a function of one value, evaluated fresh every run, with
  no memory of the last.
- Non-linear derived formulas. `a * b` between two coordinates,
  `sin(a)`, `a ** 2` in a class body are refused; that is what `law=`
  is for.
- Automatic driver-to-joint binding. A `Driver` reaches a coordinate
  only through an explicit `Driver.drives(...)`.
- MuJoCo or Modelica emission, mass and inertia, flow variables on
  ports.
- Refactoring wall clock 01 or Thor. That happens in their own
  repositories after this cycle; this cycle's evidence is the fixture
  train.

## Decisions

### 1. `drives` is a statement, registered on the class body that is executing

`drives` returns a `Relation` AND records it. Recording uses the same
mechanism ADR-061 already built: `_DeclaringNamespace.__init__` puts a
mutable list under a private key, `drives` walks the stack for the
nearest declaring namespace and appends to that list, and
`NodeMeta.__new__` pops it and stores the relations on the class.

The list is created ONCE, in `__init__`, and appended to — never
replaced. That is what makes a relation written inside a PEP 709
inlined comprehension work: the frame reports a plain `dict` copy of
the namespace, but the copy holds the same list OBJECT, so the append
lands on the real one. Rebinding the key would silently lose it. This
is the same trap the comprehension refinement in ADR-061 records, met
from the other side.

`drives` called with no class body on the stack is refused by name: a
relation is class metadata, and there is no instance-time `drives` to
mistake it for. `drives` called in a class body that is not an
`AssemblyNode` subclass is refused when the class is created, for the
reason `Time.__set_name__` refuses a time base on a leaf: only an
assembly has a `simulate()` phase, and the solver runs at the end of
one. The check is a local import of `AssemblyNode` inside
`NodeMeta.__new__`, taken only when the class carries relations, so no
import edge is added.

`declared_relations(cls)` walks the MRO base-first and concatenates,
de-duplicating by object identity. Relations are statements, not names:
a subclass does not override a base's relation, it adds to it. A
subclass that must remove one is a design the framework does not serve
this cycle, and it is recorded as an open question rather than half
built.

**Naming is optional and useful.** `great = power.drives(centre)` goes
through `_DeclaringNamespace.__setitem__`, which names the `Relation`
as it names a declaration — so the relation's own repr, and every error
message about it, can say `great` instead of describing it positionally.
Read off the class, the name yields the declaration. Read off an
instance, it yields that instance's record: the two resolved
coordinates, the law, and which way it was solved on the last run.
That is what lets a test assert the clock solved backwards rather than
asserting only the resulting angles. `Relation` is a NON-data
descriptor, like `ChildDeclaration`, so nothing about attribute
shadowing changes.

### 2. An end is a coordinate, and every kind resolves to one at realization

Five kinds of reference, all sharing one `CoordinateRef` base that
carries `drives` and the arithmetic of decision 4:

| Written | Kind | Resolves per instance to |
|---|---|---|
| `swing` (a port or joint on this class) | own coordinate | this instance's own `BoundPort` slot |
| `centre` (a child declaration) | node | the realized child's ONE joint's coordinate |
| `anchor.turn`, `shoulder.art2.art3.wrist` | path | the realized descendant's coordinate |
| `art2` (a `Driver` declaration) | driver | the driver's value, source only |
| `art3.elbow - shoulder` | derived | the class's derived coordinate |

**A node end means its one joint.** A node with no joint, or with more
than one, is refused AT CLASS DEFINITION naming the child attribute,
its class, and the joints that class declares — the child's class is
known statically on the `ChildDeclaration`, so there is nothing to wait
for. This is the whole reason `power.drives(centre)` reads as well as
it does: an arbor is one body turning at one bearing, and a class that
is not is told to name the coordinate.

**A `Driver` is a source only.** A driver's value belongs to the bound
snapshot and `DriverDeclaration.__set__` already refuses assignment; a
relation may not do by the back door what an assignment may not do. A
driver as the driven end is refused at class definition, naming the
driver and repeating `set_state`'s advice.

**Resolution happens at realization, at the END of the instance's
construction, after its children are realized** — later than cycle 2's
joint arguments, which resolve before children, because an end may be a
child or a descendant of one. A path that does not resolve on the
instance fails there by name: the attribute, the path as written, the
node it stopped at, and what that node does declare.

What is checked at class definition versus at realization follows one
rule: **anything the classes alone decide is refused at class
definition**, because the classes are all known there — an unknown
attribute anywhere along a path, a node end with the wrong number of
joints, a driver as a driven end, `ratio=` together with `law=`, a
derived formula that is not linear. Anything that depends on which
children an INSTANCE actually has — a child `omit()`ed, a legacy
non-declarative child class, a path through a class whose attribute is
resolved late — is refused at realization.

**A path through a repeated or list-held child is refused at class
definition.** `units.turn` where `units = Unit().repeat(count)` names
`count` coordinates, and a relation has one end. Told at class
definition, with the advice to declare the relation inside the repeated
class instead — which works, because relations of a class apply per
instance of that class (decision 6).

### 3. The law protocol is `forward` and, optionally, `inverse`

`Affine(ratio, offset=0)` is a frozen dataclass in
`solid_node.motion.couplings`, the only new importable name:

```python
forward(x)  ->  ratio * x + offset
inverse(y)  ->  (y - offset) / ratio
```

Plain arithmetic, deliberately: with a `DriverToken` or `$t` for `x`
these build the wire expression solid2 builds, and with a number they
give a number.

**The class that carries the arithmetic is solid2's
`OpenSCADConstant`** — `$t` is one, and `DriverToken`
(`node/qualified.py`) subclasses it. The INVERSE leans on more of its
operator surface than the forward face does: `y - offset` and the
number-on-the-left forms come from `__roperator_base__`, `/ ratio`
from `__truediv__`, and unary negation from `__unary_operator_base__`.
All three exist and produce fully parenthesised text — `(($t - 0.5) /
-3.5)`, `(-$t)`, `((1 - $t) / 2)` — which `core/expressions.py` parses
and ADR-022's runtimes evaluate. That is a dependency on another
package's operator set, so it is PINNED by a test rather than assumed:
task 1.11 solves backwards from a `$t` expression and from a
`DriverToken` and evaluates the published string through the same
helper the parity tests use (`_eval_openscad_expr` in
`tests/test_math.py` and `tests/test_mechanisms.py`), asserting it
equals the numeric answer. `invertible` is false only when the ratio is a number
equal to zero; a symbolic ratio is taken as invertible, because the
division is as well-formed as the multiplication and refusing it would
mean deciding a value the framework does not have.

The clock's evidence is that this is enough: `meshed_angle` and
`driving_angle` are one `Affine` and its inverse, which is why the
project can stop writing the second one.

`ratio=` and `offset=` are shorthand for `Affine`, and their values are
resolved per instance by the same `evaluate(arg, values)` a child
declaration's arguments use, so `ratio=teeth_ratio` over a declared
parameter works as `ratio=117/20` does. `ratio=` or `offset=` together
with `law=` is refused at class definition — two ways to state one law
is a mistake, not a composition.

`law=` is a callable of two arguments, called **once per parent
instance at realization**, immediately after the ends resolve. Its
arguments are **the realized nodes that OWN the two coordinates**,
driver first:

- a node end → that realized node;
- a port or joint end on this class → the instance the relation is
  declared on;
- a path end → the realized descendant that DECLARES the named port or
  joint (for `a.b.wrist`, the realized `a.b`), or the named node itself
  when the path ends on a node;
- a derived end → the instance the derived coordinate is declared on;
- a driver end → the instance declaring the driver.

One rule, stated once: the owner of the coordinate. So a law reads
`driver.built`, `driver.index`, `driver.wheel_teeth`, a parameter, or
anything else a realized node has — which is exactly what the clock's
`going_train` needs, because the tooth counts and the gap angles come
off the built library movement and not off a formula.

The return value must be a law: an object with a callable `forward`,
and `inverse` when it has one. A plain function or lambda returned is
wrapped as forward-only. Anything else is refused at realization,
naming the relation, the callable and what it returned. The framework
inspects nothing further — no registry, no shape list, no `law_for`
hook on a node class. **The pilot rejected a class hook explicitly**:
a hook makes "what an arbor drives" a property of a class the framework
has to look up, which is the vocabulary this whole layer was chosen to
avoid. A law is a value passed in.

Calling `law=` once per instance at realization, rather than per run,
is deliberate: a law is a property of the assembled machine — tooth
counts, registration, pitch radius — and nothing about it changes
between two instants. Per-run evaluation would run project code inside
every frame of an animation for no gain.

### 4. A derived coordinate is a linear formula, and it is a coordinate

`CoordinateRef` implements `+`, `-`, unary `-`, and `*` and `/` by a
number, token or derived formula, accumulating a `DerivedCoordinate`:
a mapping from reference to coefficient, plus a constant. `ref * ref`,
and any other operator, raise at class definition naming both operands
and pointing at `law=`. Keeping the algebra to a mapping rather than an
expression tree is what makes the backward solve exact and cheap; the
whole shape is the one MuJoCo writes as a `tendon/fixed`.

A derived coordinate assigned in a class body is named by
`_DeclaringNamespace.__setitem__` like every other declaration, and
reads on an instance as a `BoundPort` in the same `_port_values` dict
the class's ports live in, so a test reads `self.relative_elbow.value`
exactly as it reads a port. `declared_ports` reports it beside them.

Its domain and unit come from its terms: every term must share a
domain, and every term that states a unit must state the same one, or
the class is refused at class definition naming the two terms that
disagree. A coefficient converts a magnitude, never a domain.

Solving it is one equation, `d = Σ cᵢ·xᵢ + k`, treated by the solver
as a relation of its own: forward when every term is bound, backward
when `d` and all but one term are bound, and unsolvable — reported as
an unreached coordinate naming the formula and each unbound term — when
two are missing. Both directions are the same arithmetic, so both stay
symbolic.

### 5. The solver runs at the end of the owning instance's simulate phase

The framework cannot know what is bound until `simulate()` has run, so
the solver cannot run at realization. It runs inside `_lifecycle_render`
after `self.simulate()` returns, while the phase is still this
assembly's — which is what makes every motion a relation causes carry
this assembly's animator tag and be dropped by this assembly's next
sweep, exactly as a hand-written rotation is.

**Cycle 2's wirings are absorbed into that solve.** Cycle 2 binds them
at a fixed point at the end of the phase, before anything else could
have run; this cycle makes them the forward-only relation they already
are — the identity law from the parent's coordinate to the child's end,
binding through the same path so the child's declared scale still
applies — and lets them take part in the same fixpoint. The clock forces
it: `Movement` solves `centre.turn` through a relation, and `TrainArbor`
then wires that same coordinate down into the wheel and the rod that
turn with it. Bound before the relations, that wiring finds its source
unbound and refuses by cycle 2's own rule. Bound inside the fixpoint, it
waits one iteration and binds. Cycle 2's other rules are untouched: an
unbound source when propagation has FINISHED is still refused by name, a
hand binding of a wired child end is still refused, and a wiring is
still a binder, so a relation reaching the same child end is a double
binding. This is the one place cycle 3 reworks cycle 2's code rather
than adding beside it, and task 4.1 says so.

**Relations of a class are solved for each instance of that class, in
that instance's own phase.** A relation declared on a descendant class
is therefore solved when that descendant renders, which is AFTER the
ancestor's phase ended. That ordering is the useful one and it is
stated rather than discovered: an ancestor's relation reaching a deep
coordinate by path binds it BEFORE the deep node's own relations run,
so the ancestor's value is the descendant's boundary condition. Thor
reads that way — the root's `art3` driver reaches the elbow, and `Art2`
then solves `elbow - shoulder` against it.

A relation whose two ends live in different subtrees needs nothing
extra: both path references resolve from the declaring instance, so a
relation on the root may reach any two points of the tree.

The alternative — one global solve over the whole tree at the root —
was rejected. It needs a second enumeration of a tree the render
already walks, it has no phase to tag its motion with, it breaks the
one-assembly-owns-its-motion rule ADR-066 rests on, and it gives a
relation on a repeated child no per-instance identity.

### 6. Freshness, propagation, and what "bound" means

A value slot keeps what was put into it, and nothing clears it. That is
harmless while an author binds everything by hand — cycle 2's rebinding
is absolute — but it breaks a solver outright. After run 1 the solver
has bound `third.turn` and `centre.turn`; at the end of run 2 every
coordinate still "holds a value", the fixpoint finds nothing with
exactly one bound end, and the author's fresh `escape.turn` is either
refused against the stale values as doubly bound or simply ignored,
leaving the train frozen at the first instant. So **freshness is part of
the rule, not an implementation detail**:

> At the start of an assembly's simulate phase, BEFORE the author's
> `simulate()` runs, the framework clears the value and the binder
> record of every coordinate this assembly bound through a wiring or a
> relation in its previous run.

It knows which ones because it recorded them when it bound them — the
same bookkeeping cycle 2 keeps for a joint's applied operations, and the
same shape as `_sweep` dropping this assembly's own tagged operations.
What survives the clear is exactly what should: a value this author's
`simulate()` binds in the current run, a value an ancestor's wiring or
relation already applied in this walk, and a driver read. A value the
author bound in an EARLIER run and did not bind in this one is NOT
cleared — an author's binding is the author's responsibility today and
stays so; the framework clears only what the framework bound.

For one instance, at that moment:

1. **Inventory.** Every coordinate named by this class's relations
   and wirings is
   bound or not; a coordinate is bound when its slot holds a value.
   Each binding also records its BINDER for the current enumeration of
   the tree: the author's `simulate()`, a wiring, a relation (which
   one), or a driver read.
2. **Propagate to a fixpoint.** Repeat while anything changes: any
   relation with exactly one bound end is applied from that end —
   forward through `law.forward` when the driver end is bound, backward
   through `law.inverse` when the driven end is — and any derived
   coordinate with at most one unknown is solved. Every wiring the class
   declared is in the same fixpoint, applied as soon as its source is
   bound. Order within a pass
   is declaration order, which makes the result deterministic and the
   error messages stable, but the fixpoint makes it order-independent:
   the clock's three relations are written power-first and solved
   escape-first without the author reordering anything.
3. **Refuse, by name, naming node paths, the relation as written and
   the ends:**
   - `UnreachedCoordinate` — a coordinate still unbound when nothing
     changes any more. Its message names what the coordinate is waiting
     for; for a derived formula with two unknowns it names the formula
     and both.
   - `DoublyBound` — a relation would bind a coordinate that something
     else already bound in this enumeration. That covers author plus
     relation, two relations, and wiring plus relation, and it also
     covers a relation whose two ends are BOTH already bound by other
     binders, which is an over-constrained loop.
   - `NotInvertible` — the driven end is the bound one and the law
     offers no `inverse`, or is an `Affine` whose ratio is numerically
     zero.

**Two relations that would give the same value are still refused.** The
framework cannot check agreement: the values are usually symbolic
strings, and two expressions that differ textually may or may not be
equal. Comparing them would be a promise the expression layer does not
make, and a silent first-writer-wins would hide a real modelling
mistake. The pilot's preference and the safe answer agree here, and
`DoublyBound`'s message says so and names both binders.

**A relation binds through the same path an author binding takes**
(`bind`, and `Joint.__set__` for a joint), so the sink's declared
`scale` applies exactly as it does to a wiring, a joint's range check
fires exactly as it does for a hand binding, and a joint's body is
placed with the same operations and the same tag. There is no second
binding path and no unit conversion anywhere in this cycle: what
converts is the ratio the author wrote.

### 7. The sideways relaxation, and what stays refused

`ChildDeclaration.__getattr__` now looks the attribute up on
`self.node_class` before raising:

- a `Port`, a `Joint`, a `ChildDeclaration` → a path reference;
- a `RepeatDeclaration` or a list of declarations → refused, ambiguous
  (decision 2);
- anything else, a declared parameter above all → the
  `SidewaysReadError` it raises today, with the same advice.

ADR-061's rule is extended, not reversed, and the substance of its
reasoning survives intact: a class body still may not read a sibling's
VALUE, because a parameter is a number that belongs to a realized
instance and a class body has none. A port or a joint is not a value —
it is a place a value will be, and naming a place from a class body is
what a declaration has always done.

A `Driver` read off a declaration is refused: a driver is read from a
node's snapshot, and reaching one sideways would put a second address
on a value ADR-056's qualification exists to give exactly one. A root
driver reaches a deep coordinate by `driver.drives(path)`, which is the
supported direction.

### 8. Records

- `docs/adrs/NODE/ADR-089-drives-relates-two-coordinates.md` (087 is
  cycle 1's, 088 is cycle 2's). Written during apply, so it records
  what the code does: the one verb and why there is no second
  vocabulary; the law as project code passed in, with the rejected
  `law_for` class hook named as rejected; resolution oriented from the
  bound side, per run, at the end of the owning simulate phase; the
  three refusals; the narrow sideways relaxation. Extends ADR-061 and
  ADR-066, depends on ADR-076 and ADR-088.
- New baseline capability `couplings`; deltas to `declarative-nodes`,
  `joints`, `ports`, `simulation`, `kinematics` and
  `cli-startup-cost`.
- `docs/architecture.md`: Kinematics gains the relation and when it is
  solved; Expression math gains the affine lowering; Mechanisms gains
  the sentence that its laws are the arithmetic a project's `law=`
  composes, still not vocabulary.
- `docs/declaring.rst` (the verb, path references, derived
  coordinates), `docs/driving.rst` (a driver reaching a joint by path,
  and the direction of a relation), `docs/api-reference.rst`,
  `docs/changelog.rst` "Unreleased".
- `workflow/motion/roadmap.md` Progress table, row `3 couplings`.

**Checked and needing no delta:** `mechanisms` — its laws are unchanged
and are still arithmetic a project composes, and this cycle adds no
function to it; the sentence about their relationship to `law=` is
architecture, not a requirement. `node-model` — a relation is not a
parameter, not a child and not identity. `flexible-parts` — a
flexible leaf's `travel` is an ordinary port and is driven as one,
which is the point.

## Risks / Trade-offs

- **A per-run solve is project code in the frame loop** → no: `law=`
  runs once per instance at realization (decision 3), and a run does
  arithmetic over a fixed mapping. What a run costs is one pass per
  relation per instance.
- **Backward solving builds nested symbolic strings**, one wrapping per
  arbor, and the clock's train is four deep → ADR-080's interner
  publishes each distinct subexpression once, and the fixture asserts
  the published document rather than the string built in memory. If a
  deeper train ever makes this a size problem it is a document problem
  with a document fix, not a reason to make the solver numeric.
- **`DoublyBound` refuses a redundant but consistent model** — two
  relations that happen to agree → deliberate (decision 6), and it will
  eventually be somebody's annoyance. The alternative is comparing
  expressions for equality, which the framework cannot do. Recorded as
  an open question with a possible explicit escape (`allow_redundant=`)
  rather than a silent one.
- **A closed loop fails as `DoublyBound`, which is a true statement in
  unhelpful words** → the message names both binders and both paths, so
  the loop is visible in it; a real loop solver is out of this cycle
  and stays named as out.
- **Order within a run is declaration order and the solve is a
  fixpoint**, so a model with a genuine ambiguity gets a deterministic
  answer rather than an error → there is no such ambiguity in a set of
  relations with one bound side per component: the fixpoint is unique,
  and every over-constrained case is `DoublyBound`. The determinism is
  there for the messages.
- **Relations are inherited and cannot be removed by a subclass** →
  a real limitation, recorded as an open question. Composition (a
  subclass that adds) is what every project in the evidence needs; a
  subclass that must break an inherited relation can declare the
  coordinate by hand today.
- **The sideways relaxation makes a class body able to reach far** —
  `shoulder.art2.art3.art4.art56.wrist` from the root → that is the
  requirement Thor states, and the alternative is the thirty lines of
  forwarding it exists to remove. The path is checked against the
  classes at class definition, so a typo in it is a class-definition
  error, not a mystery at runtime.

## Migration Plan

Additive. No import moves, no existing declaration changes meaning, and
no project has to do anything to keep working. The one rule that
changes is the sideways read, and it changes from refusing to
permitting for three attribute kinds, so no class body that works today
stops working. A project adopts relations by deleting its own
transmission arithmetic, one node at a time. Rollback is `git revert` of
the two cycle commits.

## Open Questions

None blocking. Recorded, not decided here:

- Whether a subclass should be able to remove or replace an inherited
  relation, and with what syntax.
- Whether `DoublyBound` should have an explicit escape for a model that
  wants two relations to state the same thing, and whether that escape
  should check agreement numerically under `set_state`.
- Whether a non-invertible law should be allowed to declare a numeric
  inverse — a bisection over its forward face — for the escapement-like
  case where an inverse exists but is not analytic.
- Whether the serialized document should carry a relations table
  alongside the joints table cycle 2 left open. Both belong to the
  MuJoCo/Modelica emission discussion the roadmap defers to the pilot.
- Whether a relation should be able to state a range or a backlash, and
  where a stateful mechanism would attach if one is ever added.
