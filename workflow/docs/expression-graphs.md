# Expression graphs and removing OpenSCAD as the core broker

Status: working memorandum. All three stages are implemented; the OpenSCAD
viewer removal completed the accepted sequence.
Date: 2026-09-11.
This document is not authority over baseline specs or accepted ADRs. It records
the sequence, originating evidence, completed outcomes, and the rationale and
proof for the three changes.

## Accepted direction

solid-node now owns its motion expressions through the construction-time graph
accepted in ADR-101, which fixed Curta Type I-3x's export failure. The
separately scoped geometry lifecycle change followed in ADR-102 and removed
OpenSCAD as the framework's assembly and build broker.

The pilot accepted and implemented removal of the OpenSCAD GUI as a
`solid develop` viewer and of its installation-dependent fallback for v0.7. OpenSCAD
was solid-node's first reliable viewer; as the browser viewer gained tree
navigation, independent driver controls, instructions and continuously
evaluated flexible parts, the OpenSCAD GUI was used less and represented less
of the machine. Maintaining that second, less faithful viewer now burdens the
roadmap opened by the simulation capabilities introduced and further developed
in v0.7.

OpenSCAD remains a supported modelling technology. solid-node supports the
underlying modelling technologies; this work does not remove `OpenScadNode`,
`Solid2Node`, or the ability to use existing OpenSCAD and SolidPython designs.
OpenSCAD-specific evaluation and output belong at the boundaries that need
them, rather than in the representation every backend must use. The fixed-pose
OpenSCAD snapshot renderer is also retained as a distinct capability and keeps
its existing default; it does not need to present live machine controls.

## Originating evidence: Curta Type I-3x

Curta implementation was paused after interactive export exhausted memory
while constructing symbolic motion formulas. Fixed-pose laws compute ordinary
numbers; publication reruns those laws with symbolic drivers. The current
symbolic arithmetic immediately creates strings, so reusing a value copies
its entire expression. A Python variable does not preserve expression sharing.

The project probe recorded the following lower-bound expression sizes:

- A result-dial angle is approximately 121,000 characters.
- A carry-engagement expression reaches approximately 7.7 million characters.
- The result-bank spring spreading profile repeats its input 35 times,
  yielding an estimated 270 million characters for one spreading expression.
- That value feeds multiple spring coordinates across multiple digit stations.

These are expression-size estimates, not measurements of total memory. The
bounded export log records `MemoryError` and a maximum resident set size of
7,857,084 KiB, approximately 7.49 GiB. Its traceback reaches
`piecewise()` through a coupling law and fails in SolidPython's eager
`OpenSCADConstant` arithmetic, before the document binding pass. This supports
the diagnosis of that export failure; it does not establish the cause of the
pilot's desktop crash.

Evidence in the independent project repository:

- [Expression-size probe output](../../../projects/Calculators/Curta-Type-I-3x/_build_evidence/motion-expression-sizes.jsonl)
- [Bounded export failure](../../../projects/Calculators/Curta-Type-I-3x/_build_evidence/materials-export-direct-max.log)
- [Probe source](../../../projects/Calculators/Curta-Type-I-3x/simulation/tools/expression_size.py)
- [Measured spring spreading profiles](../../../projects/Calculators/Curta-Type-I-3x/simulation/detents.py)

Inspection used framework primary HEAD
`2bdc50b37be920e79202d1c9e9c5700e43f525e0`; this identifies the inspected
source, not a newly measured full Curta export. A separate small probe of the
installed symbolic arithmetic produced 1,835,003 characters after just 18
repetitions of `x = x + x`, starting with `$t`.

## Existing architecture and the overlap

[ADR-080](../../docs/adrs/EXPORT/ADR-080-a-shared-subexpression-is-named-once.md)
introduced schema-4 bindings: shared expressions are published once and
referenced by name. However, sharing is discovered by parsing strings the
producer has already constructed. Curta fails before this optimization can
run. The ADR deferred construction-time graphs and suggested retaining the
flat value alongside a graph in a follow-up. Curta's evidence rules out that
approach for the normal path: the enormous string must never be constructed.

OpenSCAD has several distinct architectural roles today:

| Role | Current position | Planned treatment |
| --- | --- | --- |
| Motion representation | Framework-owned construction-time graph; ADR-101 | Complete |
| Assembly and build broker | Native materialization precedes optional SCAD presentation; ADR-102 | Complete |
| Modelling technology | OpenSCAD and SolidPython produce geometry | Preserve support |
| Interactive viewer | Browser viewer is the sole interactive surface; OpenSCAD GUI and fallback removed | Complete in `remove-openscad-viewer` |
| Snapshot renderer | OpenSCAD renders one numerically bound pose | Retain separately, with its existing default |

The OpenSCAD executable is already conditional on the paths that invoke it.
That does not make the internal representation independent: even exact and
imported-mesh nodes participate in the SCAD assembly lifecycle. Removing the
executable from an installation cannot fix the expression construction defect.

## Completed first change: shared motion expressions

The intended outcome was that composed motion laws preserve reuse from the
moment expressions are built through publication. Reusing a value should add
references to its operands, not copies of all its descendants.

The implemented scope was:

1. Introduce a framework-owned expression representation for time, drivers,
   arithmetic and the symbolic face of `solid_node.math`. Preserve ordinary
   project formulas, ports, couplings, numeric operation order and existing
   degree-based semantics. Do not combine this with a new motion API or
   algebraic simplification that changes rounding or branch behavior.
2. Carry graph values through operations and flexible ports. Replace internal
   string-based dependency detection, notably `_time_fed_ports()`, with
   structural inspection of time and driver dependencies.
3. Publish directly into the existing ordered schema-4 bindings table and
   expression strings. Preserve deterministic naming, collision handling and
   transitive dependencies. The viewer already reads this format; no new
   document format is expected, subject to compatibility proof.
4. Keep sharing intact at output boundaries. Operation serialization, flexible
   parameter serialization, diagnostics and SCAD generation must not recreate
   the expanded formula as an intermediate step. Design SCAD emission to
   express sharing locally without adding SCAD-only grammar to viewer
   documents.
5. Define and test compatibility with direct SolidPython expressions,
   `scad_inline()`, comparisons, `abs`, animation time and numeric evaluation.
   Legacy text may still need parsing at an adapter boundary. A lazy framework
   value cannot prevent arbitrary external code from explicitly constructing
   an enormous string; the supported boundary must be stated honestly.

The proposal had to settle graph ownership and lifetime, handling of mixed
legacy and graph operands in either order, and preservation of public
serialization behavior. Traversal, hashing and rendering must handle deep
graphs without recursively expanding shared subgraphs. Repeated builds must
not accumulate an unbounded global expression cache. These are design issues
to resolve, not settled choices of classes or modules.

Port-boundary naming alone is insufficient because one law can expand
internally. A compact piecewise/lookup primitive may be useful later, but is
not required to fix general duplication and could introduce a separate viewer
contract. More memory, baked poses and reduced controls do not meet this goal.

### Planned proof and completion

- Establish a small red reproducer on the real framework symbolic path before
  implementing the change. Include reuse within one law, composition across
  ports, and reuse across operations and flexible parameters.
- Measure graph and publication growth for repeated subexpressions and deep
  chains. Demonstrate that work follows constructed graph size and emitted
  output, rather than the hypothetical expanded tree.
- Compare against the existing producer-generated numeric/viewer parity
  corpus and manageable legacy expressions, not only expectations generated
  by the new implementation. Cover time, independent drivers, arithmetic,
  comparisons and piecewise boundaries.
- Verify SolidPython compatibility and SCAD output separately, including that
  SCAD conversion does not reintroduce the allocation failure.
- Export the complete Curta under an enforced 8 GB memory budget, recording
  the exact limit, environment, framework and project commits, cache state,
  elapsed time, peak memory and output size. Account for relevant child
  processes; distinguish cached and fresh geometry runs.
- Load the result in the viewer and inspect poses under actual driver
  controls, including carry engagement and spring deformation. Successful
  JSON publication or a green numerical suite is not visual proof.

The completed `expression-graphs` cycle is recorded by ADR-101 and
`openspec/changes/archive/2026-09-11-expression-graphs/`. Its final fresh
Curta export peaked at 1,179,168,768 bytes (1.098 GiB) under the enforced
8,000,000,000-byte aggregate limit; its warm export peaked at 831,078,400
bytes (0.774 GiB). The archive carries the exact commits, commands, parity and
browser evidence. Curta's remaining mechanical validation resumed after that
framework acceptance.

## Completed follow-up: assembly without SCAD as broker

The next architectural change made machine structure, placement and artifact
production independent of SCAD. Each modelling adapter now produces geometry
through its own appropriate path; OpenSCAD conversion is used where the
selected backend or requested output needs it.

The completed `remove-openscad-broker` cycle is recorded by ADR-102 and
`openspec/changes/archive/2026-09-11-remove-openscad-broker/`. It preserved
`as_scad()` as an optional compatibility/output consumer, moved faceted fusion
to Manifold, and proved native project builds without assembly-wide SCAD.

## Completed third change: remove OpenSCAD as a viewer

Supporting a modelling backend does not require using its application as the
framework's viewer. OpenSCAD cannot faithfully present the machine experience
defined by independent drivers, instructions and continuously evaluated
flexible parts: it knows only `$t`, substitutes other drivers with one numeric
state, and treats flexible geometry as a fixed snapshot. Those limitations are
acceptable for an explicitly fixed-pose renderer, not for the framework's
interactive viewer.

The v0.7 change therefore removes `solid develop --openscad`, its GUI/PID
lifecycle, and the automatic fallback when `solid-node-viewer` is absent.
Ordinary `solid develop` requires the separately packaged browser viewer;
`solid develop --no-web` remains the viewerless watch loop. The viewer stays a
separate AGPL package behind its existing process boundary. The release must
explain both the historical transition and the retained boundary: OpenSCAD and
SolidPython modelling, SCAD output and OpenSCAD snapshots remain supported;
OpenSCAD is no longer an interactive solid-node viewer.

## Completed implementation

The standalone `remove-openscad-viewer` OpenSpec cycle carried this decision
from framework `main` at `748d6d9`. It removed the CLI/GUI lifecycle, retained
and proved the snapshot and modelling boundaries, and added the v0.7 release
explanation. Its completed record is
`openspec/changes/archive/2026-09-11-remove-openscad-viewer/`. This change did
not publish the framework or the separately founded, not-yet-released viewer
package.
