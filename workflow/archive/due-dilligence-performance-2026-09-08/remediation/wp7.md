# WP7 — Linear traversal-snapshot child naming (P06)

## Scope

Each parent traversal now builds one identity-to-name index from one snapshot
of its relevant public attributes.  It copies list/tuple memberships while
taking that snapshot, records public direct attributes first in insertion
order, then records sequence members in attribute/index order with first-hit
semantics.  Private attributes and the framework-owned `children` field remain
excluded.  A sibling batch refreshes every `_parent`, preserves every explicit
name, performs one constant-time identity lookup per automatic name, and
restores the class-name fallback when a child is no longer publicly referenced.
An empty batch returns before taking a snapshot, so leaf assemblies do not pay
for an index they cannot use.

`core/serializer.py`, `node/internal.py`, `node/qualified.py`, and
`node/assembly.py` all batch-link the complete returned sibling sequence before
recursive child work.  A direct legacy `_link_child(child)` call builds a fresh
one-child index and therefore still observes current alias/order/parent state.
No persistent index or invalidation protocol was introduced, and no consumer
adds a render.

## Red/green proof

[wp7-red.log](wp7-red.log) runs the final focused tests against a disposable
export of the exact planning commit.  It records the quadratic legacy walk,
the missing batch seam, stale fallback after removal, and inter-child mutation
renaming a later sibling.  [wp7-green.log](wp7-green.log) records 16 focused
tests plus 10 subtests, 396 combined compatibility tests plus 50 subtests, and the
2,048-child context-sample observation.

The candidate tests cover 128/512/2,048 siblings; serialization, simulation,
STL linking and state traversal consumers; explicit names; direct-before-all-
sequence precedence; first sequence attribute/index; list and tuple aliases;
private/`children` exclusions; class fallback; repeated identity; parent
reassignment; append, removal, replacement, direct reassignment and same-length
reorder.  Mutation tests recurse into and observe both children exactly once
from a separate entry-list copy, isolating the naming observation from Python's
mutable-list iteration behavior. The later sibling observes its entry name;
the changed alias order becomes visible on the next parent traversal. This
does not introduce a new guarantee for traversal membership when project code
mutates the very list a walker is currently iterating.

## Performance observation

The planning audit measured automatic naming at 2,048 children as 55.8 ms to
link and 1.180 s for 20 simulation ticks; equivalent explicit names took 0.179
ms and 24.4 ms.  A three-sample candidate audit measured a 1.133 ms automatic
link median and 36.6 ms for 20 ticks, with `parts-0` through `parts-2047`
preserved.  Shared-host elapsed time is not a threshold.  The structural test
instead proves exactly one index build per parent traversal, zero fallback
per-child scans in framework walks, and exactly one iteration of an
instrumented eligible public sequence.

## Provenance and limits

- Planning/baseline source is
  `4bcf4cb5201d9d4bf25e16f1f950c3c667d6ec3c` on
  `performance-analysis`.
- Candidate SHA-256 at focused green: `tests/test_traversal_naming.py`
  `cf3523bbc57fe301517204582f0d220577e2d316dfe8832bc570fbfdc8ede769`.
  The five production-file hashes in the green session are retained in the
  handoff rather than treated as package identity because those shared files
  also contain coordinated WP1/WP3 work and may continue changing.
- `tests/test_builder_lifecycle.py` received only an inert `_link_children`
  member on its `SimpleNamespace` publication-order fixture, matching its
  existing inert `_link_child`; it is a test double, not a new public node
  protocol.  The requested coordinator cleanup removed the assertion that the
  private flexible-cache default equals 64 while retaining its `2 *` actual
  limit trajectory.
- No original project, historical audit asset, dependency, OpenSpec content,
  task checkbox, ADR, progress record, commit, or staged change belongs to this
  package.
