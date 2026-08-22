## Context

`AssemblyNode.time` (ADR-008) is dual-valued: solid2's symbolic `$t`
(`get_animation_time()`) in the build/viewer path, and a plain float once
`set_keyframe(time)` has been called. ADR-022 makes that duality load-bearing —
`solid_node/math.py` computes numerically when `time` is a float and emits
deferred OpenSCAD expression strings when it is symbolic, and every `$t`
evaluator downstream must reproduce the same semantics.

An operation records whatever value user `render()` code computed:

```python
# solid_node/node/operations.py
@property
def serialized(self):
    return ['r', str(self.angle), self.axis]
```

So the symbolic form is destroyed at *render* time, not at serialization time.
Once `time` is `0.25`, `self.time * 360` has already become `90.0` and no
information remains for `serialize_node` to recover. Three producers call
`serialize_node`:

| producer | keyframes first? | document today |
| --- | --- | --- |
| `core/builder.py` (build/publish `viewer.json`) | no | symbolic `$t` |
| `core/export.py` (`export_node` → `manifest.json`) | no, by ordering only | symbolic `$t` **unless the caller keyframed** |
| `viewers/browser.py` (web snapshot) | yes, deliberately (`manager/snapshot.py::_load_and_prepare_node`) | numerically baked, intentionally |

Only the `export` spec promises raw unevaluated expressions. The build and
snapshot specs make no such promise, and the snapshot's baked document is
*correct by design*: it renders one instant, baked through `math.py`, the
ADR-022 source of truth.

`set_keyframe` is currently a one-way door — `AssemblyNode.time` reads `_time`
if present and falls back to `$t` only via `AttributeError`, and nothing ever
removes `_time`.

## Goals / Non-Goals

**Goals:**

- An exported `manifest.json` carries `$t` expressions regardless of what the
  caller did to the node before calling `export_node`, upholding the already
  ratified *Animated operations survive export* scenario unconditionally.
- Give the node API an explicit, documented way back from keyframed time to
  symbolic time, so "keyframe then publish" stops being an unrecoverable state.
- Leave the build/publish and web-snapshot document producers byte-identical.

**Non-Goals:**

- Changing the manifest schema, version, operation wire form, or any evaluator.
- Fixing or re-characterising ADR-022's recorded widget-evaluator divergence.
- Adding a deliberate "publish a frozen instant" export mode. The export spec
  already gives a static *presentation* through the widget's
  `?t=<0..1>&autoplay=0`, so freezing at publish time is not needed to get a
  static picture.
- Making the build/publish producer (`core/builder.py`) enforce the same
  guarantee. No spec promises it there and no evidence shows it broken; adding a
  full extra render pass to every `solid develop` republish would cost more than
  it demonstrably buys.

## Decisions

### Decision 1 — Restore symbolic time by clearing the keyframe and re-rendering

`clear_keyframe()` on `AssemblyNode` deletes `_time`, re-renders, and recurses
into the rendered children — the exact mirror of `set_keyframe`. The existing
`_idempotent_render` wrapper makes this sound: before each re-render an assembly
sweeps the operations it drove (`op._driver is self`), so the numeric operations
from the keyframed render are discarded and replaced by symbolic ones, while
static placement applied outside any assembly render survives untouched.
`AbstractBaseNode.clear_keyframe()` is a no-op, mirroring the existing
`set_keyframe` no-op for non-animated nodes.

Verified in this worktree with a monkeypatched prototype, on the framework's own
fixtures:

```
nested keyframed : [['t', ['5.0', '0', '0']]]
nested cleared   : [['t', ['(10 * $t)', '0', '0']]]   inner.time = $t
conrod keyframed : [['t', ['2','0','0']], ['r', '8.450002159087596', [0,0,1]]]
conrod cleared   : [['t', ['2','0','0']], ['r', 'asin((0.25 * sin((360.0 * $t))))', ...]]
conrod fresh     : [['t', ['2','0','0']], ['r', 'asin((0.25 * sin((360.0 * $t))))', ...]]
```

The cleared conrod is byte-identical to a never-keyframed render, including the
non-linear `solid_node.math` symbolic path, and the static `translate([2,0,0])`
is neither swept nor duplicated. A `set_keyframe → clear_keyframe →
set_keyframe → clear_keyframe` round trip produced exactly one operation, so
nothing accumulates.

*Alternatives considered.*

- **`set_keyframe(None)` as the reset.** Fewer names, but `time` would return
  `None` rather than falling through to `$t`, so the property needs a sentinel
  branch and every reader must know `None` means symbolic. An explicit verb is
  clearer and cannot be passed by accident from a numeric caller.
- **Serialize the symbolic expression regardless of keyframe state.** Rejected
  as impossible without a re-render: by serialization time the expression has
  already been evaluated away inside user code. Nothing to recover.
- **Keep `time` always symbolic and evaluate numerically at `as_number()`.**
  This is the deep fix — documents would always be animated and meshes always
  numeric, with no mode at all. It requires a Python evaluator for OpenSCAD
  expression strings, i.e. a *fifth* `$t` runtime, which is precisely the
  proliferation ADR-022 warns about, and it would replace `math.py`'s dual-mode
  design wholesale. Far beyond this defect; recorded here as the option a future
  architecture change would revisit.

### Decision 2 — The export producer owns the guarantee; the serializer does not

`export_node` calls `node.clear_keyframe()` before `serialize_node`.

*Alternatives considered.*

- **Put it in `serialize_node`.** Rejected: it would also force the web-snapshot
  producer symbolic. That producer keyframes on purpose and bakes the pose
  through `math.py`; making its document symbolic would hand evaluation to the
  export widget's evaluator, which ADR-022 records as diverging on degree trig
  and `^`. That converts a correct static render into a possible wrong one, for
  no benefit. Keeping `serialize_node` a pure walker also preserves its stated
  single-source-of-truth role.
- **Raise when the node is keyframed.** Loud rather than silent, and it avoids
  mutating the caller's node. Rejected as the primary behaviour because the
  fix is unambiguous and mechanical — there is exactly one document the export
  spec permits — so failing makes the obvious host code an error instead of
  making it work. It also gives no path for a host that legitimately reuses one
  node for building and publishing.
- **Warn and continue.** Rejected: it leaves a spec-violating document on disk.

### Decision 3 — Export leaves the node in symbolic time; it does not restore the caller's keyframe

Restoring would require snapshotting and reapplying per-node `_time` across a
tree whose children may be *recreated objects* on each render, so an
identity-keyed snapshot is stale the moment `clear_keyframe` re-renders. The
only safe restore is "re-apply the root's value uniformly", which would silently
flatten any non-uniform nested keyframe a host had set. Leaving the node in
symbolic time is honest, cheap, and matches what a freshly loaded node looks
like; the docstring and spec state it, and a caller that wants a pose back calls
`set_keyframe` again — one line, already proven to work after a clear.

### Decision 4 — Tolerate a non-list `render()` result during recursion

The prototype crashed on `tests/test_export.py::NonListNonRigidAssembly` with
`TypeError: 'Cube' object is not iterable`. `serialize_node` deliberately
tolerates a non-list/tuple non-rigid render ("keeps the existing partial-node
representation for lifecycle validation to handle"), but
`AssemblyNode.set_keyframe` does `for child in rendered or ()` with no type
guard. This is a **pre-existing latent defect in `set_keyframe`**, not something
the new method introduces — it is simply unreachable today because nothing
keyframes such a node. `clear_keyframe` must carry the guard, and `set_keyframe`
gets the same one so the pair stays symmetric and the export path cannot be
crashed by a partial node.

## Risks / Trade-offs

- **[An extra full render pass per export]** → `serialize_node` already renders
  the whole tree, and `export_node` already builds every STL under the project
  lock, so one more pure-Python render is small against the existing cost. It is
  paid only by `export_node`, not by the develop/publish loop.
- **[A host relying on export leaving the node keyframed]** → No such caller
  exists in the framework; `solid export` loads a fresh node and exits. Stated
  explicitly in the docstring and the export spec so the behaviour is contract,
  not accident.
- **[A host that deliberately wanted a baked, static document]** → It loses that
  ability through `export_node`. The intended way to present one instant is the
  widget's `?t=&autoplay=0`, already ratified in the export spec. If real
  evidence for a frozen-publish mode appears, it should arrive as its own change
  with an explicit parameter rather than as today's silent side effect of call
  ordering.
- **[`clear_keyframe` on a subtree whose children are recreated per render]** →
  Handled the same way `set_keyframe` already handles it: recurse into the
  freshly rendered children, never into a stale saved list.
- **[Assemblies nested inside a rigid `FusionNode`]** → `set_keyframe` does not
  reach them (a rigid fusion's `set_keyframe` is the base no-op), so
  `clear_keyframe` will not either. Symmetry preserved; this is existing
  behaviour and out of scope.

## Migration Plan

None required. No schema, version, CLI, or dependency change; no persisted
state. Existing exports remain valid and existing callers keep working. Rollback
is reverting the commit.

## Open Questions

1. Should `set_keyframe`'s non-list-render guard (Decision 4) be part of this
   change, or split into its own bug-fix cycle? It is a real latent defect with
   a distinct cause; folding it in keeps the two methods symmetric and is a
   two-line change, but it is not strictly required to fix the export defect.
2. Should the build/publish producer (`core/builder.py`) receive the same
   guarantee? No spec promises it and no reproduction exists, but a long-lived
   embedding host that keyframes and then triggers a republish would collapse
   `viewer.json` the same way. Deferred here for lack of evidence.
