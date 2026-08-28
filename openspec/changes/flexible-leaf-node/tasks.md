## 1. Dependency wiring (development)

- [ ] 1.1 Install molejo editable into the workspace venv from the molejo
      checkout; link the molejo npm package into the widget's
      `node_modules`. Record both as development-time steps; the
      committed dependency entries (`pyproject.toml`, widget
      `package.json`, license banner) name the published forms and are
      verified in section 7, which is gated on the pilot's publication
      decision.

## 2. FlexibleNode: a non-rigid leaf fed by ports

- [ ] 2.1 Red: a flexible leaf reports `rigid = False`; a `FusionNode`
      rendering one rejects it naming both nodes; `time` access still
      raises; reading `stl` raises as on any non-rigid node.
- [ ] 2.2 Red: ports declared on a flexible leaf are connectable by the
      parent assembly's `connect()`; an evaluation with an unbound port
      fails naming the node and the port; two instances of a no-arg
      flexible leaf class share one `uniq_id`.
- [ ] 2.3 Implement `FlexibleNode` in `solid_node/node/flexible.py`:
      non-rigid leaf semantics, declared-port parameter surface, the
      port/parameter name-set check (both directions, loud), and the
      snapshot evaluation entry point.
- [ ] 2.4 Rewrite the `leaf.py` `time` exception message to point at the
      flexible leaf instead of the roadmap.

## 3. MolejoNode: mesh path

- [ ] 3.1 Red: a `MolejoNode` whose `render()` returns a molejo `Shape`
      with parameters matching its ports assembles; a non-`Shape` render
      result is rejected by namespace validation; a parameter/port
      mismatch fails naming the node and both name sets.
- [ ] 3.2 Red: under a bound numeric snapshot, the node's mesh equals
      molejo's Python evaluation of the same spec and values (vertex
      count and analytic volume within tolerance); two different
      bindings give different meshes; repeated identical bindings give
      bitwise-identical meshes.
- [ ] 3.3 Implement `MolejoNode` in `solid_node/node/adapters/molejo.py`
      (namespace `molejo`, export from `solid_node/node/__init__.py`),
      with mesh evaluation through molejo.
- [ ] 3.4 Red: `as_scad()` writes a snapshot STL named with the binding
      hash and imports it; re-assembly at the same binding does not
      re-evaluate (mtime rule within one binding); a different binding
      produces a different artifact; the post-build sweep collects the
      unreferenced snapshot.
- [ ] 3.5 Implement the snapshot artifact path.
- [ ] 3.6 Red: a flexible leaf whose port is bound over animation time
      assembles without raising, contributes no geometry to the
      assembled SCAD, and writes no snapshot artifact; the published
      document still carries its spec and its symbolic `params`; an
      unbound port still fails loudly. Reproduction: v8-engine's valve
      spring, whose lift follows the crank through `$t`.
- [ ] 3.7 Implement the symbolic case in the camera path only, leaving
      `bound_values()` strict for the mesh and exact paths.

## 4. Exact path

- [ ] 4.1 Red: `MolejoNode.exact` is `True`; `shape()` at a bound
      snapshot returns a closed OCCT solid whose volume matches the
      mesh volume within molejo's fixture tolerance; an exact assertion
      between a spring instant and a rigid exact part decides exactly.
- [ ] 4.2 Implement `shape()` over `molejo.brep`, surfacing molejo's
      declared approximation tolerance.

## 5. Document schema (producer)

- [ ] 5.1 Red: serializing a tree containing a flexible leaf produces a
      `flexible` node (`tech`, embedded `spec`, `params` expression
      strings), declares `version: 3`, and lists every qualified id
      referenced by `params` in the `drivers` table; a keyframed/
      snapshot-bound tree still serializes expressions, not constants;
      a tree with no flexible leaf serializes byte-identical version-2
      output; serializing with an unbound flexible port fails naming
      the node and port.
- [ ] 5.2 Implement serializer and export support (inline spec, no
      `models/` entry, piece inventory unaffected); mirror the schema in
      the widget's `types.ts`.

## 6. Widget (consumer)

- [ ] 6.1 Red (vitest): the loader accepts version 2 and 3, renders a
      flexible node's geometry at driver defaults, refuses a `flexible`
      node with an unknown `tech` naming it, and refuses a version the
      package does not declare.
- [ ] 6.2 Red (vitest): driving a driver named in a `params` expression
      re-evaluates that node's geometry into the same buffers (no
      reallocation, unchanged vertex count); driving an unrelated driver
      does not re-evaluate it; `$t` in a `params` expression animates.
- [ ] 6.3 Implement: bundle molejo, evaluate `params` in the existing
      scope, per-node reused buffers, change-set gating by free-variable
      union; raise `solidNodeViewerApi` to 5 and add molejo to the
      license banner.
- [ ] 6.4 Extend the producer-generated parity fixture with a spring
      binding case (expression → molejo value, Python vs client) and run
      it against the shipped evaluator module.
- [ ] 6.5 Live headless-browser proof (as in stage 3c): a spring
      document served to a real browser animates its geometry when a
      driver moves, against a fresh temp bundle.

## 7. Packaging (gated on molejo publication — pilot decision)

- [ ] 7.1 With molejo published: a clean-venv install of solid-node
      resolves `molejo[brep]`; `npm ci && npm run build` in the widget
      resolves the npm package; packaging builds carry the bundled
      evaluator. Until publication, this section blocks and says so
      rather than being faked with local paths in committed metadata.

## 8. Docs, ADR, sync

- [ ] 8.1 Extract the ADR (non-rigid leaf, port-fed parameters, spec-in-
      document, snapshot artifacts, version rule); pointers from
      ADR-003/ADR-008 consequences; update `docs/architecture.md`.
- [ ] 8.2 Update `docs/leaf-nodes.rst`, `docs/animation.rst`,
      `docs/status-and-roadmap.rst` (roadmap item 3 done), and the ADR
      index.
- [ ] 8.3 Full framework suite green; v8-engine 33/33 unchanged; record
      evidence. Consumer-side validation (v8-engine valve spring,
      Metamaquina2 belt) is project work consuming this change and is
      recorded in molejo's `define-swept-shape-spec` section 8, not
      here.
