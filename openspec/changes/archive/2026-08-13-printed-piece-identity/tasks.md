## 1. Red-first proof of the finding

- [x] 1.1 Add a fixture project whose tree contains one part placed several
      times plus two differently-named classes that build identical geometry
      (the gearbox shape, minimised), so the under-merge is reproducible in the
      framework's own tests
- [x] 1.2 Write failing tests asserting a published `viewer.json` carries a
      `pieces` list, a `piece` id on every rigid node, one piece for the
      repeated part with the right count, and one merged piece for the two
      identical classes naming both sources

## 2. Piece identification

- [x] 2.1 Create `solid_node/core/pieces.py` with the content fingerprint of a
      built artifact (sha256 of file bytes, truncated), cached per
      `(path, mtime)`
- [x] 2.2 Derive per-piece geometry facts — `size`, `volume`, `watertight` —
      from the shared base-mesh cache in `solid_node/node/base.py`, read in the
      artifact's own frame, tolerating an unloadable or unclosed mesh instead of
      raising
- [x] 2.3 Implement the inventory accumulator: register a rigid node with its
      resolved model path, return its piece id, and emit entries with `id`,
      `name`, `sources`, `models`, `count`, `size`, `volume`, `watertight` in
      first-encounter order with sorted contributor lists
- [x] 2.4 Unit-test the accumulator directly: merging across classes, counting
      repeated placements, deterministic ordering, stable ids independent of
      artifact path and walk order

## 3. Publication

- [x] 3.1 Add the optional `piece_id(node, model)` mapper to
      `serialize_node`, emitting `piece` on rigid nodes and defaulting to no
      piece so existing callers are unchanged
- [x] 3.2 Publish `pieces` from the builder into `viewer.json` inside the
      existing atomic write, with build-root-relative model references
- [x] 3.3 Publish `pieces` from `export_node` into `manifest.json` with
      `models/`-relative references, on top of the existing artifact
      deduplication
- [x] 3.4 Publish `pieces` from the browser snapshot renderer so all three
      producers agree
- [x] 3.5 Confirm artifact sweeping still preserves every model the inventory
      names, and that an unchanged rebuild republishes a byte-identical document

## 4. Evidence

- [x] 4.1 Run the framework test suite
- [x] 4.2 Rebuild `v8-engine` and confirm 24 pieces covering 119 placements with
      correct counts and plausible extents
- [x] 4.3 Rebuild `gearbox` and confirm 18 pieces, with the six bushing classes
      and the two housing walls each reported as one piece naming every
      contributing source
- [x] 4.4 Confirm export and build documents agree on piece ids and counts for
      the same model

## 5. Records

- [x] 5.1 Extract an ADR for content-derived piece identity alongside
      parameter-hashed artifact keys, and update the ADR index
- [x] 5.2 Update `docs/architecture.md` if the published-document synthesis
      changed
- [x] 5.3 Sync baseline specs and archive the change
