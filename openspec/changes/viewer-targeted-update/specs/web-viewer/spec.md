## MODIFIED Requirements

### Requirement: The development page renders through the shared viewer package

The browser SHALL mount the shared viewer package against the served snapshot;
it SHALL NOT carry its own tree walk, operation composition, expression
evaluation, or animation clock. It SHALL refresh a changed model through the
package's targeted document update rather than rebuilding its tree, so unchanged
geometry is neither refetched nor re-uploaded. It SHALL preserve the maker's
viewpoint through the mount handle on reload, name the tab after the model, and
show build errors or the missing-bundle remedy in its error pane.

#### Scenario: A built project is opened in the development loop

- **WHEN** a maker opens a completed project
- **THEN** it is coloured, lit, framed, and has shared animation controls when
  animated

#### Scenario: An edit refreshes without a teardown

- **WHEN** a rebuild completes and the reload channel signals the browser
- **THEN** the page updates the model through the targeted document update,
  keeping its canvas, camera and unchanged meshes
