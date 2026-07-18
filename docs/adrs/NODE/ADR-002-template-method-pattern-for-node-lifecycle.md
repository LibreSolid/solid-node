# ADR-002: Template Method Pattern for Node Lifecycle

**Status:** Accepted
**Date:** 2023-07-09
**Depends on:** [ADR-001: Composite Pattern for Node Tree Architecture](./ADR-001-composite-pattern-node-tree-architecture.md)
**Related to:** [ADR-004: Multi-CAD Backend Adapter Pattern](./ADR-004-multi-cad-backend-adapter-pattern.md)

## Context and Problem Statement

The framework needed a consistent extension mechanism for users to create custom CAD nodes while ensuring every node follows the same build pipeline. The challenge was balancing flexibility (users define their own geometry) with consistency (all nodes must validate, generate SCAD files, optimize with cached STLs, and apply transformations in the correct order).

Without a structured approach, users could bypass validation, skip optimization steps, or apply operations incorrectly, leading to inconsistent builds, broken caching, and difficult debugging. The framework required a design that separates user-provided geometry logic from the framework's orchestration of the build process.

The Template Method pattern emerged as the solution: users implement `render()` to define geometry or child nodes, while the framework's `assemble()` method orchestrates the fixed pipeline sequence.

## Decision Drivers

- **Consistency across all nodes**: Every node must follow the same build pipeline regardless of CAD backend or complexity
- **Early error detection**: Type validation must occur before expensive SCAD generation
- **Optimization reuse**: Cached STL imports must work even when nodes have transformations applied
- **Clear extension points**: Users need obvious methods to override (render) versus framework-controlled behavior (assemble)
- **Performance through caching**: Assembled results must be cached to prevent redundant work during tree traversal
- **Pipeline correctness**: The sequence of validation, conversion, generation, optimization, and transformation must be enforced

## Considered Options

1. **Template Method Pattern with render() and assemble()** (chosen)
2. **Single build() method with optional hooks**
3. **Strategy Pattern with pluggable pipeline objects**

## Decision Outcome

Chosen option: "Template Method Pattern with render() and assemble()", because it provides the best balance of user simplicity and framework control. Users implement one method (`render()`) while the framework guarantees correct pipeline execution through non-overridable `assemble()`.

The pipeline sequence is: render → validate → as_scad → generate_scad → import_optimized → apply operations → cache result.

## Pros and Cons of the Options

### Template Method Pattern with render() and assemble()

- **Pro**: Users only implement `render()`, framework controls entire pipeline
- **Pro**: Validation occurs before SCAD generation, catching errors early
- **Pro**: Operations apply after optimization, enabling STL reuse with transformations
- **Pro**: Idempotent via cached result, safe to call assemble() multiple times
- **Con**: Fixed pipeline prevents per-node customization of build steps
- **Con**: Single render call with caching prevents dynamic re-rendering
- **Con**: Cannot validate post-operation geometry

### Single build() method with optional hooks

- **Pro**: Simpler mental model with one method instead of two
- **Pro**: Users could override entire build process for special cases
- **Con**: No guarantee users call validation, optimization, or operations correctly
- **Con**: Inconsistent build behavior across different node types
- **Con**: Error-prone for users who must remember all pipeline steps

### Strategy Pattern with pluggable pipeline objects

- **Pro**: Maximum flexibility, each node could customize pipeline
- **Pro**: Build steps could be reordered or replaced per-node
- **Con**: Significantly higher complexity for users
- **Con**: Loss of consistency guarantees across nodes
- **Con**: Difficult to ensure optimization and caching work correctly

## Consequences

**Positive**:
- All nodes follow identical build pipeline, ensuring consistent behavior
- Users have clear extension point (render) versus framework-controlled logic (assemble)
- Early validation catches type errors before expensive operations
- STL caching works reliably because operations apply after optimization
- Recursive assembly in InternalNode propagates root path correctly for relative imports

**Negative**:
- Fixed pipeline cannot be customized for special-case nodes
- Cached assembled result prevents re-rendering if parameters change after construction
- Operations apply after optimization, requiring separate mesh generation for spatial testing
- Idempotency flag hides whether assemble() performed work or returned cached result

**Neutral**:
- Pattern stability over 2.5 years indicates correct pipeline steps and ordering
- Extension points (render, validate, as_scad) are sufficient for current use cases
- Assumes single-threaded execution due to instance-level caching flag

## References

- `solid_node/node/base.py:138-166` - Template method implementation
- `solid_node/node/base.py:202-207` - Abstract render() and optimization logic
- `solid_node/node/leaf.py:46-51` - Leaf-specific validation
- `solid_node/node/internal.py:32-48` - Recursive assembly in InternalNode

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
