# WP2 retained builder lifecycle evidence

Date: 2026-09-07  
Planning HEAD: `4bcf4cb5201d9d4bf25e16f1f950c3c667d6ec3c`  
Scope: OpenSpec tasks 3.1--3.4 and the focused portion of 3.5

## Implemented boundary

The supervisor still starts every builder through the explicit spawn context,
using the module-level `build_once`/`run_builder` targets and reconstructable
plain arguments. A child now retains its one loaded root and one complete
assembly while it finishes successful sequential renderer passes for one
stable `SourceGeneration`. It exits at `CURRENT`, `SOURCE_CHANGED`, failure,
or the existing no-progress per-STL contention boundary.

The F04 project lock still surrounds assembly, every retained artifact pass,
and publication. Callback notification, the ordinary source watch, and the
reload-failure recovery watch remain outside the lock. A successful renderer
completion is distinguished internally from `trigger_stl()` making no progress
because another process owns an STL lock; the latter returns to the supervisor
instead of spinning inside the retained loop.

The retained worker uses WP1's fresh census at initial loaded-source freeze,
after project-lock acquisition, assembly, artifact currency, every artifact
pass, both sides of an asynchronous renderer wait, and publication. A source
identity disagreement returns `SOURCE_CHANGED`; ordinary missing/broken-source
and one-shot build failures remain `FAILED` and are not generation retries.

## Red evidence

Before the retained-loop production change, the new focused lifecycle tests
reported `2 failed, 5 passed`: successful renderer completions returned to the
supervisor rather than reaching `CURRENT`, and no second retained artifact-pass
boundary occurred.

The disposable real 24-artifact Solid2 fixture failed its process-count
contract after 32.32 seconds: the legacy lifecycle started 25 builder children
(24 renderer passes plus the final current/publication pass), rather than one.
It did still produce all 24 STL artifacts, which established that the red
failure was the process/reconstruction lifecycle rather than missing geometry.

## Focused green evidence

Commands were run from this bench with the workspace virtual-environment
Python and `PYTHONPATH=$PWD`.

```text
PYTHONPATH=$PWD ../../../.venv/bin/python -m pytest -q \
  tests/test_retained_builder_generation.py -k 'not FreshProcessBatchTest'
13 passed, 1 deselected in 2.78s
```

The full real fixture was then run with two independent disposable project
copies. The optimized copy started exactly one spawned child. The reference
copy deliberately retained the pre-WP2 one-pass process boundary and started
25 spawned children. It passed in 34.76 seconds. Together the real fixture and
focused structural tests assert:

- exactly one root construction, 24 part constructions, one structural root
  render, and 24 leaf renders in the retained child;
- all retained passes observe the same root object and full assembly occurs
  once;
- a focused real-`FusionNode.shape` seam records exact fusion composition once
  in the existing child order across retained continuation;
- `viewer.json` names exactly the complete set of 24 STL files; and
- the complete 24-entry relative-filename-to-full-SHA-256 map equals the
  independently built 25-child reference map (not merely the entry count or
  digest format).

An earlier combined lifecycle/manager run reached `62 passed, 1 failed in
63.83s`; its single failure was the legacy recovery assertion that expected a
repaired watching builder to exit after one intermediate artifact. That
expectation was narrowly updated to require complete publication, cleared
error state, an alive watcher outside the project lock, and exit after the next
tracked edit. The repaired focused recovery/lifecycle subset then passed 8
tests, and it is included in the 13-test result above.

## Source replacement and failure proof

Actual filesystem-identity races, not only mocked outcome routing, cover the
retained lifecycle:

- `FilesystemGenerationRaceTest` atomically replaces a same-size contributor
  with restored mtime while a future-dated contributor preserves the aggregate
  maximum, before project-lock acquisition and between retained passes;
- `BuilderGenerationGuardTest` performs the same kind of replacement during
  real assembly;
- `AsyncRendererGenerationGuardTest` replaces source during the asynchronous
  wait and proves the temporary output and lock are discarded; and
- the publication guard replaces source after complete serialization but
  before `viewer.json` becomes reachable and proves no manifest is written.

The focused lifecycle cases additionally prove `SOURCE_CHANGED` causes a new
spawned supervisor attempt, while an ordinary failed one-shot does not retry.
A failure after one completed retained pass writes `errors.json`, publishes no
viewer document, returns `FAILED`, and has assembled only once. A reload
assembly failure writes its error, releases the project lock, performs no more
geometry, waits without respawning, and returns `SOURCE_CHANGED` only after the
repair event. Existing fatal-initial-develop coverage remains in
`test_builder_reload_resilience.py` and manager outcome coverage remains in
`test_manager_develop.py`/`test_manager_build.py`.

## Pending combined validation

Task 3.5 is not claimed complete here. WP3 changed the shared Builder
publication/inventory path after the last WP2 combined run. The final owner
must run the combined source-generation, real cold OCCT-after-parent-import,
multi-model, exact-fusion, build-lock/contention, source-edit/recovery,
build/develop-manager, and WP3 publication suites on the settled integrated
worktree. The focused evidence above establishes WP2's owned behavior but does
not substitute for that final cross-package regression.
