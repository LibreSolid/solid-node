## 1. Red first

- [ ] 1.1 Test: a class body `boxes = [Box() for _ in TABLE]` over a module-level table declares two children (`declared_children`), two instances realize distinct objects, and `render()` returning `None` yields both; the same body still raises `NameError` for a class-level name
- [ ] 1.2 Test: `child = Leaf(right=right)` with `right = Flag(False)` on the parent realizes the child with `right is False`; `Parent(right=True)` flips it; an inline `Flag(True)` in a declaration is a constant; a flag not declared on the class raises `ParameterError`
- [ ] 1.3 Test: a declarative class defining `check()` that raises `ValueError` when `stop <= stem` refuses `Valve(stop=1.0, stem=2.0)` with that error and realizes no child; the default passes; `super().check()` chains; a non-declarative class's `check()` is not called by the base constructor
- [ ] 1.4 Run the three tests and record them red on the base

## 2. Framework

- [ ] 2.1 `_DeclaringNamespace` carries the body marker; `in_class_body()` accepts the namespace or a dict copy holding it; `NodeMeta.__new__` strips it
- [ ] 2.2 `_evaluate` resolves a named `Flag` from the parent's values with the formula's undeclared-name error
- [ ] 2.3 `AbstractBaseNode.check()` no-op; `__init__` calls it after `resolve_parameters` on a declarative class
- [ ] 2.4 `solid_node.node` exports unchanged; lazy-export test still lists exactly the same names

## 3. Documentation and records

- [ ] 3.1 `docs/declaring.rst`: comprehension pitfall corrected; "Checking parameters together" section for `check()`; "Where placement goes" section with the `__init__` recommendation marked provisional
- [ ] 3.2 `docs/changelog.rst` and `HISTORY.rst` Unreleased entries
- [ ] 3.3 ADR-061 implementation note (the copy during an inlined comprehension); ADR-062 note that a flag flows to a child; ADR-064 consequence on placement; new ADR for `check()`; ADR index; architecture synthesis if a boundary changed

## 4. Validation

- [ ] 4.1 Full framework suite green; flake8 no new findings against the base
- [ ] 4.2 The three migrated project branches' suites against this worktree: Inmoov-sim, Metamaquina2, v8-engine unchanged
- [ ] 4.3 Sphinx builds the declaring page without new warnings

## 5. Close

- [ ] 5.1 Sync delta specs into the main specs; `openspec validate --all`
- [ ] 5.2 Archive the change; commit 2
