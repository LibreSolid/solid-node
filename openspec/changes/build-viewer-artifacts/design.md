## Context

`solid develop` loads and assembles a project model, then its private `NodeAPI` exposes the current tree and STL files to the bundled web viewer. `solid build` now publishes `_build` atomically, but that directory contains only geometry artifacts. A long-lived consumer such as shop-floor must not load the project model itself, so it needs the same viewer state recorded by the builder before the complete build is published.

## Goals / Non-Goals

**Goals:**

- Publish a versioned viewer snapshot with the complete normal `_build` tree.
- Capture the same recursive node state the development viewer exposes: identity, type, colour, serialized operations, child relationships, and rigid-model locations.
- Keep the snapshot and its referenced models atomic with the current build publication, so callback consumers never observe a partial tree.
- Make the framework web viewer able to serve a snapshot without importing a project module, so floor can host that private implementation safely.
- Drive the change red-first with real command/build-directory evidence.

**Non-Goals:**

- Replace the existing development viewer protocol or public static-export format.
- Change geometry cache paths, rendering, or the `solid develop` watch loop.
- Make the private viewer snapshot a new independently supported public API.

## Decisions

### A builder writes the viewer snapshot before publication

After a model is loaded, assembled, and all of its current STLs are ready, the builder will serialize the same tree currently exposed by `NodeAPI` into one `_build` snapshot file. Rigid model references are relative to the published build root, never absolute host paths. The snapshot is written to the staging directory and moves with the existing atomic directory publish.

Writing it from the builder is chosen over a floor-side source load because the builder already owns the current, successfully assembled model and its publication boundary. A floor-side traversal of `_build` alone cannot recover names, hierarchy, colours, or operations from STL files.

### The private viewer accepts a published snapshot

The framework will extract the recursive state/file serving behavior from the source-backed `NodeAPI` so it can also be constructed from the snapshot and a build-root directory. `solid develop` retains its source-backed behavior; floor can use the snapshot-backed path without importing project code.

Duplicating tree traversal in floor is rejected because it would make two framework viewers diverge. Reusing static export is rejected because export is a separate model execution/publication flow and is incompatible with the normal `develop` callback lifecycle.

## Risks / Trade-offs

- [Snapshot diverges from the development viewer state] → exercise the same fixture through both source- and snapshot-backed NodeAPI paths.
- [A failed later build overwrites usable state] → write the snapshot only in the staging tree and publish it through the existing atomic replacement.
- [Private interface evolves] → keep snapshot reading inside the framework; floor consumes the framework implementation rather than parsing it itself.

## Migration Plan

1. Add a failing `solid build` test that asserts the absent viewer snapshot.
2. Implement builder serialization and snapshot-backed viewer serving until the test is green.
3. Add a failing failure-path test and prove last-known-good viewer state remains readable after a later build failure.
4. Sync the build, CLI, and web-viewer specifications; no artifact migration is required because consumers begin only after the new build is available.
