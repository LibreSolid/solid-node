## Context

`RepeatDeclaration.realize()` deliberately accepts zero and stores an empty
list on the instance. `_declarative_render()` currently tests the flattened
realized child list to decide whether `None` has declarative meaning. With a
zero repeat that list is empty, so the wrapper returns `None` even though the
class declares child structure. `InternalNode.validate()` then rejects the
result.

When every declared child is omitted, the wrapper already returns `[]`, but
`InternalNode.as_scad()` assumes at least one child and indexes `scads[0]`.
The serializer itself can represent an empty non-rigid node as
`"children": []`. The remaining design question is whether both concrete
internal kinds admit that structure: an assembly groups independently rigid
parts, while a fusion is itself a rigid solid and must produce a cached solid
artifact.

## Goals / Non-Goals

**Goals:**

- Preserve the declarative meaning of `None` when child declarations realize
  zero instances.
- Carry an empty child list through assembly, state propagation,
  serialization, and a real project build without indexing or validation
  failures.
- Treat both a zero repeat and omission of every declared child consistently
  for non-rigid assemblies.
- Refuse a zero-child rigid fusion before SCAD/STL publication with a
  diagnostic naming the fusion and the missing solid membership.
- Preserve existing behavior for explicit nonempty lists, one child, multiple
  children, leaf nodes, and invalid repeat counts.

**Non-Goals:**

- Give an empty assembly an STL, mesh, exact shape, or printed-piece identity.
- Invent identity geometry or an empty boundary representation for a fusion.
- Change whether structure may vary with time or how `omit()` records a
  selection.
- Add optional-child syntax beyond the existing `repeat()` and `omit()` APIs.

## Decisions

### D1: Detect declarations from class metadata

The declarative wrapper will ask whether the class has child declarations,
independently of the flattened realized child list. When the author returns
`None` and declarations exist, the wrapper returns the realized children
minus omissions, even when that result is `[]`.

Treating an empty realization as no declaration was rejected because it makes
the same class switch render contracts based on a valid parameter value.
Treating every methodless internal node as empty was rejected because legacy
classes with no child declarations still have no declarative list to
substitute.

### D2: Represent an empty assembly with an empty SCAD grouping

Internal SCAD composition will retain the current direct child result for one
child and `union()` for several. With zero children it will return solid2's
empty `union()` object, allowing the shared `assemble()` lifecycle and SCAD
generation to complete without claiming rigid geometry. `AssemblyNode` is
non-rigid, so its STL generation remains the existing no-op.

Returning `None` was rejected because later operation and SCAD serialization
paths expect a composable object. Skipping `assemble()` was rejected because
it would bypass the lifecycle and leave consumers with a special unassembled
state.

### D3: Publish an explicit empty children list

The existing serializer will recurse over the substituted list and publish
`children: []`. This uses the current document shape and tells consumers that
the non-rigid node was successfully enumerated and contains no present parts.
Omitting the key was rejected because that is the serializer's existing
partial representation for a non-list render result and would make a valid
empty assembly indistinguishable from an invalid/incomplete render.

### D4: Reject an empty fusion during validation

`FusionNode.validate()` will require at least one child after declarative
selection. A fusion is rigid by type, forms one topmost rigid solid, and can
produce an STL; zero input solids provide no shape that can satisfy that
contract. The refusal happens before `as_scad()`, BREP, or STL generation and
names the fusion.

Treating empty `union()` as a rigid artifact was rejected because OpenSCAD and
exact kernels have no portable solid to publish. Silently making the fusion
non-rigid was rejected because rigidity is static by node type.

### D5: Prove direct and public paths

Focused tests will cover a methodless zero repeat, omission of all children,
explicit empty assembly output, empty document serialization, and empty
fusion refusal. Existing nonempty declarative tests remain the regression for
one/many composition. The saved subprocess probe must change its
`zero_children.exitcode` from 1 to 0 and leave F11's negative-step evidence
unchanged.

## Risks / Trade-offs

- **A viewer may receive a root with no visible parts.** The document uses its
  existing `children` array with zero entries, so no schema or compatibility
  change is introduced.
- **An empty SCAD statement has no geometry.** Only the non-rigid assembly
  owns it; rigid artifact generation remains forbidden by the fusion check.
- **A class may alternate between empty and nonempty by parameter.** Declared
  parameters already determine instance structure and identity. Time-based
  changes remain prohibited by the existing omission checks.

## Migration Plan

No migration is required. Existing valid assemblies are unchanged. Projects
whose fusions explicitly return or select an empty list will receive a clearer
early error in place of the current incidental index or kernel failure.

## Open Questions

None.
