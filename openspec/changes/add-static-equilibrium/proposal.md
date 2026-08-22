# Make `assertAssemblySupported` prove static equilibrium

## Why

The pilot probed the just-shipped `assertAssemblySupported` with the exact
failure it will meet in practice: a horizontal bar supported only at one end
passes, because the assertion proves support *reachability* only — no force or
torque balance. The pilot's finding: the floating-bar defect this assertion
was built for has "support one side only" as the obvious agent fix, so the
documented toppling blind spot is not a corner case, it is the very next
failure mode. The pilot's direction is explicit: no waiting for more empirical
evidence — "I want proper support", in the same method.

## What Changes

- Extend `TestCase.assertAssemblySupported` (same method, same signature plus
  one knob) so that passing requires BOTH the existing transitive support
  reachability AND the existence of a frictionless static equilibrium: a
  distribution of unilateral (push-only) normal contact forces over the
  detected contact interfaces that balances every non-anchored solid's gravity
  wrench — force AND torque — simultaneously for the whole assembly.
- Contact interfaces are derived from the geometry already computed: the
  drop-intersection of each detected support edge yields the contact patch on
  the supporter's surface (points and outward normals). A symmetric *lift*
  pass (the same displacement, opposite direction) detects overhead-restraint
  contacts so engaged couples — a cantilevered pin held by a snug hole's upper
  and lower walls — balance legitimately instead of demanding an exemption.
- Feasibility is decided by one deterministic linear program solved with
  `scipy.optimize.linprog` (scipy is already a runtime dependency). The
  relaxed form of the same LP names, on failure, exactly which solids cannot
  be balanced and whether force or torque balance fails.
- With `ground=None`, a virtual floor body (a slab whose top plane sits at the
  assembly's furthest extent along gravity) is the only anchored body for the
  equilibrium phase, so the default-seeded solids must themselves balance on
  their real floor contact patches — a tall solid toppling off its small
  footprint fails instead of being exempt. An explicit `ground` anchors the
  named solids fully (bolted semantics), exactly as today.
- `supports=[(supported, supporter), ...]` keeps its meaning as the visible
  escape hatch, now for equilibrium too: a declared edge transmits an
  unrestricted wrench (force and torque, both signs) between the pair —
  glue/press-fit semantics.
- New knob `stability_margin` (mm, default `0.0`): shrinks each contact patch
  toward its centroid before the LP so knife-edge and boundary-exact balances
  can be rejected on request.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `test-framework`: modify the "Whole-assembly gravity support assertion"
  requirement — passing now additionally requires frictionless static
  equilibrium over detected contacts; the stated physical exclusions shrink
  accordingly (toppling and force/torque balance are now claimed; friction,
  adhesion, and dynamics remain excluded).

## Impact

- `solid_node/test.py`: equilibrium phase after the existing reachability
  phase — contact-patch extraction from drop/lift intersection meshes, mass
  properties from placed geometry, LP assembly and solve, diagnostic failure
  naming unbalanced solids. Reachability semantics are unchanged.
- `tests/`: new red-first tests and meta-project fixtures — one-end-supported
  bar fails naming the bar; two-end-supported bar passes; offset stack whose
  cumulative centre of mass leaves the base fails; counterweighted assembly
  passes; cantilevered pin in a snug hole passes through drop+lift couple;
  tippy default-seeded solid fails on the virtual floor; declared `supports`
  exempts; `stability_margin` rejects a knife-edge balance.
- Existing support fixtures re-validated: any fixture that only passed by the
  reachability blind spot must be updated to be genuinely balanced, and that
  update is evidence, not regression.
- `docs/testing.rst`, `docs/api-reference.rst`: updated contract and knobs.
- One ADR for the equilibrium-as-feasibility decision; `docs/architecture.md`
  test-framework section updated.
- No new dependencies: scipy (`>=1.18` already required) provides the LP.
