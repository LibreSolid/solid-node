# ADR-014: Recursive NodeAPI REST Pattern Mirroring Node Tree

**Status:** Accepted
**Date:** 2024-06-15
**Depends on:**
- [ADR-001: Composite Pattern for Node Tree Architecture](../NODE/ADR-001-composite-pattern-node-tree-architecture.md)
- [ADR-015: FastAPI + Uvicorn as Unified Stack for HTTP-Based Services](../IPC/ADR-015-fastapi-unified-stack-for-http-services.md)

**Related to:** [ADR-012: Three.js for 3D Mesh Rendering and Visualization](./ADR-012-threejs-for-3d-rendering.md)

## Context and Problem Statement

The web-based viewer needed an API design to expose the hierarchical node tree structure to the React frontend for 3D visualization. The challenge was determining how to represent the dynamic, arbitrary-depth CAD assembly hierarchies in a REST API that supports STL file serving, node metadata access, and tree navigation.

CAD projects built with the Composite Pattern node tree can have varying structures - from simple single-part designs to complex multi-level assemblies with dozens of nested components. The API needed to support these varying structures without requiring route definitions for each possible configuration, while maintaining intuitive URL paths that reflect the assembly hierarchy.

The decision centered on whether to create a fixed API schema with resource identifiers or to dynamically generate API structure that mirrors the backend node tree at runtime.

## Decision Drivers

- Direct alignment with Composite Pattern node tree architecture minimizes duplication
- URL paths should intuitively represent hierarchical assembly structure
- Support for arbitrary tree depths without code changes for new projects
- Frontend must efficiently traverse tree and load STL files for rendering
- Rigid vs non-rigid node distinction affects which endpoints are exposed
- FastAPI mounting capabilities enable recursive sub-application pattern

## Considered Options

1. Recursive NodeAPI with dynamic mounting mirroring node tree structure
2. Flat REST API with resource IDs and separate tree structure endpoint
3. GraphQL with single endpoint and client-driven queries

## Decision Outcome

Chosen option: Recursive NodeAPI with dynamic mounting mirroring node tree structure, because it creates structural isomorphism between the Python backend and REST API. Each node in the tree becomes a FastAPI sub-application mounted at a path matching the node's hierarchical position, automatically generating API structure that reflects the CAD assembly organization.

The NodeAPI class recursively instantiates itself for each child node, creating a fractal API where rigid nodes expose STL endpoints and non-rigid nodes expose children. This eliminates the need for manual route definitions while providing clean URLs like `/node/arm/elbow/joint/` that directly represent the assembly hierarchy.

## Pros and Cons of the Options

### Recursive NodeAPI with Dynamic Mounting

**Pros:**
- Zero duplication between node tree structure and API routes
- URL paths intuitively represent assembly hierarchy
- Automatic API updates when nodes are added, removed, or renamed
- Supports arbitrary nesting depths without code changes
- Frontend can mirror backend structure with matching recursive loading pattern

**Cons:**
- No static API schema for OpenAPI documentation generation
- API structure varies by project making testing more complex
- Tight coupling between backend tree changes and API contract
- Difficult to add API versioning or centralized route management
- Debugging requires understanding node tree structure to predict paths

### Flat REST API with Resource IDs

**Pros:**
- Simple, predictable API schema with fixed endpoints
- Easy to document and version independently of backend
- Standard REST pattern familiar to most developers
- Centralized route definitions simplify monitoring

**Cons:**
- Requires separate endpoint to retrieve tree structure
- Loses hierarchical relationships in URL paths
- Duplication between node tree and API route definitions
- Additional ID mapping layer between nodes and API resources

### GraphQL with Client-Driven Queries

**Pros:**
- Flexible client queries for exactly needed data
- Strong schema with type safety and documentation
- Single endpoint reduces over-fetching
- Industry-standard solution for hierarchical data

**Cons:**
- Additional dependency on GraphQL server and client libraries
- More complex than REST for simple tree traversal use case
- Heavier implementation for this specific problem domain
- Steeper learning curve for developers

## Consequences

The recursive NodeAPI pattern creates a fractal API architecture where each level of the node tree generates its own FastAPI sub-application. The frontend mirrors this structure with recursive node loading that constructs matching hierarchical objects, maintaining structural consistency between backend and frontend.

This tight coupling means renaming nodes automatically updates API paths, but also means the API contract implicitly depends on the node tree structure. Projects with different assembly organizations expose different API shapes, requiring the frontend to discover structure dynamically rather than relying on a fixed schema.

HTTP caching using Last-Modified headers optimizes STL file loading, with mtime-based change detection preventing unnecessary downloads. The async file waiting mechanism allows STL endpoints to block until build completion, simplifying frontend logic.

The pattern trades API predictability for automatic structural consistency. Future requirements for API versioning, centralized authentication, or monitoring would require significant refactoring to accommodate the dynamic route structure.

## References

- `solid_node/viewers/web/viewer.py:70-76` - Root NodeAPI mounting
- `solid_node/viewers/web/viewer.py:148-186` - Recursive NodeAPI class
- `solid_node/viewers/web/app/src/node.ts:237-273` - Frontend recursive loading
