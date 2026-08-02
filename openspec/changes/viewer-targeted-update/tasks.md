## 1. Geometry identity

- [ ] 1.1 Red: a node whose `model` path changes refetches; a node whose `mtime`
      changes refetches; a node with both unchanged makes no request.
- [ ] 1.2 Carry `mtime` on `ManifestNode` and record the `(model, mtime)` pair
      each `WidgetTree` node loaded.

## 2. Artifact-level update

- [ ] 2.1 Red: `artifactChanged(path)` replaces the geometry of every node
      referencing that path, requests no other model file, disposes what it
      replaces, and leaves camera, orbit target and animation clock untouched.
- [ ] 2.2 Red: an artifact path no node references is a no-op, not an error.
- [ ] 2.3 Implement `artifactChanged()` on the handle over the existing tree.

## 3. Document-level reconciliation

- [ ] 3.1 Red: `manifestChanged()` adds an introduced node, removes and disposes
      a dropped one, and keeps the same three.js objects for nodes both
      documents name.
- [ ] 3.2 Red: an operations-only or colour-only change updates the render with
      no model request.
- [ ] 3.3 Red: reconciliation matches children by name, so inserting a sibling
      at the front does not refetch its siblings.
- [ ] 3.4 Implement in-place reconciliation in `WidgetTree`, rebuilding a
      subtree it cannot match unambiguously rather than guessing.
- [ ] 3.5 Implement `manifestChanged()` on the handle, including the animation
      controls and cycle length following a document that changed them.

## 4. Failure containment

- [ ] 4.1 Red: a failed artifact fetch reports the failure, leaves the rendered
      model and camera in place, and leaves the handle usable for the next
      update.
- [ ] 4.2 Red: a failed or unparseable document fetch leaves the tree unchanged.
- [ ] 4.3 Implement fetch-then-mutate ordering so no node is removed before its
      replacement geometry has arrived.

## 5. Interface and consumers

- [ ] 5.1 Raise the declared API version to 2 in `version.ts` and
      `package.json`, and confirm the handle, the browser global and the
      package agree.
- [ ] 5.2 Switch the development shell to `manifestChanged()` in
      `viewerShell.ts`, leaving `reload()` and the reload channel protocol
      untouched.
- [ ] 5.3 Red: an e2e test in a real browser proving the canvas element's
      identity is preserved across an update, and that the camera does not
      move — the only assertion that distinguishes an in-place update from a
      reload.

## 6. Whole-system checks

- [ ] 6.1 Run the widget vitest suite, `npm run typecheck`, the full framework
      test suite, and `openspec validate --all --strict`.
- [ ] 6.2 Exercise `solid develop` on a multi-node project: edit one leaf and
      confirm the other meshes are not refetched and the camera does not move.
- [ ] 6.3 Confirm a static `solid export` still renders unchanged, since it
      mounts the same package and never calls a targeted update.
