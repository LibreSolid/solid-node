# ADR-006: Mtime-Based STL Caching Strategy

**Status:** Accepted
**Date:** 2023-07-09
**Depends on:** [ADR-003: Rigid vs Non-Rigid Node Distinction](./ADR-003-rigid-vs-non-rigid-node-distinction.md)
**Used by:** [ADR-007: Watchdog Library for Filesystem Monitoring](../BUILD/ADR-007-watchdog-library-filesystem-monitoring.md)
**Extended by:**
- [ADR-026: Node Identity — Parameter-Hashed Artifact Keys vs. Tree-Addressing Names](./ADR-026-node-identity-parameter-hashed-artifact-keys-vs-tree-names.md)
- [ADR-028: Cached Base Meshes and Single-Matrix World Composition for `.mesh`](./ADR-028-cached-base-meshes-and-single-matrix-world-composition.md)

## Context and Problem Statement

The solid-node framework generates STL files from Python-defined CAD geometry through OpenSCAD compilation. Without caching, every source change would trigger full regeneration of all STL files, even for unchanged nodes. For large projects with deep node trees, this would create unacceptable development iteration times.

The framework needed an incremental build system that could:
- Detect which nodes require STL regeneration after source changes
- Handle composition where child node changes invalidate parent STLs
- Support concurrent builds without race conditions
- Maintain fast cache checks (avoid expensive I/O)
- Work reliably across the node tree hierarchy

The challenge was determining when a generated STL file is truly up-to-date relative to all source files that contributed to its geometry.

## Decision Drivers

- Development iteration speed depends on fast incremental builds
- Node composition requires tracking transitive source file dependencies
- Cache invalidation must be precise to avoid stale geometry bugs
- File watching integration needs reliable change detection mechanism
- The framework assumes deterministic CAD compilation (same SCAD always produces same STL)
- Cross-process coordination needed for concurrent build safety

## Considered Options

1. **Mtime equality with explicit timestamp setting** (chosen)
2. **Mtime inequality (standard make-style: artifact >= source)**
3. **Content-based hashing (SHA256 of source files)**

## Decision Outcome

Chosen option: **Mtime equality with explicit timestamp setting**, because it provides precise cache invalidation with minimal I/O overhead. The framework tracks all source files contributing to a node's geometry in a `self.files` set, calculates the maximum mtime across these sources, and explicitly sets generated artifacts (SCAD, STL) to match this exact timestamp using `os.utime()`.

The key invariant: A node's STL is up-to-date if and only if `os.path.getmtime(stl_file) == node.mtime`.

This approach integrates naturally with the composite node architecture. Parent nodes aggregate child source files via `self.files.update(child.files)`, ensuring changes to any leaf file correctly invalidate all ancestor STLs through the cascading mtime comparison.

## Pros and Cons of the Options

### Mtime equality with explicit timestamp setting

**Pros:**
- Fast cache checks (single stat call per file, no content reading)
- Precise invalidation (equality prevents false cache hits from timestamp collisions)
- Natural composition through file set aggregation
- No external dependencies or databases required

**Cons:**
- Requires explicit `os.utime()` calls to set artifact timestamps
- Vulnerable to manual mtime manipulation or severe clock skew
- Assumes deterministic builds (non-determinism would break caching)
- Needs file-based locking to prevent concurrent generation race conditions

### Mtime inequality (artifact >= source)

**Pros:**
- Standard make-style approach, widely understood
- No need to explicitly set artifact timestamps
- Tolerates some clock drift

**Cons:**
- Less precise (artifact accidentally newer than source would false-cache)
- Doesn't prevent timestamp collisions when source and artifact have identical mtimes by chance
- Still requires source file aggregation for composition

### Content-based hashing

**Pros:**
- Most robust against timestamp manipulation
- Immune to clock skew issues
- Can detect functionally identical content even after file moves

**Cons:**
- Expensive I/O (must read entire source files for hashing)
- Slower cache checks, especially for large node trees
- Requires hash storage mechanism (database or sidecar files)
- Overkill for typical development workflows

## Consequences

The mtime-based strategy enables fast incremental builds critical for development iteration speed. Changing a single source file deep in a node tree correctly invalidates only the affected nodes and their ancestors, not the entire project.

The equality check requirement means developers cannot manually touch files to force rebuilds—they must modify source content or delete generated artifacts. This trade-off is acceptable given the precision benefits.

Lock files (`.stl.lock` containing process PID) prevent race conditions when concurrent builds attempt to generate the same STL. The framework checks if the PID is still alive to detect stale locks from crashed processes. This file-based approach works across processes and platforms without OS-specific locking APIs.

The strategy assumes OpenSCAD compilation is deterministic. Non-deterministic CAD backends would require additional versioning or content verification to maintain cache correctness.

Distributed builds would require clock synchronization between machines or migration to content-based hashing, as network filesystems may have timestamp resolution issues.

## References

- `solid_node/node/base.py:118` - File tracking initialization
- `solid_node/node/base.py:195-200` - Mtime calculation
- `solid_node/node/base.py:328-332` - Up-to-date equality check
- `solid_node/node/internal.py:40` - Child file aggregation
- `solid_node/node/base.py:260-272` - Lock file and STL generation
