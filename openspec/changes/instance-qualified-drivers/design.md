# Design: instance-qualified drivers

## Context

Stage 3a of ADR-056, opening the eight seams named by the 2026-08-26
expression spike (`spike/expressions/FINDINGS.md`). Current state after
stages 1–2:

- `AssemblyNode.set_state(**states)` merges one flat dict and
  propagates the same dict to every rendered descendant; two instances
  of one class can never hold different values for a same-named driver.
- `simulation.declared_drivers(cls)` scans a single class's MRO;
  `Sim.__init__` builds its bank from the root class only, so a
  machine whose drivers live on children gets an empty bank and fails
  on its first render.
- A child's `name` is derived by its parent (`_link_child` /
  `_attr_name_for`) — and the scad and serializer passes link before
  the child renders, while `set_state`'s `_rendered_children` walk
  renders without linking.
- The document (export `manifest.json` / build `viewer.json`,
  `version: 1`) carries operations as raw expression strings whose only
  variable is `$t`; the widget evaluator binds `$t` alone.
- Constraint (stage 2, preserved): `solid_node/node/` never imports
  `solid_node/simulation/`.
- Spike-proven facts this design leans on: eager qualification is
  viable (the id is knowable when `render()` runs, in linked passes);
  an `OpenSCADConstant` subclass rides solid2 arithmetic and
  `solid_node.math`'s symbolic trig for free; dotted ids parse as
  member access in jokenizer; `.scad` snapshot substitution needs no
  machinery.

## Goals / Non-Goals

**Goals**

- Two same-named drivers on sibling instances are independently
  addressable everywhere a driver is named: state binding, the `Sim`
  bank, instructions, and the serialized document.
- The serialized document carries a driver table and named-driver
  expressions, versioned, with the same verbatim-preservation guarantee
  `$t` has.
- Driver-declaring projects build and test through the CLI without
  self-binding defaults.
- `self.time` under a `Sim` reads the stepped simulation clock.
- v8-engine and every existing `$t` caller behave identically.

**Non-Goals**

- No client-side evaluation of driver expressions, no UI, no stepping
  loop in the viewer (stage 3b; a v2 document with an empty driver
  table must degrade to v1 behavior in the shipped viewer).
- No range clamping; `range` stays presentation metadata.
- No merge of `Driver.scale` and `Port.scale`.
- No sanitization of illegal derived names (v1 forbids, loudly).
- No G-code, sequencing, flow variables, acausal solving; no
  trace-driven OpenSCAD animation, ever (ADR-056 excludes it).

## Decisions

### D1. Qualified id = dotted instance path, computed, never stored

`<path from serialization/simulation root>.<local driver name>`, e.g.
`x_axis.motor`; a root-declared driver keeps its bare name. Computed
during linked walks from `_link_child`-derived names — the same names
the document already publishes for nodes — so document and bank agree
by construction. Alternative (registry of stable ids assigned at
declaration) rejected: renders rebuild the tree each pass, so identity
must derive from tree position, and a registry would be state the
guardrail forbids.

### D2. The token is an `OpenSCADConstant` subclass, eagerly qualified

Productionize the spike's `DriverToken`: its string is the qualified
id, created at driver-read time in a linked pass. Ordinary solid2
arithmetic then emits the wire form and `solid_node.math` keeps its
symbolic degree-trig mode (it dispatches on the base class).
Alternative (tree-preserving expression type) rejected by the spike:
strictly more cost — every operator reimplemented — for a condition
(path unknowable at render time) that does not hold; it stays the
recorded fallback if a future pass genuinely cannot link first.

### D3. Symbolic serialization is a mode, not a relaxed validator

Serialization binds every declared driver to its token via an internal
path distinct from `set_state`; `_validate_state` keeps rejecting
non-numbers so a bound pose remains a pure function of numbers. The
mode binds *all* declared drivers (no holes), renders, serializes, and
restores the previous binding, mirroring the export producer's
existing "return to symbolic `$t` before serializing" obligation.
Alternative (teach `set_state` to accept tokens) rejected: it would
let a numeric pass silently carry symbols into meshes and assertions.

### D4. Qualified state binding; `time` is the one global entry

`set_state` accepts qualified names for instance-scoped drivers
(passed as a mapping, since dotted names are not Python identifiers)
alongside the existing flat form. Propagation delivers to each child
only the entries addressed to its subtree, stripping the consumed path
segment; `time` propagates flat to everyone, unchanged. The stage-2
flat form for a project driver stays valid only while the name is
unambiguous in the tree — an ambiguous flat bind fails loudly naming
the colliding qualified ids rather than sharing state silently.
Alternative (nested-dict-only API) rejected: qualified strings are
what the bank, document, and instructions already use; one grammar.

### D5. Propagation walks link before recursing

`set_state`/`clear_state`'s child walk links children the way the scad
and serializer passes already do, so qualification is correct in every
pass that can reach a driver. A driver read that would qualify through
an unlinked or illegally-named segment raises, naming the node and the
cure. List-held children (`axes-0`) are legal *nodes* but illegal id
segments: declaring or reaching a driver through one fails loudly in
v1 (D1 alternative — sanitizing bijectively — deferred until a real
project needs drivers on list children).

### D6. One tree-walk enumeration authority

`simulation` gains a qualified enumeration (spike `qualified_drivers`)
walking a constructed root's tree: `{qualified_id: Driver}`. It feeds
the `Sim` bank, instruction-target resolution, the document driver
table, and build-path default binding. `Sim` keys state, trajectory,
and program targets by qualified id; instruction declarations on any
node use local names and qualify by the declaring node's path;
`Sim.trigger` addresses instructions by qualified name (root-declared
ones keep bare names).

### D7. `Sim` binds the `time` clock in seconds

Each tick binds global `time` to the exact instant `k*dt` (computed
per tick from the integer tick count, ADR-050 reasoning — never
accumulated). Under a `Sim`, `self.time` is the simulation clock;
outside, the ADR-008 normalized 0..1 `$t` path is untouched. This is
the "time demoted to one driver" decision ADR-056 drafted —
**flagged in the proposal for explicit ratification** since it fixes
the unit (seconds) of simulation time. Alternative (normalize sim time
0..1 over the run) rejected: a scenario's duration is not known at
declaration and non-periodic machines have no natural period.

### D8. Document schema v2

`manifest.json`/`viewer.json` bump the shared `version` to 2 and add a
`drivers` table: qualified id → `{default, range, unit, dtype, scale}`
(the driver's declared metadata verbatim; `range` explicitly
presentation-only). Operations serialized in symbolic mode may
reference qualified ids, preserved verbatim under the same producer
guarantee as `$t`. Consumers gate on the version; the shipped viewer
treats unknown driver variables as an unsupported document only when
the table is non-empty — an empty table is exactly v1 behavior. The
`.scad` path stays numeric-substituted with `$t` live (spike verdict
4: no machinery needed).

### D9. Build-path defaults bind in the loader

The build/test loader, after constructing the node and before its
first render, enumerates declared drivers (D6) and binds their
defaults as a numeric snapshot. It lives in the manager/loader layer,
which may import `simulation`; `node/` stays clean. A node with no
declared drivers is untouched (v8 path identical). Alternative (a
`node/`-level hook the simulation package registers) rejected as an
import-cycle dodge that hides the dependency instead of placing it.

## Risks / Trade-offs

- [Linked-walk change in `set_state` alters when `_link_child` runs]
  → v8-engine full suite and the 813-test suite must pass unchanged;
  linking is idempotent and the scad/serializer passes already do it.
- [Ambiguity check makes some stage-2 flat binds fail that silently
  "worked"] → that silence was the defect (both instances shared one
  value); the error names the qualified cure. Release-noted as
  behavior-correcting.
- [Sim `time` in seconds surprises a port of a periodic model] → the
  periodic path keeps `$t`; ADR-056's phase vocabulary covers the
  conversion; decision explicitly ratified by the pilot.
- [Schema v2 consumers lag producers] → single-repo lockstep bump, the
  export spec already mandates producers and consumers move together;
  empty-table degradation keeps old documents inert.
- [Deferred name sanitization blocks a future list-held-drivers
  project] → loud v1 failure names the limitation; bijective
  sanitization is a recorded, compatible extension.

## Migration Plan

Single repository, no deployment. Land red-first per requirement;
callers (`v8-engine` 33/33, `spike/axis/scenario.py`,
`spike/expressions/run_spike.py`) revalidate on the shipped API; the
expression spike's shims (`symbolic.py` bindings, qualified bank)
dissolve into the framework the way `steplab.py` did in stage 2, and
its runner becomes caller validation. Rollback is reverting the
implementation commit; the schema bump ships in the same commit as its
consumers.

## Open Questions

- None blocking. Deferred by decision: evaluator driver map and
  free-variable `isAnimated` replacement (3b), ADR-022 revision (3b),
  `Driver.scale`/`Port.scale` merge (when the viewer proves the need),
  name sanitization (when a project needs drivers on list children).
