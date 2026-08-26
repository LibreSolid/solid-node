# viewer-assembly-navigation delta: layered driver controls

## ADDED Requirements

### Requirement: A maker moves focus from within the widget

When the driver chrome is presented, the viewer SHALL offer an
affordance that shows the focused path from the document root and lets
the maker move focus without host code: descending into a subassembly
and returning to any ancestor, including the root. Through it the
maker SHALL be able to reach every layer that declares drivers or
instructions; a child with none declared anywhere beneath it need not
be offered. The affordance SHALL drive the same focus state as the
host focus API and SHALL reflect focus changes the host makes, so the
two never disagree about what is focused.

#### Scenario: A maker descends to an axis and comes back

- **WHEN** the maker uses the affordance to focus `x_axis` on a
  two-axis machine and then selects the root in it
- **THEN** the viewer focuses the subassembly exactly as a host
  `setRoot(['x_axis'])` would — same visibility, same re-scoped
  controls — and returns the same way

#### Scenario: The affordance offers only paths that lead to controls

- **WHEN** the focused layer has one child subtree declaring drivers
  and another declaring nothing anywhere beneath
- **THEN** the declaring child is offered for descent and the empty
  one need not be

#### Scenario: A host focus change is reflected

- **WHEN** the host calls `setRoot` while the driver chrome is shown
- **THEN** the affordance shows the new focused path and the controls
  re-scope to it
