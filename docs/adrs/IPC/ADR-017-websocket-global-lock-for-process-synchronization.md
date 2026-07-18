# ADR-017: WebSocket-Based Global Lock for Process Synchronization

**Status:** Superseded
**Date:** Unknown
**Depends on:** [ADR-016: WebSocket-Based Broker Pattern for Inter-Process Communication](./ADR-016-websocket-broker-pattern-for-ipc.md)
**Superseded by:** [ADR-018: Lean Framework Separation - Removing Platform Features from solid-node](./ADR-018-lean-framework-separation.md)

## Context and Problem Statement

The solid-node framework's multi-process development architecture requires exclusive access coordination when processes need to synchronize operations on shared resources such as the file system and build artifacts. The Builder process, WebViewer process, and other concurrent processes must prevent race conditions when performing coordinated operations that cannot be executed simultaneously.

The core problem was selecting a synchronization mechanism that would enable distributed locking across process boundaries. The solution needed to integrate with the existing WebSocket-based broker infrastructure while providing reliable lock acquisition, automatic cleanup on process crashes, and natural integration with the async/await programming model used throughout the framework.

## Decision Drivers

- Integration with existing WebSocket broker infrastructure avoiding additional IPC mechanisms
- Automatic lock release on client disconnect preventing permanent deadlocks from crashed processes
- Natural fit with async/await patterns used throughout the framework codebase
- Language-agnostic protocol enabling potential future extensibility beyond Python processes
- Debuggability using standard WebSocket tools without specialized instrumentation

## Considered Options

1. WebSocket-Based Global Lock via Broker (chosen)
2. Python multiprocessing.Lock for native process synchronization
3. File-based locking using fcntl or portalocker

## Decision Outcome

Chosen option: WebSocket-Based Global Lock, because it provides consistent integration with the existing broker architecture, enables automatic cleanup through WebSocket disconnect semantics, and maintains the async-first design philosophy. The implementation uses a single asyncio.Event at the broker's `/lock` endpoint with a simple text-based protocol where clients send "acquire" to request the lock and "release" to free it.

The lock starts in available state and uses event-based coordination: when a client requests the lock, the broker waits for the event, clears it, and notifies the client. On release, the event is set again, making the lock available to the next waiter. WebSocket disconnection automatically triggers lock release, providing crash safety.

## Pros and Cons of the Options

### WebSocket-Based Global Lock via Broker

- Good: Consistent with broker-based IPC architecture avoiding additional mechanisms
- Good: Automatic cleanup on disconnect prevents permanent deadlocks from crashed processes
- Good: Natural integration with async/await patterns throughout the framework
- Good: Protocol-level debugging using standard WebSocket tools
- Bad: Network overhead for localhost communication slower than in-memory primitives
- Bad: Requires broker availability creating additional failure mode
- Bad: No fairness guarantee or FIFO ordering for lock acquisition
- Bad: No lock ownership visibility complicating deadlock debugging

### Python multiprocessing.Lock

- Good: Native Python primitive with minimal overhead and fast performance
- Good: No broker dependency reducing architectural complexity
- Good: Built-in timeout capabilities for deadlock prevention
- Bad: Requires shared state management separate from broker architecture
- Bad: Python-specific solution limiting future language extensibility
- Bad: No integration with existing WebSocket infrastructure
- Bad: No automatic cleanup on process crash without additional handling

### File-Based Locking

- Good: Simple implementation requiring no broker infrastructure
- Good: Cross-platform lock visibility in file system
- Bad: Platform-dependent behavior across Unix and Windows systems
- Bad: Slower performance than in-memory synchronization
- Bad: No automatic cleanup requiring explicit lock file management
- Bad: No integration with existing async patterns or broker architecture

## Consequences

The WebSocket lock mechanism introduces distributed systems concerns such as network failures and connection state management despite being used only for localhost communication. Developers must understand when to use AsyncLock (functional) versus SyncLock (non-functional placeholder that only logs without actual broker communication), creating potential confusion about synchronization guarantees.

The single global lock design limits concurrency as all synchronized operations share one exclusive resource, though current usage appears limited based on codebase analysis. The lack of lock ownership tracking or timeout mechanisms makes debugging deadlock situations difficult, requiring manual broker restart to recover from stuck states.

Future evolution could include multiple named locks for different resources, lock timeout capabilities, ownership tracking for improved debugging, and potential extension to multi-machine distributed locking scenarios if remote development becomes a requirement.

## References

- solid-node/solid_node/core/broker.py:28-32
- solid-node/solid_node/core/broker.py:76-89
- solid-node/solid_node/core/broker.py:134-158
- solid-node/solid_node/core/broker.py:161-183
