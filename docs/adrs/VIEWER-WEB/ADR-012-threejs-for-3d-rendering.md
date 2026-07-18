# ADR-012: Three.js for 3D Mesh Rendering and Visualization

**Status:** Accepted
**Date:** Unknown
**Used by:** [ADR-013: React as Frontend Framework for Web Viewer](./ADR-013-react-frontend-framework.md)
**Related to:** [ADR-014: Recursive NodeAPI REST Pattern Mirroring Node Tree](./ADR-014-recursive-nodeapi-rest-pattern.md)

## Context and Problem Statement

The web viewer requires a 3D rendering engine to visualize STL meshes in the browser for the development workflow. The solution must handle STL loading, scene management, camera controls, transformations (rotations and translations), and WebGL-based real-time rendering. The framework needs programmatic mesh manipulation to mirror the backend Python node hierarchy, where operations from the backend are evaluated and applied as transformations on frontend mesh objects.

The rendering engine becomes the foundation of all 3D visualization capabilities, affecting developer experience (learning curve), browser compatibility, bundle size, performance characteristics, and architectural patterns for transformation handling.

## Decision Drivers

- Need for industry-standard WebGL library with comprehensive 3D capabilities (STL loading, camera controls, quaternion-based transformations)
- Bundle size impact on load times for remote development scenarios
- Developer learning curve and availability of documentation/community support
- Performance requirements for real-time rendering of complex STL meshes
- Browser compatibility requirements (WebGL support)
- Architecture requiring programmatic mesh manipulation (imperative transformations) rather than declarative rendering

## Considered Options

1. Three.js - Lightweight WebGL library with built-in STL loader and camera controls
2. Babylon.js - Comprehensive WebGL engine with physics and editor capabilities
3. WebGL directly - Maximum control and performance without framework abstraction

## Decision Outcome

Chosen option: **Three.js**, because it provides the right balance of functionality and bundle size for the STL viewing use case. Three.js offers comprehensive 3D capabilities (STL loading via STLLoader, camera controls via OrbitControls, quaternion-based transformations, scene management) without the overhead of features not needed for mesh visualization (physics engines, built-in editors). The mature community, extensive documentation, and stable API reduce development risk. Direct Three.js provides more control for programmatic transformations compared to declarative wrappers, fitting the imperative architecture where backend operations are applied as quaternion rotations and vector translations.

## Pros and Cons of the Options

### Three.js

- Good: Industry-standard WebGL library with active community and comprehensive documentation
- Good: Built-in STL loader and mature camera controls (OrbitControls)
- Good: Handles complex 3D math (quaternions, matrices) for stable transformations
- Good: Moderate bundle size (~600KB minified) for full-featured 3D engine
- Bad: Steeper learning curve for developers unfamiliar with 3D graphics concepts
- Bad: WebGL browser requirements (though supported in all modern browsers since 2014)
- Bad: Tree-shaking limitations with Three.js examples (STLLoader, OrbitControls add to bundle)

### Babylon.js

- Good: More comprehensive feature set including physics engine and visual editor
- Good: Similar WebGL capabilities for mesh rendering and transformations
- Bad: Larger bundle size (~1.5MB vs 600KB) for features not needed in STL viewing
- Bad: More complex API creates unnecessary overhead for simple visualization use case
- Bad: Heavier weight conflicts with framework's minimalist approach

### WebGL directly

- Good: Maximum control over rendering pipeline and performance optimization
- Good: Smallest possible bundle size (no framework overhead)
- Bad: Requires implementing camera controls, STL loaders, and scene management from scratch (months of effort)
- Bad: Need to handle complex 3D math (quaternions, matrices) without library support
- Bad: High maintenance burden for features already solved by Three.js

## Consequences

The Three.js integration creates a dual representation architecture where Python nodes on the backend generate STL meshes, while TypeScript nodes on the frontend load those STLs and maintain Three.js mesh objects. This separation allows the backend to focus on CAD operations while the frontend handles real-time 3D visualization.

Developers working on the viewer must understand Three.js concepts including the coordinate system (right-handed, Y-up vs Z-up conventions), WebGL rendering pipeline, quaternion-based rotations (used instead of Euler angles to avoid gimbal lock), async STL loading lifecycle, and memory management (disposing geometries and materials). The framework uses specific version pinning (v0.156.x) to avoid breaking changes from automatic updates.

Future visualization features (grids, axes, measurements, shadows, advanced materials) must use Three.js APIs. Performance optimization must work within Three.js's architecture. The ~600KB bundle size will grow with additional Three.js examples (loaders, controls, post-processing), though the framework currently maintains minimal dependencies (core + STLLoader + OrbitControls).

## References

- `solid_node/viewers/web/app/package.json` - Three.js dependencies declaration
- `solid_node/viewers/web/app/src/node.ts` - Node class hierarchy with Three.js mesh references and STL loading
- `solid_node/viewers/web/app/src/viewer/STLViewer.tsx` - WebGL renderer, camera, and controls initialization
- `solid_node/viewers/web/app/src/App.tsx` - Scene management
