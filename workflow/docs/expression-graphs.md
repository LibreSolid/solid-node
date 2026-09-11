# Expression graphs and removing OpenSCAD as the core broker

Status: provisional pre-spec plan, recording the pilot's accepted direction.
Date: 2026-09-11.
This is not a ratified OpenSpec change, a settled interface, or an implemented
capability. Implementation details and compatibility boundaries still need a
proposal and proof. Baseline specs and accepted ADRs remain authoritative.

## Accepted direction

Give solid-node ownership of its motion expressions, beginning with a shared
expression graph that fixes Curta Type I-3x's export failure. Design that work
as the first step toward removing OpenSCAD as the framework's internal broker.
Follow with a separately scoped change to the geometry assembly and build
lifecycle. Assess OpenSCAD's viewer role separately; removing that role is an
open possibility, not an accepted decision.

OpenSCAD remains a supported modelling technology. solid-node supports the
underlying modelling technologies; this work does not remove `OpenScadNode`,
`Solid2Node`, or the ability to use existing OpenSCAD and SolidPython designs.
OpenSCAD-specific evaluation and output belong at the boundaries that need
them, rather than in the representation every backend must use.

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
| Motion representation | Driver tokens, animation time and symbolic math use SolidPython expression strings | Replace with a framework-owned graph first |
| Assembly and build broker | Every backend passes through `as_scad()`; non-exact fusions use OpenSCAD | Address in a separate architectural change |
| Modelling technology | OpenSCAD and SolidPython produce geometry | Preserve support |
| Viewer and snapshot renderer | OpenSCAD presents generated SCAD alongside the optional browser viewer | Assess separately; no removal decision |

The OpenSCAD executable is already conditional on the paths that invoke it.
That does not make the internal representation independent: even exact and
imported-mesh nodes participate in the SCAD assembly lifecycle. Removing the
executable from an installation cannot fix the expression construction defect.

## First change: shared motion expressions

The intended outcome is that composed motion laws preserve reuse from the
moment expressions are built through publication. Reusing a value should add
references to its operands, not copies of all its descendants.

The proposed scope is:

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

The proposal must settle graph ownership and lifetime, handling of mixed
legacy and graph operands in either order, and preservation of public
serialization behavior. Traversal, hashing and rendering must handle deep
graphs without recursively expanding shared subgraphs. Repeated builds must
not accumulate an unbounded global expression cache. These are design issues
to resolve, not settled choices of classes or modules.

Port-boundary naming alone is insufficient because one law can expand
internally. A compact piecewise/lookup primitive may be useful later, but is
not required to fix general duplication and could introduce a separate viewer
contract. More memory, baked poses and reduced controls do not meet this goal.

### Planned proof

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

Curta's remaining mechanical validation resumes after the framework fix has
been validated against the originating machine. This note records no completed
implementation or new full-export measurement.

## Follow-up: assembly without SCAD as broker

The next architectural change should make machine structure, placement and
artifact production independent of SCAD. Each modelling adapter should produce
geometry through its own appropriate path; OpenSCAD conversion should be used
where the selected backend or requested output needs it.

This requires a separate proposal because the current node lifecycle,
`as_scad()` adapter contract, artifact caching and non-exact fusion behavior
are specified behavior. Replacing the non-exact fusion path requires geometry
evidence and an explicit design decision, not an assumed engine substitution.
The expression graph is a useful prerequisite; this broader work should not
delay the focused Curta fix.

## Open question: OpenSCAD as a viewer

Supporting a modelling backend does not require using its application as the
framework's viewer. Assess whether OpenSCAD can faithfully present the machine
experience defined by independent ports, drivers and interactions, rather than
only display geometry or a time-based animation. The current flexible-part
SCAD path presents a snapshot rather than continuously evaluated shape.

The pilot may choose a limited OpenSCAD viewing role or remove that role.
Neither is decided here. The assessment must cover controls, flexible parts,
snapshots and what `solid develop` does without the optional browser viewer.
The browser viewer is a separate AGPL package; its process and licensing
boundary remain in force. Any viewer changes belong to that repository under
its own records.

## Next planning step

Cut a standalone framework OpenSpec proposal for construction-time expression
sharing, preserving this note as its originating context. Address the affected
parts of ADR-080 explicitly, without rewriting its historical measurements.
Ratify the compatibility boundaries and planned proof before implementation.
The geometry lifecycle follow-up and viewer decision remain separately scoped.
