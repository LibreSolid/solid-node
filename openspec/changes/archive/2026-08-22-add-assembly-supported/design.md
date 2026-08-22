# Design: `assertAssemblySupported`

## Context

`assertNoSolidInterference` (ADR-040) proves that printed solids share no
material: it selects the topmost rigid solids under a node, places their
cached Manifolds (or exact shapes) with composed world matrices at the
runner-selected testing instant, culls candidate pairs with conservative
world AABBs, and reads verdicts straight from the kernel. The recurring
defect it cannot see is the inverse one: a solid floating with nothing
holding it. The framework already owns every primitive a support check
needs — cached placed geometry, world-frame transforms, broad-phase
culling, and translate-then-intersect perturbation semantics
(ADR-025/ADR-029).

## Goals / Non-Goals

**Goals:**

- One ordinary project assertion proving every printed solid in an assembly
  is transitively supported against gravity at the current testing instant.
- Same solid selection, caching, exact/faceted routing, and broad-phase
  discipline as `assertNoSolidInterference`.
- Diagnostic failures that name every unsupported solid.

**Non-Goals:**

- No force or torque balance, no toppling (center-of-mass vs support
  polygon), no friction, no fastener preload, no physics engine dependency.
- No lateral-restraint analysis (a part free to slide sideways still passes).
- No animation scheduling: the runner's testing instant controls placement,
  as with every other assertion.

## Decisions

### 1. Support is a drop test, not a proximity test

A solid `i` is *directly supported by* solid `j` when `i`, displaced by
`max_drop` along the unit gravity vector in world frame, intersects `j`
with positive volume. Rationale: it reuses the exact translate-and-intersect
machinery the perturbation assertions already trust; it needs no
mesh-to-mesh distance queries (trimesh proximity is vertex-sampled and can
miss face-face closeness); and dropping onto a genuine resting face yields
volume ≈ contact area × drop, far above float noise, so no epsilon is
needed. Zero-volume tangency after the drop does not count as support —
consistent with the interference assertion's "positive volume is material"
philosophy.

Alternative rejected: an epsilon-contact connectivity graph. It is
orientation-independent but weaker (a sideways touch counts as "held") and
requires a distance tolerance with no physical meaning.

### 2. Transitive grounding over a support graph

Direct support is not enough: a part resting on a floating part still falls.
Build the directed graph of drop edges `i → j` ("i rests on j"), seed a
grounded set, and propagate groundedness from supporters to supported
(plain BFS; a mutual-lean cycle resolves correctly — it is grounded exactly
when some member rests on something grounded). Every selected solid must
end grounded; the assertion fails naming all that do not.

### 3. Grounded seeds default to the assembly's lowest solids

With `ground=None`, a solid is a seed when its conservative world extent
along gravity comes within `max_drop` of the assembly's furthest extent
along gravity. This makes the default contract "the assembly holds itself
together", which is the right reading for a model floating in CAD space,
and it automatically covers assemblies resting on an unmodeled floor: the
parts that would touch that floor are the lowest ones. The `max_drop`
window doubles as the seed tolerance so seeding resolution matches the
test's own resolution.

`ground=<node or sequence of nodes>` replaces the default entirely: each
given node is resolved to its enclosing topmost rigid solid among the
selected ones, and only those are seeds. A ground argument that resolves to
no selected solid is a loud error, not a silent pass.

Alternative rejected: a ground *plane* parameter. The lowest-solid default
plus explicit anchor nodes covers its use cases without introducing a
second coordinate-convention knob.

### 4. `supports` declares edges the geometry cannot prove

`supports=[(supported, supporter), ...]` adds explicit support edges after
resolution to selected topmost rigid solids. This is the visible escape
hatch for press fits, glue, and friction holds — physics the drop test
deliberately does not model. A declared supporter must still be grounded
transitively; declaring an edge never grounds anything by itself. Unresolvable
pairs are loud errors.

### 5. Geometry routing mirrors the interference assertion

- Faceted pairs: cached Manifolds, lazily placed; the drop is one extra
  world translation folded into the placement matrix
  (`translation @ world_matrix`), so no re-conversion or watertight
  re-check occurs.
- Exact pairs: dropped `placed_shape` against `placed_shape` through the
  boundary-representation kernel, as in `_candidate_intersection`.
- Mixed pairs route faceted.
- Broad phase: only pairs whose dropped-bounds vs placed-bounds AABBs
  overlap get a boolean. The per-solid drop makes the assertion's floor
  cost N translations and box computations; booleans remain proportional to
  interacting pairs, not total geometry.

Selection of zero or one solid passes without geometric work, exactly like
the interference assertion.

### 6. Knobs and defaults

`assertAssemblySupported(node, gravity=(0, 0, -1), max_drop=1.0,
ground=None, supports=None)`

- `gravity`: any nonzero vector, normalized internally; zero vector is a
  loud error.
- `max_drop` (mm, default 1.0): must exceed the design's vertical clearance
  play (else a part sitting in its clearance gap reads as floating) and
  stay below the thinnest supporting feature's thickness plus its gap (else
  the dropped solid tunnels through its support). The default sits in the
  common window between typical clearances (≤ 0.5 mm) and typical printed
  walls (≥ 1.2 mm); the docstring states the rule. Non-positive values are
  loud errors.

## Risks / Trade-offs

- [Tunneling: a drop larger than gap + support thickness skips the support]
  → documented `max_drop` selection rule; framework test pins the behavior
  so the limitation is explicit rather than latent.
- [False confidence: passing does not mean statically stable (toppling,
  sliding, unbalanced levers pass)] → docstring names the exclusions;
  the assertion claims support reachability only.
- [Legitimate friction/adhesion holds fail the drop test] → `supports`
  makes the exemption explicit and reviewable in project test code.
- [Gravity assumes model orientation is physical] → `gravity` knob;
  default matches the framework's Z-up convention.
- [Cost: N drop booleans even when nothing overlaps] → AABB culling keeps
  booleans to interacting pairs; placement reuses the Manifold cache, so
  the added floor cost is N cheap transforms.

## Open Questions

None blocking; naming and defaults above are the proposal for ratification.
