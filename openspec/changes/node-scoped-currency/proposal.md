## Why

The content-verified currency fallback (ADR-060) digests a node's tracked
sources one *file* at a time, so two node classes defined in one file share one
digest and invalidate each other for as long as they share the file: editing
either re-derives both, plus every fusion above them, at leaf-tessellation cost.
The framework has been telling project authors to keep one node class per file
purely so the cache can tell their nodes apart — the shop's `solid-node` and
`solid-node-api` skills both call one node per file "the framework's premise,
not a style preference", and ADR-033 records it as a decision driver. That is
the cache imposing a file layout on the project, and the maintainer has decided
it should not: developers are free to organise a project however they like, and
the framework's job is to be efficient anyway.

## What Changes

- The mtime-equality hit path is untouched. An artifact whose stamp equals the
  node's `mtime_ns` is current with nothing opened, exactly as today (ADR-006,
  ADR-050).
- When equality fails and the fallback runs, the digest of a source file that
  defines more than one node class is *scoped to the node*: it covers the text
  of the file with the class bodies of the other node classes defined there
  removed — except any such class whose name the retained text still refers
  to, which stays in. Module-level code, imports, constants, helper functions
  and non-node classes always stay in, so an edit to anything shared still
  invalidates every node in the file.
- An internal node's digest covers the union of its children's scopes, as its
  file set already does, so a fusion whose children share its file still
  rebuilds when any of them changes.
- A file that defines exactly one node class, a file that defines no node
  class, and a non-Python source (an `StlNode`'s mesh, a `JScadNode`'s script)
  digest byte-for-byte as they do today. Every sidecar written by the current
  release therefore stays valid: a conventional project sees no migration
  rebuild.
- The one-node-per-file premise is withdrawn from the framework's records. It
  is neither a requirement nor a recommendation of the cache; whatever the
  framework still cannot do with a multi-node file is a property of node
  *references* (a bare path to such a file is ambiguous, ADR-024 / `cli`) and is
  named as such, not as a cache constraint.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `build-pipeline`: the *Mtime-equality caching* requirement's content-verified
  fallback is defined over node-scoped source units rather than whole files, so
  editing one node class in a file shared with others leaves the others'
  artifacts current, while an edit to code they share, or to a class they refer
  to, still rebuilds them.

## Impact

- `solid_node/currency.py` — `source_digest` takes a scope beside the file set
  and digests a scoped file's retained text; the per-file digest cache becomes
  per `(file, retained class set)`.
- `solid_node/node/base.py` — a node records the scope of its own source
  (`{src: {its class name}}`) beside `self.files`; `source_digest` passes it.
- `solid_node/node/internal.py` — the child union that already merges `files`
  merges scopes too.
- `solid_node/node/sources.py` or `currency.py` — one AST pass per source file,
  cached on `(path, mtime, size)` like the import cache, finds the top-level
  node-class spans and the identifiers the retained text uses. The module is
  already imported when a node is constructed, so which top-level classes are
  node classes is answered from the interpreter, as the import closure already
  is (ADR-033).
- `tests/` — a scratch project whose leaves and a fusion share one file, red
  first, plus guards for the shared-code, cross-reference, single-class and
  non-Python cases.
- `docs/adrs/` — a new ADR amending ADR-060 and ADR-033, withdrawing the
  one-node-per-file driver; `docs/architecture.md` updated.
- No CLI, dependency, public API, artifact-naming (ADR-026) or publication
  (ADR-030) change. The stamp, the sidecar format, its location and the sweep
  are unchanged.

## Explicitly out of scope

- **Declaring a main class in a multi-node file** so a bare path to it stops
  being ambiguous for `solid build` and `solid snapshot`, and companion test
  cases stop needing `node = TheClass`. That is a node-reference grammar
  change with its own spec (`cli`, ADR-024), not a cache change; it is the
  natural follow-up if the pilot wants multi-node files to be first-class
  everywhere.
- **The shop's skills.** `shop-skills/solid-node/SKILL.md` and
  `shop-skills/solid-node-api/SKILL.md` carry the one-node-per-file discipline
  and belong to the libresolid-studio repository; they are rewritten in a
  shop change after this cycle integrates, not here.
- **Symbol-level dependency tracking** inside a class body. A docstring edit
  inside a node's own class still rebuilds that node.
