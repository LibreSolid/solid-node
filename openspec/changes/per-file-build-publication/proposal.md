## Why

A build publishes an artifact *set*: it renders into a private candidate
directory and swings a symlink when the whole set is current. That was the right
answer to two problems — a reader must not see a torn tree, and racing
publishers must settle — and F1 has just solved the second one properly, with a
lock.

The first problem is now solved in the wrong place. Set atomicity forces every
consumer to treat a publication as one indivisible event, so a change to one
leaf replaces everything: measured on `projects/v8-engine`, 113 MB across 55
STLs re-read and re-uploaded to show a difference that usually touches a single
part. It also makes the outcome this sprint wants impossible by construction —
parts cannot appear as they finish if nothing is visible until all of them are.
And the swapping build path is itself a defect source: a consumer that resolves
`_build` more than once in a request can straddle a swap and 404 an artifact
that exists before and after, which is the measured cause of the shop's broken
model refresh (PRD section 2.1, defect B).

Per-artifact atomicity gives readers what they actually need — no torn file —
without the set. This is F2 of SPRINT-003 and implements decisions D1 and D7 of
`docs/product/sprints/PRD.md`.

## What Changes

- **BREAKING** The build path is a plain directory again. No symlink, no
  versioned siblings, no candidate copy: every builder writes into `_build`
  itself. A project whose build path is still a symlink is migrated once.
- Every artifact is written to a temporary name in its final directory and moved
  into place with `os.replace`. A reader therefore sees an artifact whole or not
  at all, and a reader already holding one keeps reading it to completion. This
  covers rendered STLs, `.scad` files, `viewer.json` and `errors.json`.
- Ordering follows reachability: the manifest is what makes an artifact
  reachable, so new artifacts are written before `viewer.json`, and on removal
  `viewer.json` is written before the artifacts it dropped are swept.
- A successful build sweeps artifacts its manifest no longer references, so a
  renamed or deleted node does not leave its STL behind forever.
- `errors.json` is cleared on every successful build. The candidate copy that
  used to carry or drop it implicitly is gone, so its lifecycle becomes explicit
  (PRD D7, and R2: it is proven here, not inherited).
- **BREAKING** A failed build now leaves a partially updated model rather than
  the previous complete one (PRD D8). The framework's documented guarantee that
  the last successful artifact set survives a failed later build is withdrawn.
- `BuildSession`, `BuildSessionPublisher` and the candidate/published directory
  split in `Builder` are removed rather than adapted.
- The BUILD architecture record deferred from F1 is filed here, covering D1 and
  D2 as one decision: it reverses ADR-030, supersedes ADR-032, and argues that
  ADR-018's lean separation is not regressed.

## Capabilities

### New Capabilities

None. This replaces the publication mechanism inside the existing build
pipeline.

### Modified Capabilities

- `build-pipeline`: the build artifact layout drops the symlink and versioned
  directories; the reader guarantee becomes per-artifact rather than per-set;
  the last-successful-set guarantee and the overlapping-publication tolerance
  requirement are retired, the latter because F1's lock now prevents the race
  they described; artifact sweeping and the `errors.json` lifecycle are stated.
- `build-viewer-artifacts`: the snapshot no longer becomes visible together with
  its models in one atomic publication — it is written last, after them — and
  the failed-build retention scenario changes to match D8.
- `one-shot-build-and-notification`: `solid build`'s race-tolerance wording
  loses the publication race it referred to.

## Impact

- `solid_node/core/builder.py` — `BuildSession` and `BuildSessionPublisher` are
  removed; the builder writes artifacts and the snapshot atomically into one
  directory, sweeps orphans, and clears `errors.json` on success.
- `solid_node/node/base.py` — OpenSCAD renders to a temporary name and
  `StlRenderStart.finish()` stamps and moves it into place; `.scad` writing
  becomes atomic the same way.
- `solid_node/manager/build.py`, `solid_node/manager/develop.py` — the
  candidate-directory plumbing disappears from both loops.
- `tests/test_build_publication.py` — rewritten around per-artifact atomicity;
  the symlink-swap tests are removed with the mechanism they cover.
- `docs/adrs/BUILD/` and `docs/architecture.md` — one new accepted record, with
  ADR-030 and ADR-032 marked as it directs, and the synthesis updated.
- Consumers reading `_build` need no change to keep working, but a consumer
  relying on set atomicity — the shop's viewer host today — will see partial
  updates until S1 and S2 consume them deliberately.
