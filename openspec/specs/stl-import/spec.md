# stl-import Specification

## Purpose
TBD - created by archiving change stl-node. Update Purpose after archive.
## Requirements
### Requirement: STL source declaration and freshness

An `StlNode` subclass SHALL declare its part with a `stl_source` class
attribute naming an STL file, resolved relative to the directory of the
Python module defining the subclass. The resolved file SHALL be the
node's source file for freshness: its mtime drives artifact currency
exactly as a `JScadNode`'s `.js` does. In addition — and unlike the
other external-file adapters — the wrapper Python module itself SHALL
be part of the node's tracked file set, because it carries
geometry-affecting code (`adjust`, `body`); editing the wrapper SHALL
invalidate the node's artifacts. A subclass without `stl_source` SHALL
fail at construction with an error naming the class.

#### Scenario: The declared file resolves relative to the wrapper module

- **WHEN** an `StlNode` subclass in `parts/bracket.py` declares
  `stl_source = 'bracket.stl'`
- **THEN** the node reads `parts/bracket.stl`, and its build artifacts
  mirror that source location

#### Scenario: Editing the STL invalidates the artifact

- **WHEN** the declared `.stl` file is modified after a build
- **THEN** the node's artifact reports not-up-to-date and is
  regenerated on the next build

#### Scenario: Editing the wrapper module invalidates the artifact

- **WHEN** the wrapper `.py` defining the `StlNode` subclass is
  modified after a build — for example its `adjust` hook or `body`
  selection changes
- **THEN** the node's artifact reports not-up-to-date and is
  regenerated on the next build

#### Scenario: A missing declaration fails at construction

- **WHEN** an `StlNode` subclass declaring no `stl_source` is
  instantiated
- **THEN** an error is raised naming the class and the missing
  attribute

### Requirement: Materialized artifact

`StlNode.as_scad()` SHALL always materialize the node's own STL
artifact from the source file when that artifact is not up to date —
selected body extracted, `adjust` applied, written in binary form, and
mtime-stamped to the node's source mtime — and SHALL return the same
SCAD import of that artifact whether or not it was rebuilt. There is no
import-in-place path: downstream consumers (fusion, piece identity,
export, the viewer) SHALL see only the node's own artifact. Producing
the artifact SHALL NOT require OpenSCAD or any external tool.

#### Scenario: A current artifact is not rewritten

- **WHEN** `as_scad()` runs on an `StlNode` whose artifact is up to
  date
- **THEN** the source STL is not re-read for materialization, no
  artifact is written, and the returned SCAD output is unchanged

#### Scenario: The leaf builds without OpenSCAD

- **WHEN** a project whose leaves are all `StlNode`s is built with no
  `openscad` on the PATH and no fusion in the tree
- **THEN** every leaf's STL artifact is produced and the build succeeds

### Requirement: Watertight admission gate

`StlNode` SHALL fail fast when the selected mesh is not watertight: the
error names the source file (and selected body, when one is selected)
and the defect, and no artifact is written. A subclass MAY declare
`require_watertight = False` to admit such a mesh knowingly. The flag
governs admission only; it SHALL NOT alter geometry and SHALL NOT
participate in artifact identity. Admission is judged on the selected
body after extraction, and on the mesh the `adjust` hook returns when
one is defined, so a broken neighbour in a pack does not condemn a
sound part and a hook cannot smuggle a defect past the gate.

#### Scenario: A leaky mesh is rejected with a named defect

- **WHEN** an `StlNode` whose selected mesh is not watertight is built
  with the default admission policy
- **THEN** an error is raised naming the source file and the
  watertightness defect, and no artifact is written

#### Scenario: The escape hatch admits a known-dirty mesh

- **WHEN** the same subclass declares `require_watertight = False`
- **THEN** the build succeeds and the artifact is materialized from the
  mesh as-is

### Requirement: Multi-body packs and body selection

A multi-body STL file SHALL be treated as a pack of separate parts, one
of which an `StlNode` subclass selects with a `body` class attribute:
a 0-based index into the file's connected components ordered
deterministically by centroid, compared lexicographically on x, then y,
then z. When `body` is unset and the file contains more than one body,
construction of the artifact SHALL fail with an error stating the body
count and an inventory line per body — index, centroid, bounding box,
and volume — so a developer or agent learns the pack's contents from
the failure itself. A single-body file SHALL need no `body`
declaration. An out-of-range `body`, or a `body` declared for a
single-body file that is not index 0, SHALL fail with the same
inventory. Extraction SHALL preserve the file's coordinates: the
selected part stays where it sat in the pack, and bringing it to a
usable frame belongs to `adjust` or to placement operations.

#### Scenario: An unselected pack reports its inventory

- **WHEN** an `StlNode` wrapping a three-body STL declares no `body`
- **THEN** the error states that three bodies were found and lists each
  body's index, centroid, bounding box, and volume

#### Scenario: A body index selects one part

- **WHEN** two `StlNode` subclasses wrap the same pack with `body = 0`
  and `body = 2`
- **THEN** each materializes a distinct artifact containing only its
  selected component, in the coordinates it occupied in the file

#### Scenario: A single-body file needs no selection

- **WHEN** an `StlNode` wraps a single-body STL with no `body`
  declared
- **THEN** the whole mesh is the part and the build succeeds

#### Scenario: Selection ordering is deterministic

- **WHEN** the same multi-body file is built twice into fresh build
  directories
- **THEN** each `body` index selects the same component both times,
  because components are ordered by centroid (x, then y, then z)

### Requirement: The adjust normalization hook

An `StlNode` subclass MAY implement `adjust(self, mesh)`, receiving the
selected local-frame trimesh before the artifact is written and
returning the corrected mesh; scale fixes, recentering, and arbitrary
mesh transformations belong in this hook. The correction SHALL be baked
into the materialized artifact so fusion, tests, export, and the viewer
all see the same geometry. `StlNode` SHALL NOT offer scale, unit, or
recenter constructor parameters — normalization is code, not knobs.

#### Scenario: A hook correction reaches the artifact

- **WHEN** a subclass's `adjust` scales the mesh by 25.4 and the node
  is built
- **THEN** the materialized artifact holds the scaled geometry, and the
  node's mesh, volume, and any fusion consuming it reflect the
  corrected size

#### Scenario: A node without the hook imports verbatim

- **WHEN** a subclass defines no `adjust`
- **THEN** the artifact geometry equals the selected source geometry
  unchanged

### Requirement: Mesh-only faceted participation

`StlNode` SHALL be a faceted adapter: `exact` is false, it exposes no
`shape()`, and it participates in a `FusionNode` through the mesh
union path, making the enclosing fusion faceted. Mesh-only is settled
doctrine for this adapter: the framework SHALL NOT offer an exact or
faceted-B-rep STL import route, and this is a recorded non-goal rather
than an open question.

#### Scenario: The adapter is not exact

- **WHEN** `exact` is read on an `StlNode` instance
- **THEN** it reports false, and reading `shape()` raises

#### Scenario: A fusion over an imported STL takes the mesh path

- **WHEN** a `FusionNode` combines an `StlNode` with an exact leaf
- **THEN** the fusion reports not exact and its union is produced
  through the mesh path, per the exact-fusion composition rule

