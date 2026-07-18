# ADR-011: Animation Testing Decorators for Time-Based Validation

**Status:** Accepted
**Date:** 2023-07-20
**Depends on:**
- [ADR-008: Time-Based Animation System for Assemblies](../NODE/ADR-008-time-based-animation-system-for-assemblies.md)
- [ADR-009: Trimesh-Based Mesh Assertions for CAD Testing](./ADR-009-trimesh-based-mesh-assertions-for-cad-testing.md)

## Context and Problem Statement

The solid-node framework supports time-based animation in AssemblyNode through a `time` property that controls dynamic mechanical configurations. Testing animated assemblies requires validating node behavior at specific animation keyframes or across entire animation sequences to ensure correctness throughout movement ranges.

Without dedicated testing support, developers would need to manually manage time state in each test method, creating repetitive boilerplate for time setup, node re-rendering, and state cleanup. This approach obscures test intent and makes comprehensive animation validation cumbersome, particularly when validating behavior across multiple time points.

The framework needed a declarative mechanism to control animation time during test execution while integrating with the existing test infrastructure and checkpoint system.

## Decision Drivers

- Animated assemblies require validation at specific time points and across time ranges
- Test intent should be clear and declarative rather than buried in time management boilerplate
- Single test method should validate behavior across entire animation sequences without duplication
- Test framework must handle node re-rendering and state restoration between time points automatically
- Integration with existing mesh assertion methods and TestCaseMixin pattern necessary
- Custom Test manager architecture required specialized solution beyond standard pytest capabilities

## Considered Options

1. **Decorator pattern with testing_instant and testing_steps** (chosen)
2. Pytest parametrize integration with time parameter injection
3. Manual time management via helper methods in test code

## Decision Outcome

Chosen option: **Decorator pattern with testing_instant and testing_steps**, because it provides declarative control over animation time that clearly expresses test intent while integrating seamlessly with the custom Test manager's checkpoint and instant iteration infrastructure.

Two decorators were implemented: `@testing_instant(time)` for single keyframe validation and `@testing_steps(steps, start, end)` for continuous validation across animation ranges. Decorators set a `testing_instants` attribute on test methods, which the Test manager reads to execute tests multiple times with different time values via `node.set_keyframe(instant)`.

The pattern has remained stable for 2.5 years since introduction, indicating successful alignment with animation testing requirements.

## Pros and Cons of the Options

### Decorator pattern with testing_instant and testing_steps

**Pros:**
- Declarative syntax clearly expresses test timing requirements at method definition
- Single test method validates behavior across multiple time points without code duplication
- Test manager handles time setup, node re-rendering, and checkpoint restoration automatically
- Visual feedback via colored dot output shows pass/fail status per instant

**Cons:**
- Tests execute multiple times for multi-step animations, increasing execution time
- Decorator pattern less discoverable than explicit method parameters for new developers
- Incompatible with standard pytest framework, requires custom Test manager
- Test failure output doesn't clearly identify which instant failed without examining dot colors

### Pytest parametrize integration

**Pros:**
- Leverages standard Python testing ecosystem and pytest features
- Familiar pattern for developers experienced with pytest
- Better IDE integration and tooling support

**Cons:**
- Framework uses custom Test manager incompatible with pytest architecture
- Would require significant refactoring of test infrastructure
- Pytest parametrization doesn't integrate with checkpoint system for state restoration
- Cannot leverage existing instant iteration and node re-rendering logic

### Manual time management via helper methods

**Pros:**
- Explicit control over time state in test code
- No new framework concepts to learn
- Compatible with any test runner

**Cons:**
- Repetitive boilerplate for time setup and node re-rendering in every test
- Test intent obscured by time management code
- Error-prone state management between time points
- Difficult to validate behavior across many time points without loops

## Consequences

**Positive:**
- Enables comprehensive validation of animated mechanical assemblies across time ranges
- Declarative decorator syntax improves test readability and maintainability
- Automatic checkpoint management prevents state leakage between instant executions
- Establishes consistent pattern for animation testing across framework

**Negative:**
- Couples testing framework to custom Test manager, preventing pytest migration
- Performance cost for high step counts requires careful test design
- Developers must understand decorator behavior and relationship to animation system
- Test output becomes unwieldy for very high step counts

**Neutral:**
- Establishes decorator pattern precedent for test execution control in framework
- Animation API changes may require corresponding decorator modifications
- Tests validate final rendered geometry at each instant rather than animation logic itself

## References

- solid_node/test.py:117-147
- solid_node/manager/test.py:84-137
- solid_node/test.py:44-106
