## 1. Red first: the fixture and the tests that fail on the current tree

- [ ] 1.1 Write `tests/coupling_project/`, in the style of
  `tests/joint_project/`: an `__init__.py`, a `parts.py` with simple
  `Solid2Node` leaves (a wheel, a rod, a pulley, a belt carrying a
  `TranslationalPort` named `travel`), and a `train.py` holding
  (a) `Arbor(AssemblyNode)` declaring
  `wheel_teeth = Count(...)`, `pinion_teeth = Count(...)`,
  `registration = Angle(0.0)` and
  `turn = Revolute(axis=(0, 0, 1), at=<per-index bearing>, unit='deg')`
  with the two leaves wired from `turn`;
  (b) `Train(AssemblyNode)` declaring three arbors `power`, `centre`,
  `escape` with real tooth counts, stating
  `power.drives(centre, law=mesh)` and `centre.drives(escape, law=mesh)`
  in POWER-FIRST order, and binding ONLY `escape.turn` in its
  `simulate()` — the clock's shape, solved backwards;
  (c) a `mesh(driver, driven)` law in the fixture returning
  `Affine(ratio=-driver.wheel_teeth / driven.pinion_teeth,
  offset=driven.registration)`, reading both off the realized nodes;
  (d) an `Arm(AssemblyNode)` root declaring `shoulder`/`elbow`/`tool`
  `Driver`s and stating `elbow_driver.drives(upper.art3.elbow)` by
  path; (e) `Upper(AssemblyNode)` declaring `shoulder = Revolute(...)`,
  a child `art3` declaring `elbow`, `relative = art3.elbow - shoulder`,
  `relative.drives(pulley.turn)` and
  `pulley.turn.drives(belt.travel, ratio=PITCH_ARC)`;
  (f) a `Wrist` declaring `wrist`, `tool`, `left = wrist + 2 * tool`
  and `right = wrist - 2 * tool`.
- [ ] 1.2 `tests/test_couplings.py`, the statement: `drives` on a child
  declaration, a port, a joint, a `Driver`, a path reference and a
  derived coordinate, with no import; a bare statement is recorded on
  the class and enumerable off it; a named relation is recorded ONCE,
  is named, reads off the class as the declaration and off an instance
  as its record; a relation written inside a class-body comprehension
  is recorded; a subclass adds to its base's relations; `drives`
  outside a class body raises; a relation on a non-assembly class
  raises at class creation.
- [ ] 1.3 Ends: a port/joint of the class, a node standing for its one
  joint, a path of three segments, a `Driver` as source, a derived
  coordinate; a node with no joint and one with two each raise at class
  definition naming the class and its joints; a `Driver` as the driven
  end raises at class definition; a misspelt path segment raises at
  class definition naming the path and what that class declares; a path
  through a `repeat()` raises at class definition; a path that cannot
  resolve on the instance raises at realization; reading a declared
  PARAMETER off a declaration still raises `SidewaysReadError` with
  today's message; reading a `Driver` off a declaration raises.
- [ ] 1.4 `Affine`: forward and inverse on numbers; the same on a
  symbolic driver token, giving an expression that evaluates to the
  numeric answer; `ratio=0` numerically is not invertible while a
  symbolic ratio is; `ratio=`/`offset=` as tokens resolve per instance;
  `ratio=` with `law=` raises at class definition.
- [ ] 1.5 The law protocol: a `law=` callable is called ONCE per
  realized instance, at realization, with the two realized OWNERS in
  driver-then-driven order — assert the exact objects for a node end, a
  path end whose last segment is a joint, a port of the declaring class
  and a derived end; a law reading a value off `driver.built` works; a
  returned plain function is forward-only; a returned non-law raises at
  realization naming the relation and what it returned; simulating at
  twenty instants calls the law no further times.
- [ ] 1.6 Derived coordinates: `a - b`, `a + 2 * b`, `-a`, `a / 2`
  build one; `a * b` and `sin(a)` raise at class definition naming both
  operands; terms of different domains or different units raise;
  reading the derived name on an instance yields a bound slot of the
  shared domain and unit; `declared_ports` reports it; forward solve
  with all terms bound; backward solve with exactly one unbound; two
  unbound raise naming the formula and both terms.
- [ ] 1.7 Freshness across runs: the three-arbor train enumerated at
  THREE successive instants re-solves at each one — the coordinates the
  assembly bound through a relation or a wiring in the previous run are
  cleared before the author's `simulate()` runs, so each instant
  produces its own angles, nothing is refused as doubly bound, and
  nothing stays frozen at the first instant; a coordinate the AUTHOR
  bound in an earlier run and not in this one is NOT cleared.
- [ ] 1.8 Wirings inside the fixpoint: an arbor whose coordinate a
  relation solves, wiring that coordinate down into two children, binds
  both in the same run rather than refusing an unbound source; a wiring
  whose source nothing ever binds still raises cycle 2's unbound-source
  error once propagation has finished; a relation reaching a wired
  child end is `DoublyBound`; cycle 2's refusal of a hand binding on a
  wired coordinate still fires.
- [ ] 1.9 The solver: the three-arbor train binds only `escape.turn`
  and solves `centre` then `power` through the inverses, with every
  arbor's body placed and the declaration order irrelevant (assert the
  same result from a fixture stating the relations escape-first);
  changing one tooth count changes the solved angles and nothing else
  is edited; the relation runs after the author's `simulate()` and
  after the wirings; motion caused by a relation is tagged with that
  assembly and swept before its next run; a relation on a repeated
  assembly solves per instance; an ancestor's relation by path binds
  before the descendant's own relations run.
- [ ] 1.10 The three refusals, each its own error kind exported from
  `solid_node.motion.couplings`, each message asserted to name the node
  paths, the relation (its name when named) and the ends:
  `UnreachedCoordinate` for a relation with neither end bound and for a
  derived formula with two unknowns; `DoublyBound` for author-plus-
  relation, wiring-plus-relation, two relations, and both ends bound by
  others — including two relations whose laws would agree, with the
  message saying the framework does not compare values; `NotInvertible`
  for a forward-only law needed backwards and for `Affine(ratio=0)`,
  while the same forward-only law used forwards passes.
- [ ] 1.11 Symbolic and numeric faces: a tree of relations serialized
  with nothing bound publishes expressions in the driver ids and `$t`;
  `set_keyframe`/`clear_keyframe` switch them; the same tree under
  `set_state` carries plain numbers; a chain solved backwards through
  three arbors publishes a document whose shared subexpressions are
  interned once (assert against the published bindings table, not the
  in-memory string). PIN the operator surface the backward solve
  depends on: solve backwards from a `$t` expression and from a
  `DriverToken` through an `Affine` with a negative ratio and a
  non-zero offset — which exercises solid2's `__roperator_base__`
  (`y - offset` and a number on the left), `__truediv__` and
  `__unary_operator_base__` — and evaluate the PUBLISHED string with
  the helper the ADR-022 parity tests use (`_eval_openscad_expr` in
  `tests/test_math.py` and `tests/test_mechanisms.py`), asserting it
  equals the numeric answer the same relation gives under `set_state`.
  Do the same for a derived formula solved backwards.
- [ ] 1.12 Cross-cycle: a relation into a scaled port applies the scale
  exactly once; a relation binding a joint past its `range` raises the
  joint range error; cycle 2's refusal of a hand binding on a wired
  coordinate still fires; a relation into a flexible leaf's `travel`
  port drives it.
- [ ] 1.13 Import cost: `solid_node.motion.couplings` in a fresh
  interpreter imports the same `solid_node` modules as
  `solid_node.motion.ports` but for itself, and no CAD backend; widen
  `tests/test_motion_package.py`'s expectation for it.

## 2. `solid_node/motion/couplings.py`

- [ ] 2.1 `Affine`, a frozen dataclass: `forward`, `inverse`,
  `invertible`, and a `__repr__` an error message can quote. Plain
  arithmetic only, so a symbolic operand rides through.
- [ ] 2.2 The law adapter: accept an object with `forward` (and
  optionally `inverse`), wrap a plain callable as forward-only, refuse
  anything else naming the relation and what was returned.
- [ ] 2.3 `CoordinateRef` and its kinds — own port/joint, node, path,
  driver, derived — each with `drives` and with the arithmetic of 2.4;
  a `resolve(instance)` that yields the coordinate slot and an
  `owner(instance)` that yields the realized node, both per the spec's
  one rule.
- [ ] 2.4 `DerivedCoordinate`: a coefficient mapping plus a constant,
  built by `+`, `-`, unary `-`, `*` and `/` by a number/token/formula;
  every other operator raises naming both operands and pointing at
  `law=`; domain and unit agreement checked where the formula is built;
  a bound value slot on the instance; forward and backward solve.
- [ ] 2.5 `Relation`: the two refs, the law or the ratio/offset pair,
  the optional name, `__set_name__`, the non-data `__get__` handing
  back the declaration off the class and the instance record off an
  instance, and a `__repr__` that reads like what the author wrote.
- [ ] 2.6 `UnreachedCoordinate`, `DoublyBound`, `NotInvertible`, and
  the message builder that names node paths through
  `instance_path`, falling back to name and class for an unlinked node
  as cycle 2's range error does.
- [ ] 2.7 The solver: inventory with binder identity, the fixpoint over
  relations and derived coordinates in declaration order, the three
  refusals, and binding through `bind`/`Joint.__set__` so scale, range
  and motion behave exactly as for a hand binding.

## 3. The class-body machinery

- [ ] 3.1 `declarative.py`: a mutable relations list created once in
  `_DeclaringNamespace.__init__` under a private key (never rebound, so
  a PEP 709 comprehension's dict copy appends to the same list); a
  `record_relation` helper walking the stack for the nearest declaring
  namespace, or raising when none is executing; `_DeclaringNamespace.__setitem__`
  naming a `Relation` and a `DerivedCoordinate` as it names a
  declaration; `NodeMeta.__new__` popping the list onto the class and
  refusing a non-`AssemblyNode` class that carries relations, by a
  local import as `Time.__set_name__` does; `declared_relations(cls)`
  walking the MRO base-first and de-duplicating by identity.
- [ ] 3.2 `declarative.py`: `ChildDeclaration.__getattr__` consults
  `self.node_class` before raising — a `Port`, a `Joint` or a
  `ChildDeclaration` yields a path reference, a `RepeatDeclaration` or
  a list of declarations raises as ambiguous, everything else keeps
  today's `SidewaysReadError` verbatim; `ChildDeclaration.drives`
  standing for the class's one joint, with the class-definition check
  of the joint count.
- [ ] 3.3 `ports.py` and `joints.py`: `drives` on `Port` and on
  `Joint`, both delegating to the couplings module through a local
  import so no module-scope import edge is added.
- [ ] 3.4 `qualified.py`: `drives` on `DriverDeclaration`, source-only,
  refusing a driver as the driven end and refusing a sideways read of a
  driver off a declaration.
- [ ] 3.5 The realization hook: resolve every relation's ends and call
  every `law=` once, at the end of the instance's construction after
  its children are realized, raising by name for a path that does not
  resolve on this instance and for a law that returns a non-law.

## 4. The lifecycle hook

- [ ] 4.1 `assembly.py`: REWORK cycle 2's end-of-phase wiring binding
  into the solver. The recorded wirings become forward-only identity
  relations in the same fixpoint, so a wiring whose source a relation
  solves binds after it; cycle 2's unbound-source error moves to the
  end of propagation and keeps its message; its hand-binding refusal
  and its scale application are untouched. Then, after
  `self.simulate()` returns, solve this instance's relations and
  wirings together inside the still-current phase.
- [ ] 4.2 The freshness clear: at the START of the phase, before the
  author's `simulate()` runs, clear the value and the binder record of
  every coordinate this assembly bound through a wiring or a relation
  in its previous run, from the record it kept when it bound them.
  Nothing the author bound is cleared.
- [ ] 4.3 The per-enumeration binder record: what bound each coordinate
  this pass, set on every binding path (author, wiring, relation,
  driver read), consulted by `DoublyBound`, and kept as the list 4.2
  clears from.

## 5. Docs and records

- [ ] 5.1 `docs/architecture.md`: Kinematics gains the relation and
  when it is solved; Expression math gains the affine lowering;
  Mechanisms gains the sentence that its laws are arithmetic a
  project's `law=` composes, still not vocabulary; the Map table's
  Motion row gains `couplings` and ADR-089.
- [ ] 5.2 `docs/declaring.rst`: the verb, path references, derived
  coordinates, and the one-joint rule for a node end.
  `docs/driving.rst`: a driver reaching a joint by path, direction
  versus solving, and the three refusals with their messages.
  `docs/api-reference.rst` gains `Affine` and the error kinds.
- [ ] 5.3 `docs/changelog.rst` "Unreleased": the verb, `Affine`, path
  references, derived coordinates, the sideways relaxation.
- [ ] 5.4 `docs/adrs/NODE/ADR-089-drives-relates-two-coordinates.md`,
  written from what the code does: the one verb and no second
  vocabulary; the law as project code passed in, with the rejected
  `law_for` class hook named as rejected by the pilot; resolution
  oriented from the bound side, per run, at the end of the owning
  simulate phase; the three refusals; the narrow sideways relaxation
  that extends ADR-061 without reversing it. Add it to
  `docs/adrs/README.md` in order.

## 6. Green, and the record of it

- [ ] 6.1 The whole framework suite green, with the counts before and
  after.
- [ ] 6.2 The fixture train's own evidence recorded in the change: the
  angles the backwards solve produces, the published expressions for
  the symbolic build, and the three refusal messages verbatim.
- [ ] 6.3 `openspec validate couplings --strict`, then sync the
  baseline specs and archive.
- [ ] 6.4 `workflow/motion/roadmap.md` Progress table, row
  `3 couplings`, "Applied" cell — a targeted substitution of that one
  row, the file re-read immediately before writing.
