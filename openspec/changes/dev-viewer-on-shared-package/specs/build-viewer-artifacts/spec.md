## REMOVED Requirements

### Requirement: The framework viewer can read a published snapshot

**Reason**: The private snapshot-backed mode existed to reproduce the
recursive per-node API from a completed build. The development viewer now
serves the published build directory directly, so nothing constructs that
mode and no consumer reproduces the per-node representation.

**Migration**: Serve the published build directory: `viewer.json` plus the
build-root-relative model files it names, which the requirement below already
guarantees are published together. The development viewer's HTTP contract for
doing so is in the `web-viewer` capability.
