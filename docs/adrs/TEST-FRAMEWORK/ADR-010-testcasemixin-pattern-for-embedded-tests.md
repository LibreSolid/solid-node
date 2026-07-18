# ADR-010: TestCaseMixin Pattern for Embedded Tests

**Status:** Accepted
**Date:** 2023-07-20
**Depends on:** [ADR-009: Trimesh-Based Mesh Assertions for CAD Testing](./ADR-009-trimesh-based-mesh-assertions-for-cad-testing.md)

## Context and Problem Statement

The framework needed to provide a testing approach for user-created CAD nodes. Developers building mechanical projects must validate geometric relationships and design constraints. The traditional approach requires separate test files (e.g., `test_my_node.py` alongside `my_node.py`), which can create friction during rapid prototyping or test-driven development workflows.

The framework provides CAD-specific assertions (intersection, containment, proximity) that require testing individual nodes. The question was whether tests should always be separated from node implementation, or whether the framework should support co-location of tests with rendering logic for convenience during development.

## Decision Drivers

- Developer workflow efficiency during prototyping and test-driven development
- Consistency with standard Python testing practices (unittest, pytest)
- Separation of concerns between production node code and test logic
- Flexibility to support different project organization preferences
- Integration with `solid <path> test` CLI command
- Multiple inheritance complexity with node base classes

## Considered Options

1. **Dual-pattern approach with optional TestCaseMixin** (chosen)
2. Require separate external test files exclusively
3. Embedded tests only via mixin pattern

## Decision Outcome

Chosen option: **Dual-pattern approach with optional TestCaseMixin**, because it provides flexibility for different development workflows while maintaining compatibility with standard testing practices. Developers can choose based on project needs: co-located tests for small nodes or rapid prototyping, separate files for complex nodes or team projects requiring strict separation.

The implementation uses a TestCaseMixin class that overrides `set_node()` to be a no-op, since `self` and `node` become the same object when a node class inherits the mixin. The test manager automatically discovers and runs both embedded tests (via TestCaseMixin) and external tests (via separate test files) for the same node.

This approach has remained stable for 2.5 years with no modifications to the core pattern, though the framework's own test suite exclusively uses external tests rather than the mixin pattern.

## Pros and Cons of the Options

### Dual-pattern approach with optional TestCaseMixin

**Pros:**
- Developers choose organization based on project context and team preferences
- Co-location reduces navigation overhead for small nodes during prototyping
- Maintains compatibility with standard unittest framework patterns
- External pattern available for projects requiring strict separation

**Cons:**
- Introduces inconsistency across projects without clear guidance on pattern selection
- Mixin requires multiple inheritance (Node + TestCaseMixin) adding complexity
- Mixed test and production code may confuse IDE tools and static analyzers
- Framework maintains dual-pattern support without using embedded pattern internally

### Require separate external test files exclusively

**Pros:**
- Enforces separation of concerns between tests and implementation
- Consistent project organization across all nodes
- No multiple inheritance complexity
- Better IDE support for test discovery

**Cons:**
- Navigation friction during rapid prototyping workflows
- More boilerplate for simple nodes with few tests
- Less convenient for test-driven development of single components

### Embedded tests only via mixin pattern

**Pros:**
- Single consistent approach reduces decision burden
- Simplified test discovery (only check node classes)
- No separate test files to maintain

**Cons:**
- Violates separation of concerns for all projects
- Node files grow large with extensive test suites
- Harder to share test utilities across nodes
- Poor fit for team projects with dedicated test maintenance

## Consequences

**Positive:**
- Flexibility supports both rapid prototyping and structured team development
- Test manager seamlessly handles both patterns with automatic discovery
- Developers can migrate from embedded to external tests as projects mature
- Framework provides CAD assertions usable in both testing approaches

**Negative:**
- Lack of documented guidance creates decision burden for users
- Dual-pattern maintenance burden in test discovery and execution infrastructure
- Framework's own practice (external tests) diverges from provided feature (mixin)
- Multiple inheritance with TestCaseMixin may conflict with complex node hierarchies

**Neutral:**
- Pattern selection becomes per-project architectural decision
- Snake_case aliasing in external tests provides automatic node attribute naming
- Test command runs both patterns sequentially if both present for same node

## References

- solid_node/test.py:108-115 - TestCaseMixin implementation
- solid_node/manager/test.py:61-83 - Test manager supporting dual patterns
- solid_node/core/loader.py:32-44 - External test file discovery convention

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
