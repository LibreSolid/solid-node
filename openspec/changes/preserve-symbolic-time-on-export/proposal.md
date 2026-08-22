## Why

The `export` capability already promises that a manifest carries "its operations
as raw unevaluated expression strings so `$t` animation is preserved verbatim"
(scenario: *Animated operations survive export*). Today the implementation keeps
that promise only by accident of call ordering. `solid export` happens to run
`load_node` → `export_node` and never keyframes, so the operations it serializes
still hold solid2 `$t` expressions. Any caller that keyframes the same node
first — which `Test.build_node()`, `solid render`'s node preparation, and any
embedding host that builds before publishing all do — silently publishes a baked
constant instead.

Reproduced in this worktree against `tests/test_export.py`'s animated `Spinner`
fixture:

```
fresh node                     ['r', '($t * 360)', [0, 0, 1]]
after node.set_keyframe(0.0)   ['r', '0.0',        [0, 0, 1]]
after node.set_keyframe(0.25)  ['r', '90.0',       [0, 0, 1]]
```

The result is a structurally valid, schema-conformant, completely static
document. Nothing warns, nothing fails, and the animation requirement becomes
unobservable downstream. Originating evidence: the `browser-engine` spike,
`openspec/changes/prove-solid-node-runs-in-browser/design.md` "Upstream findings
for the framework" item 2, and `evidence/rendering.md` "Upstream findings" item
1 — a browser host that builds and then publishes from the same node, the
obvious thing to write, silently loses every animation.

The root cause is that the collapse happens inside user `render()` code, not in
the serializer: once `AssemblyNode.time` is a float, `76.0 * self.time - 38.0`
evaluates to `-38.0` and the symbolic form no longer exists anywhere. The
serializer cannot recover it. `set_keyframe` is therefore a one-way door, and
the framework offers no way back to symbolic time.

## What Changes

- Add `clear_keyframe()` to the node API as the explicit inverse of
  `set_keyframe(time)`. It drops the fixed time, re-renders, and recurses into
  rendered children exactly as `set_keyframe` does, so an assembly subtree
  returns to symbolic `$t` and its driver-tagged operations are re-expressed as
  `$t` expressions. It is a no-op on non-assembly nodes, mirroring
  `AbstractBaseNode.set_keyframe`.
- Make `export_node` guarantee the animated document rather than depend on the
  caller: it clears any keyframe on the node before serializing, so
  `manifest.json` carries `$t` expressions regardless of what the caller did to
  the node beforehand.
- Document that `export_node` leaves the node in symbolic (build/viewer) time.
  A caller that still wants a numeric pose re-applies `set_keyframe` itself; a
  caller that wants a static *presentation* uses the widget's existing
  `?t=<0..1>&autoplay=0` option, which the export spec already provides.
- Harden the child-recursion guard shared by `set_keyframe` and
  `clear_keyframe` so a non-list/tuple `render()` result is tolerated instead of
  raising `TypeError`, matching the tolerance `serialize_node` already has for
  partial nodes.

Not breaking: no document schema, manifest version, operation wire form, or
existing keyframe behavior changes. `solid export`, the build/publish path
(`core/builder.py`), and the browser snapshot path (`viewers/browser.py`)
produce byte-identical output for every node they produce it for today.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `kinematics`: the *Normalized animation time* requirement gains the reverse
  operation — `set_keyframe` becomes reversible via `clear_keyframe()`, which
  restores symbolic `$t` through the same subtree recursion, and child recursion
  tolerates a non-list render result.
- `export`: the *Manifest contract* requirement's "raw unevaluated expression"
  promise becomes a guarantee owned by the export producer rather than a caller
  obligation — `export_node` publishes symbolic `$t` operations even when the
  node was keyframed before export, and its effect on the node's time state is
  stated.

## Impact

- `solid_node/node/assembly.py` — `AssemblyNode.clear_keyframe()`, and the
  non-list guard in `set_keyframe`.
- `solid_node/node/base.py` — `AbstractBaseNode.clear_keyframe()` no-op.
- `solid_node/core/export.py` — `export_node` clears the keyframe before
  serializing; docstring states the resulting time state.
- `tests/test_export.py` — red-first proof that a keyframed node still exports
  `$t`; `tests/test_meta.py` — red-first proof that `clear_keyframe` restores
  symbolic time through nested assemblies and non-linear `solid_node.math`
  expressions.
- `docs/animation.rst`, `docs/api-reference.rst` — document `clear_keyframe`.
- Unaffected: `solid_node/core/serializer.py` (stays a pure walker),
  `solid_node/core/builder.py`, `solid_node/viewers/browser.py` (its keyframed,
  numerically baked snapshot document is intentional and must not become
  symbolic — that would route static renders through the export widget's
  evaluator, which ADR-022 records as a divergence risk).
- No dependency, CLI surface, or manifest version change.
