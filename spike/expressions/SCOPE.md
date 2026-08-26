# Spike: named-driver expressions, render to pixels

Design evidence for [ADR-056](../../docs/adrs/NODE/ADR-056-signals-drivers-ports-and-stepped-simulation.md)
(Proposed; stepping core validated by the first spike). This spike
validates or invalidates the expression-representation direction ADR-056
names as the main remaining implementation risk, gating the stage-3a
OpenSpec change. It creates no requirements and ships no framework
code. Everything under `spike/expressions/` is non-shipping.

## Primary question

Can an operation expression referencing **named drivers** travel
end-to-end — built in `render()`, serialized into the viewer document,
numerically evaluated client-side with cross-runtime parity (ADR-022) —
while the `.scad` path emits the same expression with driver values
numerically substituted?

## Established facts this spike builds on (not re-proven)

- solid2's `OpenSCADConstant` is **string-eager**: arithmetic flattens
  to a flat string immediately (`360*t` → `'(360 * $t)'`); no
  expression tree survives, no object references survive.
- With drivers **bound**, Python render paths see plain numbers and
  re-execute per snapshot (first spike, verdict 1). Symbolic forms are
  needed only for the *unbound* serialization/scad render. Python-side
  numeric evaluation of symbolic driver expressions is therefore not
  required and not in scope.
- The widget evaluator (`viewers/widget/src/evaluator.ts`) evaluates
  wire strings via jokenizer against a context map keyed by variable
  name (`$t` today), with OpenSCAD degree-trig and `^` semantics
  shimmed per ADR-022.

## Sub-questions — each gets a verdict

1. **Symbolic driver reads.** When serializing unbound, can a driver
   or port read yield a symbolic token instead of raising the loud
   unbound error, flow through project arithmetic and into
   `Rotation/Translation.serialized` (`str(value)`), and produce a
   well-formed wire expression — via a spike-local shim, no framework
   edits? If the loud-unbound contract and the symbolic render mode
   cannot coexist behind one seam, name the seam.
2. **Qualification: local names → global ids.** Driver names are
   class-local; the wire namespace is flat. Candidate id: the instance
   path from the serialization root joined with the local name
   (`x_axis.motor`), Modelica-flattening style, computed — never
   stored. Verdict hinges on *when* the path is knowable:
   - if a node can know its tree path at the moment `render()` builds
     the expression, an eagerly-qualified string token interoperates
     with string-eager solid2 as-is;
   - if the path is only knowable after tree assembly, the
     representation must keep driver-object references until a
     serialization-time rewrite — a small solid-node expression type,
     not a solid2 constant.
   The spike must demonstrate **two instances of the same class**
   (X and Y axes sharing one `motor`-declaring class) serializing
   distinct ids with distinct bound values.
3. **Client parity.** A spike harness (jokenizer + the shipped
   evaluator's context semantics, exercised read-only) evaluates the
   serialized expressions against a driver variable map. Python
   (bound re-render, `mesh`/matrix path) and client (unbound wire
   string) must agree at N sampled snapshots including a rotation
   through degree-trig, within ADR-022's tolerance discipline. Also:
   what replaces `isAnimated`'s `includes('$t')` when expressions
   reference drivers?
4. **Scad snapshot substitution.** Emit `.scad` with every non-time
   driver substituted by its currently bound numeric value and `$t`
   left symbolic; OpenSCAD must render a screenshot from it. A mixed
   expression (one formula containing both `$t` and a driver) must
   survive partial substitution. This decides whether OpenSCAD
   snapshot support is as cheap as the existing `as_number` machinery
   suggests — the ADR keeps it only under that condition.
5. **State-bank qualification.** With two same-named drivers on
   sibling instances, can `set_state`/`Sim` address them
   independently — qualified keys, nested scoping, or per-instance
   banks, shimmed at spike level? Today's flat recursive propagation
   makes this structurally impossible; the finding is the exact seam
   stage 3a must open in the state bank, matching whatever
   qualification scheme sub-question 2 lands on.

## The model

The first spike's axis, duplicated: one class declaring `motor`,
instantiated twice as X and Y in a parent assembly, so the name
collision, per-instance state, and per-instance qualification are
exercised for real rather than by construction. Geometry fidelity
remains out of scope.

## Out of scope

- Buttons, sliders, transport, any UI (stage 3b)
- Driver/instruction table schema and versioning (stage 3a proposal,
  informed by this spike's findings)
- Trace-driven OpenSCAD animation (`$t`→tick lookup baking) —
  excluded from ADR-056 stages outright, not deferred
- G-code, sequencing, flow variables, anything acausal
- Upstream solid2 changes; Python-side numeric evaluation of symbolic
  expressions (established as unnecessary)
- Any edit to framework source files — spike code shims from outside
  and exercises shipped modules read-only

## Deliverables and exit

- Spike code under `spike/expressions/` plus `FINDINGS.md` beside this
  file: verdict per sub-question (validated / invalidated / blocked),
  the recommended representation (eagerly-qualified solid2-interop
  token vs solid-node expression type) with the evidence that decided
  it, the parity numbers, and the list of framework seams stage 3a
  must open.
- Committed on the `signal-drivers` branch beside ADR-056, citable by
  the stage-3a OpenSpec proposal.
- Timebox: day-scale, a few hundred lines. If sub-question 1 blocks
  early, stop and report the seam — that alone justifies the spike.

Design-invalidating outcomes to watch for: no viable moment exists to
qualify a string-eager token *and* no acceptable seam exists for a
tree-preserving expression type (would force per-driver document
re-render, killing client-side interactivity); or client evaluation
cannot match Python numerics within ADR-022 discipline (would put
evaluator parity, not representation, on the critical path).
