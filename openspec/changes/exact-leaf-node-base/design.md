## Context

Two adapters are exact. Their `shape()` and `as_scad()` bodies are identical
character for character:

```python
def shape(self):
    if self._up_to_date(self.brep_file):
        return cached_shape(self.brep_file)
    if self.model is not None:
        return shape_from_rendered(self.model)
    rendered = self.render()
    self.validate(rendered)
    return shape_from_rendered(rendered)
```

Everything that genuinely distinguishes the two lives elsewhere: the
`namespace` each declares, `CadQueryNode`'s `CheckCQEditor` metaclass, and
`Build123dNode.validate()`'s solid-shaped-result rule.

ADR-047 already decided that exact geometry has one shared OCCT currency
converted at the adapter boundary. The consequence for code layout — that
what follows the conversion is one implementation, not one per backend — was
not drawn at the time because there was no second copy to compare.

## Goals / Non-Goals

**Goals:**

- One home for the exact-adapter contract, so a correction to it lands once.
- Adapters reduced to their genuine differences, so a third OCCT backend is
  a `namespace` and whatever validation it needs.
- Provably no behavioural change.

**Non-Goals:**

- Changing any requirement, artifact layout, public name or import path.
- Making `ExactLeafNode` a supported extension point for projects. It is a
  framework-internal base; declaring it public API is a separate decision
  with its own compatibility obligation.
- Touching the faceted adapters. `Solid2Node`, `OpenScadNode` and `JScadNode`
  share nothing with these two beyond `LeafNode` itself.
- Moving `exact.py`'s free functions, which are already shared.

## Decisions

### `ExactLeafNode` lives in its own module, not in `leaf.py`

`leaf.py` today imports nothing heavier than `base`. Putting the exact base
there would make every adapter that imports `LeafNode` — including
`Solid2Node` — pull in `exact.py`, and through it cadquery, trimesh and OCP.
That is invisible in a default install, because `solid_node.node` imports
`CadQueryNode` eagerly anyway, but it would couple the faceted adapters to
the OCCT stack for no reason and would matter to any future lazy-import work.

`solid_node/node/exact_leaf.py` mirrors how `exact.py` is already separated
from the node tree.

### The base holds `exact`, `shape()` and `as_scad()`; adapters keep `namespace`

`namespace` stays on each adapter because it is exactly the per-backend fact.
`ExactLeafNode` declares none, so it inherits `LeafNode`'s `None` and imposes
no namespace of its own on a subclass.

`Build123dNode.validate()` stays an override calling `super()`, unchanged.
The base does not attempt a general "is this a solid" rule: CadQuery's
`Workplane` is legitimately not one until `shape_from_rendered` unwraps it,
so the check is genuinely build123d's, not the exact contract's.

### The metaclass is the one real hazard, and it is unchanged in kind

`CheckCQEditor.__new__` replaces the class's bases with `()` when
`cq_editor.__main__` is in `sys.modules`, so that a `CadQueryNode` subclass
loaded inside CQ-editor is a plain class. It drops whatever bases were
declared, so swapping `LeafNode` for `ExactLeafNode` is transparent to it —
the metaclass never names the base. This is worth stating because it is the
one place where the class hierarchy is rewritten at definition time, and a
reviewer should not have to rediscover that it is base-agnostic.

### Proof is the existing suite, not new tests

The change asserts that behaviour is unchanged, so the evidence that matters
is the tests written against the old structure passing against the new one:
565 passed and 40 subtests, including the whole of
`test_build123d_adapter.py`, `test_exact_geometry.py` and
`test_openscad_dependency.py`. A new test asserting "the adapters share a
base" would test the refactor rather than the contract, and would have to be
deleted the moment the structure changed again.

One class of test edit is expected and is not a weakening of that proof.
Three tests patch `write_stl`/`write_brep` where the calling code looks them
up, so moving `as_scad()` moves the patch target — from
`solid_node.node.adapters.cadquery` and `...adapters.build123d` to
`solid_node.node.exact_leaf`. The assertions themselves are untouched; only
the name of the place being patched follows the code. No other test may need
changing, and one that does is a finding rather than a fixup.

One test is worth adding, because it is about behaviour rather than
structure: both adapters must remain distinguishable by type, so that
`isinstance` checks and the backend-name lookup in `generate_stl` cannot
start confusing them through their new common ancestor.

## Risks / Trade-offs

- **A shared base invites unrelated behaviour to accumulate in it.** →
  Scope it in the docstring to the exact-adapter contract that
  `exact-geometry` specifies, and keep backend-specific rules in the
  adapters, as `Build123dNode.validate()` stays.
- **Inheritance makes each adapter less readable in isolation**: `as_scad()`
  is no longer visible where the backend is. → The duplication it replaces
  was the worse failure mode, and the base is one small module named for
  what it holds.
- **`generate_stl`'s backend-name lookup walks `__mro__` for adapter class
  names.** It looks for `Solid2Node`, `OpenScadNode` and `FusionNode`, none
  of which are in either exact adapter's MRO before or after. → Unchanged,
  and covered by the existing dependency tests; the added type test pins it.

## Migration Plan

None required. No public name, import path, artifact or behaviour changes, so
there is nothing for a project to migrate. Rollback is reverting the commit.

## Open Questions

Whether `ExactLeafNode` should eventually be documented as a supported base
for third-party backends. Deferred: that is a public-API commitment, and
nothing today needs it.
