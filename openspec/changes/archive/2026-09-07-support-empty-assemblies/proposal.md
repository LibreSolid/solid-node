## Why

Due-diligence finding F10 reproduced a declarative `AssemblyNode` with
`Part().repeat(Count(0, min=0))` failing to build. The repeat declaration is
valid, but the render wrapper mistakes its empty realization for absence of a
declaration and leaks `None`; after that is corrected, internal composition
still indexes the nonexistent first child. The accepted declarative contract
requires every render consumer to see the realized list, including an empty
one.

## What Changes

- Distinguish whether an internal node class declares child structure from
  how many child instances that structure realizes for one parameter set.
- Substitute an empty list when declared repeats realize zero children or
  omission selects no children.
- Let a non-rigid `AssemblyNode` assemble and serialize with zero children,
  representing a valid machine state with no present parts.
- Reject a zero-child `FusionNode` with a clear diagnostic because a rigid
  fusion promises one solid and has no identity geometry for an empty union.
- Add direct lifecycle, serialization, omission, and real CLI regressions for
  the empty boundaries while preserving one-child and multi-child composition.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `declarative-nodes`: require declared structure to substitute its realized
  children even when the realized set is empty.
- `node-model`: define empty composition as valid for assemblies and invalid
  for rigid fusions.

## Impact

- `solid_node/node/internal.py`: consult declared child metadata rather than
  realized count for `None` substitution and produce an empty SCAD grouping
  for an empty internal composition.
- `solid_node/node/fusion.py`: reject zero-child rigid fusion during render
  validation before geometry generation.
- Declarative render/node tests: cover zero repeats, omission of all children,
  empty serialization, and the fusion refusal.
- `workflow/archive/due-dilligence-2026-09-07/probe_additional.py`: the
  existing zero-repeat project becomes caller evidence for a successful build.
- Baseline specifications, architecture records, changelog, and
  due-diligence records will state the boundary. ADR disposition will be
  assessed after the implementation evidence establishes the final design.
- No parameter validation, repeat naming, viewer schema, artifact format,
  dependency, or leaf-render behavior changes.
