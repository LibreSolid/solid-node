## 1. Regression proof

- [ ] 1.1 Add a methodless declarative assembly whose zero repeat renders,
  assembles, and serializes as an empty child list; capture the current `None`
  failure before implementation.
- [ ] 1.2 Prove omitting every declared child follows the same empty assembly
  path and explicit `render() -> []` remains valid.
- [ ] 1.3 Add zero-child fusion regressions requiring a clear validation
  failure before SCAD, BREP, or STL publication.
- [ ] 1.4 Run the saved zero-repeat CLI probe before and after the fix,
  requiring `zero_children.exitcode: 0` after implementation.

## 2. Empty internal composition

- [ ] 2.1 Make declarative `None` substitution depend on declared child
  metadata rather than nonempty realized children.
- [ ] 2.2 Compose zero internal children as an empty SCAD grouping while
  preserving the direct one-child and unioned multi-child paths.
- [ ] 2.3 Reject zero-child `FusionNode` results during validation with the
  fusion identity in the diagnostic.
- [ ] 2.4 Preserve state propagation, structure stability, repeat naming,
  invalid-count validation, and leaf `None` rejection.

## 3. Completion

- [ ] 3.1 Run focused declarative, lifecycle, serializer, node-model, and CLI
  coverage plus the saved probe.
- [ ] 3.2 Run the complete framework suite and strict OpenSpec validation.
- [ ] 3.3 Update the changelog and due-diligence records, mark F10 complete in
  `PROGRESS.md`, and identify F11 as next.
- [ ] 3.4 Synchronize and archive `support-empty-assemblies`; after final
  implementation evidence, record the ADR and architecture disposition for
  the empty assembly/fusion boundary.
- [ ] 3.5 Commit the completed implementation as the second F10 commit, then
  require a clean worktree and exactly two-commit ancestry from F09 content
  commit `2da43d2`.
