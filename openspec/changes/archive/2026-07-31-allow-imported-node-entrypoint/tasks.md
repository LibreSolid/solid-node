## 1. Lock the loader contract red-first

- [x] 1.1 Change the existing project-local imported-marker fixture expectation from rejection to successful explicit selection, and prove the unchanged implicit-discovery, ambiguity, wrong-type, and test-class behaviors still hold.
- [x] 1.2 Add a package-entrypoint regression matching `snowman-2`: `__init__.py` re-exports and marks a node from a sibling implementation module, `load_node()` instantiates it, and both the facade and implementation source appear in `node.files`.
- [x] 1.3 Add a regression proving that an explicit marker whose class is defined outside the active project is rejected with an actionable `AmbiguousNodeError`.

## 2. Implement imported entry-point support

- [x] 2.1 Update explicit `NODE` resolution to accept `AbstractBaseNode` subclasses defined inside the active project while retaining strict type/subclass validation and rejecting external origins.
- [x] 2.2 Update path loading to add the normalized loaded entry-point path to the instantiated node's tracked files without changing `node.src`, artifact identity, or the existing implicit candidate filter.

## 3. Reconcile durable framework documentation

- [x] 3.1 Amend ADR-026 to record project-local imported marker support, same-file-only implicit discovery, and facade source tracking.
- [x] 3.2 Update `docs/architecture.md` so its loader and source-tracking descriptions match the implemented behavior.
- [x] 3.3 Synchronize the accepted build-pipeline requirement from this change's delta spec and archive the completed OpenSpec change.

## 4. Validate the change

- [x] 4.1 Run the focused marker-loader and source-set tests and confirm the new regressions fail before implementation and pass afterward.
- [x] 4.2 Run the full framework test suite and report any environmental failure or remaining structural blind spot.
