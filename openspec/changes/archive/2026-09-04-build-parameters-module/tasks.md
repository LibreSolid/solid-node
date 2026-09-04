## 1. Red first

- [x] 1.1 Add the parameter-module cases to `tests/test_node_lazy_exports.py`:
      the node export map carries no parameter name, `from solid_node.node
      import Length` raises `AttributeError`, and importing
      `solid_node.parameters` in a fresh interpreter pulls in no other
      `solid_node` module and no CAD backend. Confirm they fail.
- [x] 1.2 Point `tests/test_declarative_algebra.py` at
      `solid_node.parameters` for the kinds and `DimensionError`. Confirm it
      fails on the import.

## 2. Move the parameter layer

- [x] 2.1 Create `solid_node/parameters.py` with the module docstring stating
      what a build parameter is and how it differs from a driver, carrying
      `DimensionError`, `ParameterError`, the dimension helpers, `_RESERVED`,
      `Declaration`, `Expression`, `Formula`, `function_formula`, `Quantity`,
      the coercions, `Length`, `Angle`, `Count`, `Ratio`, `Scalar`, `Flag`,
      `evaluate` and `declared_parameters` with its cache, and an `__all__`.
- [x] 2.2 Reduce `solid_node/node/declarative.py` to the structure layer,
      importing `Declaration`, `Flag` and `evaluate` from the new module, and
      rewrite its docstring so it describes the two declarations it still
      owns and names the parameter module for the third.
- [x] 2.3 Drop the eight parameter entries from `solid_node/node/__init__.py`'s
      export map and say in its docstring where they went.
- [x] 2.4 Point `solid_node/math.py`'s deferred formula imports at
      `solid_node.parameters`.

## 3. Callers inside the framework

- [x] 3.1 Update the declarative test project and every test importing a kind
      or a parameter error.
- [x] 3.2 Run the full suite; it must pass with no import of a removed name.
- [x] 3.3 Run flake8 over the changed files and compare against the base.

## 4. Documentation

- [x] 4.1 `docs/declaring.rst`: every example imports the kinds from
      `solid_node.parameters`, and the page states which module answers for
      parameters, node classes and drivers.
- [x] 4.2 `docs/cli.rst`: the `--set` example's import line.
- [x] 4.3 `docs/api-reference.rst`: a Parameters section documenting the kinds,
      `Quantity` and `declared_parameters`.
- [x] 4.4 `docs/changelog.rst` and `HISTORY.rst`: record the breaking move.
- [x] 4.5 `docs/architecture.md`: the module map gains the parameter module and
      the one-way dependency.
- [x] 4.6 Build the docs and confirm no new warning or error.

## 5. Record

- [x] 5.1 Amend ADR-062 with the public-surface boundary, rather than opening
      a new ADR: where the vocabulary is imported from is part of that
      decision and was left unstated. Update the ADR index.
- [x] 5.2 Sync the three modified capabilities into `openspec/specs/`.
- [x] 5.3 Validate, archive the change, and commit the completed record.

## 6. Projects

- [x] 6.1 Migrate v8-engine, Inmoov-sim and Metamaquina2 on their
      `declarative-api` branches, one subagent per repository, each verifying
      its suite and its geometry fingerprints against the pre-change build.
      Done: Inmoov-sim `7b34603`, Metamaquina2 `a81f862`, v8-engine `6c5def2`
      (its root module left uncommitted, carrying a pilot edit it cannot be
      separated from).
