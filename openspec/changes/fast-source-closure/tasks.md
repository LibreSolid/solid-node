## 1. Baseline and red tests

- [ ] 1.1 Record the baseline on a large real project: profile `load_node` and
      capture the `realpath`/`lstat` call counts attributable to `_package_of`.
- [ ] 1.2 Red: loading the same fixture project in an interpreter that has
      imported a substantially larger set of unrelated modules does not
      multiply the path-resolution calls made while building source closures
      (count by patching `os.path.realpath`).
- [ ] 1.3 Red: constructing many nodes from one project file does not rescan
      the loaded module set per node.
- [ ] 1.4 Equality oracle: for every loaded module file, the new lookup returns
      exactly what a linear rescan of `sys.modules` returns — including
      first-wins when two modules share a real path.
- [ ] 1.5 Late-import test: look up a project file, import another project
      module, then look up the new module's file; it must resolve rather than
      returning `None`.
- [ ] 1.6 Miss test: a path no loaded module was imported from returns `None`
      and raises nothing.

## 2. Implementation

- [ ] 2.1 Replace the linear scan in `solid_node/node/sources.py::_package_of`
      with a module-level index built from `sys.modules`, preserving
      first-wins via `setdefault`.
- [ ] 2.2 Add the staleness stamp so a module imported after the index was
      built is still resolved; measure the exact-key-set stamp against the
      length-plus-miss-retry option and record which was chosen and why.
- [ ] 2.3 Follow the module-level cache shape already used by `_import_cache`
      in the same file; no `functools.lru_cache`.
- [ ] 2.4 Leave `_parse_project_imports`, its `(path, mtime)` memoisation, the
      AST scan, and the project-local test untouched.

## 3. Verification

- [ ] 3.1 Turn every red test from group 1 green.
- [ ] 3.2 Full-tree equality on a large real project: load and assemble under
      the new lookup and under the old one, and assert every node carries the
      same source closure, `mtime_ns`, and artifact path.
- [ ] 3.3 Prove currency is untouched: build a project whose artifacts are all
      current and confirm nothing re-renders and the published document is
      unchanged.
- [ ] 3.4 Run the full framework suite.
- [ ] 3.5 Re-measure 1.1 and record before/after in the change.
