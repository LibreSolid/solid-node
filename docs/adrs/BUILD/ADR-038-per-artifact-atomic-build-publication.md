# ADR-038: Per-artifact atomic build publication

- **Status:** Accepted
- **Date:** 2026-08-02
- **Subsystem:** BUILD
- **Change:** `per-file-build-publication`
- **Supersedes:** [ADR-032](ADR-032-symlink-swap-build-publication.md)
- **Reverses:** [ADR-030](ADR-030-complete-build-publication-boundary.md)

## Context

SPRINT-003 measured a 113 MB, 55-STL rebuild for a one-leaf change in
v8-engine. The complete-set boundary makes progressive display impossible and
the symlink swap allows a reader that resolves `_build` twice to straddle two
trees. F1 now serializes every framework builder with a project-local `flock`,
so ADR-032's overlapping-publisher race is no longer a publication concern.

ADR-030 correctly required that a reader never consume a torn artifact, but
incorrectly equated that requirement with a complete artifact *set*.

## Decision

Builders write directly into one ordinary build directory. Each `.scad`, STL,
`viewer.json`, and `errors.json` is written to a temporary sibling and atomically
replaced. OpenSCAD renders to a temporary STL; completion stamps and replaces
the public artifact. The manifest is written last, and a successful manifest
publication then sweeps unreferenced artifacts. Errors are cleared before a
new manifest becomes visible.

The project `flock` from F1 covers rendering and publication. It is a file
descriptor with no broker, daemon, protocol, or network surface, and is released
before test execution; ADR-018's lean framework boundary therefore remains
intact. A legacy symlink build path is migrated once under that lock.

## Consequences

- Readers observe each artifact complete or not at all, but may observe a mixed
  model while a build is running.
- A failed build can leave a partially updated model; `errors.json` reports it.
- The manifest still only names artifacts already in place; removed artifacts
  are swept only after the manifest drops them.
- Because a render now lands directly at the artifact's final path, the pass
  that follows a render finds every artifact current. That pass republishes the
  manifest when it no longer matches the model, which is what carries an edit
  into the document a viewer reads; without it the artifacts would advance
  while the document naming them stayed a build behind.
- `_build` is again an ordinary directory, eliminating symlink re-resolution
  races for consumers.

## Alternatives considered

- Retain symlink-swapped complete sets: rejected because it prevents progressive
  updates and retains the measured double-resolution race.
- Restore a broker or WebSocket lock: rejected because `flock` provides the
  required local exclusion without expanding the framework platform.
