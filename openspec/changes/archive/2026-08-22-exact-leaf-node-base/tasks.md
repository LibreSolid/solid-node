## 1. Establish the pre-refactor baseline

- [x] 1.1 Record the exact byte-identity of `shape()` and `as_scad()` across
      the two adapters, so the claim that nothing behavioural moves is
      checkable rather than asserted
- [x] 1.2 Run the full suite on the current structure and record the counts
      this refactor must reproduce exactly

## 2. Extract the base

- [x] 2.1 Add `solid_node/node/exact_leaf.py` with `ExactLeafNode`, holding
      `exact`, `shape()` and `as_scad()`, declaring no `namespace`, and
      documenting that it holds the `exact-geometry` adapter contract
- [x] 2.2 Reduce `CadQueryNode` to its `namespace` and `CheckCQEditor`
      metaclass, based on `ExactLeafNode`
- [x] 2.3 Reduce `Build123dNode` to its `namespace` and its solid-shaped
      result `validate()`, based on `ExactLeafNode`

## 3. Prove nothing moved

- [x] 3.1 Run the full suite unmodified and require the same counts as 1.2
- [x] 3.2 Add a test that the two adapters stay distinct types and that
      neither is an instance of the other, so a shared ancestor cannot make
      an `isinstance` check or the `generate_stl` backend lookup confuse them
- [x] 3.3 Confirm a `CadQueryNode` subclass still defines correctly with the
      CQ-editor metaclass active, now that the base it drops is
      `ExactLeafNode`
- [x] 3.4 Rebuild the v8-engine example as the representative CadQuery caller

## 4. Records

- [x] 4.1 Add `ExactLeafNode` to `docs/api-reference.rst` beside `LeafNode`
- [x] 4.2 Amend ADR-047 to record that the shared currency's contract has one
      implementation, and update `docs/architecture.md` to match
- [x] 4.3 Note the refactor in `HISTORY.rst` as an internal change with no
      project-visible effect
- [x] 4.4 Archive the change and commit the completed implementation record
