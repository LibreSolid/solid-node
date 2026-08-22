## Why

Adding `Build123dNode` left `shape()` and `as_scad()` duplicated verbatim
between it and `CadQueryNode`. Both bodies encode the same contract —
reload from a current BREP or convert the render result, then export STL and
BREP behind the up-to-date guard and return the SCAD that imports the STL —
and that contract is now the framework's, stated in `exact-geometry` and
ADR-047, not either backend's.

Duplication of a specified contract rots in one direction: a future
correction lands in one copy. A third OCCT front end would make it three.
The shared behaviour should have one home before that happens, while there
are exactly two copies and they are provably identical.

## What Changes

- Add `ExactLeafNode`, a `LeafNode` subclass holding the exact-adapter
  contract: `exact`, `shape()`, and the artifact-producing `as_scad()`.
- Reduce `CadQueryNode` and `Build123dNode` to what actually differs — their
  `namespace`, the CQ-editor metaclass, and build123d's solid-shaped-result
  validation.
- No behavioural change. Every requirement in `node-model`, `exact-geometry`
  and `openscad-dependency` describes the same observable system before and
  after, and the existing tests are the proof.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `node-model`: adds one requirement, that leaf adapters remain distinct
  types and that sharing an implementation base does not make one an
  instance of another. This is the single behavioural invariant a common
  ancestor puts at risk, and it constrains how adapter behaviour may be
  factored without mandating any factoring.

No existing requirement changes. `node-model` continues to require that each
adapter implement `as_scad()`, which an adapter inheriting it does.

## Impact

- **New code**: `solid_node/node/exact_leaf.py`.
- **Changed code**: `solid_node/node/adapters/cadquery.py` and
  `solid_node/node/adapters/build123d.py` lose their duplicated bodies.
- **Docs**: `docs/api-reference.rst` gains the base class beside `LeafNode`;
  `docs/architecture.md` and ADR-047 record where the exact contract lives.
- **Risk**: `CadQueryNode`'s `CheckCQEditor` metaclass replaces the class's
  bases with an empty tuple when running under CQ-editor, so it must keep
  working when the base being dropped is `ExactLeafNode` rather than
  `LeafNode`.
- **Not changed**: the public names a project imports. `CadQueryNode` and
  `Build123dNode` keep their identity, behaviour and import path.
