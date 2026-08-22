# ADR-051: Producer-owned animation time in node-tree documents

**Status:** Accepted

**Date:** 2026-08-22

**Change:** `preserve-symbolic-time-on-export`

**Amends:**
- [ADR-034: Shared node-tree document schema across export and build snapshots](ADR-034-shared-node-tree-document-schema.md)

**Depends on:**
- [ADR-008: Time-Based Animation System for Assemblies](../NODE/ADR-008-time-based-animation-system-for-assemblies.md)
- [ADR-023: Kinematic operations and driver-tagged idempotent renders](../NODE/ADR-023-kinematic-operations-and-driver-tagged-idempotent-renders.md)

**Related to:**
- [ADR-020: Static Export Channel with Embeddable, React-Free Viewer Widget](ADR-020-static-export-and-embeddable-viewer-widget.md)
- [ADR-022: Cross-Runtime Degree-Trig Parity for `$t` Expression Evaluation](../MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md)

## Context

ADR-034 gave export and the build snapshot one recursive serializer and left
each producer only its rigid-model mapper. That division turned out to be
incomplete: it settled *where artifacts point* but said nothing about *which
time the document is written in*, and the three producers do not agree.

ADR-008 makes `AssemblyNode.time` dual-valued — solid2's symbolic `$t`, or a
plain float once `set_keyframe(time)` is applied. An operation records whatever
value user `render()` code computed, and `Rotation.serialized` is
`['r', str(self.angle), self.axis]`. So a keyframe collapses the expression
*inside user code*, at render time: once `time` is `0.25`, `self.time * 360` has
already become `90.0`, and nothing symbolic survives for the serializer to find.

The `export` capability nevertheless promised operations reach `manifest.json`
"as raw unevaluated expression strings so `$t` animation is preserved verbatim".
The implementation kept that promise only by call ordering — `solid export` runs
`load_node` → `export_node` and never keyframes. Any caller that keyframed
first published constants instead, in a document that was schema-valid,
completely static, and entirely silent about it. Reproduced on the framework's
own `Spinner` fixture: a fresh export wrote `['r', '($t * 360)', [0, 0, 1]]`
while the same node after `set_keyframe(0.25)` wrote `['r', '90.0', [0, 0, 1]]`.
The empirical finding came from the `browser-engine` spike, where a host that
builds and then publishes from one node — the obvious thing to write — silently
lost every animation.

`set_keyframe` was also a one-way door: `time` falls back to `$t` only through
an `AttributeError` on `_time`, and nothing ever removed `_time`.

## Decision

**Animation time in a node-tree document is a producer decision, not a
serializer decision.** `serialize_node` remains a pure walk that reports the
tree it is given; each producer is responsible for putting the tree into the
time its own document contract requires.

The three producers therefore differ deliberately:

- **`core/export.py`** publishes the animated document. `export_node` calls
  `node.clear_keyframe()` before serializing, so `manifest.json` carries `$t`
  expressions whatever the caller did to the node beforehand. Preserving `$t` is
  the producer's guarantee, not the caller's obligation.
- **`core/builder.py`** publishes `viewer.json` from a node it loaded and never
  keyframed, and is left unchanged.
- **`viewers/browser.py`** publishes a deliberately keyframed, numerically baked
  document. `manager/snapshot.py` keyframes on purpose because a snapshot is one
  instant, and baking through `solid_node.math` uses ADR-022's source-of-truth
  semantics.

To make that possible, `set_keyframe` gains an inverse. `AssemblyNode.
clear_keyframe()` drops `_time`, re-renders, and recurses into the rendered
children exactly as `set_keyframe` does; `AbstractBaseNode.clear_keyframe()` is
a no-op, mirroring the existing `set_keyframe` no-op. Re-rendering is what
restores the symbolic form, and ADR-023's driver-tagged idempotent render is
what makes it sound: an assembly sweeps only the operations it drove, so the
keyframed render's numeric operations are replaced by `$t` expressions while
static placement applied outside any assembly render survives, and nothing
accumulates across repeated freeze/release cycles.

Export leaves the node in symbolic time and does **not** restore a previous
keyframe. An assembly's children can be recreated objects on each render, so an
identity-keyed snapshot of `_time` is stale the moment `clear_keyframe`
re-renders; the only safe restore would reapply the root's value uniformly and
silently flatten a non-uniform nested keyframe. A caller wanting a numeric pose
back calls `set_keyframe` again.

Both keyframe methods share one guard on the rendered children: a non-list or
non-tuple `render()` result yields no children to recurse into. `serialize_node`
already tolerates exactly that shape, and without the guard `set_keyframe`
raised `TypeError: 'Cube' object is not iterable` — a latent defect that was
unreachable only because nothing keyframed such a node, and that the export path
would have made reachable.

## Alternatives considered

- **Serialize the symbolic expression regardless of keyframe state.** Rejected
  as impossible, not merely undesirable: by serialization time the expression
  has already been evaluated away inside user code. There is nothing to recover.
- **Keep `time` always symbolic and evaluate numerically at `as_number()`.** The
  deep fix — documents always animated, meshes always numeric, no mode at all.
  Rejected: it needs a Python evaluator for OpenSCAD expression strings, i.e. a
  fifth `$t` runtime, which is precisely the proliferation ADR-022 warns
  against, and it would replace `solid_node/math.py`'s dual-mode design
  wholesale. Recorded as the option a future architecture change would revisit.
- **Put the guarantee in `serialize_node`.** Rejected: it would force the
  web-snapshot producer symbolic too, handing its evaluation to the export
  widget's evaluator, which ADR-022 records as diverging on degree trig and `^`.
  That converts a correct static render into a possibly wrong one. It would also
  embed producer policy in the common walk, the same reason ADR-034 rejected a
  mode flag there.
- **Raise when the node is keyframed.** Loud rather than silent, and it avoids
  mutating the caller's node. Rejected because the correct document is
  unambiguous, so failing would make the obvious host code an error instead of
  making it work, and it leaves a host that reuses one node for building and
  publishing with no path.
- **Warn and continue.** Rejected: it leaves a spec-violating document on disk.
- **`set_keyframe(None)` as the reset.** Rejected: `time` would return `None`
  rather than falling through to `$t`, so every reader needs a sentinel branch,
  and it can arrive by accident from a numeric caller.
- **Give export an explicit frozen-instant mode.** Not adopted. A static
  *presentation* needs no frozen document — the widget's `?t=` and `?autoplay=0`
  render any instant of an animated one. If evidence for publishing a frozen
  document appears, it should arrive as an explicit parameter rather than as
  today's silent consequence of call ordering.

## Consequences

- An export carries its animation regardless of what the caller did to the node
  first. The `browser-engine` reproduction now writes `($t * 360)` from a
  keyframed node, identical to a fresh export.
- `export_node` mutates the node's time state, and says so. Callers must not
  rely on it leaving a keyframe in place; none in the framework do.
- `export_node` costs one extra render pass. It is small against the STL build
  and the serializer's own walk, and the develop/publish loop does not pay it.
- Keyframing is no longer a one-way door anywhere: `clear_keyframe` is a public
  part of the node API, available to tests, hosts, and future producers.
- A future document producer must state its own time contract. Neither the
  serializer nor the node tree will decide it by default.
- Assemblies nested inside a rigid `FusionNode` are reached by neither
  `set_keyframe` nor `clear_keyframe`, since a rigid fusion inherits the base
  no-op. The symmetry is preserved; the existing limitation is unchanged.
- `solid_node/core/builder.py` keeps no such guarantee. No spec promises one
  there and no reproduction exists, but a long-lived host that keyframes and
  then republishes would collapse `viewer.json` the same way. Left open
  deliberately, for lack of evidence.

## References

- `solid_node/node/assembly.py` — `clear_keyframe`, `_rendered_children`
- `solid_node/node/base.py` — the non-animated no-op
- `solid_node/core/export.py` — the export producer's guarantee
- `solid_node/core/serializer.py` — unchanged; still a pure walk
- `solid_node/viewers/browser.py`, `solid_node/manager/snapshot.py` — the
  deliberately keyframed producer
- `tests/test_keyframe_reversal.py`, `tests/test_export.py`
- `openspec/changes/archive/2026-08-22-preserve-symbolic-time-on-export/`
- ADR-008, ADR-020, ADR-022, ADR-023, ADR-034
