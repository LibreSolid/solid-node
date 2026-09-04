## Why

Migrating v8-engine, Inmoov-sim and Metamaquina2 to the declarative node
API (change `declarative-node-api`, not yet integrated) surfaced two defects
and two gaps the pilot directed be closed before integration:

1. A list comprehension in a node class body silently produces real, shared
   instances instead of declarations. Python 3.12 inlines the comprehension
   (PEP 709) and, while its hidden loop variable is live, `frame.f_locals`
   is a plain copy of the namespace rather than the namespace itself, so
   `in_class_body()` does not recognize the body. `declared_children` is
   then empty and a `render()` returning `None` yields no children at all:
   the assembly disappears from the machine without an error.
2. A `Flag` passed to a declared child arrives as the declaration object.
   Realization resolves only `Expression` tokens, and `Flag` is outside the
   algebra by design, so `Electronics(power_supply_fitted=power_supply_fitted)`
   raises and a structural flag can never be a root parameter that `--set`
   reaches. Two v8-engine classes and one Metamaquina2 flag were blocked.
3. Cross-parameter guards (`stop_diameter > stem_diameter`) have nowhere to
   go: `min=`/`max=` cover one value, comparisons are refused in the class
   body, and nothing is called after resolution — so nine v8-engine classes
   grew an `__init__` back to hold them.
4. A class migrated off `__init__` moves its stationary placement into
   `render()`, where it is swept and re-applied every frame; the docs never
   say a declarative class may still place once in `__init__`.

## What Changes

- A list comprehension in a node class body over values it can see
  (module-level names, literals) declares an enumerated list of children,
  exactly as a literal list does. The framework recognizes a node class
  body while an inlined comprehension runs in it.
- A `Flag` token passed to a declared child resolves to the parent's
  boolean at realization, exactly as a numeric token does. `Flag` stays
  outside the algebra: no operators, no `.value`.
- A declarative node may define `check()`. The framework calls it once the
  instance's parameters are resolved and before any child is realized; an
  exception refuses the instance and propagates unchanged. The base
  implementation does nothing, so `super().check()` chains. It is not
  called on a non-declarative class, whose attributes do not exist yet
  when the base constructor runs.
- The declaring page documents the placement split — stationary parts
  placed once in `__init__` after `super().__init__(**kwargs)`, moving
  parts in `render()` — and recommends it for now, pending the lifecycle
  rename the pilot deferred; documents `check()`; and corrects the
  comprehension pitfall to what it is (class-level names are invisible;
  module-level ones work).

Nothing changes for a class that declares nothing. No existing declarative
class changes behaviour: a body without a comprehension, a child without a
flag argument and a class without `check()` are untouched.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `declarative-nodes`: "Class-body child declarations" gains the
  comprehension and the flag-flow behaviours; a new requirement "Instance
  checks" adds the `check()` hook.
- `user-documentation`: "The declarative authoring surface is documented"
  covers `check()`, the placement split and the corrected comprehension
  pitfall.

## Impact

- `solid_node/node/declarative.py`: `_DeclaringNamespace`, `NodeMeta`,
  `in_class_body`, `_evaluate`.
- `solid_node/node/base.py`: `AbstractBaseNode.__init__` calls `check()`;
  `check()` no-op on the base.
- `docs/declaring.rst`, `docs/changelog.rst`, `HISTORY.rst`; ADR-061,
  ADR-062 and ADR-064 gain notes; one new ADR records `check()`.
- Originating projects: v8-engine (guards, bank flag), Metamaquina2
  (comprehension workaround, `power_supply_fitted`), Inmoov-sim (placement
  in `render()`). Their branches are validated against this worktree; their
  own follow-up edits are project work outside this cycle.
