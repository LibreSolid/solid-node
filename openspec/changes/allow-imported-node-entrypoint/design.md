## Context

The path loader currently treats class origin as both an implicit-discovery
filter and a validity condition for an explicit `NODE` marker. The first use
prevents accidental selection of imported helpers; the second blocks a normal
Python package facade such as `root/__init__.py` re-exporting
`root/snowman_body.py:SnowmanBody`.

Simply removing the marker-origin check is incomplete. A node instance derives
its `src`, artifact location, and import closure from the class's defining
module. Without also retaining the loaded entry-point path, `solid develop`
would not watch `root/__init__.py`, and changing its `NODE` selection could
leave the old root active until an unrelated source changed.

## Goals / Non-Goals

**Goals:**

- Make a project-local imported node class a valid explicit `NODE` target.
- Preserve same-file-only implicit discovery and actionable ambiguity errors.
- Track both the entry-point facade and the selected class's implementation
  source for cache invalidation and develop-mode reloads.
- Preserve artifact identity and layout based on the selected class's real
  implementation source.

**Non-Goals:**

- Selecting node classes imported from installed libraries or paths outside
  the active project.
- Changing CLI path syntax, implicit class ordering, test-class discovery, or
  artifact naming.
- Adding configuration or a second entry-point declaration mechanism.

## Decisions

### Treat the explicit marker as authoritative within the project

`_resolve_marker` will continue validating that `NODE` is a class and an
`AbstractBaseNode` subclass. It will replace the same-file requirement with a
project-boundary requirement: the marker's defining file must resolve beneath
the active project root. This supports package facades without allowing an
entry point to redirect artifact layout and watches into installed packages.

Alternative: accept any imported subclass. Rejected because nodes derive
artifact paths and source watches from the class file; an external class would
place those concerns outside the project boundary.

### Keep implicit discovery same-file-only

The `candidates` filter remains unchanged. A module without `NODE` still sees
only classes defined in the loaded file, so imports cannot become accidental
entry points and multiple local classes still fail loudly.

Alternative: include imported classes in implicit discovery. Rejected because
import order would restore the silent wrong-class failure that `NODE` solved.

### Add the loaded entry point to the instantiated node's source set

`load_node(path)` will ensure the normalized loaded path is present in the
returned node's `files`. The node already tracks its defining implementation
module and project-local import closure. Adding the facade gives cache and
watch semantics both sides of the relationship without changing `node.src`,
artifact basenames, or child aggregation.

Alternative: make the facade replace `node.src`. Rejected because it would
hide the implementation source that actually determines geometry and would
misstate artifact identity.

### Amend the existing loader decision

ADR-026 currently records same-file marker scope as part of its accepted
choice. Implementation evidence will amend that ADR and the architecture
synthesis rather than creating a competing ADR. The build-pipeline baseline
will be synchronized from this change's delta spec.

## Risks / Trade-offs

- [A facade edit could be missed by the watcher] → Require a regression proving
  the loaded entry-point path is in `node.files` for an imported marker.
- [Relaxing the marker could select a wrong imported class] → Preserve strict
  subclass validation, require project-local origin, and leave implicit
  discovery unchanged.
- [Artifact paths may surprise facade authors] → Document that artifacts remain
  keyed to the selected class's defining source, consistent with current node
  identity and import-closure behavior.
- [The originating project currently has a local-subclass workaround] → Prove
  the direct re-export layout with a framework fixture; after integration the
  project can remove the workaround in a separate product drawing/build.
