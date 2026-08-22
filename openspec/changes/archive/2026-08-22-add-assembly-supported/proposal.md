# Add `assertAssemblySupported`

## Why

A recurring failure across shop mechanical projects, reported by the pilot: an
agent places a part that is simply floating — nothing holds it against
gravity. `assertNoSolidInterference` catches parts that share material, and it
has measurably improved agent consistency, but nothing catches the opposite
defect: a part positioned in space with no support at all. Projects need a
physical assertion that the assembly does not fall apart.

## What Changes

- Add `TestCase.assertAssemblySupported(node, ...)` to `solid_node/test.py`:
  a whole-assembly assertion that selects topmost rigid solids exactly like
  `assertNoSolidInterference`, then proves every selected solid is
  *transitively supported against gravity*.
- Support is established by per-solid drop tests: a solid displaced by
  `max_drop` along the gravity vector must intersect (positive volume) another
  solid — creating a "rests on" support edge — and every solid must reach a
  grounded seed through those edges.
- Grounded seeds default to the solid(s) at the assembly's lowest extent along
  gravity (the assembly holds itself together); an explicit `ground` overrides
  the default for assemblies that rest on an unmodeled surface.
- `supports` declares explicit extra support edges for holds the geometry
  cannot prove without friction/adhesion semantics (press fits, glue), keeping
  the exemption visible in the test.
- Reuses the existing cached-Manifold placement, conservative world AABBs, and
  sweep-and-prune broad phase; drops are pure world-frame translations of
  already-placed geometry.
- No physics engine, no force balance, no toppling analysis: the assertion's
  contract is support reachability, and its docstring states the exclusions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `test-framework`: add a requirement for the whole-assembly gravity support
  assertion (`assertAssemblySupported`), alongside the existing whole-assembly
  solid interference requirement.

## Impact

- `solid_node/test.py`: new public assertion plus private support-graph
  helpers; no change to existing assertions.
- `tests/`: new framework tests with meta-project fixtures (floating part,
  stack on lowest-solid ground, hanging part, mutual-lean cycle, explicit
  ground, declared supports, clearance play below `max_drop`, tunneling-risk
  thin shelf).
- `docs/testing.rst`: document the new assertion, its knobs, and its stated
  physical exclusions.
- No new dependencies; builders and non-test commands do not invoke it.
