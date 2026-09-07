# ADR-082: Empty composition belongs to assemblies, not fusions

**Status:** Accepted
**Date:** 2026-09-07
**Change:** `support-empty-assemblies`
**Extends:**
- [ADR-064: An Internal render() That Returns Nothing, and Structural Omission](ADR-064-an-internal-render-that-returns-nothing.md)
**Depends on:**
- [ADR-003: Rigid vs Non-Rigid Node Distinction](ADR-003-rigid-vs-non-rigid-node-distinction.md)
- [ADR-039: Solid Integrity at the Topmost Rigid Node](ADR-039-solid-integrity-at-the-topmost-rigid-node.md)
- [ADR-061: A Call in a Class Body Is a Declaration](ADR-061-a-call-in-a-class-body-is-a-declaration.md)

## Context and Problem Statement

ADR-064 lets a declarative internal `render()` return `None`, which the
framework replaces with its realized declared children minus omissions. That
decision did not state what happens when a declaration realizes no children.
A valid `repeat(Count(0, min=0))` produced an empty instance list, but the
wrapper used that list's truthiness to decide that no declaration existed and
leaked `None` to validation. When every declared child was omitted, the
wrapper did produce `[]`, but internal composition indexed its missing first
member.

Correcting those incidental failures requires an architectural boundary. An
`AssemblyNode` is a non-rigid grouping of independently meaningful parts, and
can coherently have no present parts. A `FusionNode` is itself rigid, denotes
one solid, and owns a cached artifact. Zero input solids do not provide a
portable OpenSCAD or exact-kernel shape that can satisfy that promise.

## Decision Drivers

- A declaration remains structure even when its resolved multiplicity is
  zero.
- Every consumer must see the same substituted list, including `[]`.
- Empty selection by `repeat()` and by `omit()` must agree.
- Non-rigid grouping must not invent a rigid artifact or printed piece.
- Rigidity remains static by node type; an empty fusion cannot become an
  assembly depending on parameters.
- A rigid node must fail before publishing a meaningless or missing artifact.

## Considered Options

1. **Permit empty assemblies and reject empty fusions during validation**
   (chosen)
2. Reject every empty internal node
3. Permit both kinds by treating an empty OpenSCAD union as geometry
4. Change a fusion's rigidity dynamically when it has no selected children
5. Skip the ordinary assembly lifecycle when no children are present

## Decision Outcome

Chosen: **emptiness is valid grouping, not valid rigid geometry.**

The declarative wrapper determines whether `None` has declarative meaning from
the class's child-declaration metadata, independently of the flattened
realized child count. A zero repeat therefore substitutes `[]`, as does a
render that omits every declared child. The existing rule for a class with no
child declarations remains unchanged: there is no declarative list to
substitute.

An `AssemblyNode` carries that empty list through the normal lifecycle.
Internal SCAD composition returns an empty `union()` object instead of
indexing a child, allowing `assemble()`, operations, and `.scad` generation to
use their ordinary paths. Because an assembly is non-rigid, STL generation is
already a no-op. Serialization publishes `children: []`, distinguishing a
successfully enumerated empty node from the partial document produced for an
invalid non-list render.

A `FusionNode` rejects an empty rendered list in `validate()`, before
`as_scad()`, BREP, or STL generation. The diagnostic names the fusion and
states that at least one rigid child is required. This applies equally to an
explicit empty list, a zero repeat, and omission of all declared children.

## Consequences

- Optional groups can use a non-negative `Count` naturally: zero means no
  present instances and remains a successful project build.
- An assembly may be a valid empty root or subtree. It has no linked children,
  no STL of its own, and a document with an explicit empty children array.
- Omission can select no parts from an assembly without a special placeholder
  node or hand-written render branch.
- A fusion must always contain at least one selected rigid child. Projects
  that previously reached an incidental index or renderer failure receive an
  earlier structural diagnostic.
- One-child composition still returns that child's model directly; several
  children still use `union()`; leaf render contracts do not change.
- Structure may vary between instances through declared parameters, including
  empty versus nonempty, but never between time bindings of one instance.

## Evidence

Before implementation, six focused assertions reproduced the leaked `None`,
empty-list indexing, and incidental fusion errors. After implementation, 20
direct declarative-render tests and a 155-test declarative/lifecycle/document
set passed. The saved CLI probe changed its zero-child build exit status from
1 to 0 and recorded non-rigid STL generation as a no-op. The complete suite
passed 1,630 tests with 16 skipped, 44 warnings, and 274 passing subtests.

## References

- `solid_node/node/declarative.py`
- `solid_node/node/internal.py`
- `solid_node/node/fusion.py`
- `solid_node/core/serializer.py`
- `tests/test_declarative_render.py`
- OpenSpec change `support-empty-assemblies`
