# ADR-015: FastAPI + Uvicorn as Unified Stack for HTTP-Based Services

**Status:** Accepted (amended 2026-07-18 — see Amendment)
**Date:** Unknown
**Amended by:** [ADR-018: Lean Framework Separation](./ADR-018-lean-framework-separation.md) — removed the broker, this ADR's second consumer
**Used by:**
- [ADR-014: Recursive NodeAPI REST Pattern Mirroring Node Tree](../VIEWER-WEB/ADR-014-recursive-nodeapi-rest-pattern.md)
- [ADR-016: WebSocket-Based Broker Pattern for Inter-Process Communication](./ADR-016-websocket-broker-pattern-for-ipc.md) *(superseded)*

## Amendment (2026-07-18)

[ADR-018](./ADR-018-lean-framework-separation.md) removed the BrokerServer
and its `websocket-client` dependency, so the "unified stack across both
services" framing below is historical: the **WebViewer is now the sole
HTTP service**, and what survives of this decision is that **FastAPI +
Uvicorn is solid-node's HTTP stack** — the WebViewer's app, its
`/ws/reload` websocket, and the shared `uvicorn_config` logging setup all
stand on it, and any future HTTP surface should reuse the same stack
rather than introduce a second framework. The broker-specific rationale,
trade-off analysis, and the open question at the end of Consequences are
retained unedited as the record of the original decision; the
under-utilization concern dissolved with the broker itself. References to
`core/broker.py` describe removed code.

## Context and Problem Statement

The Solid Node framework requires HTTP-based services for two distinct purposes: a lightweight IPC broker for inter-process coordination (WebSocket locking and key-value storage) and a web-based 3D visualization interface serving a React frontend with recursive NodeAPI. The framework needed to choose a web framework strategy that would support both simple IPC operations and complex web serving while managing dependency weight and developer experience.

The BrokerServer primarily needs WebSocket connections for distributed locking and simple PUT/GET endpoints for data storage. The WebViewer requires a full-featured web framework to serve static frontend assets, handle complex API routing, and support real-time 3D model updates. Both services run as independent processes with similar operational requirements around async I/O, logging configuration, and process lifecycle management.

The decision involved choosing between framework specialization (different tools optimized for each service) versus standardization (single framework across all HTTP-based services), with implications for installation size, startup time, code consistency, and long-term maintainability.

## Decision Drivers

- Technology consistency across HTTP-based services reduces cognitive load and simplifies debugging
- Installation size and startup time impact framework deployment characteristics
- WebSocket support is critical for broker's distributed locking mechanism
- Modern async/await patterns needed for concurrent process communication
- Shared logging configuration between broker and viewer services
- Future extensibility for potential OpenAPI documentation and external tool integration

## Considered Options

1. **FastAPI + Uvicorn for both broker and viewer** (unified stack)
2. **Raw asyncio + websockets library for broker, FastAPI for viewer** (specialized approach)
3. **aiohttp for broker, FastAPI for viewer** (lighter broker framework)

## Decision Outcome

Chosen option: **FastAPI + Uvicorn for both broker and viewer**, because it creates a unified technology stack across all HTTP-based services in the framework. Both services use identical FastAPI applications with shared `uvicorn_config` for logging, ensuring consistent operational patterns, simplified dependency management, and unified developer experience despite the broker using only minimal FastAPI features (no Pydantic models, no dependency injection, no middleware).

This was part of the decision on having an editor in the interface, so there was a requirement for git control, and synchronization became a big issue. FastAPI was used so that the broker would be easily compatible with the web viewer and the dependency stack would be preserved. No performance benchmarks were conducted, or other technologies considered.

## Pros and Cons of the Options

### FastAPI + Uvicorn for both (unified stack)

**Pros:**
- Single framework knowledge required across IPC and viewer modules
- Shared configuration patterns (`uvicorn_config`) simplify logging setup
- Consistent async/await patterns and WebSocket handling across codebase
- Automatic OpenAPI documentation capability available if needed
- Well-tested WebSocket support in production environments

**Cons:**
- Heavier dependency weight (~25-30MB) for minimal broker operations
- HTTP protocol overhead for simple IPC compared to raw sockets
- Slower broker startup time than minimal asyncio implementation
- Framework abstractions (routing, ASGI lifecycle) add complexity for simple use cases

### Raw asyncio + websockets library for broker

**Pros:**
- Minimal dependency weight for broker service
- Faster broker startup with direct asyncio control
- No framework overhead for simple WebSocket locking
- Maximum performance for IPC operations

**Cons:**
- Developers must understand two different WebSocket patterns
- Manual HTTP handling needed for PUT/GET endpoints
- Increased cognitive load switching between broker and viewer code
- Separate logging configuration and operational patterns

### aiohttp for broker, FastAPI for viewer

**Pros:**
- Lighter than FastAPI but provides WebSocket + HTTP support
- Mature async framework with good WebSocket performance
- Sufficient feature set for broker requirements

**Cons:**
- Developers must learn two web frameworks
- Different configuration patterns between broker and viewer
- Increased dependency complexity managing two framework stacks
- Inconsistent debugging approaches across services

## Consequences

The unified FastAPI stack creates consistent operational patterns across all HTTP-based services, with both broker and viewer using identical Uvicorn ASGI server configuration and logging setup. Developers working on either service encounter the same framework patterns, route decorators, and async/await conventions, reducing context switching and simplifying code reviews.

The broker under-utilizes FastAPI capabilities (approximately 5% feature usage with no Pydantic validation, no dependency injection, no custom middleware), suggesting the consistency benefit outweighs optimal tool selection. This creates a ~25-30MB dependency footprint for core framework operation, affecting installation size and startup time compared to minimal asyncio implementations.

Future framework updates to FastAPI or Uvicorn may require coordinated changes across both broker and viewer services, but shared dependency versions prevent version conflicts and simplify testing. The OpenAPI documentation capability remains available for broker endpoints if external tool integration becomes necessary.

[NEEDS INPUT: Are there specific business or operational requirements that influenced prioritizing consistency over broker performance optimization?]

## References

- `solid_node/core/broker.py:17-110` - BrokerServer FastAPI implementation
- `solid_node/viewers/web/viewer.py:26-91` - WebViewer FastAPI implementation
- `solid_node/core/logging.py:25-45` - Shared uvicorn_config
- `solid_node/requirements.txt:4,12` - FastAPI and Uvicorn dependencies
