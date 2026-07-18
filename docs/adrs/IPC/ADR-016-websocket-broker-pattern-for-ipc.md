# ADR-016: WebSocket-Based Broker Pattern for Inter-Process Communication

**Status:** Superseded
**Date:** Unknown
**Depends on:** [ADR-015: FastAPI + Uvicorn as Unified Stack for HTTP-Based Services](./ADR-015-fastapi-unified-stack-for-http-services.md)
**Superseded by:** [ADR-018: Lean Framework Separation - Removing Platform Features from solid-node](./ADR-018-lean-framework-separation.md)
**Used by:** [ADR-017: WebSocket-Based Global Lock for Process Synchronization](./ADR-017-websocket-global-lock-for-process-synchronization.md)

## Context and Problem Statement

The solid-node framework requires coordination between multiple concurrent processes during development workflows: the Builder process (watches files and regenerates STL models), the WebViewer process (FastAPI server rendering the React frontend), and potentially additional processes like the web development server. These processes need to synchronize operations and exchange state information, particularly build errors that must flow from the Builder to the WebViewer for display to users.

The core problem was selecting an inter-process communication mechanism that could support both distributed locking for process synchronization and message passing for state sharing across the multi-process development architecture. The solution needed to integrate with the existing FastAPI-based infrastructure while providing reliable communication for localhost development scenarios.

## Decision Drivers

- Need for both distributed locking (process synchronization) and message passing (state sharing) in a unified mechanism
- Integration with existing FastAPI-based web viewer architecture and async/await patterns
- Developer debugging capabilities for troubleshooting multi-process communication issues
- Language-agnostic interface enabling potential future extensibility beyond Python processes
- Requirement for reliable error propagation from Builder to WebViewer without polling overhead
- Port availability and localhost communication constraints in development environments

## Considered Options

1. WebSocket-Based Broker Pattern with FastAPI (chosen)
2. Python multiprocessing.Queue for direct inter-process communication
3. Unix sockets or named pipes for file-based IPC

## Decision Outcome

Chosen option: WebSocket-Based Broker Pattern, because it provides a unified approach to both locking and message passing through a central broker service, integrates naturally with the FastAPI ecosystem already used for the web viewer, and enables protocol-level debugging using standard browser developer tools or HTTP clients. The broker runs as a dedicated FastAPI application on localhost:4190, with all other processes connecting as clients.

The implementation provides two primary mechanisms: WebSocket-based distributed locking at `/lock` for process synchronization, and HTTP PUT/GET endpoints for key-based data storage enabling state sharing such as build error propagation.

## Pros and Cons of the Options

### WebSocket-Based Broker Pattern with FastAPI

- Good: Unified mechanism for both locking and message passing through single broker service
- Good: Protocol-level debugging using browser dev tools, curl, or WebSocket clients
- Good: Language-agnostic interface enabling potential future remote development scenarios
- Good: Natural integration with existing FastAPI web viewer and async/await patterns
- Bad: Additional process overhead requiring broker lifecycle management and port availability
- Bad: Network protocol overhead even for localhost communication compared to native Python IPC
- Bad: More complex error handling with connection retry logic and WebSocket lifecycle management

### Python multiprocessing.Queue

- Good: Lightweight native Python IPC with minimal overhead
- Good: No additional processes or port management required
- Good: Built-in serialization and type safety for Python objects
- Bad: Python-specific solution limiting future language extensibility
- Bad: Difficult to debug message passing without instrumentation
- Bad: Would require separate mechanism for distributed locking
- Bad: No integration with existing FastAPI infrastructure

### Unix Sockets or Named Pipes

- Good: Efficient file-based IPC with minimal overhead
- Good: No port conflicts or network configuration
- Bad: Platform-specific implementation (Unix/Windows differences)
- Bad: Requires custom protocol design for locking and message semantics
- Bad: More complex debugging requiring specialized tools
- Bad: No natural integration with HTTP/WebSocket ecosystem

## Consequences

The broker pattern introduces a dedicated process that must be started before any other development processes and requires port 4190 to be available on localhost. All IPC operations throughout the codebase use async/await patterns, requiring developers to understand asynchronous programming concepts. The architecture enables future extensibility such as remote development connections, browser-based build notifications without polling, and distributed build scenarios.

The current implementation shows over-engineering for present usage patterns, with topic-based pub/sub infrastructure implemented but unused, suggesting the design anticipates future messaging requirements. The mixed protocol usage (HTTP for data operations, WebSocket for locking) adds conceptual complexity but provides appropriate semantics for each operation type.

Failure modes require consideration: if the broker crashes, all dependent processes lose communication capabilities. The current implementation lacks connection retry logic and reconnection handling in BrokerClient, representing a potential reliability gap for long-running development sessions.

## References

- solid-node/solid_node/core/broker.py:36-183
- solid-node/solid_node/manager/develop.py:71-83
- solid-node/solid_node/core/builder.py:51,103-105
- solid-node/solid_node/viewers/web/viewer.py:77,109-110
