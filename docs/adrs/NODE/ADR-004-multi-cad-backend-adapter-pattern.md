# ADR-004: Multi-CAD Backend Adapter Pattern

**Status:** Accepted
**Date:** 2023-07-25
**Related to:** [ADR-002: Template Method Pattern for Node Lifecycle](./ADR-002-template-method-pattern-for-node-lifecycle.md)

## Context and Problem Statement

The framework supports multiple CAD libraries (SolidPython2, CadQuery, OpenSCAD, JSCAD) through a unified adapter pattern, allowing users to choose the best tool for each component while maintaining a consistent node interface. Different modeling tasks benefit from different paradigms: procedural generation (SolidPython2), parametric modeling with constraints (CadQuery), direct low-level control (OpenSCAD), or JavaScript-based workflows (JSCAD).

Forcing users to master a single CAD library limits flexibility and prevents leveraging domain-specific strengths. However, supporting multiple backends introduces integration complexity: each library has different APIs, object types, and geometric representations. The system must compose heterogeneous geometry into unified assemblies while maintaining type safety and consistent output.

The challenge is enabling multi-backend support without fragmenting the codebase or creating incompatible geometry representations.

## Decision Drivers

- Enable users to choose the best CAD tool for each component based on task requirements
- Maintain consistent node interface regardless of underlying CAD backend
- Ensure geometric compatibility when mixing components from different backends
- Prevent runtime errors from type mismatches between backends
- Support future addition of new CAD backends without major refactoring
- Leverage existing OpenSCAD ecosystem for robust STL generation

## Considered Options

1. **Multi-CAD adapter pattern with OpenSCAD compilation target** (Chosen)
2. **Single mandatory CAD backend with comprehensive feature set**
3. **Native STL generation per backend without universal intermediate format**

## Decision Outcome

Chosen option: **Multi-CAD adapter pattern with OpenSCAD compilation target**, because it maximizes user flexibility while ensuring geometric consistency. Implemented through LeafNode subclasses that wrap each CAD backend, requiring two critical methods: `as_scad()` for conversion to OpenSCAD representation, and `validate()` for namespace-based type checking.

The pattern uses OpenSCAD as the universal compilation target - all backends must output OpenSCAD code, which is then compiled to STL. This architectural choice ensures all geometry is compatible for composition while leveraging OpenSCAD's mature STL generation capabilities.

Evidence from git history shows the pattern was established in July 2023 and successfully accommodated new backends (JSCAD, CQ-editor integration) in February 2025 without requiring structural changes, validating the design's extensibility.

## Pros and Cons of the Options

### Multi-CAD adapter pattern with OpenSCAD compilation target

- **Good**: Users choose best tool for each task (procedural generation vs parametric modeling vs direct control)
- **Good**: Consistent node interface abstracts backend differences
- **Good**: OpenSCAD compilation ensures all geometry is compatible for composition
- **Good**: Successfully accommodated new backends (JSCAD 2025) without refactoring
- **Bad**: OpenSCAD's CSG limitations prevent using advanced NURBS/BREP features from CadQuery
- **Bad**: Users must learn multiple CAD libraries to leverage full power
- **Bad**: Subprocess invocations for external tools (JSCAD, OpenSCAD) add latency
- **Bad**: Namespace validation adds runtime overhead

### Single mandatory CAD backend

- **Good**: Users master one tool deeply rather than learning multiple APIs
- **Good**: No conversion overhead or subprocess invocations
- **Good**: Simpler architecture with no adapter layer
- **Bad**: Forces compromise choice - no single library excels at all modeling tasks
- **Bad**: Limits users who have existing expertise in other CAD tools
- **Bad**: Tight coupling to one library's release cycle and ecosystem

### Native STL generation per backend

- **Good**: Each backend uses its native capabilities without conversion
- **Good**: Avoids OpenSCAD CSG limitations for advanced geometry
- **Bad**: Prevents geometric composition before STL generation (only assembly-level mixing)
- **Bad**: Inconsistent STL quality across backends
- **Bad**: Cannot validate geometric compatibility until final assembly

## Consequences

The adapter pattern successfully bridges paradigm differences: procedural CSG (SolidPython2), parametric modeling (CadQuery), direct SCAD code (OpenSCAD), and JavaScript-based workflows (JSCAD). Each backend requires maintaining compatibility with LeafNode interface, particularly the `as_scad()` method.

OpenSCAD as the universal compilation target creates an architectural constraint: all geometry must be representable in OpenSCAD's CSG model. This prevents using CadQuery's advanced NURBS/BREP capabilities but ensures consistent geometric compatibility. Moving to a different universal format (STEP, BREP) would require major refactoring of all adapters.

The CadQueryNode metaclass enables dual-mode operation - same code runs standalone in CQ-editor or within the framework. This pragmatic solution increases flexibility but adds conceptual complexity. Future backend additions must implement the LeafNode contract and provide OpenSCAD conversion.

## References

- solid-node/solid_node/node/leaf.py:28-32,53-61
- solid-node/solid_node/node/adapters/solid2.py:29-38
- solid-node/solid_node/node/adapters/cadquery.py:25-46
- solid-node/solid_node/node/adapters/openscad.py
- solid-node/solid_node/node/adapters/jscad.py
