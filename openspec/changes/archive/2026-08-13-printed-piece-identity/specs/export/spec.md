## ADDED Requirements

### Requirement: Export manifests carry the piece inventory

The exported `manifest.json` SHALL include the printed-piece inventory defined
by the `printed-pieces` capability, with each piece's `models` references rooted
beneath the export's `models/` directory so they resolve to the copied artifacts
inside the export. The export SHALL therefore remain self-contained: a consumer
reading the inventory from a static host resolves every piece without a
solid-node process and without any path outside the export directory.

Model deduplication is unchanged — one copied STL per distinct rigid artifact —
and the inventory SHALL be reported on top of it, so several deduplicated
artifacts with identical content still resolve to a single piece.

#### Scenario: An export publishes its pieces

- **WHEN** a node is exported
- **THEN** `manifest.json` contains a `pieces` list beside `root`, every rigid
  node carries a `piece` id present in that list, and every model the inventory
  names is a copied artifact beneath `models/`

#### Scenario: Distinct artifacts with identical content are one piece

- **WHEN** an export copies two distinct rigid artifacts whose STL content is
  identical
- **THEN** `models/` still contains both copied files and the inventory reports
  one piece whose `models` names both, with a count covering every instance of
  either
