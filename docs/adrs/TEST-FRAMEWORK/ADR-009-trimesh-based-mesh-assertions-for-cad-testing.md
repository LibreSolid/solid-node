# ADR-009: Trimesh-Based Mesh Assertions for CAD Testing

**Status:** Accepted
**Date:** 2023-07-16
**Used by:**
- [ADR-010: TestCaseMixin Pattern for Embedded Tests](./ADR-010-testcasemixin-pattern-for-embedded-tests.md)
- [ADR-011: Animation Testing Decorators for Time-Based Validation](./ADR-011-animation-testing-decorators.md)

**Extended by:** [ADR-025: Perturbation-Based Kinematic Fit Assertions](./ADR-025-perturbation-based-kinematic-fit-assertions.md)

**Related to:** [ADR-001: Composite Pattern for Node Tree Architecture](../NODE/ADR-001-composite-pattern-node-tree-architecture.md)

## Context and Problem Statement

The solid-node framework enables development of mechanical projects using CAD tools, requiring validation of 3D geometric relationships between parts. Standard unittest assertions (`assertEqual`, `assertTrue`, etc.) are insufficient for CAD testing because they operate on primitive values, not spatial relationships. Testing mechanical designs requires validating geometric properties: whether parts intersect, maintain clearances, are properly contained, or meet distance constraints.

Traditional approaches like numerical bounding box checks lack precision for complex geometries. Visual or screenshot-based testing is subjective and cannot validate internal geometric properties. The framework needed domain-specific assertions that validate actual 3D mesh geometry with semantic meaning for mechanical design.

## Decision Drivers

- CAD testing requires validation of spatial relationships impossible with standard assertions
- Geometric validation must operate on final rendered 3D meshes, not intermediate representations
- Test assertions should provide quantitative feedback (volumes, distances) for design iteration
- Performance acceptable for test suites despite computational cost of mesh operations
- Integration with existing unittest framework to maintain familiar testing patterns
- Robustness of boolean operations critical for reliable test results

## Considered Options

1. **Trimesh library for mesh-based geometric assertions** (chosen)
2. Numerical bounding box approximations with tolerance thresholds
3. Direct OpenSCAD boolean operations for validation

## Decision Outcome

Chosen option: **Trimesh library for mesh-based geometric assertions**, because it provides robust CSG boolean operations and proximity calculations wrapped in intuitive test methods. The library handles complex computational geometry while exposing simple assertion interfaces that align with unittest patterns.

This established seven geometric assertion methods: `assertNotIntersecting`, `assertIntersecting`, `assertInside`, `assertClose`, `assertFar`, `assertIntersectVolumeAbove`, and `assertIntersectVolumeBelow`. Each assertion performs mesh operations and provides meaningful error messages with quantitative measurements.

The decision has proven stable over 2.5 years with only interface refinements and documentation improvements, indicating successful alignment with CAD testing requirements.

## Pros and Cons of the Options

### Trimesh library for mesh-based geometric assertions

**Pros:**
- Semantically correct validation of 3D geometry relationships
- Robust boolean operation implementations handle edge cases
- Proximity calculations provide precise distance measurements
- Error messages include quantitative data (volumes, distances) for debugging
- Integrates cleanly with unittest.TestCase patterns

**Cons:**
- Requires mesh generation (STL rendering) before testing, adding computational overhead
- Mesh operations slower than pure numerical calculations
- Creates dependency on trimesh library maintenance and capabilities
- May limit testing of very large models or non-rigid assemblies due to performance

### Numerical bounding box approximations

**Pros:**
- Fast computations suitable for large test suites
- Simple implementation without external dependencies
- Low computational overhead

**Cons:**
- Inaccurate for complex geometries with irregular shapes
- Cannot validate precise geometric relationships like containment
- Produces false positives/negatives for non-axis-aligned parts
- Lacks semantic meaning for mechanical design validation

### Direct OpenSCAD boolean operations

**Pros:**
- Uses same engine as production rendering
- Consistent behavior with final output
- No additional library dependencies

**Cons:**
- Requires process spawning for each test operation
- Significantly slower than in-memory mesh operations
- Less flexible for proximity and distance calculations
- Error reporting limited to OpenSCAD output format

## Consequences

**Positive:**
- Enables comprehensive geometric validation impossible with traditional assertions
- Establishes intuitive testing patterns for CAD domain developers
- Quantitative error messages accelerate design iteration debugging
- Stable implementation (2.5 years) demonstrates architectural soundness

**Negative:**
- Test execution requires mesh rendering step before assertions
- Performance constraints may affect testing strategy for large assemblies
- Creates dependency on trimesh boolean operation robustness

**Neutral:**
- Establishes trimesh as standard mesh processing library for framework
- Constrains testing to mesh-based approaches (trade-off: precision vs. performance)
- Tests validate output geometry rather than intermediate code state

## References

- solid_node/test.py:44-106 - Complete TestCase implementation with mesh assertions
- solid_node/test.py:44-51 - assertNotIntersecting implementation using boolean intersection
- solid_node/test.py:67-75 - assertClose implementation using proximity calculations
