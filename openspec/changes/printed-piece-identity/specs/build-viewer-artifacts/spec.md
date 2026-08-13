## ADDED Requirements

### Requirement: Published build snapshots carry the piece inventory

The published `viewer.json` SHALL include the printed-piece inventory defined by
the `printed-pieces` capability, with each piece's `models` references using the
same build-root-relative model paths the tree uses. The snapshot SHALL remain
non-portable: computing the inventory SHALL NOT create a `models/` directory or
copy any mesh.

The inventory SHALL be derived from the same current artifacts the snapshot
already references, and SHALL be published within the existing atomic write, so
every model path and piece a consumer reads is backed by a file already present
and complete. A piece whose facts cannot be derived SHALL NOT prevent
publication of the tree.

#### Scenario: A complete build publishes its pieces

- **WHEN** `solid build <project>` completes successfully
- **THEN** its `viewer.json` contains a `pieces` list beside `root`, every rigid
  node carries a `piece` id present in that list, and every model the inventory
  names resolves relative to that same published build directory

#### Scenario: Publication is still not an export

- **WHEN** a complete build is published
- **THEN** the inventory names ordinary build-root-relative model files, creates
  no export-style `models/` tree, and copies no mesh

#### Scenario: Artifact sweeping is unaffected

- **WHEN** a build publishes a snapshot and sweeps artifacts it no longer
  references
- **THEN** every model named by the inventory survives the sweep
