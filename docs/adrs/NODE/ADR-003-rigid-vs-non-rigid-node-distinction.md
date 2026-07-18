# ADR-003: Rigid vs Non-Rigid Node Distinction

**Status:** Accepted
**Date:** 2023-07-09
**Depends on:** [ADR-001: Composite Pattern for Node Tree Architecture](./ADR-001-composite-pattern-node-tree-architecture.md)
**Used by:**
- [ADR-006: Mtime-Based STL Caching Strategy](./ADR-006-mtime-based-stl-caching-strategy.md)
- [ADR-008: Time-Based Animation System for Assemblies](./ADR-008-time-based-animation-system-for-assemblies.md)

## Context and Problem Statement

The framework needs to represent both static mechanical parts (fixed geometry) and dynamic assemblies (movable parts with animation). A core challenge is determining when geometry can be compiled to optimized STL mesh files for incremental builds versus when it must be dynamically rendered.

Mechanical CAD models fall into two categories: rigid objects that maintain fixed geometry (bolts, brackets, enclosures) and articulated assemblies with moving parts (robot arms, hinges, animated mechanisms). The framework must distinguish these to enable STL caching for rigid nodes while supporting time-based animation for assemblies.

The build system relies on mtime-based caching to avoid regenerating unchanged models. This optimization requires knowing which nodes produce stable, time-invariant geometry suitable for STL representation.

## Decision Drivers

- Enable incremental build optimization through STL caching for static geometry
- Support time-based animation for mechanical assemblies with movable parts
- Prevent invalid STL generation for time-dependent or articulated geometry
- Provide clear user guidance on node type selection (FusionNode vs AssemblyNode)
- Ensure rigidity constraints propagate correctly through composite node trees
- Maintain architectural simplicity with binary classification

## Considered Options

1. Binary rigidity with automatic tree propagation
2. Partial rigidity system (some parts rigid, some non-rigid)
3. Time-frozen STL snapshots at specific animation frames

## Decision Outcome

Chosen option: Binary rigidity with automatic tree propagation, because it correctly models the mechanical domain where objects are either static or articulated, enables safe mtime-based caching, and provides clear architectural constraints.

Nodes declare rigidity via boolean `rigid` property (default `True`). FusionNode remains rigid and blocks `time` property access. AssemblyNode sets `rigid = False` and exposes `time` for animation. Rigidity propagates up the tree: if any child is non-rigid, the parent becomes non-rigid (`parent.rigid = parent.rigid AND child.rigid`).

Only rigid nodes generate STL files. Non-rigid nodes return early from STL generation with log message. Runtime exceptions guide users: "use AssemblyNode for animation" when accessing `time` on FusionNode.

## Pros and Cons of the Options

### Binary rigidity with automatic tree propagation

- Good: Simple mental model matching mechanical CAD domain (static vs articulated)
- Good: Enables safe STL caching without time-dependency concerns
- Good: Automatic propagation prevents invalid STL generation attempts
- Good: Clear error messages guide users to correct node types
- Bad: No middle ground for partially-rigid objects
- Bad: Deep non-rigid child makes entire ancestor chain non-rigid (can surprise users)
- Bad: Leaf nodes cannot use `time` for organic/growing shapes

### Partial rigidity system

- Good: Could support hybrid assemblies with some cached parts
- Good: More flexible for complex mechanical designs
- Bad: High complexity for STL caching logic (which parts cache when)
- Bad: Unclear semantics for partially-rigid node propagation
- Bad: Difficult to reason about incremental build correctness

### Time-frozen STL snapshots

- Good: Would allow animation preview via pre-rendered frames
- Good: Could support time-dependent leaf geometry
- Bad: High storage cost for multi-frame animations
- Bad: Discrete frames versus continuous time creates user confusion
- Bad: Breaks mtime-based caching assumptions

## Consequences

The binary rigidity constraint couples three architectural concerns: STL generation capability, animation support, and node type selection. This coupling is intentional and enforces correct usage patterns.

Users must understand rigidity propagation when composing node trees. A single animated servo buried in an assembly makes the entire top-level assembly non-rigid, preventing STL generation at ancestor levels. This is mechanically correct (cannot freeze a robot arm if one joint moves) but requires awareness.

The framework intentionally guides users toward its architectural vision through pedagogical exception messages rather than being maximally flexible. The mentioned "FlexibleNode" for time-dependent leaf geometry remains unimplemented, indicating the rigid/non-rigid distinction adequately covers current use cases.

Build optimization benefits significantly: rigid nodes leverage mtime-based STL caching for fast incremental builds, while non-rigid assemblies always render SCAD directly. The constraint enables safe caching by guaranteeing cached geometry is time-invariant.

## References

- solid-node/solid_node/node/base.py:54 (rigid property default)
- solid-node/solid_node/node/base.py:188-192 (STL generation guard)
- solid-node/solid_node/node/internal.py:41 (rigidity propagation)
- solid-node/solid_node/node/assembly.py:30 (non-rigid with time property)
- solid-node/solid_node/node/fusion.py:30-33 (rigid blocks time access)
