## 1. Dependency upgrade, proved before anything is built on it

- [x] 1.1 Raise `cadquery` to `2.7.*` and add `build123d==0.10.*` in
      `pyproject.toml`; mirror in `requirements.txt` if it pins either
- [x] 1.2 Build an isolated virtualenv from this bench (not the shared
      workspace venv) and install the framework into it on the new pins
- [x] 1.3 Run the full existing suite on the new pins and record the result
      against the pre-upgrade baseline; any regression is a CadQuery-upgrade
      finding to resolve before the adapter is written
- [x] 1.4 Build the v8-engine example as the representative caller and confirm
      its CadQuery leaves still produce geometry

## 2. Exact-geometry conversion, red first

- [x] 2.1 Add a failing test that a build123d solid converts to the shape
      `exact.py` trades in, preserving volume through a BREP roundtrip
- [x] 2.2 Extend `shape_from_rendered` to unwrap a build123d result through
      `.wrapped`, with a comment on why a build123d node yields a CadQuery
      `Shape`
- [x] 2.3 Add a failing test that `BRepAlgoAPI_Fuse` over one CadQuery and one
      build123d shape yields a single solid, then confirm it passes unchanged

## 3. The adapter, red first

- [x] 3.1 Add a failing test that `Build123dNode` renders, emits SCAD
      importing its STL, and writes both the STL and the BREP with the source
      mtime
- [x] 3.2 Implement `solid_node/node/adapters/build123d.py` mirroring
      `CadQueryNode`: `namespace = 'build123d'`, `exact` true, `shape()`,
      `as_scad()` with the up-to-date guard on both artifacts
- [x] 3.3 Add failing tests for result acceptance — a `Part`, a `Solid`, a
      `Compound`, and a `BuildPart` whose `.part` is taken — then implement
      the extraction
- [x] 3.4 Add a failing test that a sketch or curve result raises naming the
      node and the offending type, then implement the rejection
- [x] 3.5 Export `Build123dNode` from `solid_node/node/__init__.py`
- [x] 3.6 Add a failing test that `as_scad()` on an up-to-date artifact
      re-exports nothing and returns the same SCAD

## 4. Exactness and composition

- [x] 4.1 Add a failing test that `exact` is true on a `Build123dNode` without
      rendering it, and that `shape()` returns local-frame geometry with no
      operation applied
- [x] 4.2 Add a failing test that a `FusionNode` over a `CadQueryNode` and a
      `Build123dNode` reports `exact` true and fuses to one solid
- [x] 4.3 Confirm a `Build123dNode` project builds with no `openscad` on the
      PATH, extending the existing conditional-dependency test

## 5. Documentation

- [x] 5.1 Add the `Build123dNode` section to `docs/leaf-nodes.rst` with the
      same box-with-hole model the other four backends show, presented as a
      fifth backend
- [x] 5.2 Add `Build123dNode` to `docs/api-reference.rst` and the backend list
      in `README.rst`
- [x] 5.3 Note the required reinstall for the `cadquery-ocp` change in
      `HISTORY.rst`

## 6. Completion

- [x] 6.1 Run the full suite green on the new pins
- [x] 6.2 Assess whether the multi-backend exact-currency choice warrants an
      ADR beside ADR-004 and ADR-044, and write it if so
- [x] 6.3 Sync baseline specs, archive the change, and commit the completed
      implementation record
