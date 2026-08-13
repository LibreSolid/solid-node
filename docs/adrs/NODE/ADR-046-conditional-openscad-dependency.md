# ADR-046: Conditional OpenSCAD dependency

**Status:** Accepted

**Date:** 2026-08-13

**Change:** `conditional-openscad-dependency`

**Depends on:**
- [ADR-004: Multi-CAD backend adapter pattern](ADR-004-multi-cad-backend-adapter-pattern.md)
- [ADR-044: Derived exact-geometry capability](ADR-044-derived-exact-geometry-capability.md)
- [ADR-045: Exact fusion composition](ADR-045-exact-fusion-composition.md)
- [ADR-041: Browser-rendered transparent snapshots](../BUILD/ADR-041-browser-rendered-transparent-snapshots.md)

## Context

ADR-004 established OpenSCAD as a universal compilation target. Exact BREP
artifacts and exact fusion composition later removed every OpenSCAD invocation
from an all-CadQuery project, while Solid2, raw OpenSCAD, faceted fusion,
symbolic Solid2 evaluation, and explicitly OpenSCAD-backed viewer operations
still genuinely use the binary. Keeping a blanket installation requirement
made the declared architecture disagree with both the control flow and the
majority of catalogue projects. Missing installations also surfaced as bare
subprocess `FileNotFoundError` failures.

## Decision

OpenSCAD is a conditional dependency checked only at the operation that uses
it. The complete requiring set is:

- Solid2 and raw OpenSCAD leaf STL rendering;
- faceted `FusionNode` STL rendering;
- `Solid2Node.as_number()` symbolic-value evaluation;
- `solid develop --openscad`; and
- `solid snapshot --renderer openscad`.

One cached resolver locates the binary once per process. Every requiring path
raises the same actionable error before subprocess launch when it is missing,
naming what needed OpenSCAD, why, and the installation remedy. The snapshot
error additionally names `--renderer web`.

The snapshot renderer remains OpenSCAD by default. Renderer availability and
model backend do not select a substitute because that would silently change
existing visual evidence. The multi-backend adapter pattern and the common
`as_scad()` document remain; only ADR-004's universal-compilation-target
clause is superseded.

## Alternatives rejected

- **Check at import, install, or CLI startup:** reinstates a blanket
  dependency for projects that never reach an OpenSCAD path.
- **Infer requirements from the whole node tree:** obscures the actual point
  of use and risks over-requiring the tool for exact or current artifacts.
- **Select the web snapshot renderer when OpenSCAD is absent:** silently
  changes background, colour, and therefore recorded visual evidence.
- **Include `jscad` in the same change:** it has a distinct Node toolchain and
  installation story, and no catalogue project exercises it as a validating
  caller.

## Consequences

- All-exact CadQuery projects build, test, and export without OpenSCAD, and
  make no availability check.
- Existing OpenSCAD-backed behavior and output are unchanged when the binary
  is present.
- Missing binaries fail before process launch with context and a remedy; no
  geometry or renderer substitution occurs.
- `JScadNode` remains outside the requiring set because it produces its STL
  through `jscad`. That binary still has the same undeclared-external-tool
  defect: when missing it fails at subprocess launch. Extending the conditional
  dependency capability to `jscad` is the natural follow-on, but is deferred
  until its separate install story and a real caller can validate it.

## Evidence

- `tests/test_openscad_dependency.py` covers one-time resolution, every
  requiring path, exact/faceted routing, JSCAD exclusion, and renderer
  non-substitution.
- `snowman` built, passed all seven project tests, exported, and rendered with
  the web snapshot backend under an empty PATH; its default snapshot failed
  with the explicit web-renderer remedy.
- `snowman-3` built unchanged with OpenSCAD present and, without it, failed on
  node `bottom` naming the `Solid2Node` backend and installation remedy.
- `gearbox` built with zero traced OpenSCAD invocations; builds with and
  without the binary produced byte-identical STL and BREP artifact sets.

## References

- `solid_node/openscad.py`
- `solid_node/node/base.py`
- `solid_node/node/adapters/solid2.py`
- `solid_node/viewers/openscad.py`
- OpenSpec archive `conditional-openscad-dependency`
