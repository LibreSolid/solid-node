# Motion layer: execution index

Campaign: the declarative mechanics layer of solid-node, three stacked
OpenSpec cycles, 2026-09-09. Design authority: the pilot; adversarial
review of each proposal and implementation stood in for ratification.

- Worktree: `solid-node/WTs/motion`, branch `motion`, base main cb474e3.
- Integrated into main by fast-forward at 09b7c7a (2026-09-09).

| Cycle | Planning commit | Completion commit | ADR | Archived change |
|---|---|---|---|---|
| `motion-package` | fddc8a7 | 11401bb | 087 | `openspec/changes/archive/2026-09-09-motion-package/` |
| `joints` | 86498f0 | 4952231 | 088 | `openspec/changes/archive/2026-09-09-joints/` |
| `couplings` | 5f49f53 | 5e0e5a6 | 089 | `openspec/changes/archive/2026-09-09-couplings/` |
| findings | | 09b7c7a | | `workflow/warts.md`, section 2026-09-09 |

Baseline capabilities after the campaign: `ports` (moved and extended),
`joints` (new), `couplings` (new); deltas to `declarative-nodes`,
`kinematics`, `simulation`, `cli-startup-cost`, `user-documentation`.

Evidence: framework suite 1788 passed after cycle 1, 1851 after cycle 2,
1928 passed / 16 skipped after cycle 3 (`tests/test_motion_package.py`,
`tests/test_joints.py`, `tests/test_couplings.py` and the fixtures
`tests/joint_project/`, `tests/coupling_project/`). Project validation:
3DPrintedClocks wall clock 01 at 5bd67db (poses bit-identical at four
instants, faceted 7/7, clock 02 9/9, eleven models realize) and Thor at
4e6f134 (poses bit-identical at seven poses before the `art3` correction
of db0e0a4; 31 of 33, the two failures pre-existing on main).

Open after the campaign (see `warts.md`): a joint anchored at a
design-placed part's own origin; a relation chain across class bodies; a
node's own derived coordinate read in its own `simulate()`; MuJoCo and
Modelica emission, deferred to the pilot's discussion
(`workflow/docs/mujoco-viability.md` stays in `docs/` for it).
