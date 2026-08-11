# ADR-042: Host-controlled viewer assembly navigation

**Status:** Accepted

**Date:** 2026-08-11

**Change:** `add-assembly-navigation`

**Amends:**
- [ADR-035: Reusable viewer core and declared API version](ADR-035-reusable-viewer-core-and-declared-api.md)
- [ADR-037: Targeted in-place viewer updates](../VIEWER-WEB/ADR-037-targeted-in-place-viewer-updates.md)

## Context

The reusable viewer owns the published node tree and every Three.js object that
renders it, but its host handle previously exposed only lifecycle, camera,
animation, and update operations. SolidNode Studio needed an assembly tree that
could focus a subassembly and hide obstructing parts. Reading `viewer.json` and
mutating a parallel scene in Studio would duplicate colour inheritance, path
resolution, reconciliation, and renderer ownership at the first external host
to need those controls.

The interaction is inspection state, not CAD state: it must not alter the
published document, project source, or model artifacts. It must also remain
coherent when the existing targeted-update contract adds or removes nodes.

## Decision

The viewer handle at API version 4 exposes three host-safe operations:

- `assembly()` returns immutable metadata for the current published tree:
  names, root-relative sibling-name paths, effective inherited colours,
  model-bearing status, and children;
- `setRoot(path | null)` focuses a named subtree or restores the document root;
  and
- `setVisible(path, visible)` hides or shows a named subtree.

Paths are arrays of sibling names relative to the published root. The handle
validates them without exposing the source document, filesystem paths, meshes,
groups, scene, or controls. Focus and explicit visibility remain independent.
Rendering retains ancestor groups needed for world transforms, filters other
groups non-destructively, and fits bounds from visible meshes only.

Assembly state reconciles beside the existing name-based targeted update. A
focused or hidden path that remains keeps its state; a removed focused path
returns to the document root and a removed hidden path is discarded. Geometry
is not unloaded by inspection controls, and retained geometry is not refetched.

## Alternatives considered

- **Let each host parse the published document.** Rejected because effective
  colour, valid paths, and reconciliation are viewer semantics and would drift
  across hosts.
- **Expose Three.js objects.** Rejected because it would turn renderer internals
  into a public compatibility contract and let hosts violate lifecycle safety.
- **Persist focus and visibility in the document.** Rejected because temporary
  inspection state is neither authored CAD intent nor build output.
- **Unload hidden geometry.** Rejected because show/hide must be immediate and
  must not introduce new fetch or failure paths.

## Consequences

- Studio and later hosts can build their own accessible assembly controls over
  one renderer-owned tree contract.
- The widget API advances from 3 to 4; a host requiring assembly navigation can
  reject an older bundle through the existing compatibility gate.
- Focus and visibility survive compatible targeted updates without changing
  camera state or retained geometry.
- The public API grows only in serializable metadata and imperative actions;
  Three.js remains private.

## References

- `solid_node/viewers/widget/src/assembly.ts`
- `solid_node/viewers/widget/src/tree.ts`
- `solid_node/viewers/widget/src/viewer.ts`
- `openspec/changes/archive/2026-08-11-add-assembly-navigation/`
- SolidNode Studio `add-assembly-navigation` originating caller
