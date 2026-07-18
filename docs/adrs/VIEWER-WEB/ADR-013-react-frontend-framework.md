# ADR-013: React as Frontend Framework for Web Viewer

**Status:** Accepted
**Date:** Unknown
**Depends on:** [ADR-012: Three.js for 3D Mesh Rendering and Visualization](./ADR-012-threejs-for-3d-rendering.md)

## Context and Problem Statement

The web viewer requires a frontend framework to build the development interface that visualizes STL meshes and provides interactive controls. The solution must handle component architecture, state management, client-side routing, and integration with imperative Three.js APIs for 3D rendering. The framework becomes the foundation for all UI components including the STL viewer, navigation tree, animation controls, and error displays.

The framework choice affects developer experience, bundle size, build toolchain complexity, and architectural patterns for managing the impedance mismatch between declarative UI paradigms and imperative Three.js operations. The decision has long-term implications for team knowledge requirements, maintenance burden, and future feature development.

## Decision Drivers

- Need for component-based architecture to structure complex UI (viewer, navigation, controls, error handling)
- State management requirements for 3D scene state, animation time, build errors, and UI interactions
- Integration with imperative Three.js APIs requiring lifecycle management and refs
- TypeScript support for type safety across frontend codebase
- Bundle size impact on viewer load times in remote development scenarios
- Developer ecosystem maturity and availability of documentation

## Considered Options

1. React with Create React App - Industry-standard component framework with hooks and zero-config build
2. Vue.js - Progressive framework with simpler learning curve
3. Vanilla TypeScript - Maximum control with no framework overhead

## Decision Outcome

Chosen option: **React with Create React App**, because it provides comprehensive component architecture, state management via hooks, and first-class TypeScript support while offering a mature ecosystem and extensive documentation. React's hooks pattern (useState, useEffect, useRef, useImperativeHandle) effectively manages the integration between declarative React components and imperative Three.js objects, using refs to bridge the paradigm mismatch. Create React App provides a zero-configuration build system with webpack, Babel, and hot module replacement, allowing the framework to avoid custom build tooling complexity.

The decision accepts React's ~140KB bundle size (45KB gzipped) and virtual DOM overhead in exchange for component composition benefits, established patterns for Three.js integration, and reduced development time compared to building a custom component system.

## Pros and Cons of the Options

### React with Create React App

- Good: Industry-standard framework with massive ecosystem and comprehensive documentation
- Good: Hooks pattern (useState, useEffect, useRef) simplifies state management and Three.js lifecycle integration
- Good: First-class TypeScript support with official type definitions
- Good: Zero-config build system via Create React App includes webpack, Babel, HMR without ejecting
- Bad: Bundle size adds ~140KB minified (45KB gzipped) to viewer load time
- Bad: Virtual DOM overhead though minimal for this UI complexity level
- Bad: Create React App deprecated by React team (now recommend Vite/Next.js), requiring future migration
- Bad: Framework lock-in to React ecosystem and release cycle

### Vue.js

- Good: Simpler learning curve with template-based syntax
- Good: Smaller bundle size than React for equivalent functionality
- Good: Reactive state management built into framework
- Bad: Smaller ecosystem compared to React's maturity
- Bad: Less TypeScript-first compared to React's comprehensive type support
- Bad: Fewer developers familiar with Vue for team knowledge continuity

### Vanilla TypeScript

- Good: Maximum control over rendering and state management
- Good: Minimal bundle size with no framework overhead
- Good: No framework lock-in or update dependencies
- Bad: Requires building component system, state management, and routing from scratch (months of effort)
- Bad: Manual lifecycle management for Three.js integration prone to memory leaks
- Bad: High maintenance burden for features solved by React (virtual DOM, reconciliation, hooks)

## Consequences

React establishes a component-based architecture where imperative Three.js rendering is encapsulated within declarative React components. The framework uses refs (rendererRef, cameraRef, controlsRef) to bridge the impedance mismatch between React's declarative paradigm and Three.js's imperative API, with useEffect lifecycle hooks managing Three.js initialization, updates, and cleanup to prevent memory leaks.

Developers must understand React component lifecycle (useEffect dependencies, cleanup functions, hooks rules), TypeScript integration with React (JSX.Element types, component props interfaces), and patterns for integrating imperative libraries. The hooks-only approach (no class components) reflects modern React development patterns but requires familiarity with useState, useEffect, useRef, and useImperativeHandle.

Create React App's deprecation creates future technical debt requiring migration to Vite, Next.js, or custom webpack configuration. The framework currently uses React 18.2.x without leveraging concurrent features (Suspense, transitions), suggesting either upgrade from earlier versions or features not yet needed. Future advanced UI features (drag-and-drop, undo/redo, server-side rendering) must work within React's paradigm and lifecycle constraints.

## References

- `solid_node/viewers/web/app/package.json` - React dependencies and Create React App scripts
- `solid_node/viewers/web/app/src/App.tsx` - Main component with state management via hooks
- `solid_node/viewers/web/app/src/viewer/STLViewer.tsx` - Three.js integration via refs and useEffect
- `solid_node/viewers/web/app/src/index.tsx` - React app bootstrap
