## Context

The `solid-body-integrity` change (archived 2026-08-10, commits 821277f and
3307c4e on this branch) established three decisions this change keeps intact:

1. The unit of connectivity is the **topmost rigid node** — the thing that gets
   printed as one part — not the leaf and not every rigid node.
2. The count is taken from that solid's **own STL, with no operations applied**.
3. Therefore no world matrix is composed, no operation value is resolved, and
   an animated subtree is answered exactly as a static one is.

Those are correct and were validated against the originating `$t` defect. What
is wrong is where the answer is consumed.

`Builder._verify_solid_bodies` runs on both publication paths (`builder.py:266`
and `:280`). `solid test` does not construct a `Builder`: `manager/test.py:118`
calls `node.build_stls()` directly inside the project build lock, and
`manager/test.py` is untouched by the whole `solid-body-integrity` change. So
the check runs on `solid build`, `solid develop` and `solid snapshot`, and
never once under `solid test`.

Everything that follows from that is a symptom:

- a geometric contract is absent from `Ran N tests` and from the pass/fail dots;
- its failure arrives as `errors.json` / a build traceback, not as a named test;
- `--failfast`, `@testing_instant` and `@testing_steps` do not reach it;
- reading a project's test file tells you nothing about whether it is enforced;
- it cannot be scoped to a subtree, only to whatever the builder loaded.

The framework already has exactly one way to declare a geometric contract: a
`test_` method calling an assertion on `TestCase`. `manager/test.py:168`
discovers those by `dir()` and `startswith('test_')`, counts them, dots them per
instant, and honours `--failfast`. `assertNoPairwiseIntersections` is already
a whole-model sweep declared that way. Solid integrity became implicit not
because a mechanism was missing, but because this one check bypassed it.

## Goals / Non-Goals

**Goals:**

- Make whole-solid connectivity an explicit, declared, counted project test.
- Keep the measurement byte-for-byte identical to the one being removed.
- Leave no path by which the framework runs it on the project's behalf.
- Give a new project the contract as visible, editable, deletable source.

**Non-Goals:**

- Reinstating `bodies`, `assertOneBody`, `assertBodyCount`, or
  `assertNoDisconnectedParts`. All stay removed.
- Changing `assertJoined`, the fusion hierarchy rule, static rigidity, the
  Manifold cache, the AABB broad-phase, or `node.mesh` semantics.
- Adding the pairwise-intersection assembly sweep. Named as future work only.
- Any second test-declaration mechanism: no mixin, registry, decorator,
  base-class hook, config list, or `solid check` command.
- Reporting a project that declares no integrity test as an error.

## Decisions

### One ordinary assertion, no new mechanism

    def test_solid_integrity(self):
        self.assertNoDisconnectedSolids(self.node)

The assertion joins the ~15 already on `TestCase`. The runner needs no change:
inherited-or-defined `test_` methods are already discovered, counted, dotted,
and failfast-aware. Because the call site is an ordinary method body, animation
sweeps and subtree scoping come free and need no syntax of their own.

*Alternative considered — a mixin (`class GearTest(SolidIntegrity, TestCase)`).*
Rejected. It saves one line and hides which contracts run behind a base-class
list, which is the property this change exists to remove. It also needs a new
class per future check, where an assertion needs nothing.

*Alternative considered — keep the build check and add the assertion too.*
Rejected: two implementations of one measurement, and the hidden one still
fails builds for a contract the project never asked for.

*Alternative considered — a `solid check` command.* Rejected: a second entry
point with its own build, fixture and reporting story, parallel to the runner
that already does all three.

### The traversal is relative to the node passed in

Descend from `node`; on each branch stop at the first rigid node and yield it.
A rigid root is its own only solid. Rigid ingredients inside a connected fusion
are not checked independently — a leaf may legitimately be several pieces the
fusion joins, which is ordinary modelling.

Scoping falls out of the argument: `assertNoDisconnectedSolids(self.node)`
covers the model, `assertNoDisconnectedSolids(self.node.gearbox)` covers one
subassembly. The builder could not express that.

`_topmost_rigid_nodes` moves from `builder.py:31` to `node/base.py` beside
`_topmost_rigid_ancestor` (`base.py:104`). One definition of "a solid", shared
with `_compose_solid_matrix`, so the assertion and `assertJoined` cannot drift
apart.

### The measurement is unchanged

`_cached_base_mesh(node.stl_file)`, `.split(only_watertight=False)`, require
exactly 1. No transform, no keyframe, no `node.mesh`.

This is deliberately the same code the builder runs today, relocated. The
`$t` failure that motivated `solid-body-integrity` stays fixed for the same
reason it was fixed there: nothing composes a matrix, so nothing can meet an
unresolved animation expression. Splitting without filtering to watertight
components is equally deliberate — a fragment that is itself closed is exactly
the case worth catching.

Failure raises `AssertionError` naming the solid and the count, and fails at
the first disconnected solid, consistent with `assertNoPairwiseIntersections`.

### Publication performs no project geometry assertion

`_verify_solid_bodies`, both call sites, the builder-local traversal and the
`_cached_base_mesh` import are removed. The builder stops opening STLs to count
components.

The line this draws: the framework always enforces what makes a model
**well-formed** — a fusion may not contain an assembly, an artifact may not be
missing — and never enforces what a project chose to **prove about geometry**.
`FusionNode.validate` therefore stays exactly as it is; it is a model-validity
rule, not a geometric test.

### The incomplete-render guard is kept and re-justified

`_artifacts_are_current` / the `BuildOutcome.RENDERED` guard (`builder.py:342`)
was introduced under the premise "publication reads each topmost rigid node's
STL". That premise expires here. The guard is kept anyway, on independent
grounds: `_write_viewer_snapshot` serialises a manifest of
`relpath(rigid_node.stl_file)` for every rigid node, so publishing while an
artifact is absent advertises a file that is not there. That is a manifest
integrity defect regardless of whether anything counts components. The
requirement is restated on that basis rather than deleted with its old
rationale.

### The scaffold declares the contract as source

`solid new <name>` additionally emits `test_<name>.py` beside the node module,
containing one `TestCase` with one integrity test.

Verified empirically before proposing, because the `cli` baseline spec is
stale about this. The spec still says the scaffold is `<name>/root/__init__.py`;
the command actually emits `<name>/<name>/<name>.py` plus `pyproject.toml`
declaring `model = "<name>.<name>:<Class>"`. Scaffolding `demo_project` and
dropping a `test_demo_project.py` beside the module, the existing loader found
and ran it end-to-end (`Ran 1 tests in 0.18 seconds: 1 passed, 0 failed`).

So the companion needs **no new loader convention** — `loader.py:188` already
maps `<name>.py` to `test_<name>.py`. The change is template plus one copy step
in `manager/new.py`, and the stale `New command` requirement is corrected to
describe what ships.

This is the mitigation for the accepted cost below, and it is a mitigation of
the right kind: a new project starts with the test written down in its own
source, where it can be read, scoped, extended, or deleted.

## Risks / Trade-offs

- [A project that declares no integrity test can publish a part in pieces] →
  Accepted, and the point of the change: the framework stops claiming that
  every publication passed a test nobody wrote. Mitigated by the scaffold for
  new projects, and by the failure being loud once declared. Recorded in the
  build-pipeline delta so a later reader sees it was chosen, not lost.
- [The check no longer runs on `solid develop`, where a maker sees the part] →
  It never ran anywhere a maker could act on it as a test; it ran as a build
  crash. A declared test runs in the command whose exit code gates work.
- [Relocating rather than duplicating means one measurement, one place] → This
  is a benefit, but it depends on the traversal having a single home; hence the
  move to `base.py` rather than a copy in `test.py`.
- [Removing builder tests could lose coverage of the measurement itself] →
  The measurement keeps its coverage, moved to the assertion's own tests plus
  an end-to-end meta-project pair through `solid test`, matching how
  `assertJoined` was covered in 3307c4e.
- [Scaffold churn for a stale spec] → The spec correction is confined to the
  `New command` requirement, and the scaffold's actual layout is already what
  projects use; only the record was behind.

## Migration Plan

1. Declare the contract where it is wanted:

       def test_solid_integrity(self):
           self.assertNoDisconnectedSolids(self.node)

2. Stop expecting `solid build`, `solid develop` or `solid snapshot` to prove
   connectivity. `solid test` is the gate.
3. Nothing else changes: no attribute to delete, no assertion renamed, no
   project layout affected. Projects created before this change are unaffected
   until they choose to add the test.

## Open Questions

None. Ratification is requested before implementation begins; ADR-039's
amendment is drafted with the implementation commit per the framework's ADR
discipline.
