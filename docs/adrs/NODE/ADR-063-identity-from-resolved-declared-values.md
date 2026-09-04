# ADR-063: Identity From Resolved Declared Values

**Status:** Accepted
**Date:** 2026-09-01
**Extends:** [ADR-026: Node Identity — Parameter-Hashed Artifact Keys vs Tree Names](./ADR-026-node-identity-parameter-hashed-artifact-keys-vs-tree-names.md)
**Depends on:**
- [ADR-061: A Call in a Node Class Body Is a Declaration](./ADR-061-a-call-in-a-class-body-is-a-declaration.md)
- [ADR-062: Typed Parameters and the Exponent Algebra](./ADR-062-typed-parameters-and-the-exponent-algebra.md)

## Context and Problem Statement

ADR-026 keys an artifact on the class plus the constructor arguments that
reach `AbstractBaseNode.__init__`. The rule is right and the mechanism has a
hole the author fills by hand: `uniq_id` sees exactly what the subclass forwards
to `super().__init__()`, so a parameter left out of that call silently gives two
geometrically different instances one artifact, and one serves the other's
stale geometry. `base.py` records this class of bug being patched twice.

A declared parameter (ADR-062) is enumerable off the class and resolved by the
framework at construction, so the framework can compute the complete map
itself.

## Decision Drivers

- The forgotten-kwarg collision must become impossible on a declarative class,
  not merely less likely.
- A class migrated from the constructor form should keep its key when it
  forwarded everything, so a migration is not a rebuild of the world.
- Identical repeated units must be one part: one geometry, one artifact,
  many placements.

## Considered Options

1. **The existing serialization and hash, fed the resolved declared values
   sorted by name** (chosen)
2. A new identity scheme for declarative classes (a hash over the declaration
   itself, or over the whole resolved tree)
3. Include derived values in the key as well

## Decision Outcome

Chosen: **`_build_uniq_id(cls, (), resolved)`, unchanged, where `resolved` is
the coerced value of every declared — not derived — parameter, sorted by
name.** The class qualname leads, `str()` of each value follows, the readable
prefix and the 12-hex sha256 are what they were. A class that used to forward
all of its kwargs with float defaults keeps its key byte for byte; a class that
forgot one gets a new, correct key; a class that passed an integer where a
float kind now resolves re-keys once. `name` stays out, as always.

Derived values are excluded (option 3): they are functions of the declared
ones and would only lengthen the prefix. A new scheme (option 2) would have
re-keyed every migrated class for no gain and forked the one identity rule
into two.

`repeat(count)` realizes count-many instances with identical resolved values;
by ADR-026's own rule — identical arguments share an artifact — they share one
`uniq_id`, which is the bill-of-materials quantity line and the build win the
reference wanted: eight geometrically identical cylinder units used to hash to
eight identities because they carried their placement as kwargs. Placement is
now the parent's `render()`, never a parameter.

Rebuild semantics need no mechanism of their own. Artifacts are keyed by
values, so `Engine()` and `Engine(bore=32.0)` coexist on disk, switching back
is a cache hit, and a child whose parameters do not depend on the changed value
keeps its key and is not rebuilt. The published build describes one parameter
set at a time.

## Consequences

- On a declarative class the identity is complete by construction; the
  `super().__init__()` forwarding discipline has nothing left to forget.
- A `Flag` enters identity like any parameter, so a fusion whose membership a
  flag gates is two artifacts for two flag values — which is what makes
  `omit()` safe inside a fusion (ADR-064).
- Every parameter set a maker tries leaves artifacts behind, exactly as
  differing kwargs always have; the build's sweep of unreferenced artifacts
  bounds the cost.
- A migrated class may rebuild once. The changelog says so.

## References

- `solid_node/node/base.py` — `AbstractBaseNode.__init__`, `_build_uniq_id`
- `solid_node/node/declarative.py` — `identity_values`
- `tests/test_declarative_nodes.py` (`IdentityTest`)
- OpenSpec change `declarative-node-api`, capabilities `declarative-nodes`,
  `node-model`
