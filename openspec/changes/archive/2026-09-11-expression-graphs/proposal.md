## Why

Curta Type I-3x exhausts approximately 7.49 GiB of resident memory while
constructing motion expressions, before schema-4 sharing can run. Keeping
shared operations during construction makes this machine exportable and gives
solid-node ownership of motion independently of its modelling backends.

## What Changes

- Build deferred motion as shared operations rather than expanded strings,
  preserving ordinary formulas, numeric evaluation and degree conventions.
- Carry sharing through time, drivers, ports, couplings, transforms and
  flexible-part parameters, including structural dependency inspection.
- Compile build and export documents directly to the existing schema-4
  bindings, without an expanded intermediate representation.
- Adapt shared expressions to SolidPython and self-contained SCAD output;
  preserve OpenSCAD and SolidPython modelling support.
- **BREAKING for text-inspecting callers:** compound symbolic text may use
  local sharing when explicitly rendered for SCAD instead of the former fully
  expanded spelling. Bare time/driver names and simple unshared expressions
  keep their spelling; numerical behavior and published document grammar stay
  unchanged. No application formula rewrite is intended.
- Prove bounded construction and publication, legacy compatibility and
  full-machine export with Curta, including browser pose inspection. Report
  actual measured warm/cold memory peaks and headroom, not just a pass under
  the 8 GB safety cap; the cap is not an estimate of required memory.

## Capabilities

### New Capabilities

- `motion-expression-sharing`: composed motion remains usable as reuse and
  depth grow, through build, export, SCAD output and repeated builds, without
  duplicating all descendant expressions on reuse.

### Modified Capabilities

- `kinematics`: qualified driver arithmetic yields deferred values rather
  than eagerly building strings; standalone operation serialization and SCAD
  conversion preserve meaning with compact expressions.
- `export`: normal publication preserves construction-time sharing through
  final document generation and retains the existing schema and legacy-text
  fallback.

## Impact

Framework-only implementation: expression representation, `math.py`, driver
and time tokens, operations, flexible-node inspection, serializer, builder,
exporter and SolidPython compatibility. Keep the declarative parameter algebra
distinct. No new runtime dependency, geometry backend change, fusion change,
assembly lifecycle replacement, lookup primitive or viewer-role decision.
The viewer remains a separate AGPL package and consumes its existing schema;
validate against it without assuming permission to modify that repository.

Origin: `workflow/docs/expression-graphs.md`, with project evidence under the
primary shop catalogue's `projects/Calculators/Curta-Type-I-3x/_build_evidence/`.
Revisit ADR-080's eager construction and unchanged-SCAD-text decisions while
preserving its table contract and historical evidence. ADR-022's established
math semantics remain in force, including its recorded limitations.

This is a standalone cycle. Base and intended integration target:
`main` at `e51d196c74f10e240ef0f3580c52f9abee66d63b` in
`/home/asa/devel/libresolid-studio/solid-node`. Branch `expression-graphs`;
worktree `/home/asa/devel/libresolid-studio/solid-node/WTs/expression-graphs`.
The shop launcher registered slot 8 (ports 8008/3008). The pilot ratified this
design on 2026-09-11 with the explicit addition of actual memory reporting,
and authorized the planning commit and implementation. Integration into main
needs separate pilot authority.
