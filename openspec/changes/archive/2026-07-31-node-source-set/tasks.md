## 1. Fixtures the suite has never had

- [x] 1.1 Add a CadQuery leaf fixture — the suite contains none, which is why this defect survived
- [x] 1.2 Add a fixture project whose node imports a project module defining no node, mirroring `v8-engine`'s `kinematics.py`

## 2. Prove the defects red

- [x] 2.1 Test that editing an imported project module regenerates the dependent node's artifact; observe it fail on the current code
- [x] 2.2 Test that a module outside the project tree is not tracked; observe the result
- [x] 2.3 Test that an up-to-date rigid optimizing leaf is assembled without calling `render()`; observe it fail
- [x] 2.4 Test that `CadQueryNode.as_scad` performs no export when the artifact is current; observe it fail
- [x] 2.5 Test that `JScadNode.as_scad` spawns no subprocess when the artifact is current; observe it fail
- [x] 2.6 Confirm each test fails for the intended reason, not an incidental one

## 3. Correct the source set

- [x] 3.1 Build the transitive project-local import closure for a module: AST imports, resolved through `sys.modules`, filtered to the project tree (D1)
- [x] 3.2 Follow named modules only, never the package `__init__` chain, and prove with a test that one node's edit does not invalidate an unrelated node in a package whose `__init__` imports both (D2)
- [x] 3.3 Seed `node.files` from that closure; confirm `internal.py`'s recursive union and `node.mtime` still hold
- [x] 3.4 Verify `Builder`'s watch loop now watches imported modules, since it consumes the same set

## 4. Skip work that is already done

- [x] 4.1 Give `LeafNode` an up-to-date assemble path that imports the artifact and applies queued operations without rendering (D3)
- [x] 4.2 Leave `self.model` unset on that path and compute it lazily if anything asks
- [x] 4.3 Guard the export in `CadQueryNode.as_scad` and the subprocess in `JScadNode.as_scad` (D4)
- [x] 4.4 Confirm internal nodes still walk the tree and that a non-optimizing rigid node still behaves correctly

## 5. Prove it did not buy speed with staleness

- [x] 5.1 Turn every test from group 2 green
- [x] 5.2 Mutation check: a guard that never produces the artifact must fail the tests, proving they are not vacuous
- [x] 5.3 Build `v8-engine` before and after and compare the produced artifact set and geometry; account for `crank_throw`'s known pre-existing non-determinism rather than asserting byte equality
- [x] 5.4 Edit `kinematics.py` and confirm the dependent nodes rebuild with the new geometry — the correctness gate this change exists to protect
- [x] 5.5 Run the full framework suite
- [x] 5.6 Report no-op, cold, single-leaf-edit, and `test_*.py`-edit build times against the recorded baseline

## 6. Records

- [x] 6.1 Extract an ADR for the source-set obligation and the up-to-date leaf path, and update the ADR index
- [x] 6.2 Update `docs/architecture.md` where the build pipeline's caching is described
- [x] 6.3 Add the fix to `HISTORY.rst` under Unreleased
- [x] 6.4 Sync baseline specs and archive the change
