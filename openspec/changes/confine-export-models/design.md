## Context

Node artifact paths already use the build-directory resolver in
`solid_node.core.builder`: relative `SOLID_BUILD_DIR` values are anchored on
the discovered project root, and a named-model selection anchors its owned
subdirectory for the process. `core.export._model_path()` independently reads
the environment and applies `os.path.relpath()` from the current working
directory. For an explicit path exported from a project subdirectory, those
two roots differ. The resulting manifest path contains parent traversals, and
`shutil.copy2()` follows them outside the requested export.

ADR-020 and the `export` specification already require a portable,
self-contained directory. ADR-073 establishes the selected per-model build
directory as the artifact ownership boundary. F03 is a conformance repair at
that boundary; it does not introduce another artifact layout.

## Goals / Non-Goals

**Goals:**

- Derive export model paths from the build directory that produced them.
- Make export results independent of the caller's working directory.
- Reject an artifact outside the selected build directory before creating or
  modifying the requested output.
- Preserve the existing `models/<source-relative artifact>` layout and model
  deduplication for valid exports.

**Non-Goals:**

- Change the manifest schema or any viewer consumer.
- Relocate build artifacts or alter project/model selection.
- Accept arbitrary external STL paths as export inputs.
- Turn static export into an atomic directory publication operation.

## Decisions

### D1: Use the framework build-directory resolver as the single root

For each rigid node, the exporter will resolve its owning build directory with
`get_build_dir(node.src)`, the same project-aware and selection-aware function
used when the node constructs `stl_file`. The manifest path is `models/` plus
the artifact's relative path below that root.

Passing the build directory from the CLI was rejected because `export_node()`
is also a public direct-call API and already has enough node context to resolve
the same root. Reading `SOLID_BUILD_DIR` directly was rejected because it
repeats the bug: a relative setting has no project anchor, and the environment
does not by itself express the default build root.

### D2: Validate canonical source containment before writing output

The exporter will compare canonical absolute paths for the STL and resolved
build directory using `os.path.commonpath()`. A path on another drive or whose
common path is not the build directory raises a dedicated
`ExportModelPathError` that names both paths. The check happens while the
serialized model table is assembled, before `os.makedirs(output_dir)` or any
copy. A contained source produces a relative path with no parent traversal;
joining that path below `models/` therefore keeps the copy destination below
the export directory.

A lexical prefix check was rejected because `_build-other` shares a string
prefix with `_build`. Using only `normpath()` was rejected because an STL
symlink could appear lexically inside the build while resolving outside its
ownership boundary.

### D3: Give the CLI a controlled failure

`solid export` will catch `ExportModelPathError` beside the existing missing
widget error, print `Error: <diagnostic>` to standard error, and exit nonzero.
Direct callers receive the typed exception. This keeps an invariant violation
from being reported as a successful export or exposed as an implementation
traceback.

Silently flattening an external artifact into `models/` was rejected because
it hides a broken ownership invariant and creates collision semantics the
manifest has never defined.

### D4: Prove every root-selection route red-first

Tests will cover a real temporary project exported from its root and from a
nested working directory, a relative configured build root, and a selected
named-model directory. A direct-call fixture whose STL resolves outside its
build directory will prove the typed failure and absence of output; a CLI test
will prove the concise nonzero diagnostic. Existing export tests continue to
prove deduplication, inventory references, and the unchanged successful
layout.

## Risks / Trade-offs

- **A custom node that rewrites `stl_file` to an external file will stop
  exporting.** → This was never a supported portable layout; the error names
  the artifact and expected root so the node can restore the invariant.
- **Canonicalization follows symlinks.** → This deliberately prevents a
  build-local symlink from importing an artifact owned elsewhere. Framework
  generated artifacts are regular files, so normal projects are unaffected.
- **A caller could mutate filesystem links after validation.** → Export does
  not claim protection against a concurrent hostile filesystem actor; the
  validation closes framework-generated traversal and ordinary symlink
  escapes.

## Migration Plan

No migration is required. Existing valid manifests retain their paths and
schema version. Reverting the implementation restores the working-directory
dependent escape without requiring data conversion.

## Open Questions

None.
