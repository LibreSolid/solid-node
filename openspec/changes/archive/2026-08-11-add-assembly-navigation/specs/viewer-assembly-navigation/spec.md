## ADDED Requirements

### Requirement: A viewer host can inspect the rendered assembly
The viewer handle SHALL expose a serializable assembly snapshot of the current
published tree. Every node in that snapshot SHALL include its name, a
root-relative path of sibling names, effective inherited colour or null,
whether it has model geometry, and ordered children. The snapshot SHALL expose
no mutable document, Three.js object, or project filesystem reference.

#### Scenario: A host reads a nested coloured assembly
- **WHEN** a host reads the assembly snapshot of a model with a coloured
  ancestor and an uncoloured descendant
- **THEN** the descendant reports its root-relative path and the ancestor's
  effective colour

### Requirement: A viewer host can focus an assembly subtree
The viewer handle SHALL let a host set a root-relative node path as the
displayed assembly root, or reset it to the published document root. Focusing
SHALL render only that subtree, fit it for viewing, and leave every visibility
state unchanged.

#### Scenario: A host focuses a subassembly
- **WHEN** a host sets a valid nested node path as the displayed root
- **THEN** the viewer shows and frames only that subtree while retaining every
  existing hidden or shown path

#### Scenario: A host restores the document root
- **WHEN** a host resets the displayed root
- **THEN** the viewer shows the published root subject to its existing
  visibility state

### Requirement: A viewer host can hide and show an assembly subtree
The viewer handle SHALL let a host hide or show a valid root-relative node
path. Hiding SHALL affect that node and all descendants without unloading their
geometry or changing the displayed root. Showing SHALL restore the subtree
unless an ancestor remains hidden.

#### Scenario: A host hides a part
- **WHEN** a host hides a model-bearing node
- **THEN** that node's geometry and all descendant geometry are absent from
  the viewer while the rest of the focused subtree remains rendered

#### Scenario: A host restores a hidden child under a hidden parent
- **WHEN** a host shows a child whose ancestor remains hidden
- **THEN** the child remains absent until its hidden ancestor is shown

### Requirement: Assembly-navigation state reconciles with viewer updates
The viewer SHALL retain focus and visibility state across targeted updates for
paths the updated document still contains. It SHALL discard a missing hidden
path and reset a missing focused root to the document root without preventing
later updates or damaging retained geometry.

#### Scenario: A targeted update retains state
- **WHEN** `manifestChanged()` updates a model while retaining its focused and
  hidden paths
- **THEN** the focused subtree and hidden descendants remain in effect without
  refetching unchanged geometry

#### Scenario: A targeted update removes the focused node
- **WHEN** `manifestChanged()` removes the focused node
- **THEN** the viewer returns to the document root, discards unavailable state,
  and remains usable for subsequent updates
