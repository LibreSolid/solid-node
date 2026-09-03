# ADR-064: An Internal render() That Returns Nothing, and Structural Omission

**Status:** Accepted
**Date:** 2026-09-01
**Extends:** [ADR-002: Template-Method Pattern for Node Lifecycle](./ADR-002-template-method-pattern-for-node-lifecycle.md)
**Depends on:**
- [ADR-061: A Call in a Node Class Body Is a Declaration](./ADR-061-a-call-in-a-class-body-is-a-declaration.md)
- [ADR-023: Kinematic Operations and Driver-Tagged Idempotent Renders](./ADR-023-kinematic-operations-and-driver-tagged-idempotent-renders.md)

## Context and Problem Statement

An internal node's `render()` has always done two jobs: position the children
and enumerate them. Once the children are declared in the class body
(ADR-061), the enumeration is a restatement of the declaration, and the
remaining job is positioning and selecting which declared parts are present.

The shop's design reference split `render()` into two workshop verbs, `shape()`
for a leaf and `assemble()` for an internal node. Both names are already public
framework methods with other meanings — `assemble(root)` is the template-method
build entry (ADR-002) called by the builder, the simulation, the snapshot tool
and ten project test files, and `shape()` is the exact-geometry accessor
(ADR-044) called by the test runner and by project tests. Neither can mean two
things, and a rename is a breaking refactor. The pilot deferred it.

Separately, structure must not vary with time: a fusion whose membership
depended on `$t` would have no single artifact to build, and a machine does not
gain and lose parts per frame.

## Decision Drivers

- Additive: a `render()` that returns a list keeps its contract to the letter.
- Every tree walker — `as_scad`, the serializer, the driver walk, state
  propagation — calls `render()` directly and treats a non-list as "no
  children"; they must all see the same list.
- The animator sweep (ADR-023) must still run before the author's code.
- Time-dependent structure must fail, under symbolic time and under a bound
  keyframe alike.

## Considered Options

1. **`render()` stays; on a declarative internal node `None` means the declared
   children minus those `omit()` marked; the substitution lives in the
   framework's existing render wrapper** (chosen)
2. The reference's two new verbs, renaming the existing methods (deferred)
3. New verbs under other names (`make()`/`place()`), keeping the existing
   surface (rejected by the pilot as an extra vocabulary for a step that
   is not the final naming)
4. A framework-provided default `render()` only, with explicit lists still
   required from any class that positions

## Decision Outcome

Chosen: **one method, and on a declarative class it may return nothing.**

`InternalNode` wraps every subclass `render()` in `__init_subclass__` — the
same hook `AssemblyNode` already uses for the sweep — with `_declarative_render`.
The wrapper clears the omission marks on the instance's realized declared
children, runs the author's `render()`, and if it returned `None` on a class
with declared children, returns those children in declaration order minus the
omitted. A returned list passes through untouched. The base
`InternalNode.render()` returns `None`, so a class with nothing to position
needs no method at all. `AssemblyNode` inherits it under `_idempotent_render`,
so the order is sweep, clear, author, substitute; `FusionNode` subclasses get
the same wrapper, and the sweep part is a no-op for them. The wrapper runs its
bookkeeping only at the outermost call, so a subclass delegating to
`super().render()` after calling `omit()` keeps its marks. A leaf `render()`
returning `None` is still an error.

`omit()` is structural absence: the child is not linked, built, exported,
fused or serialized. Every child is always declared — the tree's vocabulary is
complete at import — and `render()` selects presence. The wrapper records the
omitted set of the instance's first render and raises `StructureError` on a
later render whose set differs, naming the node and both sets. An instance's
parameters cannot change, so a difference can only come from time or from a
bug. Under symbolic time the condition already fails — solid2 refuses to
evaluate a symbolic value as a boolean — and the recorded-set check is what
enforces the rule under a bound keyframe or a simulation snapshot, where time
is a plain number.

List indices are declared identity and never renumber: an omitted `units-3`
leaves `units-4` as `units-4`, because names derive from the position in the
realized list, not from the rendered subset.

## Consequences

- Users still override `render()` and never `assemble()` (ADR-002); the
  lifecycle is unchanged. The pun in `render()` — geometry on a leaf, parts on
  an internal node — is acknowledged and deferred with the rename.
- A pure grouping node is declarations alone. `Engine` in the docs is a class
  body with four lines and no method.
- A fusion may omit a declared child, and because the gating `Flag` is in the
  fusion's identity (ADR-063) the two memberships are two artifacts.
- A driver declared on a repeated or list-held child still cannot be qualified
  (`units-3` is not an identifier, ADR-056's stage 3a rule); identical units
  are driven through ports, fed from the parent's `render()`, which may now
  bind a port by assignment.
- Placement applied in `render()` is swept and re-applied every frame with
  the animator's operations. A stationary part is placed once in `__init__`
  after `super().__init__(**kwargs)`, by which point the children are
  realized; the declaring page recommends that split for now (change
  `declarative-node-api-fixes`), and the pilot will revisit it together with
  the deferred rename.
- The structure check needs a first render to record against; the first render
  is also the one every build, test and serializer pass performs first, so a
  time-conditioned omission is caught on the second instant at the latest.

> **Note (2026-09-03, ADR-066):** the rename deferred here is dropped for
> good — *render* also means *to make*. Positioning is split by
> lifecycle instead: `render()` places at rest and selects, once;
> `simulate()` moves per instant and may not `omit()`. The recorded-set
> check below remains for a legacy `render()` that reads a driver.

## References

- `solid_node/node/internal.py` — `_declarative_render`, `InternalNode.render`
- `solid_node/node/assembly.py` — the wrapper order
- `solid_node/node/base.py` — `omit()`
- `solid_node/node/ports.py` — `bind`, `Port.__set__`
- `tests/test_declarative_render.py`, `tests/test_ports.py`
- OpenSpec change `declarative-node-api`, capabilities `declarative-nodes`,
  `node-model`, `ports`
