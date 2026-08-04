## 1. Project root discovery

- [ ] 1.1 Red: a test that the root is the directory of the nearest ancestor
      `pyproject.toml` carrying `[tool.solid-node]`, that a `pyproject.toml`
      without the table is walked past, and that the search failing raises an
      error naming the origin directory.
- [ ] 1.2 Red: a test that `source_closure` returns the identical set for a
      node whether the command runs from the project root or from a
      subdirectory — the wrong-answer case that `os.getcwd()` produces today.
- [ ] 1.3 Implement discovery in `solid_node/core/loader.py`, and anchor
      `sys.path`, the dotted module name, and `sources.source_closure` on the
      discovered root instead of `os.getcwd()`.

## 2. Node references

- [ ] 2.1 Red: a parse test over the three spellings — qualifier, path, hybrid
      — including a path containing a colon, a module name containing a dot,
      and a bare path to a file that does not exist.
- [ ] 2.2 Red: a test that `pkg.module:Sail` and `pkg/module.py:Sail` return
      the same class object and that `sys.modules` holds one entry for the file;
      assert on object identity, because two entries corrupt `source_closure`.
- [ ] 2.3 Red: a test that a bare path to a file with one node class loads it,
      and that a bare path to a file with several raises `AmbiguousNodeError`
      naming the candidates and directing the caller to name a class.
- [ ] 2.4 Red: a test that a reference to a non-`AbstractBaseNode` target, and
      one to a class defined outside the discovered root, are both rejected —
      `solid_node.node.leaf:Leaf` is the concrete case the qualifier makes
      expressible for the first time.
- [ ] 2.5 Implement one resolver in `loader.py` used by every caller.

## 3. Removing NODE

- [ ] 3.1 Red: a test that a file defining two node classes and setting `NODE`
      still raises `AmbiguousNodeError` when loaded by bare path — the marker
      decides nothing.
- [ ] 3.2 Delete `NODE_MARKER`, `_resolve_marker`, and the marker branch of
      `find_class`, keeping `AmbiguousNodeError` with its new message.
- [ ] 3.3 Migrate the framework's own fixtures off the marker:
      `tests/test_loader_node_marker.py`, `tests/loader_fixtures/*`,
      `tests/meta_project/*`, `tests/source_set_project/__init__.py`,
      `tests/test_meta.py`, `tests/test_manager_develop.py`. Replace
      `loader_fixtures/imported_entrypoint` with a manifest naming the
      implementation module directly, since the facade existed only to work
      around an unnameable entry point.

## 4. Test binding

- [ ] 4.1 Red: a test that a companion file with two `TestCase`s runs both,
      failing first against today's first-wins behaviour.
- [ ] 4.2 Red: a test that a `TestCase` declaring `node = <Class>` binds to
      that class, and that an undeclared one in a multi-node module fails the
      run with an error naming it and the candidates — never a silent skip.
- [ ] 4.3 Red: a test that an undeclared `TestCase` beside a single-node module
      still binds, so every existing project is unaffected.
- [ ] 4.4 Implement all-`TestCase` loading in `loader.load_test`, and per-case
      binding in `manager/test.py`, preserving the snake_case alias per case.
- [ ] 4.5 Implement reference-aware test selection: a qualifier runs that node
      and the cases bound to it; a file runs every node in it and every case in
      its companion; a companion test path still maps back to its node module.

## 5. CLI surface

- [ ] 5.1 Red: a test that every node-scoped command runs with no positional
      and resolves the manifest's model, and that a directory argument is an
      error naming the accepted spellings.
- [ ] 5.2 Red: a test that `solid build` exits with `MODEL_NOT_FOUND` for an
      unresolvable reference, replacing today's `os.path.isfile` guard.
- [ ] 5.3 Implement the optional positional in `cli.py`, remove the
      directory-to-`__init__.py` coercion, and update `build.py`, `develop.py`,
      `export.py`, `test.py`, `snapshot.py`.
- [ ] 5.4 Red: a test that `solid snapshot` holds the project build lock while
      preparing its node and has released it before the OpenSCAD render, and a
      test that `-o` defaults from the resolved node rather than
      `snapshot.png`.
- [ ] 5.5 Implement the lock and the output default in `snapshot.py`.

## 6. Scaffolding

- [ ] 6.1 Red: a test that `solid new snowman-3` produces
      `snowman_3/snowman_3/snowman_3.py` and a manifest declaring
      `model = "snowman_3.snowman_3:Snowman3"`, and that the scaffolded project
      builds and tests without further edits.
- [ ] 6.2 Implement `new.py` and replace the `root/__init__.py` template; update
      the printed next steps to `solid develop`.

## 7. Whole-system checks

- [ ] 7.1 Migrate `docs/examples/v8-engine` and update `docs/cli.rst` and the
      loader documentation.
- [ ] 7.2 Run the full framework test suite and `openspec validate --all
      --strict`.
- [ ] 7.3 Exercise a real project end to end: add a manifest to a copy of a
      packed project, then `solid build`, `solid test` on a file reference,
      and `solid snapshot <qualifier>` on a sub-assembly, from a subdirectory
      as well as from the root.
- [ ] 7.4 Confirm the recorded gaps are untouched: staleness is still keyed on
      `node.mtime`, the keyframe is still absent from the artifact key, and
      `pyproject.toml` is still unwatched. This cycle must not quietly change
      SPRINT-003's D6.
