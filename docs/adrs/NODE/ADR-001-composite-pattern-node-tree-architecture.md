# ADR-001: Composite Pattern for Node Tree Architecture

**Status:** Accepted
**Date:** 2023-07-09
**Used by:**
- [ADR-002: Template Method Pattern for Node Lifecycle](./ADR-002-template-method-pattern-for-node-lifecycle.md)
- [ADR-003: Rigid vs Non-Rigid Node Distinction](./ADR-003-rigid-vs-non-rigid-node-distinction.md)
- [ADR-005: Path-Based Dynamic Module Loading](../BUILD/ADR-005-path-based-dynamic-module-loading.md)
- [ADR-014: Recursive NodeAPI REST Pattern Mirroring Node Tree](../VIEWER-WEB/ADR-014-recursive-nodeapi-rest-pattern.md)

**Related to:** [ADR-009: Trimesh-Based Mesh Assertions for CAD Testing](../TEST-FRAMEWORK/ADR-009-trimesh-based-mesh-assertions-for-cad-testing.md)

## Context and Problem Statement

The framework needed an architectural pattern to represent mechanical CAD projects that could handle varying complexity - from simple primitive shapes to complex assemblies with hundreds of components. The solution required uniform treatment of both individual geometric primitives and composite assemblies, enabling recursive operations across the entire project structure.

The core challenge was modeling hierarchical mechanical assemblies where components can be nested arbitrarily deep, while maintaining clear boundaries between geometry generation (leaf operations) and composition (internal operations). The system needed to support multiple CAD backends, incremental builds with change detection, and validation at each level of the hierarchy.

## Decision Drivers

- Need for uniform treatment of primitive shapes and complex assemblies in the same API
- Requirement to support recursive operations like assembly, validation, and file tracking across arbitrary nesting levels
- Multiple CAD backend support requiring abstraction of geometry generation from composition logic
- Incremental build system requiring source file tracking aggregated across component hierarchies
- Type safety to prevent structural inconsistencies that could break the rendering pipeline
- Intuitive mental model for mechanical engineers thinking in terms of parts and assemblies

## Considered Options

1. Composite pattern with explicit leaf/internal node separation
2. Flat node graph with manual relationship management
3. Entity-Component-System architecture from game engines

## Decision Outcome

Chosen option: Composite pattern with explicit leaf/internal node separation, because it directly models the problem domain of hierarchical mechanical assemblies. The pattern enables recursive operations through uniform node interfaces while enforcing structural constraints through base class separation.

The implementation uses AbstractBaseNode as the root, with LeafNode for geometry generation and InternalNode for child composition. Strict validation enforces that LeafNodes return CAD objects while InternalNodes return child lists, preventing type errors at runtime.

## Pros and Cons of the Options

### Composite Pattern with Leaf/Internal Separation

**Pros:**
- Direct mapping to mechanical assembly concepts that engineers understand intuitively
- Recursive operations work naturally through uniform node interface
- Type validation at base class level prevents structural errors early
- Clean separation of concerns between geometry generation and composition
- Enables feature aggregation like rigid propagation and file tracking across subtrees

**Cons:**
- Requires understanding abstract base classes and inheritance hierarchy
- Circular dependency detection must be handled explicitly without parent references
- Cross-cutting operations that need upward tree navigation require workarounds
- Higher learning curve for developers unfamiliar with Composite pattern

### Flat Node Graph

**Pros:**
- Simpler conceptual model with explicit relationship objects
- Easier to implement bidirectional navigation with parent references
- More flexible for non-hierarchical relationships between components

**Cons:**
- Parent-child relationships less intuitive for mechanical assemblies
- Recursive composition operations require manual graph traversal logic
- Type safety harder to enforce without base class constraints
- Less natural mapping to the hierarchical nature of CAD assemblies

### Entity-Component-System

**Pros:**
- Highly flexible for adding behaviors to nodes dynamically
- Common pattern in game engines with proven scalability
- Supports composition over inheritance principle

**Cons:**
- Overly complex for the problem domain of mechanical CAD
- Less intuitive mental model for mechanical engineers
- Query systems and component management add unnecessary overhead
- Poor fit for hierarchical assembly structures

## Consequences

The Composite pattern has proven stable over 2.5 years with minimal modifications to the core abstraction. All framework features - viewers, build system, testing, and CAD adapters - successfully build on this foundation.

The rigid propagation mechanism enables the build system to determine STL generation eligibility by traversing the tree. File tracking aggregates source files across subtrees for incremental builds. Validation enforcement prevents structural errors that would only manifest during rendering.

The lack of parent references simplifies the tree structure but requires passing root context downward for operations needing global state. This trade-off has not caused significant issues in practice.

Future architectural changes would require framework-wide rewrites, making this a high-commitment decision. However, the pattern's stability and successful support of diverse features validate the initial architectural choice.

## References

- `solid_node/node/base.py:41-46` - AbstractBaseNode definition
- `solid_node/node/leaf.py:20-27` - LeafNode specialization
- `solid_node/node/internal.py:21-23` - InternalNode specialization
