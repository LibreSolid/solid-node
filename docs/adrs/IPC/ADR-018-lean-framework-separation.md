# ADR-018: Lean Framework Separation - Removing Platform Features from solid-node

**Status:** Accepted
**Date:** 2026-01-10
**Supersedes:**
- [ADR-016: WebSocket-Based Broker Pattern for Inter-Process Communication](./ADR-016-websocket-broker-pattern-for-ipc.md)
- [ADR-017: WebSocket-Based Global Lock for Process Synchronization](./ADR-017-websocket-global-lock-for-process-synchronization.md)

## Context and Problem Statement

The solid-node framework has grown to include features beyond its core mission of building CAD models, displaying them, supporting animation, and running tests. Over time, "platform" and "project control" features were added in anticipation of making solid-node a web-based development platform. This vision has been reconsidered, and the decision is to keep solid-node as a lean CAD framework while moving platform features to a new repository (working name: STUDIO).

The current architecture includes:
- A WebSocket-based broker for IPC that is over-engineered for its actual usage
- Git integration for automated commits during refactoring operations
- A refactoring system for IDE-like code generation
- Dead code that was never completed or is no longer used

This ADR documents the architectural decision to simplify solid-node by removing these features.

## Decision Drivers

- Desire for a lean, focused CAD framework with minimal dependencies
- Over-engineering in IPC layer: full broker infrastructure used only to pass build errors
- Separation of concerns: CAD framework vs. development platform
- Maintenance burden of unused and dead code
- Simpler mental model for users who just want to build CAD models

## Decision

### 1. Remove the WebSocket Broker (Supersedes ADR-016, ADR-017)

**Current state:** The broker (`core/broker.py`) provides:
- WebSocket server with pub/sub messaging infrastructure
- Distributed locking mechanism (`GlobalLock`)
- HTTP endpoints for key-value storage

**Actual usage:** Only passing build errors from Builder → WebViewer.

**Decision:** Remove the broker entirely. Replace with file-based error communication:

```
_build/
├── errors.json      # Builder writes build errors here
├── *.stl           # STL outputs
└── *.scad          # SCAD outputs
```

The WebViewer will read errors from this file (polling or filesystem watching).

**Impact:**
- Remove `solid_node/core/broker.py`
- Simplify `solid_node/manager/develop.py` from 3 processes to 2 processes
- Update `solid_node/core/builder.py` to write errors to file instead of broker
- Update `solid_node/viewers/web/viewer.py` to read errors from file
- Remove `websocket-client` dependency

### 2. Move Platform Features to STUDIO Repository

The following modules serve "project control" and "platform" concerns, not core CAD functionality:

| Module | Purpose | Action |
|--------|---------|--------|
| `core/git.py` | Git integration for automated commits | Move to STUDIO |
| `core/refactor/` | IDE-like code generation (new nodes, parameter refactoring) | Move to STUDIO |

These features enable:
- Automated Git commits when refactoring code
- Scaffolding new nodes from templates
- Parameter extraction and code transformation

They are valuable for a development platform but not essential for a CAD framework.

### 3. Remove Dead Code

The following modules are self-documented as unused:

| Module | Evidence | Action |
|--------|----------|--------|
| `exceptions.py` | Contains comment indicating it's unused | Delete |
| `node/spatial.py` | Contains comment indicating it's unused | Delete |

## Consequences

### Positive

- **Simpler architecture:** 2 processes instead of 3 in development mode
- **Fewer dependencies:** No WebSocket library needed for core framework
- **Clearer boundaries:** solid-node does CAD; STUDIO does platform features
- **Easier onboarding:** Users don't need to understand broker/IPC for basic usage
- **Reduced attack surface:** No network services beyond the web viewer

### Negative

- **Migration effort:** Code must be extracted and moved to STUDIO
- **Lost flexibility:** File-based IPC is less flexible than broker (no pub/sub, no distributed lock)
- **Coordination required:** STUDIO will depend on solid-node; interface must be stable

### Neutral

- **Interface points remain:** `load_node()`, `Builder`, `Test`, and viewer classes provide natural extension points for STUDIO to build upon

## Implementation Plan

### Phase 1: Remove Dead Code
1. Delete `solid_node/exceptions.py`
2. Delete `solid_node/node/spatial.py`
3. Remove any imports of these modules

### Phase 2: Replace Broker with File-Based Errors
1. Create `_build/errors.json` format specification
2. Update `Builder` to write errors to file
3. Update `WebViewer` to read errors from file
4. Remove broker startup from `develop.py`
5. Delete `solid_node/core/broker.py`
6. Remove `websocket-client` from dependencies

### Phase 3: Extract Platform Features to STUDIO
1. Create STUDIO repository structure
2. Move `core/git.py` to STUDIO
3. Move `core/refactor/` to STUDIO
4. Update STUDIO to import solid-node as dependency
5. Remove moved modules from solid-node

## Future Considerations

If solid-node later needs more sophisticated IPC (e.g., for distributed builds, remote development), the broker pattern could be reintroduced in STUDIO as an optional layer on top of the lean framework.

## References

- solid_node/core/broker.py (to be removed)
- solid_node/core/git.py (to be moved)
- solid_node/core/refactor/ (to be moved)
- solid_node/exceptions.py (to be removed)
- solid_node/node/spatial.py (to be removed)
- solid_node/manager/develop.py:71-83 (broker orchestration)
