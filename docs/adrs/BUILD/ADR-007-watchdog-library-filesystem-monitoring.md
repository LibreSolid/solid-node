# ADR-007: Watchdog Library for Filesystem Monitoring

**Status:** Accepted
**Date:** Unknown
**Depends on:** [ADR-006: Mtime-Based STL Caching Strategy](../NODE/ADR-006-mtime-based-stl-caching-strategy.md)
**Related to:** [ADR-005: Path-Based Dynamic Module Loading](./ADR-005-path-based-dynamic-module-loading.md)

## Context and Problem Statement

The framework requires real-time monitoring of Python source file changes during development to enable hot reload and automatic STL regeneration. When developers modify `.py` files, the build system must detect these changes immediately and trigger the appropriate rebuild processes. The solution must work reliably across different platforms (Linux, macOS, Windows) and integrate seamlessly with the framework's asyncio-based architecture.

An earlier implementation used `pyinotify`, a Linux-specific filesystem monitoring library. However, this limited the framework to Linux environments, preventing adoption by developers on macOS and Windows. The framework needed cross-platform filesystem event monitoring with minimal overhead and a clean integration path with the existing Builder class architecture.

## Decision Drivers

- Cross-platform compatibility required for broader framework adoption (Linux, macOS, Windows)
- Fast detection of file changes to maintain responsive development workflow
- Clean integration with asyncio event loop architecture
- Minimal implementation complexity and maintenance burden
- Reliable fallback mechanisms for platforms without native filesystem events
- Precise tracking of individual source files rather than entire directories

## Considered Options

1. Watchdog library with Observer pattern (chosen)
2. Direct inotify integration (Linux-only)
3. Manual polling-based file change detection

## Decision Outcome

Chosen option: "Watchdog library with Observer pattern", because it provides cross-platform filesystem event monitoring with native performance on supported platforms and automatic polling fallback. The migration from pyinotify to watchdog prioritized platform compatibility over Linux-specific optimizations, enabling the framework to reach developers on all major operating systems.

The implementation extends `FileSystemEventHandler` and uses `Observer` to monitor individual source files tracked in `self.node.files`. The `on_modified()` callback bridges the Observer thread to the main asyncio event loop using `call_soon_threadsafe()`, ensuring thread-safe communication without race conditions.

## Pros and Cons of the Options

### Watchdog library with Observer pattern

- Good: Cross-platform support (Linux, macOS, Windows) vs pyinotify's Linux-only limitation
- Good: Well-maintained third-party library with clean API and established patterns
- Good: Automatic fallback to polling on platforms without native filesystem events
- Good: Minimal code footprint (~10 lines) for filesystem monitoring functionality
- Bad: Runs in separate thread requiring thread-safe asyncio integration
- Bad: File-level watching creates more watch handles than directory-level approach
- Bad: Introduces external dependency and potential cross-platform behavior differences

### Direct inotify integration

- Good: Maximum performance on Linux with direct kernel interface access
- Good: No external dependencies beyond system libraries
- Good: Fine-grained control over watch behavior and event filtering
- Bad: Linux-only, excludes macOS and Windows developers entirely
- Bad: More complex implementation requiring platform-specific code paths
- Bad: Higher maintenance burden for low-level kernel API integration

### Manual polling-based file change detection

- Good: Simplest implementation with no external dependencies
- Good: Works on any platform without special libraries
- Good: Easier to debug and understand for new contributors
- Bad: Significantly less responsive than event-based monitoring
- Bad: Higher CPU usage from continuous polling of file mtimes
- Bad: Polling interval creates trade-off between responsiveness and resource usage

## Consequences

The watchdog integration enables responsive hot reload across all major platforms, directly improving developer experience. The framework can now be adopted by developers on macOS and Windows, not just Linux, significantly expanding the potential user base.

The thread-safe integration with asyncio via `call_soon_threadsafe()` maintains clean separation between the Observer thread and the main event loop, preventing race conditions while keeping responsive file watching. Developers extending the build system must understand the Observer lifecycle and thread-safe communication patterns.

File-level watching (using `recursive=False`) provides precise tracking of exactly which source files contribute to each node, integrating cleanly with the mtime-based caching strategy: watchdog detects changes, mtime determines what to rebuild. This separation of concerns maintains architectural clarity.

The automatic polling fallback ensures compatibility even on network filesystems or environments without native event support, though with potential latency trade-offs. Edge cases like atomic file operations (editors saving via temp files) are handled by watchdog's internal logic, reducing framework-specific workaround code.

## References

- `solid_node/core/builder.py:24` - Watchdog imports and Observer setup
- `solid_node/core/builder.py:110` - File change callback implementation
- `setup.py:54` - Watchdog dependency declaration
- `requirements.txt:6` - Legacy pyinotify reference
