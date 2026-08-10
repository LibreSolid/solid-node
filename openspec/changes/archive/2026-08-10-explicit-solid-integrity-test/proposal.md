## Why

The `solid-body-integrity` change got the geometry right and the lifecycle
wrong. Its three decisions stand: a printed solid is a topmost rigid node,
connectivity is counted on that solid's own local STL, and no operation value
is ever resolved to answer the question. What it did with that answer is the
defect.

It enforces connectivity in `Builder`, on both publication paths. `solid test`
never constructs a `Builder` — `manager/test.py:118` calls `node.build_stls()`
directly — so the check runs on `solid build`, `solid develop` and
`solid snapshot`, and provably never runs under the one command whose purpose
is to run tests. A geometric contract is therefore evaluated everywhere except
in the test suite, reported as a build failure rather than a named test, absent
from the test count, invisible in project source, and unaffected by
`--failfast`.

That inverts the framework's own test model. Every other geometric contract in
solid-node is a `test_` method calling an assertion; the project decides which
properties it wants proved. This is the first of several whole-model checks —
a pairwise non-intersection sweep is already wanted — and each one added as a
build hook compounds the error.

The correction is to make the contract declared:

    def test_solid_integrity(self):
        self.assertNoDisconnectedSolids(self.node)

It runs because the project wrote it down.

## What Changes

- Add `TestCase.assertNoDisconnectedSolids(node)`. It descends from `node`,
  stops at the first rigid node on each branch, and requires each such solid's
  own STL to be exactly one connected component. Same measurement the builder
  performs today: local STL, `only_watertight=False`, no matrix composed.
- **BREAKING** Remove `Builder._verify_solid_bodies` and both publication call
  sites. Publication no longer opens an STL to count components, and a
  disconnected solid is no longer by itself a build failure.
- Move `_topmost_rigid_nodes` out of `builder.py` into `node/base.py` beside
  `_topmost_rigid_ancestor`, so one traversal serves the assertion and cannot
  drift from `_compose_solid_matrix`'s notion of a solid.
- Keep the incomplete-render guard, re-justified. Its current premise —
  "publication reads each topmost rigid node's STL" — expires with this change,
  but publishing a manifest that references an unwritten artifact is wrong
  independently of verification. The requirement is restated on manifest
  grounds rather than deleted.
- Scaffold the contract instead of enforcing it: `solid new <name>` also emits
  `test_<name>.py` declaring the integrity test, so a new project starts with
  it written down, visible and deletable.
- Correct the stale `New command` requirement, which still describes a
  `<name>/root/__init__.py` scaffold. The command has since moved to a named
  module (`<name>/<name>/<name>.py` plus `pyproject.toml`); the spec never
  followed.
- No mixin, registry, decorator, base-class hook, declaration attribute, or
  second test-declaration mechanism is introduced.

Explicitly out of scope: `assertNoPairwiseIntersections` is untouched, and the
future assembly-interference test is not added here.

## Capabilities

### New Capabilities

None. This change relocates one contract from the build pipeline to the test
framework and corrects the scaffold that carries it.

### Modified Capabilities

- `test-framework`: adds `assertNoDisconnectedSolids` to the connectivity
  assertions, and states that the framework never invokes it.
- `build-pipeline`: removes "Every topmost rigid node is one connected body";
  states that publication runs no geometric project assertion; restates the
  incomplete-render rule on manifest-integrity grounds.
- `node-model`: the topmost rigid node remains the boundary of a printed solid,
  but the model no longer claims connectivity is automatically proved.
- `cli`: `solid new` emits a companion test declaring the integrity contract,
  and the requirement is corrected to the scaffold that actually ships.

## Impact

Framework source:

- `solid_node/core/builder.py` — remove `_verify_solid_bodies` (:392), its call
  sites (:266, :280), the builder-local `_topmost_rigid_nodes` (:31), and the
  `_cached_base_mesh` import.
- `solid_node/node/base.py` — host `_topmost_rigid_nodes`.
- `solid_node/test.py` — add `assertNoDisconnectedSolids`.
- `solid_node/manager/new.py` and `templates/project/` — emit the companion
  test.

Records:

- Supersedes the enforcement location ratified by `solid-body-integrity`
  (2026-08-10, archived) while keeping its solid boundary, local frame, static
  rigidity, fusion hierarchy rule, and solid-local `assertJoined`.
- ADR-039 gains a dated amendment: the decision "verification stays in the
  builder, on both publication paths" is superseded; its topmost-rigid-node and
  local-STL decisions are retained.
- `tests/test_builder_lifecycle.py` — the fragmented-publication cases move to
  the assertion's own tests; `tests/test_meta.py` gains an end-to-end pair.

Users:

- A project relying on the build to reject a fragmented solid must declare the
  test. No project can be relying on it: the enforcement exists only on this
  unmerged branch.
- Accepted consequence, stated plainly: a project that declares no integrity
  test can build and publish a part that arrives in pieces. The scaffold is the
  mitigation, not a guarantee.
