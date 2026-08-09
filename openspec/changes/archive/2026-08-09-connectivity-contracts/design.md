## Context

The framework's geometric contracts were complete in one direction only.
`assertNotIntersecting`, `assertFreeWithin` and `assertNoPairwiseIntersections`
all answer "are these two things apart?", and a project can build a thorough
suite out of them without ever asking "is this one thing whole?".

The failure that exposed the gap is cheap to produce and invisible to every
existing check. A leaf's `render()` returns several solids; a backend "union"
of solids that do not overlap does not fail, it hands back a compound; the
resulting mesh is watertight because each shell is closed; `mesh.volume` is
positive; the STL exports; the viewer draws something part-shaped. Three shop
projects shipped that way (fan blades 3mm off the hub, a selector fork joined to
nothing, label bars floating off a plate), and in each case the whole suite was
green.

Two mechanisms were available and neither was in use: trimesh can split a mesh
into connected components, and the build already walks the node tree before
publishing.

## Goals / Non-Goals

**Goals:**

- Assertions that count connected bodies, including the inverse contract —
  two features that MUST fuse.
- A build-time guard for the property, opt-in per node, that refuses to publish
  a model which arrives in pieces.
- Zero cost for a project that does not ask for the check.

**Non-Goals:**

- Inferring intent. The framework does not guess that a node "should" be one
  body; a node says so.
- Repairing geometry. A violation is reported, never welded automatically.
- Changing the meaning of watertightness or any existing assertion.

## Decisions

**Count components with `only_watertight=False`.** The question is whether the
geometry hangs together. Filtering to watertight components would drop exactly
the evidence being sought, since the fragments in every observed defect were
themselves closed shells.

**`bodies` defaults to `None`, not to 1.** One is the right contract for almost
every printed part, but defaulting to it would make every existing project start
loading meshes at build time and would fail assemblies that are legitimately
multi-body. The declaration is opt-in; `assertNoDisconnectedParts` applies the
"one body unless declared otherwise" reading in the test layer instead, where a
project has chosen to ask.

**`FusionNode` declares `bodies = 1`.** Its docstring already promised "a
single, inseparable unit". Declaring it turns that promise into something the
build enforces, and a fusion of non-overlapping children — the exact way a part
falls apart — now fails instead of publishing.

**Verify on both publication paths.** The natural place looks like STL
completion, but a build that finds every artifact already current publishes too,
without rendering anything. Checking only the rendering path would let a
fragmented model reach the maker on the second build. `_verify_declared_bodies`
therefore runs immediately before `_write_viewer_snapshot` on both paths, inside
the existing try/except, so a violation is reported through `errors.json` like
any other build failure and the previous publication keeps serving.

**`assertJoined` is the inverse of the adjacency rule.** Everywhere else,
shared volume between two nodes is a defect. Within a single printed part it is
the requirement, and tangential contact is not enough: solids fuse only where
they overlap. `min_weld_volume` lets a drawing state how much overlap the
junction needs, so a weld that exists but is too thin to print fails too.

## Risks / Trade-offs

- `verify_bodies()` reads a node's mesh, which costs a load. Confined to nodes
  that declare a count, so the cost is opted into.
- A project that legitimately publishes a multi-body leaf must declare it, or
  leave it undeclared. This is intended: silence means unchecked, never
  "must be one".
- Splitting very large meshes is not free; the check runs once per publication,
  not per assertion sweep.
