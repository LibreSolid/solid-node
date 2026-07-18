# ADR-008: Time-Based Animation System for Assemblies

**Status:** Accepted
**Date:** 2023-07-09
**Depends on:** [ADR-003: Rigid vs Non-Rigid Node Distinction](./ADR-003-rigid-vs-non-rigid-node-distinction.md)
**Used by:** [ADR-011: Animation Testing Decorators for Time-Based Validation](../TEST-FRAMEWORK/ADR-011-animation-testing-decorators.md)
**Extended by:** [ADR-023: Kinematic Operations Model and Driver-Tagged Idempotent Renders](./ADR-023-kinematic-operations-and-driver-tagged-idempotent-renders.md)

## Context and Problem Statement

The framework needed to support animated visualizations of mechanical assemblies with movable parts while maintaining a clean separation between static geometry and dynamic motion. Mechanical CAD designs often include articulated components - robot arms, hinges, gears, servos - that must be visualized in motion and tested at specific positions.

The challenge was enabling time-dependent motion for assemblies without allowing morphing geometry at the leaf level, while integrating animation with the testing framework for validating mechanical properties across motion ranges. The solution needed to leverage OpenSCAD's existing animation infrastructure without introducing complex timeline management.

## Decision Drivers

- Enable animated visualizations for mechanical assemblies in web and OpenSCAD viewers
- Support testing of geometric relationships at specific animation keyframes
- Maintain architectural distinction between rigid geometry and articulated assemblies
- Leverage OpenSCAD's built-in animation infrastructure (0-1 normalized time variable)
- Provide simple, property-based API for expressing time-dependent motion
- Prevent time-dependent leaf geometry to preserve STL caching assumptions

## Considered Options

1. OpenSCAD-based normalized time property restricted to AssemblyNode
2. Custom timeline system with independent per-assembly animation clocks
3. Real-time clock-based animation with actual seconds instead of normalized 0-1 range

## Decision Outcome

Chosen option: OpenSCAD-based normalized time property restricted to AssemblyNode, because it directly leverages OpenSCAD's proven animation infrastructure, enforces the rigid/non-rigid architectural distinction, and provides dual-purpose support for both visualization and testing through simple property access.

AssemblyNode exposes a `time` property (0 to 1 range) that delegates to OpenSCAD's `$t` variable via SolidPython2's `get_animation_time()` function during runtime. For testing, `set_keyframe(time)` overrides the property to freeze animation at specific frames. FusionNode and LeafNode explicitly block time access with exceptions, enforcing the constraint that only non-rigid assemblies support animation.

The implementation uses a dual-mode approach: runtime animation reads from OpenSCAD's global time variable, while testing sets a fixed `_time` attribute. Test decorators (`@testing_instant(time)`, `@testing_steps(steps, start, end)`) enable geometric assertions at specific animation frames.

## Pros and Cons of the Options

### OpenSCAD-based normalized time property

- Good: Zero additional complexity by reusing OpenSCAD's proven animation system
- Good: 0-1 normalization is standard CAD animation convention
- Good: Dual-mode design elegantly serves both visualization and testing
- Good: Property-based access feels natural in code (self.time * 360)
- Good: Exception-based blocking guides users to correct node types
- Bad: Global time variable prevents independent animation timelines for different assemblies
- Bad: 0-1 range requires manual scaling to real-world units (RPM, mm/s)
- Bad: OpenSCAD coupling limits animation to OpenSCAD semantics
- Bad: AssemblyNode-only restriction prevents morphing leaf geometry

### Custom timeline system with independent clocks

- Good: Would enable different assemblies animating at different speeds
- Good: Could support complex multi-timeline synchronization
- Good: Framework-controlled timing independent of viewer implementation
- Bad: High implementation complexity for timeline management
- Bad: Requires custom synchronization logic in viewers
- Bad: Breaks OpenSCAD viewer integration
- Bad: Testing would need more complex time control mechanisms

### Real-time clock-based animation

- Good: Direct mapping to real-world motion speeds and units
- Good: No manual scaling from 0-1 range
- Good: Easier to reason about physical motion (30 RPM, 5 mm/s)
- Bad: OpenSCAD incompatibility (expects 0-1 normalized variable)
- Bad: Testing becomes time-sensitive and non-deterministic
- Bad: Unit conversion complexity (seconds vs milliseconds vs frames)
- Bad: Viewer playback controls more complex

## Consequences

The time-based animation system successfully bridges visualization, testing, and modeling through a single unified property. Users express motion in `render()` methods using simple time-based calculations, viewers control animation playback, and tests validate geometry at specific keyframes.

The restriction to AssemblyNode maintains architectural consistency with the rigid/non-rigid distinction - rigid nodes cannot change over time, preventing time access on FusionNode and LeafNode. This constraint preserves STL caching assumptions and guides users toward correct node type selection.

The global time variable creates a limitation for complex multi-assembly animations where different components need independent speeds. Users work around this through time scaling in their code (e.g., `self.time * 2` for double speed), which is sufficient for current use cases but may become limiting for sophisticated mechanical simulations.

The rename from `set_testing_time()` to `set_keyframe()` in November 2023 improved API clarity by borrowing animation terminology and acknowledging that keyframes serve dual purposes beyond just testing. This evolution demonstrates thoughtful API refinement based on usage patterns.

The mentioned "FlexibleNode" for time-dependent leaf geometry remains unimplemented in the roadmap, suggesting the current restriction adequately covers practical use cases. Implementing morphing geometry would add complexity around mesh topology changes and STL caching invalidation.

## References

- solid-node/solid_node/node/assembly.py:32-43
- solid-node/solid_node/node/fusion.py:30-33
- solid-node/solid_node/node/leaf.py:35-39
- solid-node/solid_node/node/internal.py:26-30
