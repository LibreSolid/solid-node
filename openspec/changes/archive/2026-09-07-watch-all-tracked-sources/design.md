## Context

After a successful assembly, `Builder._start()` schedules every path in
`node.files` individually. That set includes Python import closures and the
declared geometry source of `OpenScadNode`, `JScadNode`, `StlNode`, and
`StepNode`. The shared `on_modified()` callback nevertheless rejects every
non-`.py` path because its filter was written for `_watch_broadly()`, the
recursive recovery mode used when loading or assembly fails and no trustworthy
source set is available.

The two watch modes need different admission rules. A precise watch has already
classified each scheduled file as model input. A broad directory watch has no
such information and must suppress unrelated output and bytecode noise.

## Goals / Non-Goals

**Goals:**

- Exit the single-shot builder when any explicitly tracked source reports a
  modification, regardless of its filename extension.
- Preserve Python-only filtering for the broad recursive recovery watch.
- Normalize event and source paths so equivalent spellings compare reliably.
- Keep the existing thread-safe future resolution and duplicate-event guard.
- Prove behavior through direct watchdog dispatch and one real observer cycle
  over a non-Python imported geometry source.

**Non-Goals:**

- Define or implement moved, created, deleted, or editor atomic-save policy.
- Change source-closure discovery or add directory-recursive successful-build
  watches.
- Debounce events, coalesce rebuilds across processes, or change observer
  backends.
- Alter one-shot `solid build`, which does not wait for changes.

## Decisions

### D1: Retain the normalized set of precisely watched sources

When a successful build schedules `node.files`, the builder will also retain
their normalized real paths. `on_modified()` will accept a non-directory event
immediately when its normalized source path is in that set. The event's suffix
is irrelevant because membership is already the classification.

Inferring precise mode from extension was rejected because it is the current
defect. Treating every modification received by the handler as relevant was
rejected because the same handler is attached recursively to an entire project
after a load failure.

### D2: Apply the existing Python/no-bytecode filter only outside that set

An event not naming a precisely watched source will retain the existing broad
filter: accept `.py`, reject directories, `__pycache__`, and other extensions.
This allows repair of a broken Python module while preventing generated files,
editor metadata, and unrelated assets from spinning the recovery loop.

A separate event-handler class per mode was rejected because both modes share
the same observer lifecycle, asyncio bridge, and duplicate-event behavior; one
explicit membership branch states the actual difference.

### D3: Keep modification events as the scope boundary

The change will not add `on_moved`, `on_created`, or `on_deleted`. The saved
audit dispatched a move event but did not establish how supported watchdog
backends report real editor replacements. Adding one callback without a tested
cross-platform policy could produce duplicate or path-ambiguous reloads and is
not required to fix confirmed F06.

### D4: Test classification and a live non-Python watch

Dispatch-level tests will set a precise source set and require `.py`, `.scad`,
`.js`, `.stl`, and `.step` modifications to resolve the future; untracked
non-Python and `__pycache__` events remain ignored, and a second event remains
harmless. A lifecycle test will run a watching builder with a real observer on
an imported STL fixture, modify the tracked mesh, and require
`BuildOutcome.SOURCE_CHANGED` without an accompanying Python edit.

The saved probe will be updated to declare which synthetic paths represent the
precise source set so its post-fix matrix describes the real mode distinction.

## Risks / Trade-offs

- **Real paths can cease to resolve after replacement.** → This change handles
  modification events only; the stored source spelling and normalized event
  spelling are compared while the path exists, and replacement policy remains
  explicit follow-up work.
- **A geometry tool may write a tracked source repeatedly.** → The first event
  resolves the existing one-shot future and the duplicate guard ignores later
  events until the process exits.
- **A live observer test can be timing-sensitive.** → Wait for the observer and
  future to be ready with a bounded deadline, modify a temporary file, and
  always stop/join the observer in cleanup.

## Migration Plan

No migration is required. The watch set is process-local and exists only for a
running developer builder. Rollback restores the extension filter and its
non-Python stale-view behavior.

## Open Questions

None.
