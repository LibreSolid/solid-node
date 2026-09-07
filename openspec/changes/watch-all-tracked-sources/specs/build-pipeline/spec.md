## MODIFIED Requirements

### Requirement: Watch-rebuild loop

The system SHALL rebuild on change via a single-shot builder: it loads and
assembles the node, watches each file in `node.files` individually
(non-recursive, via watchdog), renders pending STLs, and exits when any
explicitly tracked source file reports a modification — regardless of filename
extension — so the develop loop can respawn it. Directory events are ignored.

When loading or assembly fails before the builder has a reliable tracked-source
set, the recovery watcher SHALL watch the project directory recursively and
SHALL accept modifications only to Python source outside `__pycache__`. Other
unclassified files SHALL remain filtered as recovery-watch noise.

#### Scenario: Edit triggers rebuild cycle

- **WHEN** a watched source file is saved during `solid develop`
- **THEN** the builder logs the change, exits, and is respawned to rebuild
  with the new source

#### Scenario: Tracked geometry-source edit triggers rebuild

- **WHEN** a successfully assembled node explicitly tracks a `.scad`, `.js`,
  `.stl`, or `.step` source and that file reports a modification
- **THEN** the builder exits its watch and the develop loop rebuilds from the
  changed geometry source without requiring a Python edit

#### Scenario: Broad recovery watch filters unrelated non-Python files

- **WHEN** a load or assembly failure starts the broad recursive recovery watch
  and an unclassified non-Python file reports a modification
- **THEN** the builder keeps waiting, while a Python source modification outside
  `__pycache__` resolves the watch
